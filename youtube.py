"""yt-dlp로 유튜브 검색, 영상 정보, 자막, 썸네일을 가져온다."""

import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import yt_dlp

YDL_BASE = {"quiet": True, "no_warnings": True, "skip_download": True}
# 유튜브는 기본(영어) 요청에 일부 한국 영상 제목을 영어로 자동 번역해서 보낸다.
# 한국어로 요청하면 원래 제목이 오지만 조회수는 비어 있어서, 제목만 이 요청에서 가져온다.
YDL_KO = {**YDL_BASE, "extract_flat": "in_playlist", "logger": None,
          "extractor_args": {"youtube": {"lang": ["ko"]}}}


class _Quiet:
    """한국어 요청 때 yt-dlp가 내는 '번역 필드 사용' 경고를 숨긴다."""
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


YDL_KO["logger"] = _Quiet()


def _korean_titles(query: str) -> dict[str, str]:
    """검색어(또는 영상 ID)로 한국어 기준 검색을 해서 {영상ID: 원래 제목}을 돌려준다."""
    try:
        with yt_dlp.YoutubeDL(YDL_KO) as ydl:
            result = ydl.extract_info(f"ytsearch{query}", download=False)
        return {e["id"]: e["title"] for e in result.get("entries") or [] if e.get("id") and e.get("title")}
    except Exception:
        return {}


def original_title(video_id: str) -> str:
    """영상 ID로 한국어 원래 제목을 찾는다. 못 찾으면 빈 문자열."""
    return _korean_titles(f"5:{video_id}").get(video_id, "")

# 자막 언어 우선순위: 한국어 수동 자막 → 한국어 자동 자막 → 영어
SUB_LANGS = ["ko", "ko-KR", "ko-orig", "en", "en-US", "en-orig"]
MAX_TRANSCRIPT_CHARS = 40000


def search(keyword: str, min_views: int, limit: int = 50) -> list[dict]:
    """키워드로 검색해서 조회수가 min_views 이상인 영상만 조회수 순으로 돌려준다."""
    def english_search():
        with yt_dlp.YoutubeDL({**YDL_BASE, "extract_flat": "in_playlist"}) as ydl:
            return ydl.extract_info(f"ytsearch{limit}:{keyword}", download=False)

    # 조회수용(영어) 검색과 제목용(한국어) 검색을 동시에 돌린다
    with ThreadPoolExecutor(2) as pool:
        en = pool.submit(english_search)
        ko = pool.submit(_korean_titles, f"{limit}:{keyword}")
        result, ko_titles = en.result(), ko.result()

    videos = []
    for e in result.get("entries") or []:
        views = e.get("view_count")
        if not e.get("id") or views is None or views < min_views:
            continue
        if e.get("live_status") == "is_live":
            continue
        videos.append({
            "id": e["id"],
            "title": ko_titles.get(e["id"]) or e.get("title") or "",
            "channel": e.get("channel") or e.get("uploader") or "",
            "views": views,
            "duration": e.get("duration"),
            "thumbnail": f"https://i.ytimg.com/vi/{e['id']}/mqdefault.jpg",
        })
    videos.sort(key=lambda v: v["views"], reverse=True)
    return videos


def _pick_track(tracks: dict) -> tuple[str, str] | None:
    """자막 목록에서 우선순위에 맞는 json3 자막 URL을 고른다."""
    for lang in SUB_LANGS:
        for f in tracks.get(lang) or []:
            if f.get("ext") == "json3":
                return lang, f["url"]
    return None


def _json3_to_text(data: dict) -> str:
    lines = []
    for ev in data.get("events") or []:
        text = "".join(s.get("utf8", "") for s in ev.get("segs") or []).strip()
        if text and text != "\n":
            lines.append(text)
    text = " ".join(lines)
    return re.sub(r"\s+", " ", text).strip()


def _download_thumbnail(video_id: str) -> bytes | None:
    for name in ("maxresdefault.jpg", "sddefault.jpg", "hqdefault.jpg"):
        try:
            with urllib.request.urlopen(f"https://i.ytimg.com/vi/{video_id}/{name}", timeout=15) as r:
                data = r.read()
                if len(data) > 2000:  # 이미지가 없을 때 오는 작은 회색 이미지는 건너뛴다
                    return data
        except Exception:
            continue
    return None


def get_details(video_id: str, title: str = "") -> dict:
    """분석에 필요한 영상 정보, 자막, 썸네일을 모은다.

    영상 페이지에서는 번역된(영어) 제목이 올 때가 있어서, 검색 결과의 원래 제목을 title로 받으면 그걸 쓰고,
    없으면 한국어 기준 검색으로 원래 제목을 찾는다.
    """
    title = title or original_title(video_id)
    opts = YDL_BASE
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

        transcript, sub_kind, sub_lang = "", None, None
        for kind, tracks in (("수동 자막", info.get("subtitles") or {}),
                             ("자동 생성 자막", info.get("automatic_captions") or {})):
            picked = _pick_track(tracks)
            if not picked:
                continue
            try:
                raw = ydl.urlopen(picked[1]).read().decode("utf-8")
                transcript = _json3_to_text(json.loads(raw))
            except Exception:
                transcript = ""
            if transcript:
                sub_kind, sub_lang = kind, picked[0]
                break

    truncated = len(transcript) > MAX_TRANSCRIPT_CHARS
    upload = info.get("upload_date") or ""
    return {
        "id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": title or info.get("title") or "",
        "channel": info.get("channel") or info.get("uploader") or "",
        "subscribers": info.get("channel_follower_count"),
        "views": info.get("view_count"),
        "likes": info.get("like_count"),
        "comments": info.get("comment_count"),
        "duration": info.get("duration"),
        "upload_date": f"{upload[:4]}-{upload[4:6]}-{upload[6:]}" if len(upload) == 8 else "",
        "description": (info.get("description") or "")[:3000],
        "tags": (info.get("tags") or [])[:30],
        "transcript": transcript[:MAX_TRANSCRIPT_CHARS],
        "transcript_truncated": truncated,
        "subtitle_info": f"{sub_kind} ({sub_lang})" if sub_kind else "자막 없음",
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "thumbnail_bytes": _download_thumbnail(video_id),
    }
