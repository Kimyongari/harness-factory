FROM python:3.12-slim

WORKDIR /app

# 의존성 레이어 캐시: 메타데이터 먼저 복사
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

# 런타임에 필요한 데이터(설문/카탈로그/템플릿)
COPY survey.ko.yaml survey.en.yaml mcp_catalog.yaml checks_catalog.yaml ./
COPY template ./template

ENV HOST=0.0.0.0 PORT=8000 HARNESS_FACTORY_ROOT=/app
EXPOSE 8000

CMD ["harness-factory"]
