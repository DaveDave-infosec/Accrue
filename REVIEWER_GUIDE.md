# Reviewer Guide

A step by step walkthrough of Accrue on GenLayer Studio Network (chain 61999).

**Live app:** https://accrue-genlayer.vercel.app

| Contract | Address |
| --- | --- |
| Assessor | `0x850bc9fC52d509c717Defe1Fda0214394BaD1237` |
| Vault | `0xB48dc48CFE2B1ced8624a0d24F407Dd1cdc4d1f9` |

---

## Read this first

Settlement runs in four ordered phases: **open, collect, finalize, release**.

The contract enforces that order. Calling a later phase before an earlier one
reverts on purpose, because settling an epoch that was never opened would divide
a pool over evidence that was never assembled.

If you call `finalize_settlement` directly on a fresh epoch, you will get:

AssertionError: epoch not opened, run open_settlement then collect_batch for this epoch first


That is the guard working, not a failure. The app now walks you through the
phases in order, so the recommended path is the app rather than direct calls.

Epoch windows are **derived by the contract**, not supplied by the caller. Epoch
N covers `[created_at + N * epoch_length, created_at + (N+1) * epoch_length)`.
An epoch cannot be opened until its window has ended.

---

## Fastest path: review the existing agreement

The live app already has a funded agreement with a completed settlement, so you
can inspect real on-chain results without creating anything.

1. Open https://accrue-genlayer.vercel.app
2. Click **Launch the app**.
3. Connect a browser wallet. The app will prompt to switch to GenLayer Studio
   Network. Studio provides test GEN through its faucet.
4. The agreement loads automatically. You will see the Attribution Ledger, the
   locked rubric, the minority note, and the settlement panel.
5. In the settlement panel, type an epoch number that has already settled into
   the **Epoch** field. The phase pill will read **Released**, and all four steps
   will show as complete.

Nothing above sends a transaction except connecting your wallet.

---

## Full path: run a settlement end to end

### Step 1. Create an agreement

Click **New agreement** and fill in:

- **Label:** any name
- **Repository owner:** a GitHub username, for example `DaveDave-infosec`
- **Repository name:** a public repo, for example `accrue-testrepo`
- **Contributor wallets:** three distinct addresses. Box 1 is prefilled with
  your connected wallet.
- **Rubric weights:** leave the defaults, they total 100
- **Pool per epoch (GEN):** `1`
- **Max per contributor (GEN):** `0.5`
- **Epoch length (days):** `0.00347` (about 300 seconds, so epoch 0 closes in
  five minutes and you do not have to wait a day)
- **Challenge window (hours):** `0.05` (about 180 seconds)

Submit and confirm in your wallet.

Terms lock at creation. There is no setter to edit them afterward.

### Step 2. Verify a contributor identity

Only merged work by a **verified** contributor can earn a share. Without this,
settlement correctly allocates nothing.

1. In the Identity panel, type your GitHub username and click **Get code**.
2. Confirm the transaction. A one time code appears, for example
   `accrue-verify-0-7bbcac9c 0x7bbc...`
3. Go to https://gist.github.com while signed in to that same GitHub account.
4. Filename: `accrue.txt`. In the content box paste the full code line exactly.
5. Click the dropdown next to the green button and choose **Create public gist**.
   A secret gist is rejected.
6. Copy the gist URL from the address bar.
7. Paste it into field 3 in the Identity panel and click **Verify**.

The contract fetches that page itself and confirms it by consensus. A gist under
a different account is rejected, so nobody can claim another developer's work.

### Step 3. Fund the pool

In the **Fund pool** box, enter `1` and click **Fund**. Confirm in your wallet.

This sends real native GEN. The ledger footer will update to
`this agreement holds 1.000 GEN`.

Nothing is promised that is not already funded.

### Step 4. Open the settlement

Wait until the epoch window has ended. With `0.00347` days, that is five minutes
after creation.

In the settlement panel, leave **Epoch** as `0` and click **Open epoch 0**.

If you click too early you will see:

epoch window has not ended yet, cannot open it early


That is the premature guard. Wait a little longer and click again.

On success the panel shows the derived window and how many pull requests were
frozen, for example `window 2026-09-29T06:37:49Z to 2026-09-29T06:42:49Z`.

### Step 5. Collect the evidence

Click **Collect batch**. Repeat until the counter reads `n/n`.

Each batch fetches up to three pull requests' diffs, reviews, and commits, and
reduces them to a canonical feature record. Batching keeps each transaction
within the host's request limits.

If a fetch fails transiently, the batch stops without marking that pull request
collected. Click again in a moment.

### Step 6. Finalize the settlement

Click **Finalize settlement**.

Validators score each contributor per rubric dimension over the collected
evidence, then divide the pool in proportion to their weighted scores. The epoch
is stamped with its finalize time and challenge window.

### Step 7. Release the funds

Click **Release funds**.

The vault reads the split directly from the assessor and records each share as
claimable. It refuses while the challenge window is still running:

challenge window has not elapsed yet, funds cannot be released


Wait for the window to pass and click again.

### Step 8. Claim

Each contributor connects their own wallet and clicks the **Claim** button.
Identity comes from the transaction sender, never from a parameter.

---

## Expected outcomes

An epoch resolves exactly one way.

| Outcome | Meaning |
| --- | --- |
| **Allocate** | Shares approved and accrued by weighted score. |
| **Return to reserve** | No qualifying work in the window, so the pool stays unallocated. |
| **Hold** | Evidence missing or the proposal would overpay, so the amount is locked rather than guessed. |

**Return to reserve is a valid result, not an error.** If you use a short epoch
length today against a repository whose pull requests were merged weeks ago, no
work falls inside the derived window, so `collect` shows `0/0` and the pool
returns to reserve with exact conservation. To see a real payout, use a
repository with pull requests merged inside the epoch window you are settling.

---

## Guard messages you may see

These are deliberate refusals, each with a reason.

| Message | Why |
| --- | --- |
| `epoch window has not ended yet, cannot open it early` | Work cannot be consumed before its window closes. |
| `epoch not opened, run open_settlement for this epoch first` | Phases must run in order. |
| `epoch already opened` / `epoch already settled` | Records are write once. |
| `not all PRs collected yet, run collect_batch until done` | No money moves on partial evidence. |
| `challenge window has not elapsed yet` | A disputed split stays visible but unspendable. |
| `agreement pool underfunded for this settlement` | The vault will not pay what was not funded. |
| `repository has more pull requests than one settlement can safely page` | Pagination fails closed rather than omitting work. |

---

## Running the tests

```bash
pip install "genlayer-test[sim]" pytest
python -m pytest tests/ -q
```

The suite runs the real contract in a local GenVM with no network, covering
premature, selective, and future epoch opening, occupied epoch identifiers,
multi page pagination, and the fail closed policy checks.

---

## Running the frontend locally

```bash
cd frontend
npm install
npm run dev
```

A browser wallet is required, and the app will prompt to switch to GenLayer
Studio Network.
