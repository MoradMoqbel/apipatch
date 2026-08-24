"""
Tests for ApiPatch Manifest Version Bumper
Verifies bumping of requirements.txt, pyproject.toml, and package.json.
"""

import json
from apipatch.manifest_bumper import ManifestBumper


def test_bump_requirements_txt_pydantic():
    old_content = "openai==0.28.0\npydantic<2.0.0\nfastapi==0.95.0\n"
    new_content, changed = ManifestBumper.bump_requirements_txt(old_content, {"pydantic", "openai"})
    assert changed is True
    assert "pydantic>=2.0.0" in new_content
    assert "openai>=1.0.0" in new_content
    assert "fastapi==0.95.0" in new_content


def test_bump_requirements_txt_no_change_when_already_modern():
    old_content = "pydantic>=2.0.0\nopenai>=1.0.0\n"
    new_content, changed = ManifestBumper.bump_requirements_txt(old_content, {"pydantic", "openai"})
    assert changed is False
    assert new_content == old_content


def test_bump_package_json():
    old_data = {
        "name": "my-app",
        "dependencies": {
            "@supabase/supabase-js": "^1.35.0",
            "express": "^4.18.0"
        }
    }
    old_json = json.dumps(old_data, indent=2)
    new_json, changed = ManifestBumper.bump_package_json(old_json, {"@supabase/supabase-js"})
    assert changed is True
    parsed = json.loads(new_json)
    assert parsed["dependencies"]["@supabase/supabase-js"] == "^2.0.0"
    assert parsed["dependencies"]["express"] == "^4.18.0"


def test_bump_pyproject_toml():
    old_content = """\
[project]
name = "demo"
dependencies = [
    "pydantic<=1.10.12",
    "requests>=2.25.0",
    "openai<1.0.0"
]
"""
    new_content, changed = ManifestBumper.bump_pyproject_toml(old_content, {"pydantic", "openai"})
    assert changed is True
    assert '"pydantic>=2.0.0"' in new_content
    assert '"openai>=1.0.0"' in new_content
    assert '"requests>=2.25.0"' in new_content
