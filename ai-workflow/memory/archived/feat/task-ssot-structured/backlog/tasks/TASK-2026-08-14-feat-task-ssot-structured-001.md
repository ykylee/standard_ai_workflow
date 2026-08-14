---
id: TASK-2026-08-14-feat-task-ssot-structured-001
status: done
created_at: 2026-08-14
source_anchor: generic-task-2026-08-14-feat-task-ssot-structured-001
source_path: backlog/2026-08-14.md
kind: generic
---

# TASK-2026-08-14-feat-task-ssot-structured-001 — task SSOT 구조화 1단계 — 파싱 자리 전수 조사 + frontmatter 정본화

## 📝 Description

- 상태: done
- 요청일: 2026-08-14
- 담당: AI Agent
- 작업 내용: task SSOT 구조화 — 기계가 읽는 필드를 frontmatter 로, 본문은 아무도 파싱하지 않는 산문으로
- 범위 밖: 2축→1축(main-004) / seed sessions gap(main-005) / 아카이브 링크(main-006)
- 완료 기준: (작성 필요 — 검증 방법을 구체적으로 적는다)

## 🛠️ Implementation / Content

- 진행 현황: `2026-08-14 06:51` 기준 기계가 읽는 필드를 frontmatter 로, 본문은 아무도 파싱하지 않는 산문으로

## ✅ Outcome

- 작업 결과: **전수 조사가 살아 있는 결함 셋을 드러냈고 1단계는 그것을 닫는 일이 됐다.** 읽는 쪽 계약을 하나로 모았다
- 작업 결과: **같은 필드에 소스가 둘** — 아카이브/축분리 검사는 frontmatter, backlog 파서는 본문. 277개 중 불일치 0 이지만 **본문 줄이 없는 것 105개(38%)** 였고 그것들은 파서에게 상태 없음이었다 → frontmatter 우선 (디스크 본문은 안 건드린다, 2년 compat)
- 작업 결과: **index 방언 셋 중 둘이 안 보였다** (링크/백틱/인라인) — active/main 의 daily index **20개가 task 0개로** 읽히고 있었다. 세 방언 모두 해석 → 0개 index 20→0, 읽힌 task 262, 상태 없는 task 0
- 작업 결과: **fallback 이 두 겹으로 죽어 있었다** — glob 패턴이 실제 파일명을 안 잡았고(`<stem>_*`), 생성자가 부재 파일에서 먼저 죽어 도달조차 못 했다
- 작업 결과: `check_task_ssot_source` 10 cases — 세 방언과 두 소스를 fixture 로 각각 재고, 자기 적용 3건으로 실물을 잰다
- 작업 결과: **되주입이 case 하나를 무력화 상태로 드러냈다** — 백틱 해석을 지워도 case 5 가 통과했다(같은 날짜라 glob fallback 이 대신 집었다). 격리했더니 이번엔 fixture 디렉터리가 실물과 달라 실패 → 실물 모양으로 수정 (오늘 같은 실수 두 번째)
- 검증 결과: 전량 2축 258/258 ×2 green. 되주입 2종: frontmatter 우선 제거 → case 1·2·9 FAIL / 백틱 해석 제거 → case 5 FAIL. state.json 산출은 전후 동일 (최신 backlog 는 이미 신형 방언이라 회귀 없이 과거 커버리지만 증가)
- 후속 작업: 2단계 — 쓰는 쪽 반복 필드 구조화, 그 다음에 본문 라벨 영어화 (라벨이 파싱 계약에서 빠진 뒤라야 안전하다)
