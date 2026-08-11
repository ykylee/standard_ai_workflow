# Beta v1.1.6 (2026-08-10)

> **상태: 릴리스 준비.** `tool_version = v1.1.6-beta`, tag `v1.1.6-beta`.
> **patch release** — 2026-08-09 세션의 "검증 못 한 것" 2건 close (title drift
> 임계 실측 캘리브레이션 + registry 비-loopback 실측) 와 **ADR-006 Memory Index
> 회고 + 후속 W-1~W-4 완결**. `cmd_release` 경로의 **3번째 실전 발행**.
>
> PyPI 배포는 정책상 미실행 (릴리스 채널 = GitHub Releases).

## 0. 릴리스 판정

본 릴리스의 공통 주제는 **"측정이 결정한다"** 다 — 임계는 저장소 자신의
데이터로 캘리브레이션하고, 회고는 telemetry 실측으로 쓰고, 33일간 1.0 에
고정돼 있던 지표는 움직일 수 있는 3-tuple 로 교체했다.

- **title drift 임계 0.6** — "출발점" 이라 적혀 있던 값을 실측으로 확정
  (양성 81/음성 375쌍). 조사는 fixture + 검사로 저장소에 고정 — 임계를
  바꾸려면 재캘리브레이션이 강제된다.
- **ADR-006 회고** — 30일 실사용 = 고정 질의 1종 → 고정 entry 1건. hit_rate
  1.0 은 캐시 적중이었다. 병목은 검색이 아니라 **운영** — 그리고 같은 날
  후속 4건(W-1~W-4)으로 그 운영을 전부 구현했다.
- **정직한 miss 의 힘** — W-2 의 첫 컨텍스트 질의 miss 가 33일간 hit_rate=1.0
  뒤에 숨어 있던 패널 간 반올림 불일치를 즉시 드러냈다. 변하지 않는 지표는
  자기 소비자의 결함도 숨긴다.

## 1. 릴리스 요약

- 범위: `v1.1.5-beta..HEAD` (TASK-2026-08-10-main-007~015, 9 commit)
- title drift 임계 0.6 실측 캘리브레이션 + registry 비-loopback bind 실측
- ADR-006 회고 (placeholder → **accepted**) + 후속 W-1~W-4 완결
- v0.15.18 dummy wrapper 물리 제거 (153개/60파일, 신호 분포 불변 실증)
- 전량 검사 **266/266 PASS** (격리 venv, `--tmp-dir` 실디스크)

## 2. deliverable

### 2.1 title drift 임계 실측 캘리브레이션 (TASK-008, `41b98db`)

- 저장소 자신의 제목 데이터 (정본 자리만: backlog bullet / task H1 / handoff
  production 섹션, 트리 326 문서 + git 히스토리 576 버전) 로 양성 81 / 음성
  375쌍 채굴 → **0.6 유지 확정** (정본 양성 노이즈 1/14, 음성 검출 373/375).
- 구조적 한계 동결: 같은-축 형제 task (0.69~0.71) 는 어떤 임계로도 유사도로
  못 가른다 — 검사 case 6 이 표본으로 고정.
- 기각 (실측): 꼬리 괄호 제거 정규화 — 양성 노이즈 26→17 대신 음성 놓침
  115→287. `scripts/calibrate_title_drift.py` + `schemas/title_drift_calibration.json`
  + `check_title_drift_calibration.py` **7/7** (되주입 2종).

### 2.2 registry server 비-loopback bind 실측 (TASK-009, `41b98db`)

- `check_registry_server` case 10 — LAN IP bind + GET + pull + 토큰 왕복
  (**10/10**). LAN IP 부재는 graceful skip + `--require-lan`.
- 잔여 명시: cross-host / 방화벽 / TLS 는 두 번째 호스트 필요 (darwin homelab).

### 2.3 ADR-006 Memory Index 회고 (TASK-010, `051e41a`)

- telemetry 256 events (07-09~08-10) 실측 회고 — 6 영역 + write-path/3-layer
  보강. ADR status placeholder → **accepted**. wiki topic
  `memory-index-retrospective-2026` 신설.
- 기각 (실측 근거 부재): BM25 tuning / embedding 3단계 / merge default 변경.
- phase_13_followup P2-1 stale 날짜 정정 (08-19 → 실제 v0.11.22 tag 07-02).

### 2.4 후속 W-1~W-4 완결 (TASK-011~014, `051e41a`·`1e50701`·`713faec`·`91e1551`)

- **W-1** `wk suggest-memory-entries` — 세션 완료 작업 중 index 가 모르는 것을
  skeleton 과 함께 advisory 제안 (무-write). 루프 실증: 회고를
  `MEM-2026-08-10-001` 로 적재 — **33일 만의 첫 신규 entry**.
- **W-2** 컨텍스트 유래 질의 (`derive_context_query_tokens`, 3 skill 공용) +
  telemetry `query_tokens`/`query_source` additive. 유도 실패는 출처를 보고.
- **W-3** `related_ids` 명시 링크 + dangling/self validation + skeleton 프리필
  + merge union. 실물 링크로 **33일 만의 expansion 첫 발동**.
- **W-4** north-star 를 `utilization_3tuple` (질의 다양성 / 30일 신규 entry /
  distinct 조회) 로 교체, hit_rate 는 보조 강등. `*_measurable` 분모로
  미측정 ≠ 0 (판정은 값 비어있음이 아니라 **필드 존재**). 첫 실측 = 정직한
  저점 (1/8 · 1 · 0/1).

### 2.5 dummy wrapper 물리 제거 (TASK-007, `f7b5217`)

v0.15.18 이 심은 `assert True` dummy 153개/60파일 제거 (-827줄). 신호 분포
완전 불변 실증 — TASK-004 측정이 dummy 를 안 세고 있었다는 물리적 재확인.

## 3. smoke 회귀

누적 smoke test **249/249 PASS** (2026-08-11, `dev,release,mcp-sdk` extra 를 깐
격리 venv, `--tmp-dir` 실디스크). 이 줄은 릴리스 시점 스냅샷이 아니라 *최신 전량
결과* 를 반영하는 살아있는 지표다.

신규 smoke (5, 261→266):

- `check_title_drift_calibration.py` **7/7** (§2.1)
- `check_memory_entry_suggestions.py` **8/8** (§2.4 W-1)
- `check_context_query_tokens.py` **8/8** (§2.4 W-2)
- `check_entry_links.py` **9/9** (§2.4 W-3)
- `check_utilization_3tuple.py` **9/9** (§2.4 W-4)

## 4. 1차 출처 (cross-ref)

- [ADR-006 (회고 본문)](../../docs/architecture/ADR-006-memory-index-retrospective.md)
- [TASK-2026-08-10-main-008](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-10-main-008.md) ~ [TASK-2026-08-10-main-015](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-10-main-015.md)
- wiki topic: `ai-workflow/wiki/topics/memory-index-retrospective-2026.md`
- 이전 release note: [Beta-v1.1.5.md](./Beta-v1.1.5.md)

## 5. 후속

- branch protection (소유자 결정) / darwin homelab 실측 2건 (mavis e2e +
  federation cross-host).
- v1.1.0 / v1.1.1 노트 누적 표기 사후 삽입 여부 (선택).
- memory_index 3-tuple 지표의 실사용 추이 관찰 (정직한 저점에서 출발).

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-08-10T11:30:53Z)_

- total wiki pages: **93**
- total memory entries: **8**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
