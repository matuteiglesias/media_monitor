from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import requests

API_ROOT = "https://www.googleapis.com/youtube/v3"
_DURATION_RE = re.compile(r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$")


def parse_iso8601_duration(value: str | None) -> int | None:
    if not value:
        return None
    match = _DURATION_RE.match(value)
    if not match:
        raise ValueError(f"unsupported YouTube duration {value!r}")
    parts = {name: int(number or 0) for name, number in match.groupdict().items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]


def _int_or_none(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(str(value))


@dataclass(frozen=True)
class ChannelInfo:
    channel_id: str
    title: str
    canonical_url: str
    uploads_playlist_id: str


@dataclass(frozen=True)
class UploadRef:
    video_id: str
    title: str
    description: str
    published_at: str


@dataclass(frozen=True)
class VideoObservation:
    video_id: str
    title: str
    description: str
    published_at: str
    duration_seconds: int | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    availability: str


class YouTubeDataClient:
    """Minimal official YouTube Data API v3 client for channel reconciliation."""

    def __init__(self, api_key: str, *, timeout: float = 20.0, session: requests.Session | None = None) -> None:
        api_key = api_key.strip()
        if not api_key:
            raise ValueError("YouTube Data API key is required")
        self.api_key = api_key
        self.timeout = timeout
        self.session = session or requests.Session()
        self.api_calls = 0
        self.quota_units_estimated = 0

    def _get(self, resource: str, params: dict[str, object]) -> dict:
        query = {**params, "key": self.api_key}
        response = self.session.get(f"{API_ROOT}/{resource}", params=query, timeout=self.timeout)
        self.api_calls += 1
        self.quota_units_estimated += 1
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"unexpected YouTube {resource} response")
        return payload

    def fetch_channel(self, channel_id: str) -> ChannelInfo:
        payload = self._get("channels", {"part": "snippet,contentDetails", "id": channel_id, "maxResults": 1})
        items = payload.get("items") or []
        if len(items) != 1:
            raise LookupError(f"YouTube channel {channel_id!r} was not returned")
        item = items[0]
        returned_id = str(item.get("id") or "")
        if returned_id != channel_id:
            raise ValueError(f"channel identity mismatch: requested {channel_id}, got {returned_id}")
        snippet = item.get("snippet") or {}
        content = item.get("contentDetails") or {}
        related = content.get("relatedPlaylists") or {}
        uploads = str(related.get("uploads") or "")
        title = str(snippet.get("title") or "").strip()
        if not title or not uploads:
            raise ValueError(f"channel {channel_id} lacks title/uploads playlist")
        return ChannelInfo(channel_id, title, f"https://www.youtube.com/channel/{channel_id}", uploads)

    def fetch_upload_refs(self, uploads_playlist_id: str, *, limit: int) -> list[UploadRef]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        refs: list[UploadRef] = []
        token: str | None = None
        while len(refs) < limit:
            params: dict[str, object] = {"part": "contentDetails,snippet", "playlistId": uploads_playlist_id, "maxResults": min(50, limit - len(refs))}
            if token:
                params["pageToken"] = token
            payload = self._get("playlistItems", params)
            for item in payload.get("items") or []:
                content = item.get("contentDetails") or {}
                snippet = item.get("snippet") or {}
                video_id = str(content.get("videoId") or "").strip()
                if not video_id:
                    continue
                title = str(snippet.get("title") or "").strip()
                description = str(snippet.get("description") or "")
                published_at = str(content.get("videoPublishedAt") or snippet.get("publishedAt") or "").strip()
                if not title or not published_at:
                    continue
                refs.append(UploadRef(video_id, title, description, published_at))
                if len(refs) >= limit:
                    break
            token = payload.get("nextPageToken")
            if not token:
                break
        seen: set[str] = set()
        unique: list[UploadRef] = []
        for ref in refs:
            if ref.video_id in seen:
                continue
            seen.add(ref.video_id)
            unique.append(ref)
        return unique

    def fetch_videos(self, refs: Iterable[UploadRef]) -> list[VideoObservation]:
        ordered = list(refs)
        details: dict[str, dict] = {}
        for start in range(0, len(ordered), 50):
            batch = ordered[start : start + 50]
            payload = self._get("videos", {"part": "snippet,contentDetails,statistics,status", "id": ",".join(ref.video_id for ref in batch), "maxResults": len(batch)})
            for item in payload.get("items") or []:
                video_id = str(item.get("id") or "")
                if video_id:
                    details[video_id] = item
        observations: list[VideoObservation] = []
        for ref in ordered:
            item = details.get(ref.video_id)
            if item is None:
                observations.append(VideoObservation(ref.video_id, ref.title, ref.description, ref.published_at, None, None, None, None, "unavailable"))
                continue
            snippet = item.get("snippet") or {}
            content = item.get("contentDetails") or {}
            statistics = item.get("statistics") or {}
            status = item.get("status") or {}
            privacy = str(status.get("privacyStatus") or "unknown")
            availability = "public" if privacy == "public" else privacy if privacy in {"private"} else "unknown"
            observations.append(VideoObservation(ref.video_id, str(snippet.get("title") or ref.title).strip() or ref.title, str(snippet.get("description") if snippet.get("description") is not None else ref.description), str(snippet.get("publishedAt") or ref.published_at), parse_iso8601_duration(content.get("duration")), _int_or_none(statistics.get("viewCount")), _int_or_none(statistics.get("likeCount")), _int_or_none(statistics.get("commentCount")), availability))
        return observations
