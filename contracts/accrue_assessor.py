# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import json

BATCH = 3


class AccrueAssessor(gl.Contract):
    # MULTI-TENANT. Anyone can create an agreement for their own public repo.
    # Identity verification is global. Settlement is permissionless per
    # agreement, now in three phases so deep evidence can be fetched in small
    # batches that stay under GitHub's burst ceiling. Nobody, including a
    # creator, can set or edit an allocation.

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
    ag_created_at: TreeMap[str, u256]          # aid -> creation time (seconds since 1970), anchors derived windows
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

    # ---- settlement records (final) ----
    epoch_settled: TreeMap[str, bool]          # "aid:epoch"
    epoch_outcome: TreeMap[str, str]
    epoch_reasoning: TreeMap[str, str]
    epoch_minority: TreeMap[str, str]
    epoch_reserve: TreeMap[str, u256]
    epoch_pr_count: TreeMap[str, u256]
    alloc_amount: TreeMap[str, u256]           # "aid:epoch:wallet"
    counted_pr: TreeMap[str, bool]             # "aid:prnumber"

    # ---- batched-settlement working state ----
    epoch_opened: TreeMap[str, bool]           # "aid:epoch"
    epoch_win_start: TreeMap[str, str]         # "aid:epoch"  frozen window start (ISO8601 UTC)
    epoch_win_end: TreeMap[str, str]           # "aid:epoch"  frozen window end   (ISO8601 UTC)
    epoch_to_collect: TreeMap[str, u256]       # "aid:epoch"  number of frozen PRs
    epoch_collected: TreeMap[str, u256]        # "aid:epoch"  progress index
    epoch_prnum_at: TreeMap[str, str]          # "aid:epoch:index" -> pr number (str)
    epoch_pr_base: TreeMap[str, str]           # "aid:epoch:num"   -> base record JSON (from list)
    epoch_pr_deep: TreeMap[str, str]           # "aid:epoch:num"   -> deep evidence JSON (from collect)
    epoch_pr_done: TreeMap[str, bool]          # "aid:epoch:num"   -> collected flag

    # ---- challenge-window stamps (set at finalize) ----
    epoch_finalized_at: TreeMap[str, str]      # "aid:epoch" -> ISO8601 UTC datetime of finalize
    epoch_challenge_secs: TreeMap[str, u256]   # "aid:epoch" -> challenge window snapshot (seconds)

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
        assert epoch_length_seconds > 0, "epoch length must be positive (derived windows need it)"

        # Fail closed on any stored policy the contract cannot enforce, so no
        # eligibility or reserve field is ever decorative.
        assert reserve_rule.strip() == "return_to_reserve", "unsupported reserve_rule"
        try:
            elig = json.loads(eligibility_json)
        except Exception:
            elig = None
        assert isinstance(elig, dict), "eligibility_json must be a JSON object"
        for k in elig:
            assert k == "min_merged_prs", "unsupported eligibility key: " + str(k)
        if "min_merged_prs" in elig:
            assert int(elig["min_merged_prs"]) >= 0, "min_merged_prs must be >= 0"

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
        self.ag_created_at[aid] = u256(self._iso_to_epoch(str(gl.message_raw["datetime"])))

        return aid

    def _register_epoch(self, aid: str, epoch_id: str) -> None:
        n = int(self.ag_epoch_count.get(aid, u256(0)))
        self.ag_epoch_at[aid + ":" + str(n)] = epoch_id
        self.ag_epoch_count[aid] = u256(n + 1)

    # ---- deterministic date helpers (integer math only, no library) ----
    def _pad(self, n: int, width: int) -> str:
        s = str(n)
        while len(s) < width:
            s = "0" + s
        return s

    def _iso_to_epoch(self, s: str) -> int:
        s = s.strip()
        if "T" in s:
            datepart, timepart = s.split("T", 1)
        else:
            datepart = s
            timepart = "00:00:00"
        timepart = timepart.replace("Z", "")
        if "." in timepart:
            timepart = timepart.split(".", 1)[0]
        dp = datepart.split("-")
        year = int(dp[0])
        month = int(dp[1])
        day = int(dp[2])
        tp = timepart.split(":")
        hour = int(tp[0])
        minute = int(tp[1])
        second = int(tp[2]) if len(tp) > 2 else 0
        y = year
        if month <= 2:
            y -= 1
        era = (y if y >= 0 else y - 399) // 400
        yoe = y - era * 400
        m_adj = month + (-3 if month > 2 else 9)
        doy = (153 * m_adj + 2) // 5 + day - 1
        doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
        days = era * 146097 + doe - 719468
        return days * 86400 + hour * 3600 + minute * 60 + second

    def _epoch_to_iso(self, secs: int) -> str:
        days = secs // 86400
        rem = secs - days * 86400
        hour = rem // 3600
        minute = (rem % 3600) // 60
        second = rem % 60
        z = days + 719468
        era = (z if z >= 0 else z - 146096) // 146097
        doe = z - era * 146097
        yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
        y = yoe + era * 400
        doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
        mp = (5 * doy + 2) // 153
        d = doy - (153 * mp + 2) // 5 + 1
        m = mp + 3 if mp < 10 else mp - 9
        if m <= 2:
            y += 1
        return (self._pad(y, 4) + "-" + self._pad(m, 2) + "-" + self._pad(d, 2) +
                "T" + self._pad(hour, 2) + ":" + self._pad(minute, 2) + ":" + self._pad(second, 2) + "Z")

    # =====================================================================
    # PHASE 1: open_settlement
    # The caller supplies only an epoch INDEX. The contract DERIVES the window
    # from the agreement's creation time and epoch length, refuses to open an
    # epoch whose window has not yet ended (no premature settlement), pages the
    # PR list to completion or FAILS CLOSED, and freezes the exact set of
    # in-window, not-yet-counted merged PRs.
    # =====================================================================
    @gl.public.write
    def open_settlement(self, agreement_id: str, epoch_index: str) -> str:
        aid = agreement_id
        assert self.ag_exists.get(aid, False), "agreement does not exist"

        try:
            idx = int(epoch_index)
        except Exception:
            idx = -1
        assert idx >= 0, "epoch index must be a non-negative integer"

        epoch_id = str(idx)
        ekey = aid + ":" + epoch_id
        assert not self.epoch_settled.get(ekey, False), "epoch already settled"
        assert not self.epoch_opened.get(ekey, False), "epoch already opened"

        # DERIVE the window from agreement state. The caller cannot set dates.
        created = int(self.ag_created_at.get(aid, u256(0)))
        ln = int(self.ag_epoch_len[aid])
        assert ln > 0, "epoch length must be positive"
        ws_sec = created + idx * ln
        we_sec = created + (idx + 1) * ln

        # Refuse to open an epoch before its window has closed.
        now_sec = self._iso_to_epoch(str(gl.message_raw["datetime"]))
        assert now_sec >= we_sec, "epoch window has not ended yet, cannot open it early"

        ws_iso = self._epoch_to_iso(ws_sec)
        we_iso = self._epoch_to_iso(we_sec)

        api_base = (
            "https://api.github.com/repos/" + self.ag_repo_owner[aid] + "/" +
            self.ag_repo_name[aid] + "/pulls?state=closed&sort=created&direction=asc&per_page=100"
        )

        def build_list() -> str:
            max_pages = 10
            all_merged = []
            page = 1
            complete = False
            while page <= max_pages:
                url = api_base + "&page=" + str(page)
                try:
                    raw = gl.nondet.web.render(url, mode="text")
                except Exception:
                    return "EVIDENCE_UNAVAILABLE"
                if raw is None:
                    return "EVIDENCE_UNAVAILABLE"
                text = str(raw)
                if not text.lstrip().startswith("["):
                    return "EVIDENCE_UNAVAILABLE"
                try:
                    data = json.loads(text)
                except Exception:
                    return "EVIDENCE_UNAVAILABLE"
                count = 0
                for pr in data:
                    count += 1
                    if not isinstance(pr, dict):
                        continue
                    if pr.get("merged_at") is None:
                        continue
                    user = pr.get("user") or {}
                    login = str(user.get("login", "")).lower() if isinstance(user, dict) else ""
                    all_merged.append({
                        "number": int(pr.get("number", 0)),
                        "author": login,
                        "merged_at": str(pr.get("merged_at", "")),
                        "title": str(pr.get("title", "")),
                    })
                if count < 100:
                    complete = True
                    break
                page += 1
            if not complete:
                # Hit the page ceiling with a full final page: more may exist.
                return "TOO_MANY_PAGES"
            # dedupe by number, then stable sort
            seen = {}
            deduped = []
            for pr in all_merged:
                n = pr["number"]
                if n in seen:
                    continue
                seen[n] = True
                deduped.append(pr)
            deduped.sort(key=lambda x: (x["merged_at"], x["number"]))
            return json.dumps({"pulls": deduped}, sort_keys=True)

        pkg = gl.eq_principle.strict_eq(build_list)
        assert pkg != "EVIDENCE_UNAVAILABLE", "PR list unavailable right now, retry in a moment"
        assert pkg != "TOO_MANY_PAGES", "repository has more pull requests than one settlement can safely page, cannot settle without omitting work"

        parsed = json.loads(pkg)
        all_pulls = parsed.get("pulls", [])

        frozen = []
        for pr in all_pulls:
            msec = self._iso_to_epoch(str(pr.get("merged_at", "")))
            if msec < ws_sec or msec >= we_sec:
                continue
            num = int(pr.get("number", 0))
            if self.counted_pr.get(aid + ":" + str(num), False):
                continue
            frozen.append(pr)

        assert len(frozen) <= 50, "more than 50 PRs in this window, cannot settle safely"

        self.epoch_opened[ekey] = True
        self.epoch_win_start[ekey] = ws_iso
        self.epoch_win_end[ekey] = we_iso
        self.epoch_collected[ekey] = u256(0)
        self.epoch_to_collect[ekey] = u256(len(frozen))

        for i in range(len(frozen)):
            pr = frozen[i]
            num = int(pr.get("number", 0))
            self.epoch_prnum_at[ekey + ":" + str(i)] = str(num)
            self.epoch_pr_base[ekey + ":" + str(num)] = json.dumps({
                "number": num,
                "author": str(pr.get("author", "")),
                "merged_at": str(pr.get("merged_at", "")),
                "title": str(pr.get("title", "")),
            }, sort_keys=True)

        return "OPENED epoch=" + epoch_id + " window=" + ws_iso + ".." + we_iso + " to_collect=" + str(len(frozen))

    # =====================================================================
    # PHASE 2: collect_batch
    # Fetches deep evidence for up to BATCH not-yet-collected PRs (3 GitHub
    # calls each) and stores it. Permissionless and idempotent. On a fetch
    # failure it stops WITHOUT marking that PR collected, so finalize stays
    # blocked until a later retry succeeds.
    # =====================================================================
    @gl.public.write
    def collect_batch(self, agreement_id: str, epoch_id: str) -> str:
        aid = agreement_id
        assert self.ag_exists.get(aid, False), "agreement does not exist"
        ekey = aid + ":" + epoch_id
        assert self.epoch_opened.get(ekey, False), "epoch not opened"
        assert not self.epoch_settled.get(ekey, False), "epoch already settled"

        to_collect = int(self.epoch_to_collect.get(ekey, u256(0)))
        start = int(self.epoch_collected.get(ekey, u256(0)))
        if start >= to_collect:
            return "ALL_COLLECTED " + str(to_collect) + "/" + str(to_collect)

        owner = self.ag_repo_owner[aid]
        name = self.ag_repo_name[aid]
        end = start + BATCH
        if end > to_collect:
            end = to_collect

        idx = start
        while idx < end:
            num_str = self.epoch_prnum_at.get(ekey + ":" + str(idx), "")
            pkey = ekey + ":" + num_str
            if not self.epoch_pr_done.get(pkey, False):
                files_url = "https://api.github.com/repos/" + owner + "/" + name + "/pulls/" + num_str + "/files?per_page=100"
                reviews_url = "https://api.github.com/repos/" + owner + "/" + name + "/pulls/" + num_str + "/reviews?per_page=100"
                commits_url = "https://api.github.com/repos/" + owner + "/" + name + "/pulls/" + num_str + "/commits?per_page=100"

                def build_deep() -> str:
                    lock_suffixes = [
                        "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                        "poetry.lock", "cargo.lock", "go.sum", "composer.lock",
                    ]
                    gen_dirs = ["dist", "build", "vendor", "node_modules"]

                    def is_discounted(p: str) -> bool:
                        for suf in lock_suffixes:
                            if p.endswith(suf):
                                return True
                        if p.endswith(".min.js") or p.endswith(".min.css"):
                            return True
                        segs = p.split("/")
                        for d in gen_dirs:
                            if d in segs:
                                return True
                        return False

                    # files
                    try:
                        fraw = gl.nondet.web.render(files_url, mode="text")
                    except Exception:
                        return "FETCH_FAILED"
                    if fraw is None:
                        return "FETCH_FAILED"
                    ftext = str(fraw)
                    if not ftext.lstrip().startswith("["):
                        return "FETCH_FAILED"
                    try:
                        fdata = json.loads(ftext)
                    except Exception:
                        return "FETCH_FAILED"
                    files = []
                    for f in fdata:
                        if not isinstance(f, dict):
                            continue
                        files.append({
                            "path": str(f.get("filename", "")),
                            "status": str(f.get("status", "")),
                            "additions": int(f.get("additions", 0)),
                            "deletions": int(f.get("deletions", 0)),
                        })
                    files.sort(key=lambda x: x["path"])
                    if len(files) > 100:
                        files = files[:100]
                    footprint = 0
                    breadth = 0
                    for f in files:
                        churn = f["additions"] + f["deletions"]
                        if churn > 400:
                            churn = 400
                        if is_discounted(f["path"].lower()):
                            footprint += churn // 10
                        else:
                            footprint += churn
                            breadth += 1
                    if breadth > 40:
                        breadth = 40
                    changed_files = len(files)

                    # reviews
                    try:
                        rraw = gl.nondet.web.render(reviews_url, mode="text")
                    except Exception:
                        return "FETCH_FAILED"
                    if rraw is None:
                        return "FETCH_FAILED"
                    rtext = str(rraw)
                    if not rtext.lstrip().startswith("["):
                        return "FETCH_FAILED"
                    try:
                        rdata = json.loads(rtext)
                    except Exception:
                        return "FETCH_FAILED"
                    approvers = []
                    for rv in rdata:
                        if not isinstance(rv, dict):
                            continue
                        if str(rv.get("state", "")) != "APPROVED":
                            continue
                        u = rv.get("user") or {}
                        lg = str(u.get("login", "")).lower() if isinstance(u, dict) else ""
                        if lg != "" and lg not in approvers:
                            approvers.append(lg)
                    approvers.sort()
                    approvals = len(approvers)
                    if approvals > 3:
                        approvals = 3

                    # commits
                    try:
                        craw = gl.nondet.web.render(commits_url, mode="text")
                    except Exception:
                        return "FETCH_FAILED"
                    if craw is None:
                        return "FETCH_FAILED"
                    ctext = str(craw)
                    if not ctext.lstrip().startswith("["):
                        return "FETCH_FAILED"
                    try:
                        cdata = json.loads(ctext)
                    except Exception:
                        return "FETCH_FAILED"
                    commits = []
                    for c in cdata:
                        if not isinstance(c, dict):
                            continue
                        sha = str(c.get("sha", ""))
                        cm = c.get("commit") or {}
                        msg = str(cm.get("message", "")) if isinstance(cm, dict) else ""
                        first = msg.split("\n")[0]
                        if len(first) > 200:
                            first = first[:200]
                        commits.append({"sha": sha, "msg": first})
                    commits.sort(key=lambda x: x["sha"])
                    if len(commits) > 30:
                        commits = commits[:30]
                    commit_msgs = []
                    for c in commits:
                        commit_msgs.append(c["msg"])

                    rec = {
                        "footprint": footprint,
                        "breadth": breadth,
                        "changed_files": changed_files,
                        "approvals": approvals,
                        "files": files,
                        "commit_messages": commit_msgs,
                        "commit_count": len(commits),
                    }
                    return json.dumps(rec, sort_keys=True)

                deep = gl.eq_principle.strict_eq(build_deep)
                if deep == "FETCH_FAILED":
                    self.epoch_collected[ekey] = u256(idx)
                    return "COLLECT_INCOMPLETE stopped at pr " + num_str + ", retry in a moment"
                self.epoch_pr_deep[pkey] = deep
                self.epoch_pr_done[pkey] = True
            idx += 1

        self.epoch_collected[ekey] = u256(idx)
        if idx >= to_collect:
            return "COLLECT_DONE " + str(idx) + "/" + str(to_collect)
        return "COLLECTED " + str(idx) + "/" + str(to_collect)

    # =====================================================================
    # PHASE 3: finalize_settlement
    # Blocks until every frozen PR is collected. Enforces the stored eligibility
    # and reserve policies, runs the band-gated consensus allocation, and writes
    # the split, reserve, minority note, and outcome. Marks each frozen PR counted.
    # =====================================================================
    @gl.public.write
    def finalize_settlement(self, agreement_id: str, epoch_id: str) -> str:
        aid = agreement_id
        assert self.ag_exists.get(aid, False), "agreement does not exist"
        ekey = aid + ":" + epoch_id
        assert self.epoch_opened.get(ekey, False), "epoch not opened"
        assert not self.epoch_settled.get(ekey, False), "epoch already settled"

        to_collect = int(self.epoch_to_collect.get(ekey, u256(0)))
        collected = int(self.epoch_collected.get(ekey, u256(0)))
        assert collected >= to_collect, "not all PRs collected yet, run collect_batch until done"

        # Stamp the challenge window. Every settled path below inherits this,
        # so the vault can refuse to release funds until it has elapsed.
        self.epoch_finalized_at[ekey] = str(gl.message_raw["datetime"])
        self.epoch_challenge_secs[ekey] = self.ag_challenge.get(aid, u256(0))

        pool_local = int(self.ag_pool[aid])
        max_per = int(self.ag_max_per[aid])
        rubric_local = self.ag_rubric[aid]

        # Enforce the stored eligibility policy. Validated at creation, so only
        # known keys are present; read min_merged_prs (default 0).
        min_prs = 0
        try:
            elig = json.loads(self.ag_eligibility.get(aid, "{}"))
            if isinstance(elig, dict) and "min_merged_prs" in elig:
                min_prs = int(elig["min_merged_prs"])
        except Exception:
            min_prs = 0

        # Enforce the stored reserve policy (validated at creation).
        assert self.ag_reserve_rule.get(aid, "") == "return_to_reserve", "unsupported reserve_rule"

        new_numbers = []
        by_contrib = {}   # wallet -> list of pull records (insertion order is deterministic)
        for i in range(to_collect):
            num_str = self.epoch_prnum_at.get(ekey + ":" + str(i), "")
            num = int(num_str)
            new_numbers.append(num)
            base_raw = self.epoch_pr_base.get(ekey + ":" + num_str, "")
            if base_raw == "":
                continue
            base = json.loads(base_raw)
            login = str(base.get("author", "")).lower()
            wallet = self.verified_handle_to_wallet.get(login, "")
            if wallet == "" or not self.ag_is_contributor.get(aid + ":" + wallet, False):
                continue
            if self.counted_pr.get(aid + ":" + str(num), False):
                continue
            deep_raw = self.epoch_pr_deep.get(ekey + ":" + num_str, "")
            deep = json.loads(deep_raw) if deep_raw != "" else {}
            files = deep.get("files", [])
            if len(files) > 15:
                files = files[:15]
            msgs = deep.get("commit_messages", [])
            if len(msgs) > 8:
                msgs = msgs[:8]
            pull = {
                "number": num,
                "contributor": wallet,
                "merged_at": str(base.get("merged_at", "")),
                "title": str(base.get("title", "")),
                "footprint": int(deep.get("footprint", 0)),
                "breadth": int(deep.get("breadth", 0)),
                "changed_files": int(deep.get("changed_files", 0)),
                "commit_count": int(deep.get("commit_count", 0)),
                "approvals": int(deep.get("approvals", 0)),
                "files": files,
                "commit_messages": msgs,
            }
            if wallet not in by_contrib:
                by_contrib[wallet] = []
            by_contrib[wallet].append(pull)

        # A contributor below the merged-PR threshold is ineligible: their work
        # is excluded from the evidence entirely, so they score and receive 0.
        epoch_pulls = []
        for wallet in by_contrib:
            if len(by_contrib[wallet]) >= min_prs:
                for pull in by_contrib[wallet]:
                    epoch_pulls.append(pull)
        epoch_pulls.sort(key=lambda x: (x["merged_at"], x["number"]))

        if len(epoch_pulls) == 0:
            for num in new_numbers:
                self.counted_pr[aid + ":" + str(num)] = True
            self.epoch_settled[ekey] = True
            self._register_epoch(aid, epoch_id)
            self.epoch_outcome[ekey] = "ReturnToReserve"
            self.epoch_reasoning[ekey] = "No merged work by an approved, verified, eligible contributor in this window."
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
                "Each PR is attributed to an approved contributor by its 'contributor' field. "
                "Beyond title and merge time, each PR carries objective signals computed from "
                "its diff, reviews, and commits:\n"
                " - footprint: size-weighted lines changed, capped per file, with lock and "
                "generated files already discounted. Do not reward padding further.\n"
                " - breadth: count of meaningful (non-generated) files touched.\n"
                " - changed_files: total files in the diff.\n"
                " - commit_count and commit_messages: the work's commit substance.\n"
                " - approvals: distinct reviewer approvals the PR received.\n"
                " - files: a sample of changed file paths with per-file additions/deletions.\n"
                "Weight genuine substance and reviewed, broad, meaningful work. Discount "
                "trivial churn, generated output, and title-only signal.\n\n"
                "MERGED PR EVIDENCE:\n" + evidence_local + "\n\n"
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
            "created_at": self._epoch_to_iso(int(self.ag_created_at.get(aid, u256(0)))) if self.ag_exists.get(aid, False) else "",
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
            "finalized_at": self.epoch_finalized_at.get(ekey, ""),
            "challenge_seconds": str(self.epoch_challenge_secs.get(ekey, u256(0))),
        }

    @gl.public.view
    def get_settlement_progress(self, agreement_id: str, epoch_id: str) -> dict:
        ekey = agreement_id + ":" + epoch_id
        return {
            "opened": self.epoch_opened.get(ekey, False),
            "settled": self.epoch_settled.get(ekey, False),
            "window_start": self.epoch_win_start.get(ekey, ""),
            "window_end": self.epoch_win_end.get(ekey, ""),
            "to_collect": str(self.epoch_to_collect.get(ekey, u256(0))),
            "collected": str(self.epoch_collected.get(ekey, u256(0))),
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
