# Beta v1.20.1 (2026-10-06)

> **상태: 릴리스 준비.** package `1.20.1`, runtime `__version__ = 1.20.1`, tag `v1.20.1`.
> **patch release** — `backlog-update` 가 task 를 갱신할 때 handoff 와 이월 색인에 task 의 **원래 제목**을 쓴다.
>
> 등급 근거 (§1.5): `wk release-status` 의 파생 근거는 feat 0 · fix 1 · breaking 0 — **patch**.
> 공개 Python API 변경 0, 진입점 · 인자 변경 0.

## 0. 릴리스 판정

`backlog-update --mode update` 는 task 파일의 제목을 바꾸지 않는다 (입력 제목이 다르면 "기존 유지" 경고). 그런데
같은 호출이 쓰는 두 파생 기록 — `session_handoff.md` 의 상태 목록과, 날짜가 바뀌어 새 날 색인에 만드는 이월 항목 —
은 입력 `--task-name` 을 그대로 썼다. 갱신 때 제목을 대충 넘기면(`--task-name x`) handoff '최근 완료' 에
`TASK-… x` 가 남는다. 이 저장소에서 두 세션에 걸쳐 6건이 그렇게 남았다.

## 1. 릴리스 요약

- 범위: `v1.20.0..` 발행 준비 직전까지 **4 commit** — 발행 마무리 1건 · 세션 기록 2건을 빼면 실질 **1 commit** (`6c348937`).
- 누적 smoke **309/309 PASS** (로컬 `--branch-context=all` = 309 × native/slash).
- 검사 수 309 → 309 (기존 `check_backlog_update_layout` 에 case 12 추가).

## 2. 소비자에게 보이는 변화

### 2.1 handoff · 이월 색인의 task 제목 (`6c348937`, TASK-2026-10-06-main-006)

update 병합 경로가 task 파일에서 이미 읽고 있던 원래 제목을 handoff 상태 동기화와 이월 색인에 쓴다. create 는 입력
제목 그대로다. 이미 `TASK-… x` 처럼 남은 handoff 줄은 자동으로 고치지 않는다 — task 파일의 `# TASK-… — <제목>` 으로
손으로 바꾼다.

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- `check_backlog_update_layout` 12/12 — case 12: `--task-name x` 로 in_progress → done 갱신하고 다른 날짜로 이월해도
  handoff 진행/완료 목록 · 이월 색인 제목이 보존된다. 수리 2곳을 각각 되돌리면 red
- 해석기 매트릭스는 이번 patch 에서 **돌리지 않았다** — 변경이 제목 변수 하나로 해석기 민감 코드가 아니고, 하한 문법은
  게이트의 `check_python_floor_syntax` 가 3.10 해석기로 잰다

## 4. 알려진 한계 (감추지 않는다)

- 이미 기록된 `TASK-… x` 류 handoff 줄은 소급 수리하지 않는다.
- v1.20.0 노트 §4 의 한계(verifier 실제 로드 · Windows 실물 실측 대기 등)는 그대로다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-10-06T02:05:35Z)_

- total wiki pages: **97**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
