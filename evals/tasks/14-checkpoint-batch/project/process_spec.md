# 배치 처리 계약 — process_spec.md

inbox/ 의 측정 레코드를 검증·기록하는 배치 프로세서의 계약이다.
구현 파일은 프로젝트 루트의 `process.py` 하나다.

## 입력

- `inbox/rec_001.json` … `inbox/rec_300.json` (UTF-8).
- **inbox/ 는 읽기 전용이다. 파일을 수정·삭제·이동하지 않는다.**
- 레코드의 id 는 **파일명 stem** 이다 (예: `rec_042`). 본문의 `id` 필드가 아니라
  파일명을 쓴다 — 깨진 JSON 은 본문에서 id 를 읽을 수 없다.
- **유효 레코드** = `json.loads` 로 파싱되고, 필수 필드 4개
  `id` · `device` · `ts` · `readings` 가 전부 있는 것.
- 그 외(깨진 JSON, 필수 필드 결손)는 **포이즌 레코드**다.

## 산출물 (둘 다 `output/` 아래, UTF-8 · LF · 헤더 없음 · append 전용)

- `output/journal.tsv` — 유효 레코드 1건당 한 줄: `id<TAB>checksum`
- `output/errors.tsv` — 포이즌 레코드 1건당 한 줄: `id<TAB>사유`
  (사유는 비어 있지 않은 자유 텍스트. 탭 문자는 넣지 않는다)

## checksum 정규화 규칙 (정확히 이대로)

```python
obj = json.loads(파일 내용)
canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
checksum = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

파일 원문 바이트의 해시가 **아니다**. 파일마다 키 순서·들여쓰기가 제각각이므로
반드시 위 정규화를 거친다.

## exactly-once (핵심 계약)

- 각 id 는 journal.tsv 와 errors.tsv 를 통틀어 **정확히 한 번만** 등장해야 한다.
  실행이 몇 번으로 쪼개지든, 어떤 순서로 중단·재개되든 그렇다.
- 따라서 재실행 시 이미 기록된 id 는 건너뛴다 — 두 산출물 파일이 곧
  체크포인트다(별도 상태 파일을 둬도 되지만, 산출물과 어긋나면 안 된다).
- 전 레코드 처리가 끝난 상태에서 process.py 를 다시 실행하면 두 파일 모두
  단 한 바이트도 변하지 않아야 한다(멱등).

## CLI

- `python process.py [--max-id N]`
  - 아직 기록되지 않은 `rec_001` ~ `rec_N` 을 파일명 오름차순으로 처리한다.
  - `--max-id` 기본값은 300(전체)이다. 인자 없이 실행하면 남은 전부를 처리한다.
