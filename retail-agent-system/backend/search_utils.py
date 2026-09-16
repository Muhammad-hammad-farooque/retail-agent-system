"""Shared product search matching.

Used by both the inventory API (the Inventory page search box) and the agent
tools, so a staff member and the AI assistant get the same results for the
same words.
"""
from sqlalchemy import and_, or_

# LLMs and copy-pasted text often carry typographic quotes/dashes (curly
# apostrophes, non-breaking hyphens) that never match the plain ASCII
# characters stored in the database.
_SEARCH_CHAR_MAP = str.maketrans({
    "‘": "'", "’": "'", "‛": "'", "′": "'",
    "“": '"', "”": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    " ": " ", " ": " ",
})

MAX_SEARCH_RESULTS = 25


def normalize_search_text(text: str) -> str:
    """Fold typographic characters to ASCII and trim surrounding whitespace."""
    return text.translate(_SEARCH_CHAR_MAP).strip()


def text_search_filter(columns, term: str):
    """Match `term` against any of `columns`, one word at a time.

    Every word must appear in at least one column, in any order, so
    "loreal serum" finds "L'Oreal Paris Revitalift Face Serum 30ml".
    """
    return and_(*[
        or_(*[column.ilike(f"%{word}%") for column in columns])
        for word in term.split()
    ])


def product_search_filter(model, term: str):
    """Match `term` against a product's name or SKU."""
    return text_search_filter([model.name, model.sku], term)
