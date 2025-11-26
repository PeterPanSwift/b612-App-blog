#!/usr/bin/env python3
"""Collect Medium export post metadata into JSON for the Little Prince UI."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "posts"
OUTPUT_PATH = BASE_DIR / "posts_summary.json"


def is_comment(title: str, body_text: str) -> bool:
    """判斷是否為留言而非文章。
    
    留言的特徵是標題和內文幾乎相同。
    """
    # 標題和內文完全相同
    if title == body_text:
        return True
    # 內文以標題開頭，且內文長度不超過標題太多（留言通常很短）
    if body_text.startswith(title) and len(body_text) < len(title) + 50:
        return True
    return False


def load_posts(directory: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    for html_path in sorted(directory.glob("*.html")):
        if html_path.name.startswith("draft_"):
            continue

        with html_path.open(encoding="utf-8") as handle:
            soup = BeautifulSoup(handle, "html.parser")

        body_section = soup.find("section", attrs={"data-field": "body"})
        if not body_section:
            continue

        title_tag = soup.find("h1", class_="p-name")
        time_tag = soup.find("time", class_="dt-published")

        if not title_tag or not time_tag:
            # Skip files that do not have the expected structure.
            continue

        title = title_tag.get_text(strip=True)
        iso_datetime = time_tag.get("datetime")
        display_date = time_tag.get_text(strip=True)
        subtitle_section = soup.find("section", attrs={"data-field": "subtitle"})
        subtitle = subtitle_section.get_text(strip=True) if subtitle_section else ""
        body_text = body_section.get_text(" ", strip=True)

        # 過濾留言：標題和內文幾乎相同的是留言而非文章
        body_text_stripped = body_section.get_text(strip=True)
        if is_comment(title, body_text_stripped):
            continue

        if iso_datetime:
            sort_key = parse_datetime(iso_datetime)
            date_value = iso_datetime
        else:
            sort_key = datetime.min
            date_value = display_date

        records.append(
            {
                "title": title,
                "date": date_value,
                "subtitle": subtitle,
                "path": f"posts/{html_path.name}",
                "content": body_text,
                "_sort_key": sort_key,
            }
        )

    records.sort(key=lambda entry: entry["_sort_key"], reverse=True)

    for record in records:
        record.pop("_sort_key", None)

    return records


def parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min


if __name__ == "__main__":
    if not POSTS_DIR.exists():
        raise SystemExit(f"Posts directory not found: {POSTS_DIR}")

    posts = load_posts(POSTS_DIR)

    OUTPUT_PATH.write_text(
        json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Wrote {len(posts)} posts to {OUTPUT_PATH}")
