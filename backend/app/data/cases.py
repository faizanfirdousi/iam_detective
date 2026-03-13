from __future__ import annotations

"""
No dummy/mocked case content lives here.

This module only defines *identifiers* and pointers to the upstream source
that will be ingested into the DigitalOcean Gradient knowledge base.
All case narrative, link-board structure, and chat responses come from the
configured Gradient agent at runtime.
"""

from app.models import CaseListItem


def list_cases() -> list[CaseListItem]:
    # Minimal "real pointer" to a famous public case.
    # The actual content must come from your Gradient KB + agent.
    return [
        CaseListItem(
            id="zodiac-killer",
            title="Zodiac Killer",
            subtitle="",
            status="unsolved",
            hero_image_url=None,
        )
    ]


