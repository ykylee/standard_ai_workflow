---
id: TASK-2026-08-14-feat-task-ssot-writer-001
status: done
created_at: 2026-08-14
source_anchor: generic-task-2026-08-14-feat-task-ssot-writer-001
source_path: backlog/2026-08-14.md
kind: generic
---

# TASK-2026-08-14-feat-task-ssot-writer-001 — task SSOT 구조화 2단계 — 다중값 필드

## 📝 Description

- 상태: done
- 요청일: 2026-08-14
- 담당: AI Agent
- 작업 내용: task SSOT 2단계 — 쓰는 쪽: 다중값 필드를 목록으로 (반복 플래그 소실 + update 중복 제거)
- 범위 밖: 본문 라벨 영어화(3단계) / 읽는 쪽(1단계 완료)
- 완료 기준: (작성 필요 — 검증 방법을 구체적으로 적는다)

## 🛠️ Implementation / Content

- 진행 현황: `2026-08-14 07:20` 기준 반복 플래그 소실 + update 중복 제거

## ✅ Outcome

- 작업 결과: **소실과 중복은 같은 뿌리였다** — 열거인데 스칼라로 다뤘다. 처방도 하나: action="append" + 묶음 단위 교체
- 작업 결과: 열거형 네 필드(완료 기준/작업 결과/남은 리스크/후속 작업)를 반복 지정 가능하게. 값 하나당 한 줄
- 작업 결과: `_set_list_field` 신설 — **연속한** 라벨 줄을 묶음으로 교체한다. 다른 절의 같은 라벨은 안 건드린다 (case 8 이 경계를 잰다)
- 작업 결과: update 는 `list_updates` 로 흘려 스칼라 경로와 분리. **멱등이 계약**이다 (case 5)
- 작업 결과: 우회책이 두 번째 결함을 만들었다 — 스칼라 API 를 목록처럼 쓰면 값 안에 구조를 넣게 되고, 그 구조는 읽는 쪽이 모른다
- 검증 결과: 전량 2축 259/259 ×2 green. 되주입 2종이 원래 증상을 그대로 재현: append 제거 → case 1 이 마지막 하나만 남는 소실 / 묶음 교체를 첫 줄만으로 → case 4·5·7 이 중복 누적
- 후속 작업: 3단계 — 라벨 리터럴을 한 자리로 모은 뒤 본문 라벨 영어화
