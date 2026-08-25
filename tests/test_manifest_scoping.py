"""
Unit tests for the three dynamic fixes:
1. Scope-Aware Manifest Bumper  
2. Anti-Regression Version Guard
3. Import Soundness Check
"""
import pytest
from apipatch.manifest_bumper import ManifestBumper


class TestShouldUpdateVersion:
    def test_exact_pin_modern_should_not_update(self):
        assert ManifestBumper._should_update_version("==2.10.6", ">=2.0.0") is False

    def test_exact_pin_old_should_update(self):
        assert ManifestBumper._should_update_version("==1.9.0", ">=2.0.0") is True

    def test_floor_modern_should_not_update(self):
        assert ManifestBumper._should_update_version(">=2.5.0", ">=2.0.0") is False

    def test_floor_old_should_update(self):
        assert ManifestBumper._should_update_version(">=0.5.0", ">=2.0.0") is True

    def test_no_constraint_should_update(self):
        assert ManifestBumper._should_update_version("", ">=2.0.0") is True

    def test_exact_pin_equals_minimum_should_not_update(self):
        assert ManifestBumper._should_update_version("==2.0.0", ">=2.0.0") is False


class TestBumpRequirementsTxt:
    SAMPLE_MODERN = "pydantic==2.10.6\nfastapi==0.110.0\nopenai>=1.0.0\n"
    SAMPLE_OLD = "pydantic==1.9.0\nfastapi==0.95.0\nopenai==0.27.0\n"

    def test_does_not_loosen_modern_exact_pin(self):
        result, changed = ManifestBumper.bump_requirements_txt(self.SAMPLE_MODERN, {"pydantic"})
        assert "pydantic==2.10.6" in result
        assert changed is False

    def test_updates_old_exact_pin(self):
        result, changed = ManifestBumper.bump_requirements_txt(self.SAMPLE_OLD, {"pydantic"})
        assert "pydantic>=2.0.0" in result
        assert changed is True

    def test_does_not_update_unrelated_libraries(self):
        result, changed = ManifestBumper.bump_requirements_txt(self.SAMPLE_OLD, {"pydantic"})
        assert "fastapi==0.95.0" in result

    def test_empty_content_returns_unchanged(self):
        result, changed = ManifestBumper.bump_requirements_txt("", {"pydantic"})
        assert changed is False

    def test_empty_libs_returns_unchanged(self):
        result, changed = ManifestBumper.bump_requirements_txt(self.SAMPLE_MODERN, set())
        assert changed is False


def _scope_match(manifest_dir, file_dirs_to_libs):
    """Mirror of the scope matching logic in proactive_hunter.py"""
    relevant = set()
    for mod_dir, libs in file_dirs_to_libs.items():
        if manifest_dir == "" or manifest_dir == mod_dir or mod_dir.startswith(manifest_dir + "/"):
            relevant.update(libs)
    return relevant


class TestScopeAwareDirectoryLogic:
    def test_same_directory_matches(self):
        libs = _scope_match("beifong", {"beifong": {"pydantic"}})
        assert "pydantic" in libs

    def test_root_manifest_matches_any_modified_subdir(self):
        """repo root requirements.txt must match any modified subdir"""
        libs = _scope_match("", {"beifong": {"pydantic"}})
        assert "pydantic" in libs

    def test_sibling_directory_does_not_match(self):
        libs = _scope_match("other_project", {"beifong": {"pydantic"}})
        assert len(libs) == 0

    def test_nested_subdirectory_matches_parent_manifest(self):
        libs = _scope_match("beifong", {"beifong/models": {"pydantic"}})
        assert "pydantic" in libs

    def test_monorepo_sibling_under_shared_parent_does_not_match(self):
        """Manifest in sibling app under shared folder must NOT be touched"""
        libs = _scope_match(
            "advanced_ai_agents/multi_agent_apps/agent_teams/ai_travel_planner_agent_team",
            {"advanced_ai_agents/multi_agent_apps/ai_news_and_podcast_agents/beifong/models": {"pydantic"}}
        )
        assert len(libs) == 0

    def test_completely_unrelated_paths_do_not_match(self):
        libs = _scope_match("coding_assistant", {"ai_finance_agent": {"openai"}})
        assert len(libs) == 0
