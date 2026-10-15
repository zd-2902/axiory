"""Conservative CHF literal matching; no semantic table/coverage inference."""

import re
from decimal import Decimal

# Consume entire numeric tokens before validating, so malformed/grouped numbers,
# dates, identifiers and fractions cannot be reinterpreted as smaller amounts.
TOKEN = re.compile(
    r"(?<![\w.,'’:/+−\-])\d+(?:[.,'’:/\-]\d+|[ \u00a0\u202f]\d+)*"
    r"(?![\w]|[.,'’:/\-]\d|[ \u00a0\u202f]\d)"
)
PLAIN = re.compile(r"(?:0|[1-9]\d*)(?:[.,]\d{1,2})?")
GROUPED = re.compile(
    r"[1-9]\d{0,2}(?P<sep>['’ \u00a0\u202f])\d{3}(?:(?P=sep)\d{3})*(?:[.,]\d{1,2})?"
)


def literal_amounts(text):
    """Only unambiguous complete numbers; punctuation is not a decimal."""
    found = set()
    for match in TOKEN.finditer(text):
        token = match.group()
        # The token regex may backtrack before a letter. Never accept that prefix.
        if match.end() < len(text) and text[match.end()].isalnum():
            continue
        grouped = GROUPED.fullmatch(token)
        if not PLAIN.fullmatch(token) and grouped is None:
            continue
        if grouped:
            token = token.replace(grouped["sep"], "")
        found.add(Decimal(token.replace(",", ".")))
    return found
