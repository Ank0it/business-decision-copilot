"""
Unit tests for JSONParser.

Covers:
- Plain JSON parsing
- Fenced JSON with language tag
- Fenced JSON without language tag
- Empty/whitespace responses
- Invalid JSON
- Prose before/after JSON
- require_fields() behavior
"""

from __future__ import annotations

import pytest

from app.utils.parser import JSONParser, ParserError


# ==========================================================
# Plain JSON
# ==========================================================

def test_parse_plain_json():
    result = JSONParser.parse_json('{"status":"ok"}')
    assert result == {"status": "ok"}


# ==========================================================
# Fenced JSON
# ==========================================================

def test_parse_fenced_json_with_language_tag():
    response = '```json\n{"status":"ok"}\n```'
    result = JSONParser.parse_json(response)
    assert result == {"status": "ok"}


def test_parse_fenced_json_without_language_tag():
    response = '```\n{"status":"ok"}\n```'
    result = JSONParser.parse_json(response)
    assert result == {"status": "ok"}


def test_parse_fenced_json_with_extra_whitespace():
    response = '\n```json\n{"status":"ok"}\n```\n'
    result = JSONParser.parse_json(response)
    assert result == {"status": "ok"}


# ==========================================================
# Empty / whitespace responses
# ==========================================================

def test_parse_empty_response():
    with pytest.raises(ParserError, match="empty response"):
        JSONParser.parse_json("")


def test_parse_whitespace_only_response():
    with pytest.raises(ParserError, match="empty response"):
        JSONParser.parse_json("   \n\t  ")


# ==========================================================
# Invalid JSON
# ==========================================================

def test_parse_invalid_json():
    with pytest.raises(ParserError, match="Invalid JSON"):
        JSONParser.parse_json("this is not json")


def test_parse_prose_before_json():
    with pytest.raises(ParserError, match="Invalid JSON"):
        JSONParser.parse_json('Here is the result: {"status":"ok"}')


def test_parse_prose_after_json():
    with pytest.raises(ParserError, match="Invalid JSON"):
        JSONParser.parse_json('{"status":"ok"} and that is the result')


def test_parse_non_object_json():
    with pytest.raises(ParserError, match="JSON object"):
        JSONParser.parse_json('["a", "b"]')


# ==========================================================
# require_fields()
# ==========================================================

def test_require_fields_success():
    data = {"route": "rag", "reason": "test"}
    JSONParser.require_fields(data, ["route", "reason"])


def test_require_fields_missing():
    data = {"route": "rag"}
    with pytest.raises(ParserError, match="Missing required field"):
        JSONParser.require_fields(data, ["route", "reason"])


# ==========================================================
# parse_and_validate()
# ==========================================================

def test_parse_and_validate_success():
    result = JSONParser.parse_and_validate(
        response='{"route":"rag"}',
        required_fields=["route"],
    )
    assert result == {"route": "rag"}


def test_parse_and_validate_allowed_keys():
    result = JSONParser.parse_and_validate(
        response='{"a":1}',
        required_fields=["a"],
        allowed_keys=["a"],
    )
    assert result == {"a": 1}


def test_parse_and_validate_unexpected_key():
    with pytest.raises(ParserError, match="Unexpected field"):
        JSONParser.parse_and_validate(
            response='{"a":1,"b":2}',
            required_fields=["a"],
            allowed_keys=["a"],
        )
