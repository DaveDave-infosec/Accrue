"""
Accrue assessor tests, in-process (gltest direct runner, no network).

Run fully offline with `pytest`. The direct runner executes the REAL contract in
a local GenVM. Two cheatcodes do the work:

  - direct_vm.warp(<iso>)  controls the block time (see conftest.py, which makes
    warp reach the contract clock), so we place "now" before or after a derived
    epoch window.
  - direct_vm.mock_web(<regex>, ...) serves the GitHub responses the contract
    fetches, so pagination and opening run against the contract's real
    open_settlement path with no network.

Covers the follow-up review's cases against the contract itself:
  - premature / selective / future epoch opening
  - occupied (already-opened) epoch identifier
  - multi-page pagination: complete assembly, and fail-closed on overflow
  - stored eligibility and reserve policies that fail closed at creation

Setup:  pip install "genlayer-test[sim]"   then   pytest tests/test_assessor_guards.py
"""

import json
import pytest

ASSESSOR = "contracts/accrue_assessor.py"
# genvm release pinned to a tag that actually ships genvm-universal.tar.xz
# (the v0.3.0-rc* tags renamed that asset, so the runner default 404s).
SDK = "v0.2.16"

WALLET_A = "0x7bbcac9c77aabc2aca19cd34f944fbc015f06a54"
WALLET_B = "0x4fb1e8d04735e104a25c2235e29ee2acc045fbe1"
WALLET_C = "0x1b0c5244dd571b9d9db5e1b8ca9e862ce9bf71d3"

T0 = "2026-08-01T00:00:00Z"          # agreement creation time
AFTER = "2026-08-01T02:00:00Z"       # well past epoch 0's 1-hour window
IN_WINDOW_A = "2026-08-01T00:30:00Z"  # inside epoch 0
IN_WINDOW_B = "2026-08-01T00:45:00Z"  # inside epoch 0
OUT_OF_WINDOW = "2025-06-01T00:00:00Z"  # before the window

EMPTY_LIST = {"method": "GET", "status": 200, "body": "[]"}


def _create(contract, *, epoch_len=3600, eligibility='{"min_merged_prs":1}',
            reserve="return_to_reserve",
            rubric='{"implementation":60,"review_docs":25,"consistency":15}'):
    return contract.create_agreement(
        "guard test", "DaveDave-infosec", "accrue-testrepo",
        WALLET_A, WALLET_B, WALLET_C,
        rubric, eligibility,
        epoch_len, 1000, 500, 60, reserve,
    )


def _pr(number, merged_at):
    return {"number": number, "merged_at": merged_at,
            "user": {"login": "davedave-infosec"}, "title": "pr " + str(number)}


def _page(prs):
    return {"method": "GET", "status": 200, "body": json.dumps(prs)}


# ---- stored-policy fail-closed (create-time) ----

def test_create_rejects_unsupported_reserve_rule(direct_vm, direct_deploy):
    direct_vm.sender = WALLET_A
    direct_vm.warp(T0)
    c = direct_deploy(ASSESSOR, sdk_version=SDK)
    with pytest.raises(Exception):
        _create(c, reserve="pay_the_creator")


def test_create_rejects_unknown_eligibility_key(direct_vm, direct_deploy):
    direct_vm.sender = WALLET_A
    direct_vm.warp(T0)
    c = direct_deploy(ASSESSOR, sdk_version=SDK)
    with pytest.raises(Exception):
        _create(c, eligibility='{"min_stars":10}')


def test_create_rejects_zero_epoch_length(direct_vm, direct_deploy):
    direct_vm.sender = WALLET_A
    direct_vm.warp(T0)
    c = direct_deploy(ASSESSOR, sdk_version=SDK)
    with pytest.raises(Exception):
        _create(c, epoch_len=0)


def test_create_accepts_valid_policies(direct_vm, direct_deploy):
    direct_vm.sender = WALLET_A
    direct_vm.warp(T0)
    c = direct_deploy(ASSESSOR, sdk_version=SDK)
    assert str(_create(c)) == "1"


# ---- selective / invalid / premature / future epoch opening ----

def test_open_rejects_negative_epoch_index(direct_vm, direct_deploy):
    direct_vm.sender = WALLET_A
    direct_vm.warp(T0)
    c = direct_deploy(ASSESSOR, sdk_version=SDK)
    _create(c)
    with pytest.raises(Exception):
        c.open_settlement("1", "-1")


def test_open_rejects_nonexistent_agreement(direct_vm, direct_deploy):
    direct_vm.sender = WALLET_A
    direct_vm.warp(T0)
    c = direct_deploy(ASSESSOR, sdk_version=SDK)
    with pytest.raises(Exception):
        c.open_settlement("999", "0")


def test_open_rejects_current_epoch_not_ended(direct_vm, direct_deploy):
    # still at T0, epoch 0's 1-hour window has not closed.
    direct_vm.sender = WALLET_A
    direct_vm.warp(T0)
    c = direct_deploy(ASSESSOR, sdk_version=SDK)
    _create(c, epoch_len=3600)
    with pytest.raises(Exception):
        c.open_settlement("1", "0")


def test_open_rejects_future_epoch(direct_vm, direct_deploy):
    direct_vm.sender = WALLET_A
    direct_vm.warp(T0)
    c = direct_deploy(ASSESSOR, sdk_version=SDK)
    _create(c, epoch_len=3600)
    direct_vm.warp(AFTER)  # epoch 0 has closed, but epoch 5 is still in the future
    with pytest.raises(Exception):
        c.open_settlement("1", "5")


# ---- occupied (already-opened) epoch identifier ----

def test_open_rejects_reused_epoch_identifier(direct_vm, direct_deploy):
    direct_vm.sender = WALLET_A
    direct_vm.warp(T0)
    c = direct_deploy(ASSESSOR, sdk_version=SDK)
    _create(c, epoch_len=3600)
    direct_vm.mock_web(r"/pulls\?", EMPTY_LIST)  # empty list -> first open succeeds
    direct_vm.warp(AFTER)                         # epoch 0 window has closed
    first = c.open_settlement("1", "0")
    assert "OPENED" in str(first)
    with pytest.raises(Exception):               # re-opening the same index is refused
        c.open_settlement("1", "0")


# ---- multi-page pagination against the contract's real fetch path ----

def test_open_pages_multiple_pages_and_windows(direct_vm, direct_deploy):
    direct_vm.sender = WALLET_A
    direct_vm.warp(T0)
    c = direct_deploy(ASSESSOR, sdk_version=SDK)
    _create(c, epoch_len=3600)

    # Page 1 is a FULL page of 100 (forces a second fetch); 10 fall in-window.
    page1 = [_pr(i, IN_WINDOW_A if i <= 10 else OUT_OF_WINDOW) for i in range(1, 101)]
    # Page 2 is short (ends pagination); 5 fall in-window.
    page2 = [_pr(i, IN_WINDOW_B if i <= 105 else OUT_OF_WINDOW) for i in range(101, 121)]
    direct_vm.mock_web(r"&page=1$", _page(page1))
    direct_vm.mock_web(r"&page=2$", _page(page2))

    direct_vm.warp(AFTER)
    result = c.open_settlement("1", "0")
    # Both pages were fetched and assembled; only the 15 in-window PRs are frozen.
    assert "to_collect=15" in str(result)


def test_open_fails_closed_on_page_overflow(direct_vm, direct_deploy):
    direct_vm.sender = WALLET_A
    direct_vm.warp(T0)
    c = direct_deploy(ASSESSOR, sdk_version=SDK)
    _create(c, epoch_len=3600)

    # Every page returns a full 100, so the page ceiling is hit with more to come.
    full = [_pr(i, IN_WINDOW_A) for i in range(1, 101)]
    direct_vm.mock_web(r"&page=\d+$", _page(full))

    direct_vm.warp(AFTER)
    with pytest.raises(Exception):  # reverts rather than settling on partial data
        c.open_settlement("1", "0")
