import re

_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize_mobile(raw: str, default_country: str | None = None) -> str:
    if not raw or not isinstance(raw, str):
        return raw

    s = raw.strip().translate(_DIGIT_MAP)
    s = re.sub(r"(?i)(?:ext\.?|extension|x|#)\s*\d+\s*$", "", s)
    s = re.sub(r"[^\d+]+", "", s)
    s = re.sub(r"^00+", "+", s)
    s = re.sub(r"^\++", "+", s)
    s = ("+" + re.sub(r"\D", "", s[1:])) if s.startswith("+") else re.sub(r"\D", "", s)

    return s
