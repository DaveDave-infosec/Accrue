# Accrue

**Consensus-settled contributor compensation for open-source teams.**

A project funds a pool. At the end of each epoch, an Intelligent Contract fetches
the repository's merged pull requests itself, and independent GenLayer validators
divide the pool among approved contributors under a rubric that was locked before
any work was judged. No project manager sets anyone's share.

> Contribution becomes compensation.

**Live app:** _(deployment URL)_
**Network:** GenLayer Studio Network (chain 61999)

| Contract | Address |
| --- | --- |
| Assessor | `0x66333721fF17e2c74ac070132FBC16cd55cA57B2` |
| Vault | `0x2269F5F141dC87e378975155b9167e13539Ef4fb` |

---

## The trust model

Accrue has no privileged operator. That is the whole point, so here is the proof
rather than the claim.

**A wallet with no role in the system finalized a real payout epoch:**
[`0xfb946037...1c54c76c`](https://explorer-studio.genlayer.com/tx/0xfb94603758b2797907897d11059232991b0fdc366562da92fdc9e3371c54c76c)

That wallet is not a contributor, not the agreement creator, and has no verified
identity. It settled an epoch and finalized it, on the contracts linked above.

Concretely:

- **Nobody sets a share.** Allocations come only from validator consensus over
  fetched evidence. There is no owner function that writes an allocation, and no
  relay that a human passes a verdict through.
- **Settlement is permissionless.** Anyone may settle an epoch and anyone may
  finalize it. The caller never supplies the verdict or the evidence.
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

- `settle_epoch(agreement_id, epoch_id)` builds the evidence URL from the
  agreement's own locked `repo_owner` and `repo_name`, and reads the rubric, pool,
  and cap from locked storage. The repository is never a parameter, so a caller
  cannot point settlement at a different repo.
- Attribution flows only through gist-verified identities, and each of those is
  bound to the transaction sender at verification time.
- The allocation is produced by validator consensus, not supplied by the caller.
- `finalize_epoch(agreement_id, epoch_id)` reads the outcome, contributors, and
  every allocation **directly from the assessor** via `gl.get_contract_at`. It
  accepts no outcome or amount, so a relayer cannot fake the number.

The caller chooses only *which* agreement and *which* epoch to act on. Everything
that decides who is paid, and how much, is read from locked state or from
consensus, never from the transaction that triggers it.

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
   approved contributors, pool size, maximum per contributor, and a weighted
   rubric. Terms lock on creation and cannot be edited afterward.

3. **Fund the pool.** Real native GEN is deposited before settlement. Nothing is
   promised that is not already funded.

4. **Settle the epoch.** Anyone triggers it. The contract fetches the repository's
   merged pull requests, attributes each to a verified contributor, and validators
   score every contributor per rubric dimension, then divide the pool in
   proportion to their weighted scores.

5. **Finalize.** The vault reads the split straight from the assessor and records
   each contributor's share as claimable.

6. **Claim.** Each contributor pulls their own earned GEN. Unallocated funds stay
   in the pool as reserve.

---

## What makes it hold together

Two structural pieces do the heavy lifting.

**A measurable rubric is what lets validators converge.** "How valuable was
Alice's work" is unanswerably subjective. "Score implementation, review and docs,
and consistency, each from 0 to 100 in steps of 5, then combine by locked weights"
is answerable. Consensus is gated on the resulting allocation bands rather than on
exact figures, which is what keeps honest variation from fracturing agreement.

**Evidence is assembled deterministically.** Validators must reason over an
identical package or they will disagree about noise instead of substance. Pull
requests are fetched, filtered to merged only, stripped to their decisive fields,
sorted by a stable key, capped, and serialized canonically. Independent runs
produce byte-identical packages.

---

## Preserved disagreement

Every settlement records a **minority note**: the strongest good-faith case that
the split should have been different, stored on-chain beside the verdict.

From a real epoch on the live contracts:

> A reasonable alternative would score the documentation PR somewhat higher on
> consistency or review value relative to the two implementation PRs, because
> notes can support team coordination. However, the evidence does not show content
> or impact beyond the titles, so large adjustments would be speculative.

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
- Permissionless creation, settlement, and finalization by unrelated wallets.
- Byte-identical evidence packages across independent consensus runs.
- Per-dimension allocation that caps a contributor at the agreed maximum and
  redistributes the freed remainder proportionally.
- A contributor with no merged work correctly receiving zero rather than erroring.
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
- **Merged pull requests are the evidence.** Review threads, issues, and releases
  are not yet part of the assembled package.
- **Three contributors per agreement.** Allocation variance grows with contributor
  count, so the scope is deliberately tight while convergence is being proven.
- **No scheduler.** Settlement is a permissionless call after the epoch, not an
  autonomous trigger.
- **Evidence is capped.** Oversized histories return an explicit error rather than
  silently truncating someone's work out of a payout.

---

## Repository layout

```
contracts/
  accrue_assessor.py  identity, agreements, consensus settlement
  accrue_vault.py     per-agreement pools, finalize, claims
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
