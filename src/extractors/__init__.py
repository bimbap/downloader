# =============================================================================
# downloader/src/extractors/__init__.py – Extractor Registry & Factory
# =============================================================================
from extractors.base import BaseExtractor, MediaItem
from extractors.youtube import YouTubeExtractor
from extractors.twitter import TwitterExtractor
from extractors.instagram import InstagramExtractor
from extractors.threads import ThreadsExtractor

EXTRACTORS: list[type[BaseExtractor]] = [
    YouTubeExtractor,
    TwitterExtractor,
    InstagramExtractor,
    ThreadsExtractor,
]


def detect_platform(url: str) -> str | None:
    """Detects platform string ('youtube', 'twitter', 'instagram', 'threads') from URL."""
    clean = url.strip().lower()
    if "youtube.com" in clean or "youtu.be" in clean:
        return "youtube"
    if "twitter.com" in clean or "x.com" in clean:
        return "twitter"
    if "instagram.com" in clean:
        return "instagram"
    if "threads.net" in clean:
        return "threads"
    return None


def get_extractor_for_url(url: str) -> BaseExtractor | None:
    """Finds and instantiates the suitable extractor for the given URL."""
    for extractor_cls in EXTRACTORS:
        if extractor_cls.is_suitable(url):
            return extractor_cls()
    return None
