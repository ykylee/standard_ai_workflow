# Beta v0.6.3 — P4 harness overlay consistency + memory/log.md

- **릴리스 일자**: 2026-06-12
- **브랜치**: `main`
- **상태**: ✅ P4 DoD (memory/log.md + harness overlay consistency). PATCH release. breaking change 없음.

## 1. 무엇이 바뀌었나

### memory/log.md

`ai-workflow/memory/log.md` 신규. wiki/log.md 와 동일 형식의 append-only 메모리 작업 로그.

### Harness overlay consistency check

`workflow-source/tests/check_harness_overlay_consistency.py` 신규. 6개 harness 의 overlay_spec/AGENTS 문서가 memory/active/ + wiki/ 진입점을 올바르게 참조하는지 검증.

## 2. 변경 파일

| 파일 | 변경 종류 | 라인 |
|---|---|---|
| `ai-workflow/memory/log.md` | 신규 | +12 |
| `workflow-source/tests/check_harness_overlay_consistency.py` | 신규 | +40 |

## 3. 검증

```text
$ python3 workflow-source/tests/check_harness_overlay_consistency.py
Harness overlay check passed (6 harnesses).

$ ls ai-workflow/memory/log.md
ai-workflow/memory/log.md (12 lines)
```

## 4. 최종 v0.6.x 로드맵

v0.6.3 으로 P1~P4 모든 마일스톤 완료. v0.6.x 라인 종료.

다음: v0.7 (contract v2 streaming, 추가 하네스, federated sync 평가)
