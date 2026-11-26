# Beta v3.9.0 — 허브 화면 재정비, DCR 웹 승인 (2026-11-26)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- **개요 = 진척 + 사람이 결정할 일**: 프로젝트 개요 맨 위에 "사람이 결정할 일" 한 줄(확인 요청 · 중계 승인 · 열린 결정 task · DCR · 지침 제안 · 막힌 task — 각 숫자가 그 자리로 가는 링크, 못 읽으면 "확인 못 함")과 로드맵 띠(마일스톤 제목 · 진척)를 둔다. task 목록은 기본 "지금"(막힘 + 진행 중) 탭이고 제목이 첫 열이다. KPI 줄은 뺐다.
- **DCR 웹 승인**: `POST /api/projects/{pid}/dcr/{id}/decision` — 관리 권한이 있는 사람이 DCR 화면에서 "판단 근거" 를 적고 승인 · 거절한다(`expected_version`). Python · Go 같은 계약.
- **결정 라디오를 미리 고르지 않는다**: task 화면의 계획 결정이 기본값을 고르거나 펼치기만 해도 '확인함' 이 되던 결함을 고쳤다 — 고르지 않은 결정이 있으면 제출이 막힌다.
- **한국어로 풀기**: 상태 · 단계 · 경로 · 이력 동작명 · 역할 · 메시지 칸 · 로드맵 경고 18종 · DCR 상태를 한국어로 보이고 원문은 `title` 에 둔다. 오류는 사람이 읽을 말을 먼저, 코드는 괄호 안에. 개요에 접힌 낱말 풀이.
- **오케스트레이션**: 세션 승인이 메시지보다 위, 미확인 메시지는 접고 "모두 읽음으로 정리". '전체 정지' 는 확인을 묻는다.
- **휴대폰 · 접근성**: 48rem 아래 표를 쌓은 줄로, 탭은 줄을 바꿔 모두 보인다. 칩 · 입력 테두리 대비(WCAG 2.2 AA), `:focus-visible`, 결과 알림 `aria-live`. 이력은 50건씩.
- **디자인 규약**: 저장소 뿌리 `DESIGN.md` · `PRODUCT.md`, 프론트엔드 도구 세트 `docs/frontend-toolkit/setup.sh --local`.

## 검증

- 누적 smoke **360/360 PASS**
- `check_hub_screens` 93/93 — 실제 Chrome 으로 Python · Go 허브 렌더(1440 · 360px), 결정 타일 숫자 · 링크, DCR 승인 · 거절 · 근거 없음, 미선택 제출 막힘, 한국어 라벨. 되주입 red 확인.
- impeccable critique 재채점 허브 17/40 → 27/40, detector 지적 0건.

## 운영 범위

- **DB 판은 22 그대로다** — 3.8.0 으로 되돌릴 때 실행 파일만 바꾸면 된다.
- 워크벤치(1.x) 의 같은 '미리 고른 결정' 결함과 PC 중계 화면은 이번 판에 들지 않았다(TASK-2026-11-26-claude-plex-009 · 010).

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-26T08:10:39Z)_

- total wiki pages: **104**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
