# Accrue
**Consensus-settled contributor compensation for open-source teams.**

A project funds a pool. At the end of each epoch, an Intelligent Contract fetches
the repository's merged pull requests itself, reads their diffs, reviews, and
commits, and independent GenLayer validators divide the pool among approved
contributors under a rubric that was locked before any work was judged. No
project manager sets anyone's share.

> Contribution becomes compensation.

**Live app:** _(deployment URL)_
**Network:** GenLayer Studio Network (chain 61999)

| Contract | Address |
| --- | --- |
| Assessor | `0xFe1604EB2B6B09Df45AB89ac11b05a211b9E350F` |
| Vault | `0x72073670362EB5ceabAAD5Ad8213FaEFAcF8160A` |

---

## The trust model

Accrue has no privileged operator. That is the whole point, so here is the proof
rather than the claim.

**A wallet with no role in the system ran a real payout epoch to completion:**
[`0xfb946037...1c54c76c`](https://explorer-studio.genlayer.com/tx/0xfb94603758b2797907897d11059232991b0fdc366562da92fdc9e3371c54c76c)

That wallet is not a contributor, not the agreement creator, and has no verified
identity. It settled and finalized an epoch with zero authority. GenLayer
contracts are immutable, so each revision is a fresh deploy, and this receipt is
from an earlier deploy of the same permissionless design. The property is
structural, not incidental, and anyone can reproduce it on the contracts above.

Concretely:

- **Nobody sets a share.** Allocations come only from validator consensus over
  fetched evidence. There is no owner function that writes an allocation, and no
  relay that a human passes a verdict through.
- **Settlement is permissionless.** Anyone may open, collect, and finalize an
  epoch. The caller never supplies the verdict or the evidence.
- **The vault reads consensus directly.** At finalize, the vault calls the
  assessor and reads the split. No amounts are passed in by the caller.
- **Creating an agreement grants no power.** The creator locks terms up front and
  funds the pool. They cannot edit the rubric after seeing who contributed, and
  cannot influence who gets paid.
- **Contributors are self-sovereign.** Each proves their own GitHub account and
  claims their own share. Identity is derived from the transaction sender, never
  from a parameter.

**No caller-supplied verdicts.** This is worth stating plainly, because it is the
most common way a settlement contract goes wrong. Accrue's settlement functions
accept no verdict, no amount, no evidence source, and no identity from the caller.

- Settlement builds every evidence URL from the agreement's own locked
  `repo_owner` and `repo_name`, and reads the rubric, pool, and cap from locked
  storage. The repository is never a parameter, so a caller cannot point
  settlement at a different repo.
- Attribution flows only through gist-verified identities, and each of those is
  bound to the transaction sender at verification time.
- The allocation is produced by validator consensus, not supplied by the caller.
- `finalize_epoch(agreement_id, epoch_id)` reads the outcome, contributors, and
  every allocation **directly from the assessor** via `gl.get_contract_at`. It
  accepts no outcome or amount, so a relayer cannot fake the number.

The caller chooses only *which* agreement and *which* epoch to act on. Everything
that decides who is paid, and how much, is read from locked state or from
consensus, never from the transaction that triggers it.

**Records are write-once.** A verdict is only trustworthy if what it was made
against cannot change afterward, so nothing consensus has blessed can be
overwritten.

- **Agreement terms are set once, at creation.** The repository, rubric,
  contributors, pool, and cap are written only inside `create_agreement` and have
  no setter anywhere else. They cannot be edited after work is judged.
- **A new agreement cannot clobber an old one.** Each is stored under a fresh
  auto-incremented id. The caller never supplies an id, so no existing agreement
  can be targeted and overwritten.
- **Opened settlements freeze their scope.** `open_settlement` asserts the epoch
  is not already opened, records the exact set of in-window pull requests, and
  cannot be reopened to add or drop work later.
- **Settled epochs are final.** `finalize_settlement` asserts the epoch is not
  already settled before writing anything, so an allocation cannot be re-run or
  replaced.
- **Finalization happens once.** `finalize_epoch` asserts the epoch is not already
  finalized, so no share is ever double-credited.
- **Paid work stays paid.** A pull request counted in one epoch is permanently
  marked and cannot re-enter a later settlement.

**Work cannot be consumed prematurely.** The epoch is bounded by a window that is
frozen when settlement opens, and payouts are gated by a challenge period.

- **The window is load-bearing.** Only pull requests merged inside the frozen
  `[start, end)` window are eligible. Work merged after the boundary is excluded,
  and the frozen set is auditable before any allocation runs.
- **A challenge window guards the funds.** When an epoch is finalized, the
  assessor stamps it with the finalize time and the agreement's challenge length.
  The vault refuses to release funds until that window has fully elapsed, so a
  disputed split is visible but unspendable until the period passes.

---

## Why this needs GenLayer

The question Accrue answers is genuinely contested: *how much was each person's
contribution worth?* Reasonable people disagree, and raw commit counts cannot
settle it. A contributor who wrote two careful implementation PRs and one who
wrote a documentation file are not equivalent, and no deterministic formula
resolves that fairly.

So the judgment has to be made by something that can reason, and the money must
not depend on any single reasoner being honest. That is exactly what GenLayer
provides: multiple validators independently assess the same evidence and must
converge before value moves.

Remove GenLayer and one backend, or one manager, has unilateral payroll authority
over everyone. The consensus is not decorative here, it *is* the allocation.

---

## How it works

1. **Verify identity.** A contributor publishes a one-time code in a public gist
   under their own GitHub account. The contract fetches that page itself and
   confirms it by consensus. A gist under a different account is rejected, so
   nobody can claim another developer's work.

2. **Lock the agreement.** Anyone can create one for any public repository:
   approved contributors, pool size, maximum per contributor, a weighted rubric,
   and a challenge window. Terms lock on creation and cannot be edited afterward.

3. **Fund the pool.** Real native GEN is deposited before settlement. Nothing is
   promised that is not already funded.

4. **Open the settlement.** Anyone triggers it. The contract fetches the merged
   pull request list, freezes the exact set merged inside the epoch window, and
   records it. Nothing outside the window can enter this epoch afterward.

5. **Collect the evidence.** Anyone runs the collection, in small batches. For
   each frozen pull request the contract fetches its files, reviews, and commits,
   and reduces them to a canonical, padding-resistant feature record. Batching
   keeps each transaction within the host's request limits, and finalize stays
   blocked until every pull request in the set has been collected.

6. **Finalize the settlement.** Validators score every contributor per rubric
   dimension over the collected evidence, then divide the pool in proportion to
   their weighted scores. The epoch is stamped with its finalize time and
   challenge window.

7. **Release after the challenge window.** The vault reads the split straight from
   the assessor and records each contributor's share as claimable, but only once
   the challenge window has elapsed. Inside the window it refuses.

8. **Claim.** Each contributor pulls their own earned GEN. Unallocated funds stay
   in the pool as reserve.

---

## What makes it hold together

Two structural pieces do the heavy lifting.

**A measurable rubric is what lets validators converge.** "How valuable was
Alice's work" is unanswerably subjective. "Score substance, breadth, review, and
volume, each from 0 to 100 in steps of 5, then combine by locked weights" is
answerable. Consensus is gated on the resulting allocation bands rather than on
exact figures, which is what keeps honest variation from fracturing agreement.

**Evidence is assembled deterministically, and it is deep.** Validators must
reason over an identical package or they will disagree about noise instead of
substance. For each merged pull request the contract fetches the file diffs,
review approvals, and commit messages, then reduces them to canonical integers
and sorted sets: a size-weighted footprint with lock and generated files
discounted, the breadth of meaningful files touched, distinct reviewer
approvals, and commit substance. Everything is stripped to decisive fields,
sorted by a stable key, capped, and serialized canonically, so independent runs
produce byte-identical packages. Because the host rate-limits bursts of requests,
this deep fetch runs in small batches across separate transactions rather than
all at once, and no money moves until the full set is assembled.

This is what lets the split reflect real work rather than a title string. In one
live epoch the allocation separated a contributor's rate-limiting implementation
from another's foundational auth stubs by their measured footprint and substance,
a distinction that is invisible from pull request titles alone.

---

## Preserved disagreement

Every settlement records a **minority note**: the strongest good-faith case that
the split should have been different, stored on-chain beside the verdict.

From a real epoch on the live contracts:

> A case could be made for the contributor behind the authentication and session
> work to receive a higher share, since that work is more central to the
> application architecture than the documentation notes and the rate limiting.

Systems that pay people usually hide disagreement behind one confident number.
When validators diverge on how to divide credit, that divergence is information,
so Accrue keeps it.

---

## Outcomes

An epoch resolves exactly one way, and several of the outcomes exist to avoid
paying out badly.

| Outcome | Meaning |
| --- | --- |
| **Allocate** | Shares approved and accrued by weighted score. |
| **Return to reserve** | No qualifying work, so the pool stays unallocated. |
| **Hold** | Evidence missing or the proposal would overpay, so the amount is locked rather than guessed. |
| **Reassign** | Work by an unverified or non-approved account earns nothing. |
| **Escalate** | Validators cannot converge, so the epoch stays unsettled. |

The safe failure mode is deliberate: **no consensus means no money moves.**

---

## Verified behavior

Each of these was exercised on the live contracts, not simulated.

- Identity verification, including rejection of a wallet presenting a valid gist
  belonging to someone else.
- Permissionless open, collect, finalize, and claim by unrelated wallets.
- Deep evidence collected in batches across separate transactions, staying within
  the host's per-transaction request limits, with finalize blocked until the full
  set is assembled.
- A frozen settlement window that excludes work merged after the boundary: the
  same repository returns a smaller pull request set under a tighter window.
- Allocation that separates contributors by measured diff size, files touched,
  reviews, and commit substance rather than by pull request titles.
- Byte-identical evidence packages across independent consensus runs.
- Per-dimension allocation that caps a contributor at the agreed maximum and
  redistributes the freed remainder proportionally.
- A contributor with no merged work correctly receiving zero rather than erroring.
- A challenge window that refuses to release funds inside the window on the exact
  assertion, then releases them once it has elapsed, both exercised live.
- Real native GEN payouts with exact conservation across funding, allocation,
  reserve, and claims.
- No double payment: work already counted in one epoch cannot be paid again in a
  later one.
- A vault refusing to finalize when the agreement's pool would not cover the
  settlement.

---

## Honest limitations

- **This is not employment payroll.** It is opt-in compensation for open-source
  contributors, not a replacement for wages, HR, or an employment agreement.
- **Public repositories only.** Private or offline work is out of scope and is not
  judged.
- **Merged pull requests are the evidence.** Their diffs, review approvals, and
  commit messages are assembled. Issues, discussion threads, and releases are not
  yet part of the package.
- **Three contributors per agreement.** Allocation variance grows with contributor
  count, so the scope is deliberately tight while convergence is being proven.
- **No scheduler.** Settlement is a permissionless sequence of calls after the
  epoch, not an autonomous trigger.
- **Evidence is capped.** Pull requests per epoch, files per request, and commits
  per request are bounded, and oversized histories are truncated at a stable
  limit rather than silently reshaping a payout.

---

## Repository layout

```
contracts/
  accrue_assessor.py  identity, agreements, three-phase consensus settlement
  accrue_vault.py     per-agreement pools, challenge-gated finalize, claims
frontend/
  src/                React + TypeScript + Vite, genlayer-js
```

## Running locally

```bash
cd frontend
npm install
npm run dev
```

A browser wallet is required, and the app will prompt to switch to GenLayer Studio
Network. Studio provides test GEN through its faucet.

---

Built on [GenLayer](https://genlayer.com), where validators reason about evidence
and reach consensus on questions no deterministic contract can settle.
