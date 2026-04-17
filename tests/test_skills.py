"""Tests for figwatch.skills — prompt building and skill discovery."""

import json
import os
import pytest

from figwatch.domain import WorkItem
from figwatch.skills import _build_prompt, find_skills, _resolve_builtin_skill


# ── Helpers ───────────────────────────────────────────────────────────

def _make_item(**kwargs):
    defaults = dict(
        file_key="abc", comment_id="1", reply_to_id="1", node_id="2:3",
        trigger="@ux", skill_path="builtin:ux", user_handle="alice", extra="",
        locale="uk", model="gemini-flash", reply_lang="en", pat="figd_x",
        claude_path="api", on_status=None,
    )
    defaults.update(kwargs)
    return WorkItem(**defaults)


SKILL_CONTENT = "# UX Skill\nEvaluate usability."
REFS = ""
TREE_DATA = {"name": "Home Screen", "type": "FRAME", "children": []}
FRAME_NAME = "Home Screen"


# ── _build_prompt ─────────────────────────────────────────────────────

def test_build_prompt_contains_skill_content():
    item = _make_item()
    data = {"screenshot": "/tmp/shot.png", "node_tree": "/tmp/tree.json"}
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, TREE_DATA, FRAME_NAME, inline_files=True)
    assert SKILL_CONTENT in prompt


def test_build_prompt_inline_screenshot():
    item = _make_item()
    data = {"screenshot": "/tmp/shot.png"}
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, TREE_DATA, FRAME_NAME, inline_files=True)
    assert "attached as image" in prompt
    assert "/tmp/shot.png" not in prompt


def test_build_prompt_file_path_screenshot():
    item = _make_item()
    data = {"screenshot": "/tmp/shot.png"}
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, TREE_DATA, FRAME_NAME, inline_files=False)
    assert "/tmp/shot.png" in prompt
    assert "attached as image" not in prompt


def test_build_prompt_inline_tree_data_embedded():
    item = _make_item()
    data = {"node_tree": "/tmp/tree.json"}
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, TREE_DATA, FRAME_NAME, inline_files=True)
    assert "Home Screen" in prompt  # tree_data name embedded


def test_build_prompt_file_path_tree_passes_path():
    item = _make_item()
    data = {"node_tree": "/tmp/tree.json"}
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, TREE_DATA, FRAME_NAME, inline_files=False)
    assert "/tmp/tree.json" in prompt


def test_build_prompt_contains_frame_name():
    item = _make_item()
    data = {}
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, None, "Checkout Flow", inline_files=True)
    assert "Checkout Flow" in prompt


def test_build_prompt_contains_trigger():
    item = _make_item(trigger="@tone")
    data = {}
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, None, FRAME_NAME, inline_files=True)
    assert "@tone" in prompt


def test_build_prompt_includes_extra_context():
    item = _make_item(extra="focus on the button colour")
    data = {}
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, None, FRAME_NAME, inline_files=True)
    assert "focus on the button colour" in prompt


def test_build_prompt_no_extra_context_when_empty():
    item = _make_item(extra="")
    data = {}
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, None, FRAME_NAME, inline_files=True)
    assert "Additional context" not in prompt


def test_build_prompt_chinese_instruction():
    item = _make_item(reply_lang="cn")
    data = {}
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, None, FRAME_NAME, inline_files=True)
    assert "Simplified Chinese" in prompt


def test_build_prompt_no_chinese_instruction_by_default():
    item = _make_item(reply_lang="en")
    data = {}
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, None, FRAME_NAME, inline_files=True)
    assert "Simplified Chinese" not in prompt


def test_build_prompt_tree_truncated_when_large(monkeypatch):
    import figwatch.skills as skills_mod
    monkeypatch.setattr(skills_mod, "_NODE_TREE_CHAR_LIMIT", 10)
    item = _make_item()
    big_tree = {"name": "Frame", "data": "x" * 100}
    data = {"node_tree": "/tmp/tree.json"}
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, big_tree, FRAME_NAME, inline_files=True)
    assert "truncated" in prompt


def test_build_prompt_text_nodes_listed():
    item = _make_item()
    data = {
        "text_nodes": [
            {"name": "Heading", "text": "Welcome back"},
            {"name": "Body", "text": "Here is your dashboard"},
        ]
    }
    prompt = _build_prompt(item, SKILL_CONTENT, REFS, data, None, FRAME_NAME, inline_files=True)
    assert "Welcome back" in prompt
    assert "Here is your dashboard" in prompt


# ── find_skills ───────────────────────────────────────────────────────

def test_find_skills_returns_list():
    skills = find_skills()
    assert isinstance(skills, list)


def test_find_skills_bundled_included():
    skills = find_skills()
    names = {s["name"] for s in skills}
    # bundled skills directory should have at least ux and tone
    assert "ux" in names or "tone" in names


def test_find_skills_builtin_flag():
    skills = find_skills()
    builtins = [s for s in skills if s["builtin"]]
    assert len(builtins) > 0


# ── _resolve_builtin_skill ────────────────────────────────────────────

def test_resolve_builtin_skill_ux():
    path = _resolve_builtin_skill("builtin:ux")
    assert path is not None
    assert os.path.exists(path)
    assert path.endswith(".md")


def test_resolve_builtin_skill_tone():
    path = _resolve_builtin_skill("builtin:tone")
    assert path is not None
    assert os.path.exists(path)


def test_resolve_builtin_skill_missing():
    path = _resolve_builtin_skill("builtin:nonexistent")
    assert path is None
