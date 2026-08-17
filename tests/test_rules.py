"""
Unit tests for RulesEngine transformations
"""

import unittest
from apipatch.rules import RulesEngine, transform_pydantic_v2, transform_openai_v1, transform_stripe_payment_intents


class TestRulesEngine(unittest.TestCase):
    def test_pydantic_v2_transform(self):
        code = """from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True

def parse_user(d):
    return User.parse_obj(d)
"""
        res = RulesEngine.apply_rules(code, file_path="user.py")
        self.assertTrue(res["has_breaking_changes"])
        self.assertIn("ConfigDict", res["refactored_code"])
        self.assertIn("model_validate", res["refactored_code"])

    def test_openai_v1_transform(self):
        code = """import openai

def ask(p):
    res = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": p}])
    return res['choices'][0]['message']['content']
"""
        res = RulesEngine.apply_rules(code, file_path="ai.py")
        self.assertTrue(res["has_breaking_changes"])
        self.assertIn("client.chat.completions.create", res["refactored_code"])
        self.assertIn("res.choices[0].message.content", res["refactored_code"])

    def test_stripe_transform(self):
        code = """import stripe

def pay(token, amount):
    return stripe.Charge.create(amount=amount, source=token)
"""
        res = RulesEngine.apply_rules(code, file_path="billing.py")
        self.assertTrue(res["has_breaking_changes"])
        self.assertIn("stripe.PaymentIntent.create", res["refactored_code"])


if __name__ == "__main__":
    unittest.main()
