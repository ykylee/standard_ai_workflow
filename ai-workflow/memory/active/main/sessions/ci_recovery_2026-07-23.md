# Session — 2026-07-23 / CI 복구 + 배포 정리 (§2.26~§2.28)

- 문서 목적: 특정 세션의 단기 메모리 (영구 보존은 wiki/topics/ 와 함께).
- 날짜: 2026-07-23
- 주제: generic (post-release hardening + CI/배포 복구)
- 상태: stable

## 📋 Session Summary

직전 세션이 남긴 "다음 릴리스에서 `drift_ledger.jsonl` 첫 entry 확인" 을 하려다,
**첫 entry 가 생길 수 있는 경로 자체가 없다**는 것을 발견했다. 그것을 고치고 전량을
다시 돌리는 과정에서 **CI 가 40회 연속 red 였고 아무도 원인을 볼 수 없었다**는 사실이
드러났다. 관측성을 먼저 복구하자 나머지가 연쇄적으로 나왔다.

## 🛠️ Detail

**시작 상태**: `main = 576a05f`, clean, 전량 smoke "209/209" 로 기록돼 있었다.

### 1. §2.26 — north-star 의 분자가 도달 불가였다 (`fea44fa`)

`cmd_release` 안에서 순서가 이랬다:

```
step 2.7  : self-recover → manual_required 1+ 이면 early return
step 6.5b : (gh release create 성공 뒤) 원장 append      ← 도달 불가
```

원장의 분자는 `manual_required_count > 0` 인 line 인데, 그런 line 을 만들 수 있는
cycle 은 **정확히 step 2.7 에서 멈추는 cycle** 이다. 지표가 한 방향으로만 움직일 수
있었다. 릴리스가 한 번이라도 성공하면 `measured` 가 True 로 뒤집혀 정직한 *미측정* 이
거짓 초록불로 바뀐다는 점에서 단순 누락보다 나쁘다.

`_self_recover_step` 추출로 기록을 **판정이 확정되는 지점**(early return 앞)에 두고,
reader 를 line 단위 → **version 단위 cycle 집계**로 바꿨다 (재시도가 분모를 부풀리던 문제).

> **§2.22 왕복 계약이 왜 못 잡았나**: 왕복 테스트는 writer 를 *직접* 불러 dirty payload 를
> 넣는다. 프로덕션 orchestrator 는 그 payload 를 건넬 수 없는데도 pair 는 green 이었다.
> → **orchestrator 가 writer 를 그 값으로 부를 수 있는 경로가 있는가** 를 따로 봐야 한다.

### 2. §2.27 — "209/209" 는 작성자 워킹카피에서만 성립했다 (`9d40289`)

깨끗한 워크트리에서 정본 러너를 돌리자 5건이 실패했고, GitHub Actions smoke 는
**최근 40회 전량 failure** (성공 기록 없음) 였다 — "전량 209/209" 를 적은 커밋들 포함.
CI 는 fresh clone 에 pip install 만 하므로, 그 수치는 `.venv` 와 gitignore 된 런타임
데이터가 누적된 원본 사본에서만 재현됐다.

5건의 뿌리는 하나 — *테스트가 실행 환경에 누적된 상태에 의존한다*. **skip 이 아니라
fixture 로** 고쳤다 (CI 에서 항상 skip 되면 red 보다 나쁘다 — 초록으로 보인다).
fixture 는 손으로 쓰지 않고 프로덕션 writer 로 만든다.

곁들여 정본 helper 결함: `state_path_for_workspace(workspace_root)` 가 접두는 인자에서,
**branch 는 모듈이 속한 저장소에서** 가져와 *호출 위치가 답을 바꾸고* 있었다.
`branch_for_workspace()` 신설로 해소. §2.25 가 경로 조립을 정본으로 모았는데
**정본 자신이 두 출처를 섞고 있었다.**

### 3. CI 관측성 — 무엇이 깨졌는지 볼 수 없었다 (`101125d`, `c686544`)

40회 red 가 방치된 진짜 이유. `smoke-result.json` 은 아티팩트로 올라가지 않았고,
실패 목록은 step summary 로만 갔으며, annotation 에는 `exit code 1` 만 남았다.

고치고 돌려 보니 `smoke-summary.md` 가 여전히 없었다. **원인은 더 앞이었다** —
GitHub 의 bash 는 `-e` 로 돌고 step 의 `set -uo pipefail` 은 그것을 끄지 않으므로,
러너가 non-zero 로 끝나는 순간 **다음 줄 `rc=$?` 에 닿기도 전에 스텝이 중단**됐다.
요약 생성 블록은 실패 시 **한 번도 실행된 적이 없었다**. `|| rc=$?` 로 해소.

### 4. CI 실패 11건 → 1건 (`eab24ac`, `88d0641`)

관측성 확보 후 처음으로 목록을 얻었다.

- **의존성 (7건 해소)** — `dev`(mypy) / `release`(build, twine) extra 가 pyproject 에
  §2.14 로 **이미 선언**돼 있었는데 CI 는 `requirements-dev.txt`(`mcp[cli]` 한 줄)만
  깔았다. **선언은 했는데 설치를 안 했다.** editable install 이 `bootstrap_lib` 도
  올려 `ModuleNotFoundError` 까지 함께 해소.
- **잔여 3건** — 전부 환경 의존이고 둘은 *클론한 누구도 통과시킬 수 없었다*:
  - `path_resolver`: `GITHUB_*` 가 **있으면** 실패 → CI 에서 구조적으로 통과 불가
  - `v0_7_25_legacy_l2`: **저장소 밖** `~/wiki/...` 의존
  - `release_pipeline_lib`: 앞선 실행이 남긴 `dist/` 에 의존 (1회차 FAIL, 2회차 PASS)

> **`~/wiki` 는 옛 wiki 방식의 잔재였다.** 커밋된 산출물
> `_external-wiki-legacy.md` 의 출처는 `/Users/yklee/...` (macOS) — **다른 머신**에서
> 만들어졌다. 지금 리눅스 홈의 `~/wiki` 는 그때 그 디렉터리가 아니고, "15건" 이
> 맞아떨어진 것은 우연에 가깝다. 마이그레이션은 v0.7.25 에서 이미 끝났으므로,
> 테스트가 지킬 것을 **도구 로직(fixture)** 과 **커밋된 산출물의 자기 정합** 둘로 나눴다.

### 5. §2.28 — mkdocs, 층이 셋이었다 (`7b1d63e`, `5b6a2a7`)

`plugins: - tools.mkdocs_git_dates:GitDatesPlugin` 은 **구조적으로 로드 불가**였다.
mkdocs 는 `plugins:` 를 entry point *이름* 으로만 해석한다 — import 경로가 아니다.
`PYTHONPATH` 로는 풀리지 않는다. (게다가 그 클래스는 `BasePlugin` 을 상속하지도 않았다.)
**최근 100회 성공 0회 → 문서 사이트가 한 번도 배포된 적이 없다.**

`hooks:` (파일 경로 기반) 로 옮겨 build 성공. 그러자 **그때까지 실행된 적 없던 deploy
job** 이 OIDC 권한 부족으로 실패했고, 그것도 고쳤다. 맨 아래 층(Pages 미활성)은
공개 게시 결정이라 남겨 뒀다.

| 층 | 상태 |
|---|---|
| plugin 로드 | ✅ 해소 (`hooks:`) |
| deploy 권한 | ✅ 해소 (`id-token: write`) |
| Pages 활성화 | ⬜ **미결정** (`gh api .../pages` → 404) |

### 6. GitHub 배포 정리

| 항목 | 이전 → 이후 |
|---|---|
| Latest | `v0.15.0-beta`(BREAKING) → **`v1.0.0-beta`** |
| pre-release 플래그 | 정식 93 / pre 19 → **정식 1 / pre 111** |
| 로컬 전용 태그 | 5 → **0** |

`beta-v1` 은 그 커밋을 가리키는 **유일한 참조**(고아)여서 지우지 않고 원격에 푸시해
보존한 뒤 로컬을 정리했다.

## ✅ Outcome

| 항목 | 시작 | 종료 |
|---|---|---|
| north-star | 영구 0 (분자 도달 불가) | 측정 가능 |
| smoke CI 실패 | 40회 연속 red, **원인 불명** | **1건** (`ci_stale`) |
| CI 실패 상세 | 볼 수 없음 | 로그 + 아티팩트 30일 |
| mkdocs build | 100회 중 성공 0 | **success** |
| smoke 파일 | 209 | **211** |

커밋 10건, `main` FF 병합 + 푸시 (`576a05f` → `5b6a2a7`). 신규 smoke 2종
(`check_drift_ledger_cycle_recording` 5 case, `check_mkdocs_config` 4 case) 모두
**결함을 되돌려 주입해 FAIL 하는 것까지 확인**.

## 🔁 이번 사이클에서 내가 낸 오류 2건 (지우지 않고 남긴다)

- **tmpfs 귀인 (`600f6e1`)** — `release_pipeline_lib` flake 를 tmpfs 탓으로 적었다.
  근거는 "tmpfs 실패 → 실디스크 통과" **2회 관측**뿐이었고, 3회차에 깨졌다. 실제
  원인은 `cmd_dist` 가 공유 경로 `workflow-source/dist/` 에 쓰는 것이었다.
- **과잉 제약 시뮬레이션** — `~/wiki` 없는 상태를 만들려고 `HOME` 을 통째로 갈아,
  CI 보다 가혹한 환경을 만들어 무관한 2건을 깨뜨리고 잠깐 오진했다.

둘 다 이번 사이클의 주제(재현 조건을 고정하지 않은 측정)와 **같은 부류**다.

## ⏭️ Next Actions

- [ ] **Pages 활성화 여부 결정** — 켜기 전까지 deploy 는 계속 실패한다 (build 는 green).
- [ ] `okf-validate` V-R10 온라인 URL 검증 / `consumer-metrics-digest` 이슈 포스팅
- [ ] 릴리스 제목 형식 4종 혼재 + `v1.0.0-beta` 제목의 **"199/199 PASS"** (재현 불가
      조건에서 잰 수치가 Latest 릴리스 제목에 박혀 있다)
- [ ] **`pyproject.toml` 3중 불일치** — 루트는 `uv init` 잔여물(`standard-ai-workflow`
      0.1.0, deps 가 deepagents/fastmcp/langchain-openai)로 실제 패키지와 **이름 충돌**.
      `workflow_kit/` 것은 v0.5.2-beta stale 인데 **`mypy-strict.yml` 이 그걸 설치**한다.
- [ ] ponytail 채택 A1(효율 사다리) / B1~B3(유보 마커) —
      설계는 `wiki/topics/ponytail-adoption-design-2026-07-23.md` 에 기록 완료
- [ ] `check_release_pipeline_lib` 의 `dist/` 공유 경로 경합 (전제는 보장했으나
      per-check 격리는 아니다)

## ⚠️ Risks & Blockers

- **잔여 `ci_stale` 1건**은 같은 SHA 의 mypy-strict run 이 완료돼야 풀린다. 두 워크플로우가
  동시에 시작하므로 타이밍에 따라 남을 수 있다 — 코드 결함이 아니다.
- 전량 수치를 적을 때는 **어디서 쟀는지** 를 함께 적을 것. 이번에 tmpfs / 실디스크,
  fresh clone / 작성자 사본에서 결과가 갈렸다.
