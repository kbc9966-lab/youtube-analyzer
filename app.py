"""유튜브 분석기 웹 서버. 실행: python app.py → http://127.0.0.1:5000"""

import re
from datetime import datetime
from urllib.parse import quote

from flask import Flask, Response, jsonify, render_template, request

import analyzer
import report
import youtube

app = Flask(__name__)
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/search")
def api_search():
    keyword = (request.args.get("keyword") or "").strip()
    if not keyword:
        return jsonify(error="키워드를 입력해 주세요."), 400
    try:
        min_views = int(request.args.get("min_views") or 0)
        limit = max(10, min(int(request.args.get("limit") or 50), 200))
    except ValueError:
        return jsonify(error="조회수와 검색 개수는 숫자로 입력해 주세요."), 400
    try:
        videos = youtube.search(keyword, min_views, limit)
    except Exception as e:
        return jsonify(error=f"검색 실패: {e}"), 500
    analyzed = {r["video"]["id"] for r in report.load_all()}
    for v in videos:
        v["analyzed"] = v["id"] in analyzed
    return jsonify(videos=videos)


@app.get("/analyze/<video_id>")
def analyze_page(video_id):
    if not VIDEO_ID.match(video_id):
        return "잘못된 영상 ID", 400
    return render_template("analyze.html", video_id=video_id)


@app.post("/api/analyze/<video_id>")
def api_analyze(video_id):
    if not VIDEO_ID.match(video_id):
        return jsonify(error="잘못된 영상 ID"), 400
    body = request.get_json(silent=True) or {}

    # 이미 분석한 영상은 저장된 결과를 보여준다 (다시 분석을 누르면 새로 분석)
    saved = report.load(video_id)
    if saved and not body.get("refresh"):
        return jsonify(**saved, cached=True)

    title = (body.get("title") or "")[:300] or (saved["video"]["title"] if saved else "")
    try:
        details = youtube.get_details(video_id, title)
    except Exception as e:
        return jsonify(error=f"영상 정보를 가져오지 못했어요: {e}"), 500
    try:
        result = analyzer.analyze(details)
    except Exception as e:
        return jsonify(error=f"AI 분석 실패: {e}. 로그인.bat으로 Claude 로그인이 되어 있는지 확인해 주세요."), 500

    details.pop("thumbnail_bytes", None)
    transcript = details.pop("transcript")
    details["transcript_chars"] = len(transcript)
    return jsonify(**report.save(details, result), cached=False)


@app.get("/report")
def report_page():
    return render_template("report.html")


@app.get("/api/results")
def api_results():
    return jsonify(results=report.load_all())


@app.delete("/api/results/<video_id>")
def api_delete_result(video_id):
    if not VIDEO_ID.match(video_id):
        return jsonify(error="잘못된 영상 ID"), 400
    report.delete(video_id)
    return jsonify(ok=True)


@app.get("/report/download")
def report_download():
    """ids=영상ID,영상ID&format=html|md&full=1 → 보고서 파일 다운로드"""
    ids = [i for i in (request.args.get("ids") or "").split(",") if VIDEO_ID.match(i)]
    records = [r for r in (report.load(i) for i in ids) if r]
    if not records:
        return "보고서에 넣을 분석 결과가 없어요.", 400
    full = request.args.get("full") == "1"
    fmt = request.args.get("format", "html")

    if fmt == "md":
        content, mime, ext = report.build_markdown(records, full), "text/markdown", "md"
    else:
        content, mime, ext = report.build_html(records, full), "text/html", "html"
    name = f"유튜브분석보고서_{datetime.now():%Y%m%d_%H%M}.{ext}"
    return Response(content, content_type=f"{mime}; charset=utf-8", headers={
        "Content-Disposition": f"attachment; filename=report.{ext}; filename*=UTF-8''{quote(name)}"})


if __name__ == "__main__":
    print("유튜브 분석기: http://127.0.0.1:5000 을 브라우저로 여세요.")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
