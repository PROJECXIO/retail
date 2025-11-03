from __future__ import annotations
import re
import unicodedata
from typing import Iterable, Tuple, List
import frappe


def _normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _fold(s: str) -> str:
    """Remove diacritics/accents and lowercase (NFKD → strip combining marks)."""
    s = s or ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()


def _letters_digits(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _split_tokens(q: str) -> list[str]:
    return [t for t in _normalize_spaces(q).split(" ") if t]


def _subsequence_like_pattern(q: str) -> str:
    letters = [c for c in q if c.isalnum()]
    return "%" + "%".join(letters) + "%" if letters else "%"


def _edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(a) + 1))
    for j, bj in enumerate(b, 1):
        cur = [j]
        for i, ai in enumerate(a, 1):
            cost = 0 if ai == bj else 1
            cur.append(min(cur[-1] + 1, prev[i] + 1, prev[i - 1] + cost))
        prev = cur
    return prev[-1]


def _normalized_sim(a: str, b: str) -> float:
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    m = max(len(a), len(b)) or 1
    return 1.0 - (_edit_distance(a, b) / m)


def _subseq_stats(text: str, pat: str) -> Tuple[int, int]:
    if not pat:
        return 0, 10**9
    t, p = text.lower(), pat.lower()
    ti = 0
    first = -1
    last = -1
    matched = 0
    for ch in t:
        if ti < len(p) and ch == p[ti]:
            if first < 0:
                first = last = 0
            matched += 1
            ti += 1
        if first >= 0:
            last += 1
        if ti >= len(p):
            break
    if matched == 0:
        return 0, 10**9
    return matched, (last if last > 0 else 1)


def _score_subseq(q_raw: str, cand_text: str, tokens: Iterable[str]) -> float:
    if not cand_text:
        return 0.0
    text = cand_text.lower()
    q = _letters_digits(q_raw)
    if not q:
        return 0.0

    pos = text.find(q)
    if pos >= 0:
        return min(1.0, 1.0 + (0.15 if pos == 0 else 0.0))

    matched, span = _subseq_stats(text, q)
    completeness = matched / max(len(q), 1)
    density = matched / max(span, matched or 1)
    base = 0.65 * completeness + 0.35 * density

    toks = [t for t in _split_tokens(q_raw)]
    if toks:
        hits = sum(1 for t in toks if t in text)
        base += 0.08 * (hits / len(toks))
        base += 0.15 * max((_normalized_sim(t, cand_text) for t in toks), default=0.0)
        if any(text.startswith(t) for t in toks):
            base += 0.05

    return max(0.0, min(base, 1.0))


def _trigrams(s: str) -> list[str]:
    s = re.sub(r"\s+", " ", (s or "").strip())
    if len(s) < 3:
        return [s] if s else []
    return [s[i : i + 3] for i in range(len(s) - 2)]


def _trigram_sim(a: str, b: str) -> float:
    A = set(_trigrams(a))
    B = set(_trigrams(b))
    if not A or not B:
        return 0.0
    return (2 * len(A & B)) / (len(A) + len(B))


def _get_text_fields_row(r: dict, fold: bool) -> tuple[str, str]:
    code = (r.get("item_code") or "").strip()
    name = (r.get("item_name") or "").strip()
    agg = (r.get("custom_search") or "").strip()
    if fold:
        code_f = _fold(code)
        name_f = _fold(name)
        agg_f = _fold(agg)
        return code_f, (f"{code_f} {name_f} {agg_f}").strip()
    return code.lower(), (f"{code.lower()} {name.lower()} {agg.lower()}").strip()


@frappe.whitelist()
def custom_search_subsequence(
    q: str = "",
    limit: int | str = 200,
    *,
    mode: str = "subseq",
    fold: int | str = 1,
):
    """
    Smart search with ranking & options:
      - mode="prefix": ANDed prefix-only per token (fast); ranking: strong prefix > code/name prefix > length.
      - mode="subseq": subsequence fuzzy (default) + quality scoring.
      - mode="trigram": similarity by trigrams (Python fallback). If an N-gram FULLTEXT index exists, we try that first.

    Returns a list[item_code] ordered by relevance (max `limit`).
    """
    try:
        lim = int(limit)
        lim = lim if lim > 0 else 200
    except Exception:
        lim = 200
    mode = (mode or "subseq").lower()
    do_fold = str(fold) == "1" or str(fold).lower() == "true"

    q_in = _normalize_spaces(q)
    if not q_in:
        return []

    tokens_raw = _split_tokens(q_in)
    tokens = (
        [_fold(t) for t in tokens_raw] if do_fold else [t.lower() for t in tokens_raw]
    )

    if mode == "prefix":
        patterns = [t + "%" for t in tokens]
    else:
        patterns = [_subsequence_like_pattern(t) for t in tokens]

    col = "custom_search"
    where_clause = " AND ".join([f"LOWER(`{col}`) LIKE %s"] * len(patterns))
    params = list(patterns)
    prefetch = max(lim * 5, 200)

    rows = frappe.db.sql(
        f"""
        SELECT item_code, item_name, {col} AS search_content
        FROM `tabItem`
        WHERE {where_clause}
        LIMIT %s
        """,
        params + [prefetch],
        as_dict=True,
    )

    if not rows and do_fold:
        alt_col = "custom_search"
        where_clause2 = " AND ".join([f"LOWER(`{alt_col}`) LIKE %s"] * len(patterns))
        rows = frappe.db.sql(
            f"""
            SELECT item_code, item_name, {alt_col} AS search_content
            FROM `tabItem`
            WHERE {where_clause2}
            LIMIT %s
            """,
            params + [prefetch],
            as_dict=True,
        )

    q_rank_text = _fold(q_in) if do_fold else q_in.lower()
    scored: List[tuple[float, str]] = []

    if mode == "prefix":
        for r in rows:
            code_f, agg_f = _get_text_fields_row(r, do_fold)
            score = 0.0
            if any(code_f.startswith(t) for t in tokens):
                score += 1.0
            if any((r.get("item_name") or "").lower().startswith(t) for t in tokens):
                score += 0.6
            if any(agg_f.startswith(t) for t in tokens):
                score += 0.4
            score += max(0.0, 0.3 * (1.0 - min(len(agg_f), 200) / 200.0))
            scored.append((score, r["item_code"]))
        scored.sort(key=lambda x: x[0], reverse=True)

    elif mode == "trigram":
        codes_seen = set()
        try:
            tri_terms = _trigrams(q_rank_text)
            if tri_terms:
                boolean_q = " ".join(f"+{t}" for t in tri_terms)
                col_ft = "custom_search"
                ft_rows = frappe.db.sql(
                    f"""
                    SELECT item_code, item_name, {col_ft} AS search_content
                    FROM `tabItem`
                    WHERE MATCH({col_ft}) AGAINST (%s IN BOOLEAN MODE)
                    LIMIT %s
                    """,
                    (boolean_q, prefetch),
                    as_dict=True,
                )
                for r in ft_rows:
                    if r["item_code"] not in codes_seen:
                        codes_seen.add(r["item_code"])
                        s_text = (
                            _fold(r["search_content"])
                            if do_fold
                            else r["search_content"].lower()
                        )
                        score = _trigram_sim(q_rank_text, s_text)
                        scored.append((score, r["item_code"]))
        except Exception:
            pass

        for r in rows:
            if r["item_code"] in codes_seen:
                continue
            s_text = (
                _fold(r["search_content"]) if do_fold else r["search_content"].lower()
            )
            score = _trigram_sim(q_rank_text, s_text)
            scored.append((score, r["item_code"]))

        scored.sort(key=lambda x: x[0], reverse=True)

    else:
        for r in rows:
            s_text = (
                _fold(r["search_content"]) if do_fold else r["search_content"].lower()
            )
            score = _score_subseq(q_rank_text, s_text, tokens)
            scored.append((score, r["item_code"]))
        scored.sort(key=lambda x: x[0], reverse=True)

    return [code for score, code in scored[:lim] if code]
