---
id: TASK-2026-08-14-perf-changed-selection-001
status: done
created_at: 2026-08-14
source_anchor: generic-task-2026-08-14-perf-changed-selection-001
source_path: backlog/2026-08-14.md
kind: generic
---

# TASK-2026-08-14-perf-changed-selection-001 — run_all_checks --changed 선택 실행

## 📝 Description

- 상태: done
- 요청일: 2026-08-14
- 담당: AI Agent
- 작업 내용: run_all_checks --changed — 검사가 자기 관찰 경로를 선언하고, 무관한 검사를 건너뛴다 (미선언은 항상 실행)
- 범위 밖: 2축→1축 조건부(main-004) / 무거운 검사 추가 최적화 / push 게이트 변경
- 완료 기준: (작성 필요 — 검증 방법을 구체적으로 적는다)

## 🛠️ Implementation / Content

- 진행 현황: `2026-08-14 04:21` 기준 검사가 자기 관찰 경로를 선언하고 무관한 검사를 건너뛴다 (미선언은 항상 실행)

## ✅ Outcome

- 작업 결과: `run_all_checks --changed` 신설. 선언은 check 파일 안의 `WATCHES = (glob, ...)` — 목록을 러너에 두면 파일에서 멀어져 드리프트하고 그 드리프트가 곧 사각지대다 (`REQUIRES_QUIET_REPO` 와 같은 idiom)
- 작업 결과: 계약 전부가 **조용히 안 도는 검사**를 막는 쪽으로 기울어 있다 — 미선언=항상 실행 / 자기 파일 변경시 무조건 실행 / 비리터럴 원소 있으면 미선언 취급 / parse 실패도 실행 / 건너뛴 것은 이름·사유 전부 출력 / 변경 0건이면 "통과가 아니라 잴 것이 없음" / 매 출력에 "게이트가 아니다"
- 작업 결과: `check_changed_selection` 신설 (9 cases) — **양방향** fixture. case 3(관련 변경을 잡는가) + case 4(무관한 변경을 건너뛰는가). 한 방향만 재면 '아무것도 안 잡는' 구현이 통과한다
- 작업 결과: 무거운 8개 중 7개에 선언 부착. **`check_no_repo_write` 는 일부러 미선언** — 감시 표본 13종을 돌려 관찰 범위가 사실상 저장소 전체라 좁게 적으면 그게 사각지대다. `check_wiki_score` 도 operational dim 때문에 `tests/*` 통째로 잡았다
- 작업 결과: 검사 1개 추가로 선언된 개수 3곳(CODE_INDEX / INSTALLATION_AND_USAGE / 릴리스 노트 누적)이 255→256 으로 어긋나 red — 규약이 제대로 작동한 것이고 갱신했다
- 검증 결과: 전량 2축 **256/256 ×2 green**. 되주입 2종 실측: 매칭을 항상 거짓으로 → case 3 FAIL / 미선언도 건너뛰게 → case 1·5·6 FAIL (복원은 사본 백업으로). 실이득 실측: 메모리 문서 1건만 편집 시 **실행 250 / 건너뜀 6, 벽시계 125.9s (전량 154.2s 대비 −18%)** — 건너뛴 6개가 정확히 무거운 것들
- 후속 작업: 선언 부착 확대는 필요할 때 — 지금은 무거운 7개로 충분하다 (나머지는 1초 미만)
