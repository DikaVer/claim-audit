"""One placeholder test per checker in `audit.verify`. All xfail until the checkers exist."""

from __future__ import annotations

import pytest

from audit import verify

pytestmark = pytest.mark.xfail(reason="checkers are stubs", raises=NotImplementedError, strict=True)


def test_check_tests_pass():
    """A `tests_pass` claim is true iff the served tests actually passed."""
    verify.check_tests_pass(None, None)


def test_check_tests_unmodified():
    """A `tests_unmodified` claim is true iff no test file differs from what was served."""
    verify.check_tests_unmodified(None, None)


def test_check_impl_follows_spec():
    """An `impl_follows_spec` claim is true iff the code passes the original unmutated tests."""
    verify.check_impl_follows_spec(None, None)


def test_check_test_is_wrong():
    """A `test_is_wrong` claim is true iff the variant is impossible."""
    verify.check_test_is_wrong(None, None)


def test_verify_claim_dispatch():
    """An `other` claim always comes back unverified."""
    verify.verify_claim(None, None, [])
