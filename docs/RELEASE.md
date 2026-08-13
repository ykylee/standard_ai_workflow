# Release Procedure (v0.5.7+)

- 문서 목적: Standard AI Workflow 릴리스 절차 (버전 박기 → 빌드 → 스모크 → GitHub Release attach) 를 한 자리에 정리한다.
- 범위: 채널 정책, 사전 점검, 빌드, 로컬 smoke, GitHub Release 생성, 트러블슈팅, 회귀 표
- 대상 독자: 저장소 maintainer (`ykylee`), 릴리스 매니저
- 상태: stable (v1.2.0-beta 기준; 절차 자체는 v0.5.7+ 부터 정식 도입된 정책 유지)
- 현재 package version: 1.1.8 (`workflow-source/pyproject.toml`)
- 최종 수정일: 2026-08-13
- 관련 문서: [README.md](https://github.com/ykylee/standard_ai_workflow/blob/main/README.md), [./PROJECT_PROFILE.md](./PROJECT_PROFILE.md), [./INSTALLATION_AND_USAGE.md](./INSTALLATION_AND_USAGE.md), [Workflow Kit Roadmap](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/workflow_kit_roadmap.md), [workflow-source/releases/](https://github.com/ykylee/standard_ai_workflow/tree/main/workflow-source/releases/)

> **최종 갱신**: 2026-07-18 (회귀 표를 v0.15.15 까지 확장하고 `release_pipeline.py` 자동화 경로 반영)
> **변경 이력**: PyPI/TestPyPI 업로드 정책 폐기 → **GitHub Releases 만** 사용 (v0.5.7 부터).
> **이유**: 토큰 회전 부담, 외부 공개 단계 미도달, downstream 은 `pip install <wheel>` 로 로컬 검증.

---

## 1. 채널 정책

> **이 절이 릴리스 채널 정책의 정본이다** (v1.2.1, TASK-2026-08-13-main-007).
> 이전에는 `release_pipeline.py` 주석이 정책 근거로 *agent memory* 를 인용했는데,
> 그건 저장소 밖 파일이라 소비자도 새 기여자도 열어볼 수 없었다. 정책을 바꾸든
> 유지하든 **바꿀 자리는 이 표 하나**이고, 코드 주석은 여기를 가리킨다.

| 채널 | 상태 | 비고 |
|---|---|---|
| GitHub Releases (wheel + sdist) | ✅ **유일한 공식 채널** | `gh release create` 한 줄로 끝 |
| TestPyPI | ⚠️ **1회 한정 허용** (리허설 목적) | 2026-08-13 소유자 승인 — 아래 **각주 1** 의 조건 안에서만 |
| PyPI | ❌ 사용 안 함 | (v0.5.7 부터, 이전부터 보류) — 기술 제약은 v1.2.0 에서 해소됐고 **남은 것은 이 정책 결정뿐**이다: [PyPI 발행 정책 검토](./planning/pypi-publication-policy-review-2026-08.md) |
| Docker / brew / system pkg | ❌ 해당 없음 | (Python wheel 만 다룸) |

**v0.5.7 부터** 모든 release 는 GitHub Releases 페이지에 wheel + sdist 가 attach 된 형태.
release 본문은 `workflow-source/releases/Beta-v<X>.<Y>.<Z>.md` 가 그대로 들어감.

### 각주 1 — TestPyPI 1회 한정 허용 (2026-08-13 소유자 승인)

**공식 배포 채널은 여전히 GitHub Releases 하나다.** 이 허용은 채널 추가가 아니라
*발행 전 검증 1회* 를 여는 것이다. 범위를 좁게 적어 둔다 — 넓게 읽히면 정책이
사실상 바뀐 것이 되고, 그건 소유자가 결정하지 않은 일이다.

- **목적**: PyPI 발행 여부를 판단하기 전, 업로드 경로와 프로젝트 페이지 렌더링을
  실측한다 ([검토 §6.1](./planning/pypi-publication-policy-review-2026-08.md)).
- **범위**: `standard-ai-workflow` **1.2.0** 아티팩트(whl + sdist) **1회 업로드**.
- **범위 밖 (별도 승인 필요)**: 다른 버전의 추가 업로드 / TestPyPI 를 상시
  릴리스 단계로 편입 / **실사용 PyPI 업로드** — PyPI 행은 위 표대로 ❌ 그대로다.
- **소비자 안내 금지**: TestPyPI 링크를 설치 경로로 문서에 싣지 않는다.
  거기 올라간 것은 검증용이고 유지·보수 대상이 아니다.
- **비가역성 인지**: TestPyPI 도 같은 (이름, 버전, 파일명) 재업로드가 불가하다.
  1.2.0 은 TestPyPI 에서 소각되며, 재리허설이 필요하면 다음 번호를 쓴다.
  (실사용 PyPI 의 이름 예약과는 무관 — 별개 인덱스다.)
- **만료**: 위 1회가 끝나면 이 각주의 효력도 끝난다. 그 다음 판단은 검토 문서
  §6 의 4번(발행 여부 소유자 결정)이다.

## 2. 절차 (한 사람이 직접 실행)

### 2.1 사전 점검

```bash
# cwd 는 저장소 루트로 가정 (절대 경로는 각자 환경에 맞게 조정)
git status                 # clean 트리 확인
git log --oneline -3       # 머지된 release squash 커밋 확인
gh auth status             # gh CLI 로그인 확인 (keyring)
```

### 2.2 버전 박기 (pyproject.toml)

`workflow-source/pyproject.toml`:

```toml
name = "standard-ai-workflow"
version = "<X>.<Y>.<Z>"   # ← 매 release 마다 수동 또는 release_pipeline 으로 갱신
```

runtime `workflow_kit.__version__` 은 이 값을 **그대로**(`<X>.<Y>.<Z>`) 노출한다 — v1.2.1 부터 PEP 440 정규화 결과와 같고, 빌드 파일명과도 같다 (TASK-2026-08-13-main-007: stable 정리로 `v` 접두사·`-beta` 접미사 제거). **git tag 와 GitHub Release 제목만** 관례대로 `v` 를 붙인다 — `v<X>.<Y>.<Z>`.

### 2.3 자동화 경로 (권장)

```bash
# 저장소 루트
wk release-pipeline validate --json
wk release-pipeline dist --dry-run --json
wk release-pipeline release \
  --version <X>.<Y>.<Z> \
  --dry-run \
  --json
```

`--dry-run` 결과와 릴리스 노트·태그·산출물을 검토한 뒤에만 `--apply`로 외부 배포한다. `release`는 tag push와 GitHub Release 생성을 포함하므로 maintainer 승인이 필요하다.

v1.1.4+ 기본값: `--apply` 를 명시하지 않으면 `release` 는 **dry-run** 이다 (이전에는 무인자 실행이 APPLY 로 진입했다). v1.1.5+ 에서 `dist` 도 같은 기본값으로 반전됐다 — 무인자 `dist` 는 빌드 plan 만 낸다. `--dry-run --apply` 동시 지정 시 dry-run 이 이긴다. pre_check 게이트는 `--skip-packaging` / `--skip-doctor` / `--skip-state` / `--skip-git` / `--skip-mypy` 로 개별 skip 할 수 있다 — `--skip-validate` 는 5 게이트 전부를 끄므로 개별 flag 를 우선한다.

### 2.4 수동 빌드

```bash
cd workflow-source
# 빌드 venv (없으면 생성)
python3 -m venv .venv-build
.venv-build/bin/pip install --upgrade pip build twine

# wheel + sdist 산출
.venv-build/bin/python -m build
.venv-build/bin/twine check dist/*
#   → Checking dist/standard_ai_workflow-<X>.<Y>.<Z>-...whl: PASSED
#   → Checking dist/standard_ai_workflow-<X>.<Y>.<Z>.tar.gz: PASSED
```

### 2.5 로컬 smoke (fresh venv)

```bash
python3 -m venv /tmp/sawsmoke
/tmp/sawsmoke/bin/pip install dist/standard_ai_workflow-<X>.<Y>.<Z>-py3-none-any.whl
/tmp/sawsmoke/bin/python -c "
from workflow_kit.contract_v1 import choose_role, choose_roles, validate_fanin_output, recommend_model_tier
# ... spec-strict smoke (sub_task 5필드 + artifact_kind enum)
"
```

spec 의 strict validation 이 red 로 빨개지면 그대로 멈추고 fix → 재빌드.

### 2.6 GitHub Release 생성 + asset attach

```bash
# cwd 는 저장소 루트
REPO="<github-owner>/<github-repo>"     # 예: ykylee/standard_ai_workflow
TAG="v<X>.<Y>.<Z>"

gh release create "$TAG" \
  --repo "$REPO" \
  --title "v<X>.<Y>.<Z> — <한 줄 요약>" \
  --notes-file workflow-source/releases/Beta-v<X>.<Y>.<Z>.md \
  --target main \
  --verify-tag \
  workflow-source/dist/standard_ai_workflow-<X>.<Y>.<Z>-py3-none-any.whl \
  workflow-source/dist/standard_ai_workflow-<X>.<Y>.<Z>.tar.gz
```

확인:

```bash
gh release view "v<X>.<Y>.<Z>" --repo "$REPO"
#   asset: standard_ai_workflow-<X>.<Y>.<Z>-py3-none-any.whl
#   asset: standard_ai_workflow-<X>.<Y>.<Z>.tar.gz
```

### 2.7 downstream 안내 (선택)

릴리스 직후 본인 사용 프로젝트 (downstream 예: `Devhub_example`, `my_harness`) 의 dep 박스를
`standard-ai-workflow @ https://github.com/<owner>/<repo>/releases/download/v<X>.<Y>.<Z>/standard_ai_workflow-<X>.<Y>.<Z>-py3-none-any.whl`
형태로 pin 하거나, `requirements.txt` 에 `git+` 형태 사용.

## 3. 트러블슈팅

### 3.1 `workflow_kit/contract_v1` 또는 `workflow_kit.common.{state,contracts,schemas}` 가 wheel 에 포함 안 됨

원인: `pyproject.toml` 의 `tool.setuptools.packages` 누락 (v0.5.6 / v0.5.7.1 에서 이미 fix 됨).
확인:

```bash
unzip -l dist/standard_ai_workflow-*.whl | grep -E "contract_v1|common/(state|contracts|schemas)/__init__"
#   → "workflow_kit/contract_v1/__init__.py"                       ← 반드시 있어야 함
#   → "workflow_kit/common/state/__init__.py"                      ← v0.5.7.1+ 필수
#   → "workflow_kit/common/contracts/__init__.py"                  ← v0.5.7.1+ 필수
#   → "workflow_kit/common/schemas/__init__.py"                    ← v0.5.7.1+ 필수
```

수정 후 재빌드. 회귀: `wk check-packaging`.

### 3.2 `twine check` 가 README 파싱 실패

원인: `readme = "README.md"` 인데 빌드 시점에 README 가 표준 CommonMark 가 아님 (v0.5.7 기준 OK).
해결: README.md 의 표/코드블록 CommonMark 호환 점검.

### 3.3 Release page 가 draft 로 생성됐을 때

```bash
gh release edit "v<X>.<Y>.<Z>" --repo "$REPO" --draft=false
```

## 4. 회귀 (Reference)

| release | wheel / sdist | release page | 비고 |
|---|---|---|---|
| v0.5.0-beta | local only | ✅ |  |
| v0.5.1 / 5.2 / 5.3 / 5.4 | (wheel build 까지만, 미배포) | (release page 없음) |  |
| v0.5.5-beta | tag only | ❌ (소급 정정 가능) | Phase 11 pilot |
| v0.5.6-beta | tag only | ❌ (소급 정정 가능) | P0 enforcement (validator + delegator) |
| v0.5.7-beta | **GitHub Release + wheel/sdist** | ✅ (2026-06-08) | v0.5.7 wheel packaging 도입 |
| v0.5.7.1-beta | (wheel packaging fix) | (v0.5.7 에 통합) | state/contracts/schemas wheel 누락 fix |
| v0.5.8-beta | GitHub Release | (v0.5.7.1 직후) | interactive harness picker + packaging smoke automation |
| v0.5.9-beta | GitHub Release | ✅ | wire 가이드 §7/§8/§9 보강 |
| v0.5.9.1-beta | GitHub Release | ✅ | wire 가이드 §3 sub_payloads fix + 회귀 test |
| v0.5.10-beta | GitHub Release | ✅ (2026-06-08) | choose_roles sub.delegation_id parent-prefix spec 정합 |
| v0.5.11-beta | GitHub Release | ✅ (2026-06-09) | Mavis engine hook (§6.5) + ADR 정식 기록 + 비대화형 가이드 보강 |
| v0.6.0-beta | GitHub Release | (planned) | LLM wiki layer git-tracked (ai-workflow/wiki/) |
| v0.6.0.1-beta | GitHub Release | ✅ (2026-06-12) | memory/active/ rename + bootstrap --enable-wiki + 6 harness wiki/ stub (P1.5) |
| v0.7.0~v0.7.62 | 누적 follow-up batch — AIDLC Extension 시스템 + 9-Artifact + UOW + audit log + wiki 운영 cross-link + release pipeline 정식화 + mkdocs strict + consumer feedback metrics | ✅ | 95+ 신규 smoke test 누적. 회귀 표 v0.5.7~v0.6.0.1 사이는 follow-up batch 로 통합 표기 |
| v0.8.0-beta | GitHub Release | ✅ (2026-06-15 기준 추정, SemVer stable API frozen 시작) | Stable API frozen (2-year SemVer guarantee: v0.8.0 → v2.0.0). `deprecation 1st/2nd cycle` 정책 도입 |
| v0.8.1~v0.8.15 | mypy strict 단계적 격상 cumulative (19 file clean) | ✅ | spec §5.3 정공법 1 release = 1-2 file 격상. workflow_kit_cli 49 error 는 mypy 1.x 기준, 후속 |
| v0.8.10~v0.8.11 | read-only MCP manifest + transport | ✅ | phishing_keywords pre-existing fix 2 종 |
| v0.8.15 | release-dist 1-command + housekeeping (spec §9 9/12) | ✅ |  |
| v0.9.0-beta | **Phase 11 closed** + Phase 12 kickoff | ✅ (2026-06-18) | spec drift patch + release note + mypy config 정합 ([tool.workflow-doctor] section 분리) + deprecation 1st cycle 적용 (`phishing_federation_v4.fetch_federated_phishing_urls_v4` DeprecationWarning) |
| v0.9.1-beta | mypy workflow_kit_cli strict + release --full-auto + deprecation contract | ✅ (2026-06-18+) |  |
| v0.9.2-beta | purpose.md concept 흡수 (외부 reference 차용 정공법 1차 적용) | ✅ |  |
| v0.9.3-beta | deprecation 2nd cycle 적용 (`phishing_federation_v4.build_default_sources_v4`) | ✅ |  |
| v0.9.4-beta | R-A follow-up part 1 (state.json.purpose_digest 1-line 자동 생성) | ✅ |  |
| v0.9.5-beta | R-A follow-up part 2 (skill context load integration) | ✅ |  |
| v0.9.6-beta | R-A follow-up part 3 (wiki-event-sync R-A trigger) | ✅ |  |
| v0.10.0-beta | deprecation 1st + 2nd cycle 동시 종료 (SemVer major) | ✅ |  |
| v0.10.1-beta | skill-only entry mode + claude-code adapter (SemVer minor) | ✅ |  |
| v0.10.2-beta | delivery layer 확장 (claude-code 진입점 정정 + aider/goose/custom + self-bootstrap) | ✅ |  |
| v0.10.3-beta | wiki file deletion cascade cleanup (R-A follow-up cycle 2) | ✅ | 2026-06-24 release note 기준 본문 drift 발생 (CHANGELOG.md 본문) |
| v0.10.4-beta | **CodeWhale 10번째 하네스** (commit `cf0060d`, 2026-07-03) | ✅ (release note 정정, 2026-07-18) | 단일 SKILL.md overlay (Constitution handles verification/parallelism/context) |
| v0.11.0-beta | two-step CoT ingest (R-A follow-up cycle 3) — `workflow_kit.common.purpose_ingest` helper (5 함수 + 5 dataclass) + 3 skill context load + dispatcher `ingest-purpose` + 6 acceptance test | ✅ |  |
| v0.11.1-beta | graph insights (R-A follow-up cycle 4) — `workflow_kit.common.purpose_graph` helper (6 함수 + 7 dataclass) + dispatcher `graph-insights` + 8 acceptance test | ✅ |  |
| v0.11.2~v0.11.10 | 누적 mypy strict 격상 21→35 file (cycle 3~26단계) + Layer 1/Layer 2 mypy defense + release pipeline 자동화 + consumer metrics | ✅ |  |
| v0.11.11-beta | mypy strict CI 통합 (`.github/workflows/mypy-strict.yml` + dev extra `mypy==2.1.0`) | ✅ |  |
| v0.11.12-beta | mypy strict release-time gate (`cmd_validate` 5번째 source `mypy`) | ✅ |  |
| v0.11.13-beta | mypy CI cross-verify (Layer 1 ↔ Layer 2 정합 advisory, `_cross_verify_ci_mypy`) | ✅ |  |
| v0.11.14-beta | release-status dispatcher (신규 `workflow_kit/release_status.py` + subcommand 36) | ✅ |  |
| v0.11.15-beta | release summary 1-line (jq-friendly verdict) | ✅ |  |
| v0.11.16-beta | release-status --auto-bump 확장 | ✅ |  |
| v0.11.17-beta | (cumulative) | ✅ |  |
| v0.11.18-beta | **FULL mypy strict 도달** 공식 release — 누적 35→54 file clean, 48→0 errors (-48) | ✅ (2026-06-30) | commit `4253eed` 12 file 일괄 격상. CI mypy-strict workflow passing |
| v0.11.19-beta | 1st batch 4 skill stable (session-start / doc-sync / validation-plan / code-index-update) | ✅ | 누적 stable=4 |
| v0.11.20-beta | 2nd batch 4 skill stable (backlog-update / merge-doc-reconcile / workflow-linter / project-status-assessment) + 2 latent bug fix | ✅ | 누적 stable=8 |
| v0.11.21-beta | 3rd batch 1 skill stable (robust-patcher) — `workflow_kit/common/schemas/patcher.py` + `scripts/run_robust_patcher.py` + 5 smoke test | ✅ (2026-07-02) | 누적 stable=9. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.21-beta> |
| v0.11.22-beta | **ADR-005 Memory Index Phase 1~3d** 8 release + ADR-006 retrospective 자리 박기 | ✅ | Phase 12 운영 지능화 기반 |
| v0.13.0~v0.13.3-beta | Quality Dashboard, telemetry, self-recovery, wiki↔memory bidirectional link | ✅ | Operational Intelligence 1차 close-out |
| v0.14.0~v0.15.0-beta | append-only memory layout + 2-cycle deprecation 안정화 | ✅ (2026-07-17) | v0.15.0은 `.bak` drop breaking release |
| v0.15.1~v0.15.15-beta | dashboard·harness·sample·README·설치·quickstart cross-check와 stale 정정 | ✅ (2026-07-18) | 누적 20종 smoke PASS; v1.0.0 진입 평가 준비. tag `v0.15.15-beta` push + gh release create 완료 |

> 회귀 표의 시점은 *적용 release* 기준. *GHRelease 본문 작성일*은 `gh release view` 로 확인 권장. v0.7.x follow-up batch 와 v0.8.x mypy 격상 구간은 follow-up batch 단위로 통합 표기.

## 다음에 읽을 문서

- [릴리스 노트 디렉토리](https://github.com/ykylee/standard_ai_workflow/tree/main/workflow-source/releases/)
- [현재 릴리스 노트 v1.2.0](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/releases/Beta-v1.2.0.md)
- [Maturity Matrix](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/maturity_matrix.json)
- [설치·사용 가이드](./INSTALLATION_AND_USAGE.md)
- [Project Profile](./PROJECT_PROFILE.md)
