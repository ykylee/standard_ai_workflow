# Handoff notes (rolled off from handoff §5)

- 문서 목적: `session_handoff.md` §5 에서 이관된 누적 기록(완료 기록 · 지난 계획 · 닫힌 안건)을 보존한다.
- 범위: 이관일 2026-11-22 의 이관분
- 대상 독자: AI agent, 저장소 관리자
- 상태: append-only
- 관련 문서: [session_handoff.md](../session_handoff.md)

## 이관 2026-11-22

### §5 서두 회차 줄 (1블록)

- (137차 후속, 2026-11-21) **M-036 WBS-36.1 done** (TASK-2026-11-21-main-001 — 허브 위키: DB 판 5 · `hub/wiki.py` · 도구 5종 · V-1/V-4 본체 `common/wiki_rules.py` 공유 · `check_hub_wiki` 5/5). **다음 WBS-36.2** — memory_index · 양방향 링크(E5) · 저장소 참조 sha · freshness 원격 읽기(R8.4, 지금은 미측정) · 점수 함수. 36.3 OKF 들여오기는 요청 상한 256KB 때문에 묶음을 나눠 보내야 한다. kit 결함 후보: 주장 린트 L7 이 인용된 주장을 '재지 않는' 으로 경고.

## 이관 2026-11-22

### §5 서두 회차 줄 (1블록)

- (137차, 2026-11-21) **다음 일: M-036 WBS-36.1** (위키 페이지 · ingest · index/log · lint, E2) — 2.0 작업은 이제 main 에서 (새 작업 브랜치는 session-start 가 seed). 시작할 때 M-036 을 `in_progress` 로 열면 현재 마일스톤이 M-036 이 된다. 1.x 결함 수리는 `release/1.x` 체크아웃에서. `claude/workflow-hub-concept` 원격 브랜치는 병합 끝 — 지울지 소유자 판단.
