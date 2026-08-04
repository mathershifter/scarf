from typing import Iterable
from pydantic import BaseModel


def _verify_helper(
    have: BaseModel, want: Iterable[tuple[str, str]] | None
) -> Iterable[tuple[bool, str, str]]:
    if want is None:
        # yield True, have.__class__.__name__, "OK"
        return

    for key, value in want:
        if value is None:
            continue
        have_val = getattr(have, key)
        if have_val != value:
            yield False, key, f"Expected {value}, got {have_val}"
