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