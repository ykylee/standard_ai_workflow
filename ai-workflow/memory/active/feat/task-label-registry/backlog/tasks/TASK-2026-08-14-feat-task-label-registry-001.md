---
id: TASK-2026-08-14-feat-task-label-registry-001
status: done
created_at: 2026-08-14
source_anchor: generic-task-2026-08-14-feat-task-label-registry-001
source_path: backlog/2026-08-14.md
kind: generic
---

# TASK-2026-08-14-feat-task-label-registry-001 — task SSOT 3단계 — 라벨 정본화

## 📝 Description

- 상태: done
- 요청일: 2026-08-14
- 담당: AI Agent
- 작업 내용: task SSOT 3단계 — 라벨 리터럴을 정본 한 곳으로 + 리더를 두 표기 모두 받게 (영어 전환의 선행 조건)
- 범위 밖: 라벨 실제 전환(4단계, deprecation cycle 필요) / 2축→1축
- 완료 기준: (작성 필요 — 검증 방법을 구체적으로 적는다)

## 🛠️ Implementation / Content

- 진행 현황: `2026-08-14 08:04` 기준 라벨 리터럴을 정본 한 곳으로 + 리더를 두 표기 모두 받게

## ✅ Outcome

- 작업 결과: **바꾸기가 아니라 "바꿀 수 있게"** — 라벨은 파싱 계약이라 리더가 먼저 두 표기를 받아야 한다. 쓰는 쪽을 먼저 바꾸면 소비자의 옛 리더가 새 문서를 못 읽는다
- 작업 결과: 리터럴이 12개 라벨 × 46곳에 흩어져 있었다 → `TASK_FIELD_LABELS`(현재 표기) + `TASK_FIELD_ALIASES`(받아들일 표기)를 `project_docs` 에 정본으로
- 작업 결과: 원칙은 **찾기는 넓게, 쓰기는 좁게** — 옛/영어 표기 줄도 찾지만 쓸 때는 정본 하나로
- 작업 결과: case 6 이 "정본이 하나" 의 유일한 증거다 — 표를 바꾸면 산출물이 따라 바뀐다. case 8 은 반대 방향으로 렌더 경로의 잔여 리터럴을 AST 로 훑는다
- 작업 결과: 마지막 잔여는 **읽는 비교**였다 (`line.strip() == "- 작업 내용:"`) — 영어 표기 문서에서 항상 거짓이라 "비어 있으니 채운다" 분기가 조용히 안 돌았다
- 검증 결과: 전량 2축 260/260 ×2 green. 되주입: 별칭 인식 무력화 → case 4·5·6 FAIL (영어 표기 못 읽음 / 쓸 때 정본 안 씀 / 정본 변경이 안 따라옴)
- 후속 작업: 4단계는 **다음 release** — TASK_FIELD_LABELS 를 영어로. 이번 release 를 받은 소비자의 리더가 두 표기를 알게 된 뒤여야 한다
- 후속 작업: read_only_bundle 의 라벨 리터럴은 별도 검토 (MCP 번들의 task 생성 경로)
