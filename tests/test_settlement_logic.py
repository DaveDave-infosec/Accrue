"""
Offline logic tests for the Accrue assessor (plain pytest, no network).

These mirror, line for line, the deterministic algorithms the contract runs
inside open_settlement and finalize_settlement, and assert the properties the
follow-up review asked about:

  - GitHub pagination is COMPLETE or FAILS CLOSED, never silently truncated
    (the "repositories with more than one API page" case).
  - The stored min_merged_prs eligibility threshold is enforced.
  - The ISO <-> seconds date conversions used to derive epoch windows are
    exact in both directions.

They run anywhere with `pytest`, with no GenLayer runtime, because they exercise
the pure logic that the on-chain code executes.

Run:  pytest tests/test_settlement_logic.py
"""

# ---------- reference copies of the contract's pure logic ----------

def paginate(pages, max_pages=10):
    """Mirror of open_settlement.build_list page loop."""
    all_merged = []
    page = 1
    complete = False
    while page <= max_pages:
        data = pages.get(page, [])
        count = 0
        for pr in data:
            count += 1
            if pr.get("merged_at") is None:
                continue
            all_merged.append({"number": pr["number"], "merged_at": pr["merged_at"]})
        if count < 100:
            complete = True
            break
        page += 1
    if not complete:
        return "TOO_MANY_PAGES"
    seen = {}
    dedup = []
    for pr in all_merged:
        if pr["number"] in seen:
            continue
        seen[pr["number"]] = True
        dedup.append(pr)
    dedup.sort(key=lambda x: (x["merged_at"], x["number"]))
    return dedup


def eligible_pulls(attributed, min_prs):
    """Mirror of finalize_settlement eligibility grouping.
    attributed: list of (wallet, number, merged_at)."""
    by = {}
    for w, num, merged in attributed:
        by.setdefault(w, []).append({"contributor": w, "number": num, "merged_at": merged})
    out = []
    for w in by:
        if len(by[w]) >= min_prs:
            out.extend(by[w])
    out.sort(key=lambda x: (x["merged_at"], x["number"]))
    return out


def pad(n, width):
    s = str(n)
    while len(s) < width:
        s = "0" + s
    return s


def iso_to_epoch(s):
    s = s.strip()
    datepart, timepart = (s.split("T", 1) if "T" in s else (s, "00:00:00"))
    timepart = timepart.replace("Z", "")
    if "." in timepart:
        timepart = timepart.split(".", 1)[0]
    dp = datepart.split("-")
    year, month, day = int(dp[0]), int(dp[1]), int(dp[2])
    tp = timepart.split(":")
    hour, minute = int(tp[0]), int(tp[1])
    second = int(tp[2]) if len(tp) > 2 else 0
    y = year - 1 if month <= 2 else year
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    m_adj = month + (-3 if month > 2 else 9)
    doy = (153 * m_adj + 2) // 5 + day - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    days = era * 146097 + doe - 719468
    return days * 86400 + hour * 3600 + minute * 60 + second


def epoch_to_iso(secs):
    days = secs // 86400
    rem = secs - days * 86400
    hour, minute, second = rem // 3600, (rem % 3600) // 60, rem % 60
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
    return (pad(y, 4) + "-" + pad(m, 2) + "-" + pad(d, 2) + "T" +
            pad(hour, 2) + ":" + pad(minute, 2) + ":" + pad(second, 2) + "Z")


# ---------- pagination: complete or fail closed ----------

def test_single_short_page_completes():
    pages = {1: [{"number": i, "merged_at": "2026-07-2%dT00:00:00Z" % (i % 9)} for i in range(4)]}
    r = paginate(pages)
    assert isinstance(r, list) and len(r) == 4


def test_two_pages_assemble_fully():
    full = [{"number": i, "merged_at": "2026-07-01T00:00:00Z"} for i in range(100)]
    half = [{"number": 100 + i, "merged_at": "2026-07-02T00:00:00Z"} for i in range(30)]
    r = paginate({1: full, 2: half})
    assert isinstance(r, list) and len(r) == 130


def test_overflow_fails_closed():
    pages = {i: [{"number": (i - 1) * 100 + j, "merged_at": "2026-07-01T00:00:00Z"}
                 for j in range(100)] for i in range(1, 12)}
    assert paginate(pages) == "TOO_MANY_PAGES"


def test_pagination_never_silently_truncates():
    pages = {i: [{"number": (i - 1) * 100 + j, "merged_at": "2026-07-01T00:00:00Z"}
                 for j in range(100)] for i in range(1, 10)}
    pages[10] = [{"number": 900 + j, "merged_at": "2026-07-01T00:00:00Z"} for j in range(20)]
    r = paginate(pages)
    assert isinstance(r, list) and len(r) == 920


# ---------- eligibility threshold ----------

def test_min_merged_prs_keeps_all_at_threshold_one():
    attr = [("0xA", 1, "2026-07-01T00:00:00Z"),
            ("0xA", 2, "2026-07-02T00:00:00Z"),
            ("0xB", 3, "2026-07-03T00:00:00Z")]
    out = [(p["contributor"], p["number"]) for p in eligible_pulls(attr, 1)]
    assert out == [("0xA", 1), ("0xA", 2), ("0xB", 3)]


def test_min_merged_prs_drops_below_threshold():
    attr = [("0xA", 1, "2026-07-01T00:00:00Z"),
            ("0xA", 2, "2026-07-02T00:00:00Z"),
            ("0xB", 3, "2026-07-03T00:00:00Z")]
    out = [p["contributor"] for p in eligible_pulls(attr, 2)]
    assert out == ["0xA", "0xA"]


def test_min_merged_prs_can_exclude_everyone():
    attr = [("0xA", 1, "2026-07-01T00:00:00Z"), ("0xB", 3, "2026-07-03T00:00:00Z")]
    assert eligible_pulls(attr, 2) == []


# ---------- derived-window date math ----------

def test_date_roundtrip_exact():
    for s in ["1970-01-01T00:00:00Z", "2024-02-29T23:59:59Z", "2100-03-01T00:00:00Z",
              "2026-07-23T15:26:39Z", "2026-08-24T21:38:34Z"]:
        assert epoch_to_iso(iso_to_epoch(s)) == s


def test_derived_windows_are_epoch_aligned_and_contiguous():
    created = iso_to_epoch("2026-08-01T00:00:00Z")
    length = 7 * 86400
    w0 = (epoch_to_iso(created + 0 * length), epoch_to_iso(created + 1 * length))
    w1 = (epoch_to_iso(created + 1 * length), epoch_to_iso(created + 2 * length))
    assert w0 == ("2026-08-01T00:00:00Z", "2026-08-08T00:00:00Z")
    assert w1 == ("2026-08-08T00:00:00Z", "2026-08-15T00:00:00Z")
    assert w0[1] == w1[0]
