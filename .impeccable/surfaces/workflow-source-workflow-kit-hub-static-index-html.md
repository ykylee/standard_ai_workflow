---
version: 1
slug: "workflow-source-workflow-kit-hub-static-index-html"
primary_target: "workflow-source/workflow_kit/hub/static/index.html"
related_targets: []
---

# Hub screens — surface brief

Scope: 허브 웹 화면 전체(`workflow-source/workflow_kit/hub/static/`, Go 사본 동기). Mode: Operate.
Audience · job: 팀(처음 온 팀원 포함)이 프로젝트의 전체 진척을 파악하고, 사람이 결정할 일을 놓치지 않고 처리한다. 소유자는 iPad · 휴대폰에서도 승인한다.
Constraints: 외부 자원 없음, CSP style-src 'self'(인라인 style 없음), 빌드 단계 없음, Python · Go 두 서버 같은 API. 확인 요청 화면의 안전 장치(계산된 실행 · diff · sha · 유효 시간 · 낡은 요청 잠금 · 숨은 문자)는 그대로.
Input: 위키 queries/ui-baseline-2026-11-26.md (기준선 17/40).

## Direction contract

THESIS: 첫 화면은 표가 아니라 "지금 어디까지 왔고, 사람이 무엇을 정해야 하나" 다. task 표를 첫 화면 중심에 두는 관리 화면 기본형을 거절한다.

OWN-WORLD: 차분한 운영 콘솔. 짙은 남색 머리 막대(#14233a)가 화면을 붙잡고, 바탕은 찬 회색(#f2f4f6), 판은 흰 면 + 1px 선(그림자 없음), 모서리 6~8px. 강조색 하나(#1d5fbf)는 주 동작 · 현재 위치 · 진척 채움에만. 상태 꼬리표는 알약이 아닌 각진 작은 표(4px) — 진행 중(파랑) · 막힘/사람 필요(주황) · 끝남(초록) · 예정(회색) · 실패(빨강). 주황은 '사람이 필요' 에만. 시스템 글꼴 하나, 1.2 비율, 숫자는 tabular.

STORY: 팀원은 열자마자 마일스톤 진척 띠로 위치를 알고, 그 위 한 줄에서 자기가 결정할 일의 수와 종류를 보고 바로 그 화면으로 간다. 그 아래 진행 중 · 막힌 task 가 제목으로 읽힌다.

FIRST VIEWPORT: 머리 막대(이름 · 위치 · 계정) → 프로젝트 제목 줄 + 탭 → '사람이 결정할 일' 한 줄(확인 요청 · 중계 승인 · 열린 결정 · DCR · 지침 제안 · 막힌 task, 0 이 아닌 것만 강조, 각각 링크) → 진척 띠(마일스톤 칸, 칸 폭 = WBS 수, 채움 = 끝난 비율, 현재 마일스톤 표시) → task 목록(제목 먼저). 주 동작은 결정 한 줄의 첫 항목.

FORM: seed: none (pinned) — 소유자 2026-11-26 답: "로드맵 띠 + 결정 한 줄", "차분한 운영 콘솔". 시그니처: 마일스톤 진척 띠.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
