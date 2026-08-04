import re
from typing import Any
# from scarf.utils import snake_case
from scarf.utils import snake_case

def _split_line(line: str) -> list[str]:
    return re.split(r"\s{2,}", line.strip())


def _parse_show_table(output: str) -> list[dict[str, Any]]:
    lines = output.splitlines()
    fields = []
    data = []
    fields_line = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if "----" in line:
            fields = [f.lower().replace(" ", "_") for f in _split_line(fields_line)]
            continue

        if not fields:
            fields_line = line
            continue

        parts = re.split(r"\s{2,}", line)
        parts = parts + [None] * (len(fields) - len(parts))

        data.append(dict(zip(fields, parts)))

    return data


def _parse_show_keyval(output: str) -> dict[str, str]:
    data = {}
    for line in output.splitlines():
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[snake_case(key)] = value.strip()

    return data
