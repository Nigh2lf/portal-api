"""Política de senha (validators do Django)."""

from __future__ import annotations

import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def test_rejects_weak_password() -> None:
    with pytest.raises(ValidationError):
        validate_password("123456")


def test_accepts_strong_password() -> None:
    validate_password("Strong#Pass1234")
