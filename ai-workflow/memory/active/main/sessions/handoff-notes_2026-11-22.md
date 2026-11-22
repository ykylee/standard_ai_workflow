# Handoff notes (rolled off from handoff §5)

- 문서 목적: `session_handoff.md` §5 에서 이관된 누적 기록(완료 기록 · 지난 계획 · 닫힌 안건)을 보존한다.
- 범위: 이관일 2026-11-22 의 이관분
- 대상 독자: AI agent, 저장소 관리자
- 상태: append-only
- 관련 문서: [session_handoff.md](../session_handoff.md)

## 이관 2026-11-22

### §5 서두 회차 줄 (2블록)

- (137차 후속, 2026-11-21) **M-036 done** — WBS-36.3 A (TASK-2026-11-21-main-003: 위키 운반 = 1.x 디렉터리 무손실, OKF 는 출판 · 남의 묶음 loose 만 — R8.6 소유자 결정으로 정정) · B (TASK-2026-11-21-main-004: 선택 클라이언트 `hub_client.py` 첫 판 — 보낼편지함 · 캐시 · 세션 시작 보고). 1.x OKF 결함 2건은 `release/1.x` backlog (`release-1.x-002` · `-003` — 그 브랜치 메모리에). **다음 M-037** (허브 화면 · 워크벤치 확장). 후속 후보: 클라이언트 hook 체크포인트(§7 ①) · 위키 점수 함수 인자화 · 원격 clone 캐시.
- (137차 후속, 2026-11-21) **M-036 WBS-36.2 done** (TASK-2026-11-21-main-002 — memory_index · 양방향 링크 · 출처 sha · 위키 원격 읽기, `check_hub_wiki` 9/9). 1.x 결함 `bidir_link` 수리는 main(`41b39d51`) · `release/1.x`(`05678400`) 둘 다 — 다음 1.x patch 노트에 싣는다. **다음 WBS-36.3** — 들여오기 · 내보내기 (OKF · git 스냅샷) · 오프라인 보낼편지함. 들여오기는 요청 상한 256KB 로 묶음을 나눈다. 후속 후보: 위키 점수 함수 인자화 · 원격 clone 캐시.

## 이관 2026-11-22

### §5 서두 회차 줄 (1블록)

- (137차 후속, 2026-11-21) **M-036 WBS-36.1 done** (TASK-2026-11-21-main-001 — 허브 위키: DB 판 5 · `hub/wiki.py` · 도구 5종 · V-1/V-4 본체 `common/wiki_rules.py` 공유 · `check_hub_wiki` 5/5). **다음 WBS-36.2** — memory_index · 양방향 링크(E5) · 저장소 참조 sha · freshness 원격 읽기(R8.4, 지금은 미측정) · 점수 함수. 36.3 OKF 들여오기는 요청 상한 256KB 때문에 묶음을 나눠 보내야 한다. kit 결함 후보: 주장 린트 L7 이 인용된 주장을 '재지 않는' 으로 경고.

## 이관 2026-11-22

### §5 서두 회차 줄 (1블록)

- (137차, 2026-11-21) **다음 일: M-036 WBS-36.1** (위키 페이지 · ingest · index/log · lint, E2) — 2.0 작업은 이제 main 에서 (새 작업 브랜치는 session-start 가 seed). 시작할 때 M-036 을 `in_progress` 로 열면 현재 마일스톤이 M-036 이 된다. 1.x 결함 수리는 `release/1.x` 체크아웃에서. `claude/workflow-hub-concept` 원격 브랜치는 병합 끝 — 지울지 소유자 판단.
