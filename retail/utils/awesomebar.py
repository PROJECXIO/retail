from __future__ import annotations
import re
import unicodedata
from typing import List
import frappe

def _normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

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

def _similarity(a: str, b: str) -> float:
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    m = max(len(a), len(b)) or 1
    return 1.0 - (_edit_distance(a, b) / m)

def _is_subsequence(q: str, target: str) -> bool:
    q = (q or "").lower()
    target = (target or "").lower()
    it = iter(target)
    return all(c in it for c in q)

@frappe.whitelist()
def find_closest_items(q: str, limit: int = 20) -> List[str]:
    """
    Return item_code for matches where query q is a subsequence
    of item_code OR item_name, ranked by similarity.
    """
    try:
        limit = int(limit)
    except Exception:
        limit = 20

    q_norm = _normalize_spaces(q).lower()
    # Increase the limit for SQL rows, or remove it if performance allows
    rows = frappe.db.sql(
        "SELECT item_code, item_name FROM `tabItem` LIMIT 20000", as_dict=True
    )
    results = []
    for r in rows:
        code = (r.get("item_code") or "").lower()
        name = (r.get("item_name") or "").lower()
        if not (_is_subsequence(q_norm, code) or _is_subsequence(q_norm, name)):
            continue
        score_code = _similarity(q_norm, code)
        score_name = _similarity(q_norm, name)
        score = max(score_code, score_name)
        results.append((score, r["item_code"]))
    return [item_code for score, item_code in sorted(results, key=lambda x: x[0], reverse=True)[:limit]]

@frappe.whitelist()
def find_closest_customers(q: str, limit: int = 20) -> List[str]:
    """
    Return item_code for matches where query q is a subsequence
    of item_code OR item_name, ranked by similarity.
    """
    try:
        limit = int(limit)
    except Exception:
        limit = 20

    q_norm = _normalize_spaces(q).lower()
    # Increase the limit for SQL rows, or remove it if performance allows
    rows = frappe.db.sql(
        "SELECT name, customer_name FROM `tabCustomer` LIMIT 20000", as_dict=True
    )
    results = []
    for r in rows:
        code = (r.get("name") or "").lower()
        name = (r.get("customer_name") or "").lower()
        if not (_is_subsequence(q_norm, code) or _is_subsequence(q_norm, name)):
            continue
        score_code = _similarity(q_norm, code)
        score_name = _similarity(q_norm, name)
        score = max(score_code, score_name)
        results.append((score, r["name"]))
    return [name for score, name in sorted(results, key=lambda x: x[0], reverse=True)[:limit]]
