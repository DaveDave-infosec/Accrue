"""
Accrue assessor guard tests (GenLayer, run with gltest).

These cover the follow-up review's named cases at the contract's validation
layer. Each guard below fires BEFORE any GitHub access, so the create-time and
premature/selective/reused-index cases are deterministic and need no network.
The one case that reaches a real fetch (reusing an already-opened epoch) uses a
one-second epoch so the derived window has closed by the time we open it.

Run against a configured GenLayer network:

    gltest                # if gltest is configured for your project
    # or
    pytest tests/test_assessor_guards.py

The contract is loaded directly from its source path, so no artifact build step
is required.
"""

from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded, tx_execution_failed

ASSESSOR = "contracts/accrue_assessor.py"

WALLET_A = "0x7bbcac9c77aabc2aca19cd34f944fbc015f06a54"
WALLET_B = "0x4fb1e8d04735e104a25c2235e29ee2acc045fbe1"
WALLET_C = "0x1b0c5244dd571b9d9db5e1b8ca9e862ce9bf71d3"


def _agreement_args(
    owner="DaveDave-infosec",
    repo="accrue-testrepo",
    epoch_len=604800,          # 7 days
    challenge=60,
    rubric='{"implementation":60,"review_docs":25,"consistency":15}',
    eligibility='{"min_merged_prs":1}',
    reserve="return_to_reserve",
):
    return [
        "guard test", owner, repo,
        WALLET_A, WALLET_B, WALLET_C,
        rubric, eligibility,
        epoch_len, 1000, 500, challenge, reserve,
    ]


def _deploy():
    factory = get_contract_factory(contract_file_path=ASSESSOR)
    return factory.deploy(args=[])


# ---- stored-policy fail-closed (create-time, no fetch) ----

def test_create_rejects_unsupported_reserve_rule():
    c = _deploy()
    r = c.create_agreement(args=_agreement_args(reserve="pay_the_creator")).transact()
    assert tx_execution_failed(r)


def test_create_rejects_unknown_eligibility_key():
    c = _deploy()
    r = c.create_agreement(args=_agreement_args(eligibility='{"min_stars":10}')).transact()
    assert tx_execution_failed(r)


def test_create_rejects_zero_epoch_length():
    c = _deploy()
    r = c.create_agreement(args=_agreement_args(epoch_len=0)).transact()
    assert tx_execution_failed(r)


def test_create_accepts_valid_policies():
    c = _deploy()
    r = c.create_agreement(args=_agreement_args()).transact()
    assert tx_execution_succeeded(r)


# ---- selective / invalid epoch opening (no fetch) ----

def test_open_rejects_negative_epoch_index():
    c = _deploy()
    assert tx_execution_succeeded(c.create_agreement(args=_agreement_args()).transact())
    r = c.open_settlement(args=["1", "-1"]).transact()
    assert tx_execution_failed(r)


def test_open_rejects_nonexistent_agreement():
    c = _deploy()
    r = c.open_settlement(args=["999", "0"]).transact()
    assert tx_execution_failed(r)


# ---- premature opening (guard is before the fetch, no network) ----

def test_open_rejects_current_epoch_not_ended():
    c = _deploy()
    assert tx_execution_succeeded(c.create_agreement(args=_agreement_args(epoch_len=604800)).transact())
    r = c.open_settlement(args=["1", "0"]).transact()
    assert tx_execution_failed(r)


def test_open_rejects_future_epoch():
    c = _deploy()
    assert tx_execution_succeeded(c.create_agreement(args=_agreement_args(epoch_len=604800)).transact())
    r = c.open_settlement(args=["1", "5"]).transact()
    assert tx_execution_failed(r)


# ---- occupied / reused epoch identifier (reaches a real fetch) ----

def test_open_rejects_reused_epoch_identifier():
    import time
    c = _deploy()
    assert tx_execution_succeeded(c.create_agreement(args=_agreement_args(epoch_len=1)).transact())
    time.sleep(3)
    first = c.open_settlement(args=["1", "0"]).transact()
    assert tx_execution_succeeded(first)
    second = c.open_settlement(args=["1", "0"]).transact()
    assert tx_execution_failed(second)
