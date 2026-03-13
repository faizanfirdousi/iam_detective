from __future__ import annotations

"""
Case registry — only identifiers and static metadata live here.
All narrative, link-board structure, and chat responses come from the
per-case DigitalOcean Gradient agent at runtime.
"""

from app.models import CaseListItem


def list_cases() -> list[CaseListItem]:
    return [
        CaseListItem(
            id="zodiac-killer",
            title="Zodiac Killer",
            subtitle="A serial killer who taunted police with cryptic ciphers.",
            status="unsolved",
            year=1968,
            location="California, USA",
            difficulty="hard",
            hero_image_url=None,
        ),
        CaseListItem(
            id="aarushi-talwar",
            title="Aarushi Talwar Murder",
            subtitle="A 14-year-old found dead in her home. Her parents were convicted, then acquitted.",
            status="unsolved",
            year=2008,
            location="Noida, India",
            difficulty="medium",
            hero_image_url=None,
        ),
        CaseListItem(
            id="oj-simpson",
            title="O.J. Simpson Trial",
            subtitle="NFL star acquitted of murdering his ex-wife and her friend in the 'Trial of the Century'.",
            status="solved",
            year=1994,
            location="Los Angeles, USA",
            difficulty="medium",
            hero_image_url=None,
        ),
    ]


def get_case_ids() -> set[str]:
    return {c.id for c in list_cases()}
