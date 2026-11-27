# =============================================================================
# downloader/src/core/batch.py – Single & Batch URL Parsing and Execution
# =============================================================================
import re
from pathlib import Path
from typing import Any, Callable

from core.config import load_config
from core.file_manager import save_caption_file
from extractors import get_extractor_for_url


def parse_batch_input(raw_input: str) -> list[str]:
    """
    Parses raw user input (single URL, space/comma/newline-separated URLs, or a .txt file path)
    into a deduplicated list of URL strings preserving input order.
    """
    cleaned = (raw_input or "").strip()
    if not cleaned:
        return []

    # Check if input is a path to an existing .txt batch file
    unquoted = cleaned.strip('"').strip("'")
    if unquoted.lower().endswith(".txt"):
        p = Path(unquoted)
        if p.exists() and p.is_file():
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            extracted = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                for token in re.split(r"[\s,;]+", line):
                    if token:
                        extracted.append(token)
            return list(dict.fromkeys(extracted))

    tokens = [tok.strip() for tok in re.split(r"[\s,;]+", cleaned) if tok.strip()]
    return list(dict.fromkeys(tokens))


def validate_batch_urls(
    urls: list[str],
    extractor_cls: type | None = None
) -> tuple[list[tuple[Any, str]], list[tuple[str, str]]]:
    """
    Validates each URL against either a specific extractor class or auto-detection.
    Returns (valid_targets, invalid_entries).
    """
    valid_targets: list[tuple[Any, str]] = []
    invalid_entries: list[tuple[str, str]] = []

    for url in urls:
        extractor = extractor_cls() if extractor_cls else get_extractor_for_url(url)
        if not extractor:
            invalid_entries.append((url, "Unsupported platform or invalid URL"))
            continue

        ok, norm_url, reason = extractor.validate_url(url)
        if not ok:
            invalid_entries.append((url, reason or "Invalid URL"))
            continue

        valid_targets.append((extractor, norm_url))

    return valid_targets, invalid_entries


def execute_batch_download(
    targets: list[tuple[Any, str]],
    options: dict[str, Any] | None = None,
    on_item_start: Callable[[int, int, Any, str], None] | None = None,
    on_item_done: Callable[[int, int, str, bool, list[Path]], None] | None = None,
) -> dict[str, Any]:
    """
    Executes sequential downloads for a validated list of (extractor, normalized_url) pairs.
    Returns a summary dict with succeeded, failed, and files lists.
    """
    base_opts = dict(options or {})
    succeeded: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    all_files: list[Path] = []
    total = len(targets)

    for idx, (extractor, norm_url) in enumerate(targets, 1):
        if on_item_start:
            on_item_start(idx, total, extractor, norm_url)

        item = extractor.fetch_metadata(norm_url)
        if not item:
            failed.append({"url": norm_url, "reason": "Could not retrieve metadata"})
            if on_item_done:
                on_item_done(idx, total, norm_url, False, [])
            continue

        item_opts = dict(base_opts)
        if item.items and len(item.items) > 1 and "selected_indices" not in item_opts:
            item_opts["selected_indices"] = list(range(1, len(item.items) + 1))

        ok, files = extractor.download(item, item_opts)
        if ok:
            save_cap = item_opts.get("save_caption")
            if save_cap is None:
                save_cap = load_config().get("save_caption", True)
            if save_cap:
                save_caption_file(item, files)
            succeeded.append({"url": norm_url, "title": item.title, "files": files})
            all_files.extend(files)
        else:
            failed.append({"url": norm_url, "reason": "Download failed"})

        if on_item_done:
            on_item_done(idx, total, norm_url, ok, files)

    return {
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "files": all_files,
    }
