"""Claude Agent SDK(구독 로그인 인증)로 영상을 분석한다."""

import asyncio
import base64
import json
import re

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

SYSTEM_PROMPT = """너는 유튜브 콘텐츠 전략 분석가다.
주어진 영상이 왜 조회수가 많이 나왔는지를 기준으로 분석한다.
일반론이 아니라 이 영상의 썸네일, 제목, 자막 내용에서 근거를 찾아 구체적으로 설명한다.
답은 한국어로, 지정된 JSON 형식으로만 한다."""

INSTRUCTIONS = """아래 영상을 분석해줘. 분석의 기준은 "이 영상이 왜 조회수가 많이 나왔는가"야.
한눈에 볼 수 있게 짧게 써야 해. 모든 항목은 한 문장, 40자 안팎으로. 마크다운 기호는 쓰지 마.

반드시 아래 JSON 하나만 출력해. 코드 블록이나 다른 말은 붙이지 마.

{
  "one_line": "조회수가 많이 나온 핵심 이유 한 문장 (50자 이내)",
  "reasons": [
    {"title": "이유를 4~8자로", "detail": "근거 한 문장"},
    {"title": "...", "detail": "..."},
    {"title": "...", "detail": "..."}
  ],
  "scores": {"thumbnail": 1~10 정수, "title": 1~10 정수, "content": 1~10 정수},
  "thumbnail": ["썸네일이 클릭을 부르는 포인트 3개"],
  "content": ["시청을 붙잡는 내용 포인트 3~4개 (도입부 훅, 구성, 시청 유지 장치, 타깃)"],
  "summary": ["영상 흐름을 순서대로 3~5줄"],
  "takeaways": ["비슷한 영상을 만들 때 따라 할 점 3개"]
}

reasons는 중요한 순서대로 정확히 3개. scores는 이 영상의 조회수에 각 요소가 얼마나 기여했는지야."""


def _fmt_num(n):
    return f"{n:,}" if isinstance(n, int) else "알 수 없음"


def _build_text(d: dict) -> str:
    ratio = ""
    if d.get("views") and d.get("subscribers"):
        ratio = f"(구독자 대비 조회수 {d['views'] / d['subscribers']:.1f}배)"
    minutes = f"{d['duration'] // 60}분 {d['duration'] % 60}초" if d.get("duration") else "알 수 없음"
    transcript = d["transcript"] or "(자막을 찾지 못함. 제목, 설명, 썸네일로만 분석할 것)"
    if d.get("transcript_truncated"):
        transcript += "\n(자막이 길어서 뒷부분은 잘림)"
    return f"""{INSTRUCTIONS}

## 영상 정보
- 제목: {d['title']}
- 채널: {d['channel']} (구독자 {_fmt_num(d.get('subscribers'))})
- 조회수: {_fmt_num(d.get('views'))} {ratio}
- 좋아요: {_fmt_num(d.get('likes'))} / 댓글: {_fmt_num(d.get('comments'))}
- 길이: {minutes} / 업로드: {d.get('upload_date') or '알 수 없음'}
- 태그: {', '.join(d.get('tags') or []) or '없음'}

## 영상 설명
{d.get('description') or '없음'}

## 자막 ({d['subtitle_info']})
{transcript}

첨부한 이미지는 이 영상의 썸네일이야."""


def _parse(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {"one_line": "", "reasons": [], "scores": {}, "thumbnail": [], "content": [text],
            "summary": [], "takeaways": []}


async def _analyze(d: dict) -> dict:
    content = []
    if d.get("thumbnail_bytes"):
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg",
                       "data": base64.b64encode(d["thumbnail_bytes"]).decode()},
        })
    content.append({"type": "text", "text": _build_text(d)})

    async def prompt():
        yield {"type": "user", "message": {"role": "user", "content": content},
               "parent_tool_use_id": None}

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        tools=[],              # 파일·명령 도구 없이 분석만 한다
        setting_sources=[],    # 사용자 설정·CLAUDE.md를 불러오지 않는다
        max_turns=1,
    )

    texts, error = [], None
    async for msg in query(prompt=prompt(), options=options):
        if isinstance(msg, AssistantMessage):
            texts += [b.text for b in msg.content if isinstance(b, TextBlock)]
        elif isinstance(msg, ResultMessage) and msg.is_error:
            error = msg.result or msg.subtype
    if error and not texts:
        raise RuntimeError(f"Claude 분석 실패: {error}")
    return _parse("".join(texts))


def analyze(details: dict) -> dict:
    return asyncio.run(_analyze(details))
