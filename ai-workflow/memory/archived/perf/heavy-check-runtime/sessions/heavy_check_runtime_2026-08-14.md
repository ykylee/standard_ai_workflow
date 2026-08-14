# 세션 기록 — 무거운 8개 검사 실행시간 (2026-08-14)

- 문서 목적: 전량 검사 벽시계를 정하는 무거운 검사들의 원인과 수리를 남긴다.
- 범위: `check_wiki_score` / 릴리스 계열 3종 / seed 경로 결함 2건
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 관련 문서: [task](../backlog/tasks/TASK-2026-08-14-perf-heavy-check-runtime-001.md), `active/main/backlog/tasks/TASK-2026-08-13-main-009.md`
- 주의: 다른 네임스페이스(`active/main/`)로는 **상대 링크를 걸지 않는다** — 아카이브되면
  `archived/main/…` 으로 풀려 깨진다. 경로 표기로 둔다 (2026-08-14 실측, 같은 함정 2회째).

## 0. 원인은 하나였다 — 같은 계산을 여러 번

무거운 4개가 전부 같은 모양이었다: **안 바뀐 대상을 여러 번 다시 계산**한다.
검사 범위를 줄인 것은 없다 — 같은 산출물을 한 번만 만들어 나눠 본다.

| 검사 | 전 | 후 | 원인 |
|---|---|---|---|
| `check_wiki_score` | 58.1s | **19.4s** | 점수 도구(6.4s)를 **동일 인자로 9회** |
| `check_release_summary_v0_11_15` | 32.0s | **21.1s** | `mypy --no-incremental`(5.1s) **3회** |
| `check_release_status_auto_bump_v0_11_16` | 29.2s | **18.9s** | 같음 |
| `check_release_status_v0_11_14` | 22.9s | **12.8s** | 같음 |

합 142.2s → 72.2s (**−70s**). 각 검사의 case 목록과 판정은 **전후 diff 로 동일** 확인.

## 1. `check_wiki_score` — 9번 계산해 9번 들여다봤다

7개 case 가 전부 `_run_score_tool()` 을 *같은 인자로* 부르고 반환 dict 를 들여다보기만
했다. 점수는 저장소 상태의 함수인데 그 사이 저장소는 안 바뀐다.

`_score_once()` 를 두고 한 번만 실행해 **deep copy** 를 나눠 준다. 원본을 주면 앞 case 가
dict 를 건드릴 때 뒤 case 가 조용히 다른 것을 보게 된다.

**`test_score_idempotent` 는 캐시를 안 쓴다.** 그 case 가 재는 것이 *두 번 실행이 같은
값을 내는가* 라서, 캐시를 쓰면 자기 자신과 비교하는 동어반복이 된다 — 검사를 고치면서
검사를 무력화하는 자리다.

## 2. 릴리스 계열 3종 — `cmd_release_status` 는 호출마다 mypy 를 돈다

cProfile: `check_release_summary` 31.7s 중 `_check_local_mypy` **3회 = 15.3s**.
세 검사 모두 같았다. 셋 다 구조가 같다 — **한 case 는 실제 판정이 필요**하고(schema
verify / mypy clean file count), **나머지는 dispatcher 출력 모양만** 본다.

그래서 앞 case 가 *실제로 얻은* `local_mypy` 판정을 뒤 case 가 재사용하게 했다.
**가짜 값을 넣지 않았다** — 같은 실행의 결과를 넘긴다.

### 프로덕션 invocation 은 건드리지 않았다

`--no-incremental` 을 빼면 mypy 가 5.1s → 1s 미만이 된다. **하지 않았다.** 그 플래그는
계약으로 고정돼 있다:

- `.github/workflows/mypy-strict.yml` 이 그 invocation 을 쓴다
- `check_mypy_strict_ci_v0_11_11.py:74` 가 `"--no-incremental" in workflow_text` 를 assert
- `check_yaml_surfaces.py` 의 `fallback_pattern` 이 같은 문자열을 요구
- v1.0.0 Gate 3 의 근거 문장이 그 명령이다

CI·release gate·로컬이 **같은 명령**을 쓰게 만든 값이라, 로컬만 바꾸면 그 동일성이
깨진다. 느린 것이 곧 잘못은 아니다 — 이건 값을 치르고 산 성질이다.

## 3. 덤 — seed 가 슬래시 브랜치에서 깨져 있었다 (첫 사용에서 바로)

브랜치를 파고 `wk seed-workspace-memory` 를 돌리자 `state.json` 이
`active/perf/**perf**/heavy-check-runtime/` 에 생겼다.

```python
state_path = state_path_in_active(branch_dir.parent, branch)   # 잘못
```

`branch_dir` = `active/<branch>` 이므로 슬래시 브랜치에서 `.parent` 는 `active/perf` 다.
거기에 브랜치 **전체**를 다시 이어 붙이니 `perf/` 가 두 번 들어간다. 슬래시 없는
브랜치에서만 우연히 맞던 조립이다. 36차가 넣은 코드의 **첫 슬래시 브랜치 사용**에서 바로
나왔다 — `fix/…` 브랜치들은 그 기능이 생기기 전에 seed 됐다.

`active_dir` 를 넘기도록 고쳤다. **`check_branch_memory_namespace` (36차 case 12)가 이걸
정확히 지목했다** — 잘못 생긴 경로와 없는 경로를 둘 다 이름으로 찍었다. 가드가 일했다.

**남은 gap**: seed 직후 `sessions/` 가 비어 있어 `check_appendonly_memory_layout` 이 여전히
red 다 (빈 디렉터리만 만든다). 36차의 "seed 한 벌이면 green" 은 `state.json` 까지만
참이었다. 별건으로 남긴다 — 세션 기록은 세션이 쓰는 것이라 seed 가 stub 을 써야 하는지
자체가 판단 대상이다.

## 4. 밟은 함정

`git checkout -- .` 로 방금 한 수정을 스스로 지웠다. 메모리에 이미 있는 함정이었다
(`reinject-restore-via-backup`). 되주입·임시 상태 정리에는 **사본 백업**을 쓰고 blanket
checkout 을 쓰지 않는다.
