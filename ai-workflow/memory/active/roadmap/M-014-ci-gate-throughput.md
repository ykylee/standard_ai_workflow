---
id: M-014
title: CI·게이트 처리량 — 반복 계산 제거 · 시간 기준 샤딩 · 셋업 비용
sdlc_phase: concept
status: planned
order: 14
parallel_allowed:
  - M-007
  - M-013
deliverables:
  - docs/planning/ci-throughput-review-2026-09.md
goals: [G2]
---

# M-014 — CI·게이트 처리량

소유자 제기(2026-09-23, 87차): Linear 의 "AI coding has made CI a bottleneck, so we
reworked ours to keep up" (https://linear.app/now/ci-bottleneck-reworked) 를 참고해
테스트·CI 병목을 해소할 아이디어를 얻는다. 그 글의 핵심은 테스트가 4배로 늘어도
**셋업 반복 제거 → 임계경로 정리 → 셋업이 작아진 뒤 시간 기준 샤딩** 순서로 벽시계를
줄였고, 동적 테스트 선택은 하지 않았다는 것이다.

**착수 시점 실측** (2026-09-23, CI run 35872111845 · 로컬 macOS 10코어):

| 항목 | 값 |
|---|---|
| CI 임계경로 | smoke 벽시계 334s — 셀당 설치 15–34s + 검사 179–280s |
| 병렬도 | 셀당 CPU 합 ~960s / 벽시계 ~277s = **3.48** (4 vCPU 포화) |
| 러너 편차 | 같은 작업량에 `slash/py3.11` 178s vs 나머지 272–280s (1.56배) |
| 분포 | 293 검사 중 153개 <1s, 상위 8개가 CPU 의 33%, 최장 `branch_context_matrix` 55s |
| 검사당 고정비 | 인터프리터 기동 + kit import ≈ 40ms — **병목 아님** |
| 로컬 게이트 | 두 축 순차 102s + 104s |
| 반복 계산 (프로파일) | `check_root_anchor_audit` 26s 중 ~25s 가 전 저장소 감사 반복(파싱 3445회 ≈ 파일 265 × 13) · `check_release_summary_v0_11_15` 15s 중 subprocess 40회(release 파이프라인 전체 + CI 조회 2회) |

**전제 이력** (concept 검토가 대면할 것):

- 게이트 축소(조건부 1축 생략·동적 선택)는 기각됐다 (TASK-2026-08-14-main-004,
  53차 규칙 "전량 게이트는 필터로 대체되지 않는다"). 이 축은 **같은 전량을 더 싸게**
  돌리는 것이지 덜 돌리는 것이 아니다.
- 정숙 구간(`REQUIRES_QUIET_REPO`)과 워킹 트리 배타 락은 샤딩·축 병렬화의 제약이다.
- 반복 계산 제거는 결과가 같아야 한다 — 캐시가 case 간 독립성을 깨지 않는지 잰다.

**concept 이 다룰 후보** (근거가 강한 순): ① 검사 내부 반복 계산 전수 조사(동일 인자
N회 호출) ② 셀 내 시간 기준 샤딩(이전 `smoke-result.json` 소요 시간으로 분배) 또는
더 큰 러너 ③ 임계경로 단일 검사(`branch_context_matrix`) 단축 ④ 설치 단계 — 캐시
복원 vs 재설치 실측 후 결정 ⑤ 로컬 게이트 두 축 동시 실행(worktree 분리 전제)
⑥ 검사별 소요 시간 추세(p50/p90 · 임계경로 · CPU 합)를 like-for-like 로 관찰.
**가져오지 않는 것**: 게이트 단계의 동적 선택, in-process 실행(고정비 40ms 라 이득 없음).

SDLC 온보딩 기본 순서를 따른다. 단, 개별 검사의 명백한 반복 계산은 결함 수리로
M-007/WBS-7.2 에서 먼저 닫는다 (TASK-2026-09-23-main-020 · main-021).

## WBS

- **WBS-14.1** concept 검토 — 셀·검사별 시간 실측, 반복 계산 전수 조사 방법, 샤딩
  단위와 분배 기준, 정숙 구간·락 제약, 기대 이득 상한, 소유자 선택지 —
  산출물: `docs/planning/ci-throughput-review-2026-09.md`
