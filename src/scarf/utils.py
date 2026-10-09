import re


def split_keyval(line: str, sep: str = ":") -> tuple[str, str | None]:
    """Split a line into a key and a value. Returns (key, None) if no value is found."""
    line = line.strip()
    parts = [p.strip() for p in line.split(sep, maxsplit=1)]
    return parts[0], sep.join(parts[1:]) if len(parts) > 1 else None

def snake_case(s: str) -> str:
    s = s.strip()

    # if has spaces, convert to snake_case
    if " " in s:
        s = s.lower().replace(" ", "_")

    # if all caps, return
    if s == s.upper():
        return s.lower()

    # if has caps, convert to snake_case
    if s != s.lower():
        return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()

    return s

def numerize(s: str | None) -> str | None:
    """Extract the first number from a string."""
    if not s:
        return None
    m = re.search(r"\d+(\.\d+)?(?:[Ee][\+-]\d+)?", s)
    if m:
        return m.group()

    return None


def iorn(s: str | None) -> int | None:
    """Convert a string to an integer, or None if not a number."""
    s = numerize(s)
    if s:
        return int(s)
    return None


def forn(s: str | None) -> float | None:
    """Convert a string to a float, or None if not a number."""
    s = numerize(s)
    if s:
        return float(s)
    return None