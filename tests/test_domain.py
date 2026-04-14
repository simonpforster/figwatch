"""Tests for figwatch.domain — trigger matching and config loading."""

import json
import os
import pytest

from figwatch.domain import (
    DEFAULT_TRIGGERS,
    WorkItem,
    load_trigger_config,
    match_trigger,
)


# ── match_trigger ─────────────────────────────────────────────────────

TRIGGERS = [
    {"trigger": "@ux", "skill": "builtin:ux"},
    {"trigger": "@tone", "skill": "builtin:tone"},
]


def test_match_trigger_exact():
    result = match_trigger("@ux", TRIGGERS)
    assert result["trigger"] == "@ux"
    assert result["skill"] == "builtin:ux"
    assert result["extra"] == ""


def test_match_trigger_with_extra():
    result = match_trigger("@ux please check the nav", TRIGGERS)
    assert result["trigger"] == "@ux"
    assert result["extra"] == "please check the nav"


def test_match_trigger_mid_message():
    result = match_trigger("hey can you @tone this screen", TRIGGERS)
    assert result["trigger"] == "@tone"


def test_match_trigger_case_insensitive():
    result = match_trigger("@UX audit this", TRIGGERS)
    assert result is not None
    assert result["trigger"] == "@ux"


def test_match_trigger_no_match():
    assert match_trigger("just a regular comment", TRIGGERS) is None


def test_match_trigger_empty_message():
    assert match_trigger("", TRIGGERS) is None


def test_match_trigger_first_wins():
    # @ux appears before @tone in config — should match @ux
    result = match_trigger("@ux @tone", TRIGGERS)
    assert result["trigger"] == "@ux"


# ── load_trigger_config ───────────────────────────────────────────────

def test_load_trigger_config_defaults_when_no_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    config = load_trigger_config()
    assert config == DEFAULT_TRIGGERS


def test_load_trigger_config_from_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    figwatch_dir = tmp_path / ".figwatch"
    figwatch_dir.mkdir()
    config_data = {"triggers": [{"trigger": "@a11y", "skill": "/skills/a11y.md"}]}
    (figwatch_dir / "config.json").write_text(json.dumps(config_data))

    config = load_trigger_config()
    assert any(t["trigger"] == "@a11y" for t in config)


def test_load_trigger_config_discovers_custom_skills(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    custom_dir = tmp_path / "custom-skills"
    custom_dir.mkdir()
    (custom_dir / "brand.md").write_text("# Brand skill")

    config = load_trigger_config()
    assert any(t["trigger"] == "@brand" for t in config)


def test_load_trigger_config_custom_skill_subdir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / "custom-skills" / "motion"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.md").write_text("# Motion skill")

    config = load_trigger_config()
    assert any(t["trigger"] == "@motion" for t in config)


# ── WorkItem ──────────────────────────────────────────────────────────

def test_work_item_is_namedtuple():
    item = WorkItem(
        file_key="abc", comment_id="1", reply_to_id="1", node_id="2:3",
        trigger="@ux", skill_path="builtin:ux", user_handle="alice", extra="",
        locale="uk", model="gemini-flash", reply_lang="en", pat="figd_x",
        claude_path="api", on_status=None,
    )
    assert item.file_key == "abc"
    assert item.trigger == "@ux"


def test_work_item_replace():
    item = WorkItem(
        file_key="abc", comment_id="1", reply_to_id="1", node_id="2:3",
        trigger="@ux", skill_path="builtin:ux", user_handle="alice", extra="",
        locale=None, model=None, reply_lang=None, pat="figd_x",
        claude_path=None, on_status=None,
    )
    filled = item._replace(locale="uk", model="gemini-flash", reply_lang="en", claude_path="api")
    assert filled.locale == "uk"
    assert filled.model == "gemini-flash"
