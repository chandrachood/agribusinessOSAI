from typing import List
from ..models.source import Source


def get_ranked_sources() -> List[Source]:
    return [
        Source(
            id="trustpilot",
            name="Trustpilot",
            type="trustpilot",
            base_url="https://www.trustpilot.com",
            weight=1.0,
        ),
        Source(
            id="reddit_uk",
            name="Reddit (UK)",
            type="reddit",
            base_url="https://www.reddit.com/r/UKPersonalFinance",
            weight=0.9,
        ),
        Source(
            id="apple_app_store",
            name="Apple App Store",
            type="app_store",
            base_url="https://apps.apple.com",
            weight=0.8,
        ),
        Source(
            id="google_play",
            name="Google Play Store",
            type="play_store",
            base_url="https://play.google.com/store",
            weight=0.7,
        ),
        Source(
            id="moneysavingexpert",
            name="MoneySavingExpert",
            type="mse",
            base_url="https://www.moneysavingexpert.com",
            weight=0.6,
        ),
    ]
