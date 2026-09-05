import pytest
from apipatch.validator import CodeValidator, ValidationResult
from apipatch.engine import shield_unaffected_functions, node_references_libraries
import ast


class TestStringFormattingGuard:
    def test_valid_logger_formatting(self):
        code = """
import logging
logger = logging.getLogger(__name__)

def log_data(items, size):
    logger.info("Loaded %d items with size %f", len(items), size)
    logger.error("Failed with code %s: %s", 500, "Internal error")
    logger.debug("Simple static message")
    logger.warning("Single specifier: %s", "warning message")
"""
        res = CodeValidator.validate_string_formatting_integrity(code)
        assert res.is_valid is True

    def test_missing_logger_argument_rejected(self):
        # Reproduces the FlyingFathead TelegramBot issue where max_content_size was dropped
        broken_code = """
import logging
logger = logging.getLogger(__name__)

def dump_page_content(page_content, max_content_size):
    logger.info("Limiting page content to %d characters.")
    return page_content[:max_content_size]
"""
        res = CodeValidator.validate_string_formatting_integrity(broken_code)
        assert res.is_valid is False
        assert "format string expects 1 argument(s) (%d) but only 0 were provided" in res.error_message
        assert res.error_line == 6

    def test_missing_error_argument_rejected(self):
        broken_code = """
import logging
logger = logging.getLogger(__name__)

def handle_error(code, msg):
    logger.error("Error %s: %s", code)
"""
        res = CodeValidator.validate_string_formatting_integrity(broken_code)
        assert res.is_valid is False
        assert "format string expects 2 argument(s)" in res.error_message

    def test_modulo_operator_mismatch(self):
        broken_code = """
def format_item(name, age):
    return "User: %s, Age: %d" % (name,)
"""
        res = CodeValidator.validate_string_formatting_integrity(broken_code)
        assert res.is_valid is False
        assert "format string expects 2 argument(s)" in res.error_message


class TestSyntaxWarningGuard:
    def test_clean_raw_regex_passes(self):
        orig = 'text = "hello"'
        ref = 'import re\ntext = re.sub(r"\\.", "", "hello.world")'
        res = CodeValidator.validate_syntax_warnings(orig, ref)
        assert res.is_valid is True

    def test_introduced_syntax_warning_rejected(self):
        orig = 'text = "hello"'
        # String with invalid escape sequence '\.' without raw string 'r' prefix
        ref = 'import re\ntext = re.sub("\\.", "", "hello.world")'
        res = CodeValidator.validate_syntax_warnings(orig, ref)
        assert res.is_valid is False
        assert "SyntaxWarning" in res.error_message
        assert "invalid escape sequence" in res.error_message

    def test_preexisting_syntax_warning_not_penalized(self):
        # If the original legacy codebase already had the warning, do not fail refactored code
        orig = 'import re\ntext = re.sub("\\.", "", "old")'
        ref = 'import re\ntext = re.sub("\\.", "", "old")\nx = 1'
        res = CodeValidator.validate_syntax_warnings(orig, ref)
        assert res.is_valid is True


class TestSurgicalFunctionShielding:
    def test_unaffected_functions_restored(self):
        original = '''import logging
import re
import openai

logger = logging.getLogger(__name__)

def dump_page(content, max_size):
    logger.info("Limiting page content to %d characters.", max_size)
    return content[:max_size]

def clean_html(text):
    return re.sub(r"<br\\s*/?>", "", text)

def run_agent():
    return openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[])
'''

        # Simulated LLM hallucination: mutated dump_page and clean_html while updating run_agent
        mutated = '''import logging
import re
from openai import OpenAI

client = OpenAI()
logger = logging.getLogger(__name__)

def dump_page(content, max_size):
    logger.info("Limiting page content to %d characters.")
    return content[:max_size]

def clean_html(text):
    return re.sub(r"<br\\s*/>", "", text)

def run_agent():
    return client.chat.completions.create(model="gpt-4o", messages=[])
'''

        shielded = shield_unaffected_functions(original, mutated, ["openai"], ".py")

        # Unaffected functions must be restored to original source
        assert 'logger.info("Limiting page content to %d characters.", max_size)' in shielded
        assert 'r"<br\\s*/?>"' in shielded

        # Affected function must remain modernized
        assert 'client.chat.completions.create(model="gpt-4o", messages=[])' in shielded

    def test_affected_functions_not_shielded(self):
        original = '''
def run_search(q):
    import elasticsearch
    es = elasticsearch.Elasticsearch()
    return es.search(index="idx", body={"query": q})
'''
        modernized = '''
def run_search(q):
    import elasticsearch
    es = elasticsearch.Elasticsearch()
    return es.search(index="idx", query={"query": q})
'''
        # Since run_search uses elasticsearch, it should NOT be restored
        shielded = shield_unaffected_functions(original, modernized, ["elasticsearch"], ".py")
        assert 'query={"query": q}' in shielded


class TestApiModernityGuard:
    def test_responses_api_downgrade_rejected(self):
        # Reproduces the slack-samples bolt-python-ai-chatbot issue
        original = '''
def generate_response(self, prompt, system_content):
    response = self.client.responses.create(
        model=self.current_model,
        input=[{"role": "developer", "content": system_content}],
        max_output_tokens=1000,
    )
    return response.output_text
'''
        downgraded = '''
def generate_response(self, prompt, system_content):
    response = self.client.chat.completions.create(
        model=self.current_model,
        messages=[{"role": "system", "content": system_content}],
        max_tokens=1000,
    )
    return response.choices[0].message.content
'''
        res = CodeValidator.validate(original, downgraded)
        assert res.is_valid is False
        assert "API Downgrade detected" in res.error_message
        assert "Responses API" in res.error_message

    def test_developer_role_downgrade_rejected(self):
        original = 'input = [{"role": "developer", "content": "instructions"}]'
        downgraded = 'input = [{"role": "system", "content": "instructions"}]'
        res = CodeValidator.validate(original, downgraded)
        assert res.is_valid is False
        assert "developer" in res.error_message

    def test_max_output_tokens_downgrade_rejected(self):
        original = 'create_params = {"max_output_tokens": 500}'
        downgraded = 'create_params = {"max_tokens": 500}'
        res = CodeValidator.validate(original, downgraded)
        assert res.is_valid is False
        assert "max_output_tokens" in res.error_message

    def test_genuine_v0_to_v1_allowed(self):
        original = '''
import openai
def call():
    return openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[])
'''
        modernized = '''
from openai import OpenAI
client = OpenAI()
def call():
    return client.chat.completions.create(model="gpt-4o", messages=[])
'''
        res = CodeValidator.validate(original, modernized)
        assert res.is_valid is True
