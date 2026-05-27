"""웹 API: 설문 스키마 + MCP 카탈로그 제공, 답변 → 하네스 zip 다운로드.

실행:
    uvicorn harness_maker.app:app --reload
엔드포인트:
    GET  /                -> 4단계 설문 위저드(정적 HTML)
    GET  /api/survey      -> 설문 스키마 + MCP 카탈로그(JSON)
    POST /api/generate    -> 답변(JSON) → 하네스 zip 다운로드
"""

from __future__ import annotations

import io
from pathlib import Path
from urllib.parse import quote

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from .engine import ValidationError, generate_zip, load_catalog, load_schema

ROOT = Path(__file__).resolve().parents[2]
SURVEY_PATH = ROOT / "survey.yaml"
CATALOG_PATH = ROOT / "mcp_catalog.yaml"
TEMPLATE_DIR = ROOT / "template"
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Harness Maker", version="0.2.0")


class GenerateRequest(BaseModel):
    answers: dict[str, object]
    project_slug: str = "harness"


@app.get("/api/survey")
def get_survey() -> dict:
    """UI 렌더링용: 설문 스키마(steps) + MCP 카탈로그를 함께 반환한다."""
    if not SURVEY_PATH.exists():
        raise HTTPException(500, "survey.yaml을 찾을 수 없습니다.")
    survey = yaml.safe_load(SURVEY_PATH.read_text(encoding="utf-8")) or {}
    survey["mcp_catalog"] = load_catalog(CATALOG_PATH) if CATALOG_PATH.exists() else []
    return survey


@app.post("/api/generate")
def generate(req: GenerateRequest) -> StreamingResponse:
    """답변을 검증·치환하고 MCP 설정을 생성해 zip을 스트리밍 다운로드로 반환한다."""
    schema = load_schema(SURVEY_PATH)
    catalog = load_catalog(CATALOG_PATH) if CATALOG_PATH.exists() else []
    # zip 내부 루트 폴더는 안전한 ASCII slug로(파일시스템/헤더 호환).
    slug = "".join(c for c in req.project_slug if c.isascii() and (c.isalnum() or c in "-_")) or "harness"
    try:
        data = generate_zip(TEMPLATE_DIR, req.answers, schema, catalog=catalog, root_dir=slug)
    except ValidationError as e:
        raise HTTPException(422, detail=str(e))
    # 다운로드 파일명: ASCII fallback + RFC 5987 filename*(유니코드 보존).
    display = (req.project_slug or slug).strip() or slug
    disposition = (
        f'attachment; filename="{slug}.zip"; '
        f"filename*=UTF-8''{quote(display + '.zip')}"
    )
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": disposition},
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


def serve() -> None:
    """콘솔 스크립트 진입점: `harness-factory` 명령으로 서버를 띄운다."""
    import os

    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Harness Factory → http://{host}:{port}")
    uvicorn.run("harness_maker.app:app", host=host, port=port)
