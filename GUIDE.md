# Using Accrue

A walkthrough for running a compensation epoch on your own repository.

Everything below happens in the app. You will need a browser wallet and a public
GitHub repository with some merged pull requests.

---

## Before you start

**Connect a wallet.** Open the app and click *Connect wallet*. It will prompt you
to switch to GenLayer Studio Network. Studio has a faucet, so test GEN costs
nothing.

**Have a repository ready.** It must be public, and it needs merged pull requests
authored by the people you want to compensate. Closed-but-unmerged pull requests
are ignored.

---

## 1. Prove your GitHub account

Only work by a verified contributor earns a share, so each contributor links their
own wallet to their own GitHub account. Nobody can do this on your behalf.

In the **Identity** panel:

1. Enter your GitHub username and click *Get code*. Approve the transaction.
2. A one-time line appears, something like
   `accrue-verify-0-7bbcac9c 0x7bbc...`. Copy it.
3. Go to [gist.github.com](https://gist.github.com), signed in as that GitHub
   account. Give the file any name, paste the line as the content, and choose
   **Create public gist**. It must be public.
4. Copy the gist URL and paste it into step 3 of the panel, then click *Verify*.

The contract fetches that page itself and confirms it by consensus. Because only
you can publish under your own GitHub namespace, this proves control without
trusting anything you typed.

The panel will show a green check when it is done.

---

## 2. Create an agreement

Click *New agreement*, or *Create the first agreement* if none exist yet.

Fill in:

- **Repository owner and name.** For `github.com/acme/toolkit`, that is `acme` and
  `toolkit`.
- **Three contributor wallets.** Exactly three. Your own is pre-filled.
- **Rubric weights.** How much implementation, review and documentation, and
  consistency each count. They must total 100.
- **Pool per epoch.** How much GEN is divided each epoch.
- **Max per contributor.** A ceiling on any single share. Anything above it
  returns to reserve.
- **Epoch length** and **challenge window.**

Click *Create agreement*.

**These terms lock permanently.** You cannot change the rubric after seeing who
contributed, and creating the agreement gives you no authority over the split.
That constraint is the point.

---

## 3. Fund the pool

In the **Actions** panel, enter an amount and click *Fund pool*.

Fund at least the pool size, otherwise finalize will refuse the settlement rather
than pay out money the agreement does not hold.

The ledger footer shows what the agreement currently holds.

---

## 4. Settle an epoch

Enter any epoch identifier, `epoch-1` works, and click *Settle epoch*.

This takes longer than other actions. The contract is fetching your repository and
several validators are independently scoring every contributor against your rubric.

When it finishes, the ledger fills in:

- Each contributor's share, sized against the pool.
- The outcome, usually **Allocate**.
- How many pull requests were counted.
- The **minority note**, the strongest argument that the split should have been
  different, recorded on-chain.

Anyone can settle. The caller does not influence the result.

---

## 5. Finalize

Click *Finalize epoch* with the same identifier.

The vault reads the split directly from the assessor and records each share as
claimable. Nobody passes in amounts.

Contributor rows change from *pending finalize* to *claimable*.

---

## 6. Claim

Each contributor connects their own wallet and clicks the green claim button. It
pays whoever is connected, so you cannot claim on someone else's behalf.

Unallocated funds stay in the pool as reserve.

---

## Running more epochs

Merge more pull requests, then settle a new epoch identifier, `epoch-2` and so on.

Work already counted cannot be counted again. If a contributor was paid for a pull
request in one epoch, that same pull request will not earn them anything later, so
each epoch reflects only new work.

Settled epochs appear as chips above the ledger, and you can switch between them
to see any past split with its minority note.

---

## When things do not go as expected

**"No merged work"** next to a contributor usually means one of three things: they
have no merged pull requests in this window, their work was already counted in an
earlier epoch, or they have not verified their GitHub account yet.

**"Agreement pool underfunded for this settlement"** means the allocation is larger
than what the agreement holds. Fund more, then finalize again. This is the vault
refusing to promise money it does not have.

**"Epoch already settled"** means that identifier has been used. Pick another.

**A node interruption message** means Studio hiccuped rather than the contract
rejecting anything. Refresh and check whether it actually went through before
retrying.

---

## What the app cannot do

You cannot edit an agreement after creating it, cancel a settled epoch, or claim
on another contributor's behalf. Those are not missing features. They are the
constraints that make the result worth trusting.
