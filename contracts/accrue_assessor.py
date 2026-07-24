# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json


class AccrueAssessor(gl.Contract):
    # MULTI-TENANT. Anyone can create an agreement for their own public repo.
    # Identity verification is global: a wallet-to-GitHub link is a property of
    # the person, not of one agreement. Settlement is permissionless per
    # agreement. Nobody, including a creator, can set or edit an allocation.

    # ---- global identity ----
    nonce_counter: u256
    pending_handle: TreeMap[str, str]
    pending_nonce: TreeMap[str, str]
    verified_wallet_to_handle: TreeMap[str, str]
    verified_handle_to_wallet: TreeMap[str, str]

    # ---- agreements (flat parallel TreeMaps keyed by agreement id) ----
    agreement_count: u256
    ag_exists: TreeMap[str, bool]
    ag_creator: TreeMap[str, str]
    ag_label: TreeMap[str, str]
    ag_repo_owner: TreeMap[str, str]
    ag_repo_name: TreeMap[str, str]
    ag_rubric: TreeMap[str, str]
    ag_eligibility: TreeMap[str, str]
    ag_epoch_len: TreeMap[str, u256]
    ag_pool: TreeMap[str, u256]
    ag_max_per: TreeMap[str, u256]
    ag_challenge: TreeMap[str, u256]
    ag_reserve_rule: TreeMap[str, str]
    ag_c1: TreeMap[str, str]
    ag_c2: TreeMap[str, str]
    ag_c3: TreeMap[str, str]
    ag_is_contributor: TreeMap[str, bool]      # "aid:wallet"

    # ---- per-agreement settled-epoch registry ----
    ag_epoch_count: TreeMap[str, u256]         # aid -> count
    ag_epoch_at: TreeMap[str, str]             # "aid:index" -> epoch_id

    # ---- settlement records ----
    epoch_settled: TreeMap[str, bool]          # "aid:epoch"
    epoch_outcome: TreeMap[str, str]
    epoch_reasoning: TreeMap[str, str]
    epoch_minority: TreeMap[str, str]
    epoch_reserve: TreeMap[str, u256]
    epoch_pr_count: TreeMap[str, u256]
    alloc_amount: TreeMap[str, u256]           # "aid:epoch:wallet"
    counted_pr: TreeMap[str, bool]             # "aid:prnumber"

    def __init__(self):
        self.nonce_counter = u256(0)
        self.agreement_count = u256(0)

    # ---------- global identity ----------
    @gl.public.write
    def request_verification(self, github_handle: str) -> str:
        assert github_handle.strip() != "", "handle required"
        sender = str(gl.message.sender_address).lower()
        n = int(self.nonce_counter)
        self.nonce_counter = u256(n + 1)
        nonce = "accrue-verify-" + str(n) + "-" + sender[2:10]
        self.pending_handle[sender] = github_handle
        self.pending_nonce[sender] = nonce
        return nonce

    @gl.public.write
    def confirm_verification(self, gist_url: str) -> str:
        sender = str(gl.message.sender_address).lower()
        assert sender in self.pending_handle, "no pending verification for this wallet"
        handle = self.pending_handle[sender]
        nonce = self.pending_nonce[sender]

        expected_prefix = ("https://gist.github.com/" + handle + "/").lower()
        assert gist_url.lower().startswith(expected_prefix), "gist URL must be under the claimed GitHub handle"

        url_local = gist_url
        nonce_local = nonce
        wallet_local = sender

        def fetch_and_check() -> str:
            try:
                content = gl.nondet.web.render(url_local, mode="text")
            except Exception:
                return "FETCH_FAILED"
            if content is None:
                return "FETCH_FAILED"
            text = str(content).lower()
            if nonce_local in text and wallet_local in text:
                return "MATCH"
            return "NO_MATCH"

        result = gl.eq_principle.strict_eq(fetch_and_check)
        assert result == "MATCH", "gist did not contain the required nonce and wallet"

        self.verified_wallet_to_handle[sender] = handle
        self.verified_handle_to_wallet[handle.lower()] = sender
        return "VERIFIED"

    # ---------- create an agreement (PERMISSIONLESS) ----------
    # Creating moves no funds, so anyone may register terms for their own repo.
    # The creator gains no authority over allocations.
    @gl.public.write
    def create_agreement(
        self,
        label: str,
        repo_owner: str,
        repo_name: str,
        contributor1: str,
        contributor2: str,
        contributor3: str,
        rubric_json: str,
        eligibility_json: str,
        epoch_length_seconds: int,
        pool_per_epoch: int,
        max_per_contributor: int,
        challenge_window_seconds: int,
        reserve_rule: str,
    ) -> str:
        sender = str(gl.message.sender_address).lower()
        assert repo_owner.strip() != "", "repo owner required"
        assert repo_name.strip() != "", "repo name required"
        assert pool_per_epoch > 0, "pool must be positive"

        c1 = contributor1.lower().strip()
        c2 = contributor2.lower().strip()
        c3 = contributor3.lower().strip()
        assert c1 != "" and c2 != "" and c3 != "", "three contributors required"
        assert c1 != c2 and c2 != c3 and c1 != c3, "contributors must be distinct"

        idx = int(self.agreement_count) + 1
        self.agreement_count = u256(idx)
        aid = str(idx)

        self.ag_exists[aid] = True
        self.ag_creator[aid] = sender
        self.ag_label[aid] = label
        self.ag_repo_owner[aid] = repo_owner.strip()
        self.ag_repo_name[aid] = repo_name.strip()
        self.ag_rubric[aid] = rubric_json
        self.ag_eligibility[aid] = eligibility_json
        self.ag_epoch_len[aid] = u256(epoch_length_seconds)
        self.ag_pool[aid] = u256(pool_per_epoch)
        self.ag_max_per[aid] = u256(max_per_contributor)
        self.ag_challenge[aid] = u256(challenge_window_seconds)
        self.ag_reserve_rule[aid] = reserve_rule
        self.ag_c1[aid] = c1
        self.ag_c2[aid] = c2
        self.ag_c3[aid] = c3
        self.ag_is_contributor[aid + ":" + c1] = True
        self.ag_is_contributor[aid + ":" + c2] = True
        self.ag_is_contributor[aid + ":" + c3] = True
        self.ag_epoch_count[aid] = u256(0)

        return aid

    def _register_epoch(self, aid: str, epoch_id: str) -> None:
        n = int(self.ag_epoch_count.get(aid, u256(0)))
        self.ag_epoch_at[aid + ":" + str(n)] = epoch_id
        self.ag_epoch_count[aid] = u256(n + 1)

    # ---------- permissionless epoch settlement ----------
    @gl.public.write
    def settle_epoch(self, agreement_id: str, epoch_id: str) -> str:
        aid = agreement_id
        assert self.ag_exists.get(aid, False), "agreement does not exist"
        ekey = aid + ":" + epoch_id
        assert not self.epoch_settled.get(ekey, False), "epoch already settled"

        api_url = (
            "https://api.github.com/repos/" + self.ag_repo_owner[aid] + "/" +
            self.ag_repo_name[aid] + "/pulls?state=closed&sort=created&direction=asc&per_page=50"
        )
        pool_local = int(self.ag_pool[aid])
        max_per = int(self.ag_max_per[aid])
        rubric_local = self.ag_rubric[aid]

        def build_pkg() -> str:
            try:
                raw = gl.nondet.web.render(api_url, mode="text")
            except Exception:
                return "EVIDENCE_UNAVAILABLE"
            text = str(raw)
            if not text.lstrip().startswith("["):
                return "EVIDENCE_UNAVAILABLE"
            try:
                data = json.loads(text)
            except Exception:
                return "EVIDENCE_UNAVAILABLE"
            merged = []
            for pr in data:
                if not isinstance(pr, dict):
                    continue
                if pr.get("merged_at") is None:
                    continue
                user = pr.get("user") or {}
                login = str(user.get("login", "")).lower() if isinstance(user, dict) else ""
                merged.append({
                    "number": int(pr.get("number", 0)),
                    "author": login,
                    "merged_at": str(pr.get("merged_at", "")),
                    "title": str(pr.get("title", "")),
                })
            merged.sort(key=lambda x: (x["merged_at"], x["number"]))
            if len(merged) > 50:
                return "EVIDENCE_TOO_LARGE"
            return json.dumps({"pulls": merged}, sort_keys=True)

        pkg = gl.eq_principle.strict_eq(build_pkg)

        if pkg == "EVIDENCE_UNAVAILABLE" or pkg == "EVIDENCE_TOO_LARGE":
            self.epoch_settled[ekey] = True
            self._register_epoch(aid, epoch_id)
            self.epoch_outcome[ekey] = "Hold"
            self.epoch_reasoning[ekey] = "Evidence could not be assembled (" + pkg + ")."
            self.epoch_minority[ekey] = ""
            self.epoch_reserve[ekey] = u256(pool_local)
            self.epoch_pr_count[ekey] = u256(0)
            return "Hold"

        parsed = json.loads(pkg)
        all_pulls = parsed.get("pulls", [])
        epoch_pulls = []
        new_numbers = []
        for pr in all_pulls:
            num = int(pr.get("number", 0))
            if self.counted_pr.get(aid + ":" + str(num), False):
                continue
            new_numbers.append(num)
            login = str(pr.get("author", "")).lower()
            wallet = self.verified_handle_to_wallet.get(login, "")
            if wallet == "" or not self.ag_is_contributor.get(aid + ":" + wallet, False):
                continue
            epoch_pulls.append({
                "number": num,
                "contributor": wallet,
                "merged_at": str(pr.get("merged_at", "")),
                "title": str(pr.get("title", "")),
            })

        if len(epoch_pulls) == 0:
            for num in new_numbers:
                self.counted_pr[aid + ":" + str(num)] = True
            self.epoch_settled[ekey] = True
            self._register_epoch(aid, epoch_id)
            self.epoch_outcome[ekey] = "ReturnToReserve"
            self.epoch_reasoning[ekey] = "No merged work by an approved, verified contributor in this window."
            self.epoch_minority[ekey] = ""
            self.epoch_reserve[ekey] = u256(pool_local)
            self.epoch_pr_count[ekey] = u256(0)
            return "ReturnToReserve"

        contributors_local = [self.ag_c1[aid], self.ag_c2[aid], self.ag_c3[aid]]
        evidence_local = json.dumps({"pulls": epoch_pulls}, sort_keys=True)
        pool_str = str(pool_local)
        max_str = str(max_per)

        def allocate_fn() -> str:
            prompt = (
                "You are an impartial contribution auditor dividing a fixed reward pool "
                "among APPROVED contributors, based ONLY on the merged-pull-request evidence "
                "provided. Judge nothing you cannot see in the evidence.\n\n"
                "APPROVED CONTRIBUTORS (wallet addresses, only these may receive a share):\n"
                + json.dumps(contributors_local) + "\n\n"
                "POOL TO DIVIDE (integer units): " + pool_str + "\n"
                "MAX any single contributor may receive: " + max_str + "\n\n"
                "LOCKED RUBRIC (weights as percentages), score each contributor 0-100 PER "
                "DIMENSION in multiples of 5, grounded strictly in the evidence:\n"
                + rubric_local + "\n\n"
                "Each PR below is already attributed to an approved contributor by its "
                "'contributor' field (their verified wallet). MERGED PR EVIDENCE:\n"
                + evidence_local + "\n\n"
                "Rules:\n"
                "1. Combine each contributor's per-dimension scores by the rubric weights, then "
                "split the pool in PROPORTION to weighted scores.\n"
                "2. A contributor with no attributed PRs scores 0 and receives 0.\n"
                "3. No contributor may exceed the MAX, excess goes to reserve.\n"
                "4. Amounts are integers summing to AT MOST the pool, any remainder is reserve.\n\n"
                "Respond ONLY as valid JSON, no markdown, no preamble:\n"
                "{\"allocations\": {\"<wallet>\": <integer>, ...}, "
                "\"reserve\": <integer>, "
                "\"reasoning\": \"1-2 sentences grounded in the evidence\", "
                "\"minority_note\": \"1-2 sentences giving the strongest good-faith case the "
                "split should differ, or an empty string\"}"
            )
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            if isinstance(result, str):
                parsed2 = json.loads(result)
            else:
                parsed2 = result
            return json.dumps(parsed2, sort_keys=True)

        principle = (
            "The allocations must agree on WHICH contributors receive a non-zero share (the "
            "same set of wallets), and each contributor's amount must agree within a tolerance "
            "of 10 percent of the pool. The reserve must agree within the same tolerance. No "
            "contributor may exceed the stated MAX. Reasoning and minority_note wording may differ."
        )
        verdict = gl.eq_principle.prompt_comparative(allocate_fn, principle)

        v = json.loads(verdict)
        allocations = v.get("allocations", {}) or {}
        reasoning = str(v.get("reasoning", ""))
        minority = str(v.get("minority_note", ""))

        clamped = []
        total_alloc = 0
        for i in range(len(contributors_local)):
            w = contributors_local[i]
            amt = 0
            if w in allocations:
                try:
                    amt = int(allocations[w])
                except (TypeError, ValueError):
                    amt = 0
            if amt < 0:
                amt = 0
            if amt > max_per:
                amt = max_per
            clamped.append((w, amt))
            total_alloc += amt

        for num in new_numbers:
            self.counted_pr[aid + ":" + str(num)] = True
        self.epoch_settled[ekey] = True
        self._register_epoch(aid, epoch_id)
        self.epoch_minority[ekey] = minority
        self.epoch_pr_count[ekey] = u256(len(epoch_pulls))

        if total_alloc > pool_local:
            for pair in clamped:
                self.alloc_amount[ekey + ":" + pair[0]] = u256(0)
            self.epoch_outcome[ekey] = "Hold"
            self.epoch_reasoning[ekey] = "Proposed allocation exceeded the pool, held rather than overpay."
            self.epoch_reserve[ekey] = u256(pool_local)
            return "Hold"

        for pair in clamped:
            self.alloc_amount[ekey + ":" + pair[0]] = u256(pair[1])
        self.epoch_reserve[ekey] = u256(pool_local - total_alloc)
        self.epoch_reasoning[ekey] = reasoning
        if total_alloc > 0:
            self.epoch_outcome[ekey] = "Allocate"
            return "Allocate"
        self.epoch_outcome[ekey] = "ReturnToReserve"
        return "ReturnToReserve"

    # ---------- views ----------
    @gl.public.view
    def get_agreement_count(self) -> u256:
        return self.agreement_count

    @gl.public.view
    def get_agreement(self, agreement_id: str) -> dict:
        aid = agreement_id
        return {
            "id": aid,
            "exists": self.ag_exists.get(aid, False),
            "creator": self.ag_creator.get(aid, ""),
            "label": self.ag_label.get(aid, ""),
            "repo_owner": self.ag_repo_owner.get(aid, ""),
            "repo_name": self.ag_repo_name.get(aid, ""),
            "rubric_json": self.ag_rubric.get(aid, ""),
            "eligibility_json": self.ag_eligibility.get(aid, ""),
            "epoch_length_seconds": str(self.ag_epoch_len.get(aid, u256(0))),
            "pool_per_epoch": str(self.ag_pool.get(aid, u256(0))),
            "max_per_contributor": str(self.ag_max_per.get(aid, u256(0))),
            "challenge_window_seconds": str(self.ag_challenge.get(aid, u256(0))),
            "reserve_rule": self.ag_reserve_rule.get(aid, ""),
            "epoch_count": str(self.ag_epoch_count.get(aid, u256(0))),
        }

    @gl.public.view
    def get_contributors(self, agreement_id: str) -> list:
        aid = agreement_id
        return [
            self.ag_c1.get(aid, ""),
            self.ag_c2.get(aid, ""),
            self.ag_c3.get(aid, ""),
        ]

    @gl.public.view
    def get_epochs(self, agreement_id: str) -> list:
        aid = agreement_id
        n = int(self.ag_epoch_count.get(aid, u256(0)))
        out = []
        for i in range(n):
            out.append(self.ag_epoch_at.get(aid + ":" + str(i), ""))
        return out

    @gl.public.view
    def get_epoch(self, agreement_id: str, epoch_id: str) -> dict:
        ekey = agreement_id + ":" + epoch_id
        return {
            "settled": self.epoch_settled.get(ekey, False),
            "outcome": self.epoch_outcome.get(ekey, ""),
            "reasoning": self.epoch_reasoning.get(ekey, ""),
            "minority_note": self.epoch_minority.get(ekey, ""),
            "reserve": str(self.epoch_reserve.get(ekey, u256(0))),
            "pr_count": str(self.epoch_pr_count.get(ekey, u256(0))),
        }

    @gl.public.view
    def get_epoch_allocation(self, agreement_id: str, epoch_id: str, contributor: str) -> u256:
        key = agreement_id + ":" + epoch_id + ":" + contributor.lower()
        return self.alloc_amount.get(key, u256(0))

    @gl.public.view
    def is_verified(self, wallet: str) -> bool:
        return wallet.lower() in self.verified_wallet_to_handle

    @gl.public.view
    def get_handle(self, wallet: str) -> str:
        return self.verified_wallet_to_handle.get(wallet.lower(), "")

    @gl.public.view
    def get_wallet(self, handle: str) -> str:
        return self.verified_handle_to_wallet.get(handle.lower(), "")

    @gl.public.view
    def get_pending_nonce(self, wallet: str) -> str:
        return self.pending_nonce.get(wallet.lower(), "")
