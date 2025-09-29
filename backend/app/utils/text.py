import re
import unicodedata


def normalize(text: str) -> str:
    """Return a normalized representation of the given text for comparisons."""
    if not text:
        return ""

    decomposed = unicodedata.normalize("NFKD", text)
    ascii_only = decomposed.encode("ASCII", "ignore").decode("utf-8")
    lowered = ascii_only.lower()
    return re.sub(r"[^a-z0-9]", "", lowered)
