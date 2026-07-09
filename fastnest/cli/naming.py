import re


def to_pascal_case(name: str) -> str:
    parts = re.split(r"[-_\s]+", name.strip())
    return "".join(part[:1].upper() + part[1:] for part in parts if part)


def singularize(name: str) -> str:
    if name.endswith("s") and len(name) > 1:
        return name[:-1]
    return name
