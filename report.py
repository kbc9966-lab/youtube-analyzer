"""분석 결과를 저장하고, 여러 영상의 결과를 요약 보고서(Markdown/HTML)로 만든다."""

import json
from datetime import datetime
from pathlib import Path

import markdown

RESULTS_DIR = Path(__file__).parent / "results"


def save(video: dict, analysis: dict) -> dict:
    RESULTS_DIR.mkdir(exist_ok=True)
    record = {"video": video, "analysis": analysis,
              "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
    (RESULTS_DIR / f"{video['id']}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def _is_current(record: dict) -> bool:
    """요약 형식(one_line)으로 바뀌기 전에 저장된 결과는 다시 분석하도록 없는 것으로 친다."""
    return "one_line" in (record.get("analysis") or {})


def load(video_id: str) -> dict | None:
    path = RESULTS_DIR / f"{video_id}.json"
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    return record if _is_current(record) else None


def load_all() -> list[dict]:
    """저장된 분석 결과를 최근 분석한 순서로 돌려준다."""
    if not RESULTS_DIR.exists():
        return []
    records = [json.loads(p.read_text(encoding="utf-8")) for p in RESULTS_DIR.glob("*.json")]
    records = [r for r in records if _is_current(r)]
    records.sort(key=lambda r: r.get("analyzed_at", ""), reverse=True)
    return records


def delete(video_id: str) -> None:
    (RESULTS_DIR / f"{video_id}.json").unlink(missing_ok=True)


def _num(n):
    return f"{n:,}" if isinstance(n, int) else "-"


def _ratio(v):
    if v.get("views") and v.get("subscribers"):
        return f"{v['views'] / v['subscribers']:.1f}배"
    return "-"


SCORE_LABELS = {"thumbnail": "썸네일", "title": "제목", "content": "내용"}


def _bullets(items) -> list[str]:
    return [f"- {x}" for x in items or []] or ["- -"]


def build_markdown(records: list[dict], full: bool = False) -> str:
    """요약 보고서. full=True면 썸네일·내용 포인트와 내용 흐름까지 넣는다."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    out = ["# 유튜브 영상 분석 보고서", "",
           f"- 작성: {now}", f"- 영상 수: {len(records)}개",
           "- 분석 기준: 조회수가 많이 나온 이유", ""]

    out += ["## 한눈에 보기", "",
            "| # | 제목 | 조회수 | 구독자 대비 | 핵심 이유 |",
            "|---|---|---:|---:|---|"]
    for i, r in enumerate(records, 1):
        v, a = r["video"], r["analysis"]
        cell = lambda t: (t or "-").replace("|", "/")
        out.append(f"| {i} | [{cell(v['title'])}]({v['url']}) | {_num(v.get('views'))} | "
                   f"{_ratio(v)} | {cell(a.get('one_line'))} |")
    out.append("")

    for i, r in enumerate(records, 1):
        v, a = r["video"], r["analysis"]
        scores = a.get("scores") or {}
        score_line = " · ".join(f"{label} {scores[k]}/10" for k, label in SCORE_LABELS.items() if k in scores)
        out += [f"## {i}. {v['title']}", "",
                f"![썸네일]({v['thumbnail_url']})", "",
                f"- 채널: {v['channel']} (구독자 {_num(v.get('subscribers'))})",
                f"- 조회수: {_num(v.get('views'))} (구독자 대비 {_ratio(v)}) · 댓글 {_num(v.get('comments'))}",
                f"- 업로드: {v.get('upload_date') or '-'} · 링크: {v['url']}"]
        if score_line:
            out.append(f"- 점수: {score_line}")
        out += ["", f"**핵심: {a.get('one_line') or '-'}**", "",
                "### 조회수가 나온 이유 TOP 3", ""]
        out += [f"{n}. **{x.get('title', '')}**: {x.get('detail', '')}"
                for n, x in enumerate(a.get("reasons") or [], 1)] or ["-"]
        out += ["", "### 따라 할 점", "", *_bullets(a.get("takeaways")), ""]
        if full:
            out += ["### 썸네일 포인트", "", *_bullets(a.get("thumbnail")), "",
                    "### 내용 포인트", "", *_bullets(a.get("content")), "",
                    "### 내용 흐름", "", *_bullets(a.get("summary")), ""]
        out += ["---", ""]
    return "\n".join(out)


HTML_TEMPLATE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>유튜브 영상 분석 보고서</title>
<style>
/* 화면에서는 어두운 테마, 인쇄(PDF 저장)할 때는 흰 바탕 */
:root {{ color-scheme: dark; --bg: #161615; --text: #ececea; --line: #34342f; --head: #20201f;
  --accent: #ff5a52; --link: #8ab4f8; }}
body {{ font-family: "Pretendard", "Malgun Gothic", system-ui, sans-serif; line-height: 1.7;
  color: var(--text); background: var(--bg); max-width: 860px; margin: 0 auto; padding: 32px 20px 80px; }}
h1 {{ border-bottom: 3px solid var(--accent); padding-bottom: 8px; }}
h2 {{ margin-top: 48px; padding-top: 12px; border-top: 1px solid var(--line); }}
h3 {{ color: var(--accent); margin-bottom: 4px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
th, td {{ border: 1px solid var(--line); padding: 6px 8px; text-align: left; }}
th {{ background: var(--head); }}
img {{ max-width: 420px; width: 100%; border-radius: 8px; }}
a {{ color: var(--link); }}
hr {{ display: none; }}
@media print {{
  :root {{ color-scheme: light; --bg: #fff; --text: #1d1d1b; --line: #e3e3de; --head: #f6f6f4;
    --accent: #e5322d; --link: #1a5fb4; }}
  h2 {{ page-break-before: always; }} h2:first-of-type {{ page-break-before: auto; }}
}}
</style></head>
<body>{body}</body></html>"""


def build_html(records: list[dict], full: bool = False) -> str:
    body = markdown.markdown(build_markdown(records, full), extensions=["tables"])
    return HTML_TEMPLATE.format(body=body)
