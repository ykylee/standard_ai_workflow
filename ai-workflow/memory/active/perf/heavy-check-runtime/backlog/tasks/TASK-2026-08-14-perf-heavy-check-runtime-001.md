---
id: TASK-2026-08-14-perf-heavy-check-runtime-001
status: done
created_at: 2026-08-14
source_anchor: generic-task-2026-08-14-perf-heavy-check-runtime-001
source_path: backlog/2026-08-14.md
kind: generic
---

# TASK-2026-08-14-perf-heavy-check-runtime-001 — 무거운 8개 검사 실행시간 단축 — 범위를 줄이지 않고

## 📝 Description

- 상태: done
- 요청일: 2026-08-14
- 담당: AI Agent
- 작업 내용: 전량 검사 벽시계를 정하는 무거운 8개 — 임계경로(wiki_score 68s) + 정숙 구간(no_repo_write 39s) 부터
- 완료 기준: (작성 필요 — 검증 방법을 구체적으로 적는다)

## 🛠️ Implementation / Content

- 진행 현황: `2026-08-14 03:40` 기준 전량 검사 벽시계를 정하는 무거운 8개 — 임계경로 + 정숙 구간부터

## ✅ Outcome

- 작업 결과: **무거운 4개 = 같은 계산 반복.** 검사 범위를 줄이지 않고 산출물을 한 번만 만들어 나눠 본다. 단독 실행 기준 142.2s → 72.2s (−70s), 각 검사 case 목록·판정은 전후 diff 로 동일 확인
- 작업 결과: `check_wiki_score` 58.1→19.4s — 점수 도구(6.4s)를 동일 인자로 9회 호출하던 것을 `_score_once()` 공유 실행 + deep copy 로. `test_score_idempotent` 는 캐시를 안 쓴다 (두 번 실행이 같은가를 재는 case 라 캐시를 쓰면 자기 자신과 비교하는 동어반복)
- 작업 결과: 릴리스 계열 3종 — `cmd_release_status` 가 호출마다 `mypy --no-incremental`(5.1s)을 돈다. 실제 판정이 필요한 case 는 그대로 두고, dispatcher 출력 모양만 보는 case 가 **앞 case 의 실측 판정을 재사용**하게 했다 (가짜 값 아님). summary 32.0→21.1 / auto_bump 29.2→18.9 / status 22.9→12.8
- 작업 결과: **프로덕션 invocation 은 안 건드렸다** — `--no-incremental` 제거가 가장 큰 절감이지만 CI yml·`check_mypy_strict_ci_v0_11_11`·`check_yaml_surfaces`·v1.0.0 Gate 3 이 같은 명령을 쓰도록 고정한 값이다. 로컬만 바꾸면 게이트 동일성이 깨진다
- 작업 결과: 나머지 4개는 낭비가 아니었다 — `branch_context_matrix` 는 서로 다른 컨텍스트 3 probe / `mypy_config_actually_loaded` 는 config 로딩 실측이 목적 / `no_repo_write` 는 감시 표본 13종 직렬(정숙 구간 필수) / `release_pipeline_lib` 는 위 계열 수정으로 함께 내려감
- 작업 결과: **덤 — seed 가 슬래시 브랜치에서 깨져 있었다.** `state_path_in_active(branch_dir.parent, ...)` 가 `active/perf/perf/heavy-check-runtime/` 을 만들었다 (36차 코드의 첫 슬래시 브랜치 사용). `active_dir` 를 넘기도록 수정. `check_branch_memory_namespace` case 12 가 정확히 지목했다
- 검증 결과: **전량 2축 255/255 ×2 green.** 벽시계(native, 같은 호스트): 수정 전 중앙값 195.5s (n=5: 193.1/195.2/195.5/195.8/196.6) → 수정 후 중앙값 154.2s (n=3: 150.9/154.2/154.5) = **−21%**. 2축 게이트 기준 약 −83s. 각 검사 단독 실행도 전후 2회씩 측정했고 case 목록·판정 diff 동일
- 후속 작업: seed 직후 sessions/ 가 비어 check_appendonly_memory_layout 이 red — 36차의 '한 벌이면 green' 은 state.json 까지만 참이었다. 별건 task 로 등록 필요
