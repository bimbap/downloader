# =============================================================================
# downloader/src/extractors/base.py – Abstract Base Class for Media Extractors
# =============================================================================
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MediaItem:
    """Standardized representation of extracted media across all platforms."""
    platform: str                    # 'youtube', 'twitter', 'instagram', 'threads'
    url: str                         # Canonical URL
    title: str                       # Clean title or caption snippet
    author: str = "Unknown"          # Creator / Account name
    media_type: str = "video"        # 'video', 'audio', 'image', 'gallery', 'playlist'
    duration: float = 0.0            # Duration in seconds (for video/audio)
    thumbnail: str | None = None
    items: list[dict[str, Any]] = field(default_factory=list)  # Multi-items (gallery photos or playlist tracks)
    raw_info: dict[str, Any] = field(default_factory=dict)


class BaseExtractor(ABC):
    """Abstract interface for platform-specific media extractors."""

    @classmethod
    @abstractmethod
    def is_suitable(cls, url: str) -> bool:
        """Returns True if this extractor can handle the given URL."""
        pass

    @abstractmethod
    def validate_url(self, url: str) -> tuple[bool, str, str]:
        """Validates and normalizes URL. Returns (is_valid, normalized_url, error_reason)."""
        pass

    @abstractmethod
    def fetch_metadata(self, url: str) -> MediaItem | None:
        """Fetches metadata without downloading the full media."""
        pass

    @abstractmethod
    def download(self, item: MediaItem, options: dict[str, Any]) -> tuple[bool, list[Path]]:
        """Downloads media item based on options. Returns (success, list_of_downloaded_paths)."""
        pass
