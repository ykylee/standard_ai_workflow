---
id: TASK-2026-08-14-fix-archive-history-integrity-001
status: done
created_at: 2026-08-14
source_anchor: generic-task-2026-08-14-fix-archive-history-integrity-001
source_path: backlog/2026-08-14.md
kind: generic
---

# TASK-2026-08-14-fix-archive-history-integrity-001 — 아카이브 이력 무결성 — 미완료 task 이월 + 경로 재작성 + 검사 신설

## 📝 Description

- 상태: done
- 요청일: 2026-08-14
- 담당: AI Agent
- 작업 내용: 브랜치 아카이브가 이력을 깨뜨리는 자리 — 미완료 task 소실 + 경로/링크 미재작성 + 회귀 방지 부재
- 범위 밖: 검사 실행 시간 최적화(main-009) / TestPyPI
- 완료 기준: 미완료 task 가 있으면 아카이브가 exit≠0 으로 차단되고 어느 task 때문인지 지목한다 (`--allow-open-tasks` 로만 통과 + `open_task_ids` 기록)
- 완료 기준: 이관은 `carried_over_to` 별도 축으로 적어 `status` 를 거짓으로 바꾸지 않는다
- 완료 기준: 아카이브가 링크와 `state.json` 경로를 resolve 해서 재작성하고, 살아 있는 링크는 건드리지 않는다
- 완료 기준: `check_archive_history_integrity` 가 fixture 로 계약을 고정하고 실물 저장소에 자기 적용된다
- 완료 기준: 전량 검사 2축 + CI 전 체크 green

## 🛠️ Implementation / Content

- 진행 현황: PR #25 병합 완료 (origin/main f8c3321). 브랜치 정리 세션(2026-08-13)에서 사후 마감.

## ✅ Outcome

- 작업 결과: `archive_branch_memory` 를 이동에서 이관으로 전환 — 미완료 차단 + `carried_over_to` + 참조(링크·`state.json`) 재작성
- 작업 결과: `check_archive_history_integrity` 신설 (13 cases) + `check_branch_memory_namespace` 절반짜리 통과 차단 (case 12)
- 작업 결과: `seed-workspace-memory` 가 `state.json` 까지 생성해 seed 직후 절반짜리 상태 제거
- 작업 결과: 기존 이력 복구 14건 — `state.json` 2 / 처음부터 잘못 쓴 링크 1 / 영구 삭제 대상 죽은 참조 11 표기
- 작업 결과: 자기 리뷰 결함 5건 수리 — 본문 status 오인 / 긴 frontmatter 누락 / root 미resolve 시 침묵 / 앵커 소실 / CommonMark 미처리
- 검증 결과: 전량 검사 2축 255/255 ×2 green (native/slash) + CI env 축 255/255 + mypy strict 193 files 0 errors + CI 13 체크 전부 green
- 후속 작업: TASK-2026-08-13-main-008 TestPyPI 리허설 (blocked — 소유자 토큰)
