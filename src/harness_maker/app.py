"""웹 API: 설문(ko/en) + MCP 카탈로그 제공, 답변 → 하네스 zip 다운로드.

실행:
    harness-factory            # 콘솔 스크립트
    uvicorn harness_maker.app:app --reload
엔드포인트:
    GET  /                     -> 4단계 위저드(정적 HTML)
    GET  /api/survey?lang=ko   -> 설문 스키마 + MCP 카탈로그(JSON)
    POST /api/generate         -> 답변(JSON, lang 포함) → 하네스 zip 다운로드
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from urllib.parse import quote

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from .engine import ValidationError, generate_zip, load_catalog, load_schema


def _data_root() -> Path:
    """설문/카탈로그/템플릿이 있는 디렉터리. 비편집(non-editable) 설치·Docker에서도 동작하도록 해석한다."""
    env = os.environ.get("HARNESS_FACTORY_ROOT")
    if env:
        return Path(env)
    p = Path(__file__).resolve().parents[2]   # editable 설치: 레포 루트
    if (p / "survey.ko.yaml").exists():
        return p
    return Path.cwd()                          # 그 외: 실행 디렉터리


ROOT = _data_root()
CATALOG_PATH = ROOT / "mcp_catalog.yaml"
STATIC_DIR = Path(__file__).resolve().parent / "static"

LANGS = ("ko", "en")
SURVEY_PATHS = {"ko": ROOT / "survey.ko.yaml", "en": ROOT / "survey.en.yaml"}
TEMPLATE_DIRS = {"ko": ROOT / "template" / "ko", "en": ROOT / "template" / "en"}

app = FastAPI(title="Harness Factory", version="0.4.0")


class GenerateRequest(BaseModel):
    answers: dict[str, object]
    project_slug: str = "harness"
    lang: str = "ko"


def _lang(value: str) -> str:
    return value if value in LANGS else "ko"


def _localized_catalog(lang: str) -> list[dict]:
    """카탈로그의 description을 요청 언어로 맞춘다(en이면 description_en 사용)."""
    catalog = load_catalog(CATALOG_PATH) if CATALOG_PATH.exists() else []
    if lang == "en":
        for s in catalog:
            if s.get("description_en"):
                s = s  # noqa
                s["description"] = s["description_en"]
    return catalog


@app.get("/api/survey")
def get_survey(lang: str = "ko") -> dict:
    """UI 렌더링용: 해당 언어의 설문 스키마(steps) + MCP 카탈로그를 반환한다."""
    lang = _lang(lang)
    path = SURVEY_PATHS[lang]
    if not path.exists():
        raise HTTPException(500, f"{path.name}을 찾을 수 없습니다.")
    survey = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    survey["lang"] = lang
    survey["mcp_catalog"] = _localized_catalog(lang)
    return survey


@app.post("/api/generate")
def generate(req: GenerateRequest) -> StreamingResponse:
    """답변을 검증·치환하고 MCP 설정을 생성해 zip을 스트리밍 다운로드로 반환한다."""
    lang = _lang(req.lang)
    schema = load_schema(SURVEY_PATHS[lang])
    catalog = load_catalog(CATALOG_PATH) if CATALOG_PATH.exists() else []
    slug = "".join(c for c in req.project_slug if c.isascii() and (c.isalnum() or c in "-_")) or "harness"
    try:
        data = generate_zip(TEMPLATE_DIRS[lang], req.answers, schema, catalog=catalog, root_dir=slug)
    except ValidationError as e:
        raise HTTPException(422, detail=str(e))
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
