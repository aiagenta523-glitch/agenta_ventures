"""
prompts.py のユニットテスト
"""

from core.prompts import SYSTEM_PROMPT


def test_system_prompt_is_string():
    """SYSTEM_PROMPT が文字列であることを確認"""
    assert isinstance(SYSTEM_PROMPT, str)


def test_system_prompt_not_empty():
    """SYSTEM_PROMPT が空でないことを確認"""
    assert len(SYSTEM_PROMPT.strip()) > 0


def test_system_prompt_contains_key_domains():
    """SYSTEM_PROMPT がキャリア相談の主要領域を含むことを確認"""
    assert "転職" in SYSTEM_PROMPT
    assert "スキルアップ" in SYSTEM_PROMPT
    assert "年収" in SYSTEM_PROMPT
    assert "フリーランス" in SYSTEM_PROMPT


def test_system_prompt_contains_principles():
    """SYSTEM_PROMPT が回答の原則を含むことを確認"""
    assert "具体的" in SYSTEM_PROMPT
    assert "エンジニア" in SYSTEM_PROMPT


def test_system_prompt_contains_restrictions():
    """SYSTEM_PROMPT が禁止事項を含むことを確認"""
    assert "禁止" in SYSTEM_PROMPT
