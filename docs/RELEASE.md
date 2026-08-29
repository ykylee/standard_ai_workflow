# Release Procedure (v0.5.7+)

- 문서 목적: Standard AI Workflow 릴리스 절차 (버전 박기 → 빌드 → 스모크 → GitHub Release attach) 를 한 자리에 정리한다.
- 범위: 채널 정책, 사전 점검, 빌드, 로컬 smoke, GitHub Release 생성, 트러블슈팅, 회귀 표
- 대상 독자: 저장소 maintainer (`ykylee`), 릴리스 매니저
- 상태: stable (v1.2.0-beta 기준; 절차 자체는 v0.5.7+ 부터 정식 도입된 정책 유지)
- 현재 package version: 1.2.0 (`workflow-source/pyproject.toml`)
- 최종 수정일: 2026-08-28
- 관련 문서: [README.md](https://github.com/ykylee/standard_ai_workflow/blob/main/README.md), [./PROJECT_PROFILE.md](./PROJECT_PROFILE.md), [./INSTALLATION_AND_USAGE.md](./INSTALLATION_AND_USAGE.md), [Workflow Kit Roadmap](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/workflow_kit_roadmap.md), [workflow-source/releases/](https://github.com/ykylee/standard_ai_workflow/tree/main/workflow-source/releases/)

> **최종 갱신**: 2026-07-18 (회귀 표를 v0.15.15 까지 확장하고 `release_pipeline.py` 자동화 경로 반영)
> **변경 이력**: PyPI/TestPyPI 업로드 정책 폐기 → **GitHub Releases 만** 사용 (v0.5.7 부터).
> 2026-08-14 소유자 최종 결정으로 **PyPI 발행 안 함이 확정**됐다 (§1 각주 0 — 재검토 트리거 포함).
> **이유**: 토큰 회전 부담, 외부 공개 단계 미도달, downstream 은 `pip install <wheel>` 로 로컬 검증.

---

## 1. 채널 정책

> **이 절이 릴리스 채널 정책의 정본이다** (v1.2.1, TASK-2026-08-13-main-007).
> 이전에는 `release_pipeline.py` 주석이 정책 근거로 *agent memory* 를 인용했는데,
> 그건 저장소 밖 파일이라 소비자도 새 기여자도 열어볼 수 없었다. 정책을 바꾸든
> 유지하든 **바꿀 자리는 이 표 하나**이고, 코드 주석은 여기를 가리킨다.

| 채널 | 상태 | 비고 |
|---|---|---|
| GitHub Releases (wheel + sdist + native plugin ZIP) | ✅ **유일한 공식 채널** | Codex·Claude Code 플러그인 asset 을 함께 attach |
| TestPyPI | ❌ 사용 안 함 | 2026-08-14 각주 1 **만료** — 리허설의 목적이던 PyPI 판단이 끝났다 |
| PyPI | ❌ 사용 안 함 — **결정 완료, 재론하지 않는다** | 2026-08-14 소유자 최종 결정. 아래 **각주 0** 이 근거와 재검토 트리거를 고정한다 |
| Docker / brew / system pkg | ❌ 해당 없음 | (Python wheel 만 다룸) |

모든 release 는 GitHub Releases 페이지에 wheel + sdist 및 아래 native plugin ZIP이 attach 된 형태다.

- `standard-ai-workflow-codex-plugin-<X>.<Y>.<Z>.zip`
- `standard-ai-workflow-claude-code-plugin-<X>.<Y>.<Z>.zip`

새 플러그인 지원 하네스는 `workflow_kit.plugin_distribution.PLUGIN_HARNESS_SPECS`에 등록하면 동일한 dist/release 경로에 자동 포함된다.
ZIP 이 이 둘뿐인 이유: 나머지 플러그인 하네스(Antigravity · Grok Build · pi.dev)는 저장소/`plugin/` 에서 직접 설치한다 — 채널 전체 그림은 `workflow-source/core/workflow_harness_distribution.md` §2.1.
release 본문은 `workflow-source/releases/Beta-v<X>.<Y>.<Z>.md` 가 그대로 들어감.

### 각주 0 — PyPI 발행 안 함 (2026-08-14 소유자 최종 결정)

**결정**: PyPI 에 발행하지 않는다. 배포는 이 저장소의 **GitHub Releases 하나**로 간다.

**이 절이 있는 이유는 결정이 반복해서 다시 올라오는 것을 막기 위해서다.** 기술 준비가
끝나 있으면(v1.2.0 이후가 그렇다) "이제 올릴 수 있다" 는 제안이 계속 생긴다. 아래
트리거가 성립하지 않는 한, 에이전트도 사람도 **이 결정을 다시 안건으로 올리지 않는다.**

**근거** (검토 문서의 판정을 그대로 씀 — [PyPI 발행 정책 검토](./planning/pypi-publication-policy-review-2026-08.md)):

- **비용이 상시로 든다**: 발행에는 계정·API 토큰(또는 Trusted Publishing OIDC 구성)이
  필요하고 토큰은 회전 대상이다. 소유자가 그 부담을 지지 않기로 했다.
- **얻는 것이 지금 없다**: 소비자는 GitHub Releases 의 wheel 로 이미 `pip install` 이
  된다. 대상 사용자가 저장소를 아는 사람들이라 이름 해석(`pip install <이름>`) 이점이
  실질적이지 않다.
- **되돌릴 수 없는 약속이 붙는다**: 공개는 `stable_guarantee.md` 의 2년 backward compat
  을 **낯선 소비자**에게 지운다. PyPI 는 같은 (이름, 버전) 재업로드가 불가하다.

**재검토 트리거 — 아래 중 하나가 실제로 생겼을 때만 다시 연다** (추측·선제 준비 금지):

1. 저장소를 모르는 외부 사용자가 `pip install standard-ai-workflow` 경로를 **요청**한 경우
2. 배포가 이 저장소 밖으로 나가야 하는 사유가 생긴 경우 (예: 조직 내부 표준 채택)
3. 소유자가 명시적으로 재검토를 지시한 경우

**같이 닫힌 것**: TestPyPI 리허설(TASK-2026-08-13-main-008)은 *PyPI 발행 여부를 판단*
하려는 사전 검증이었다. 판단이 끝났으므로 목적이 사라졌고 **취소**한다. 아래 각주 1 은
효력을 잃었다 — 이력으로만 남긴다.

### 각주 1 — TestPyPI 1회 한정 허용 (2026-08-13 소유자 승인) — ⛔ **만료됨 (2026-08-14, 각주 0)**

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
  §6 의 4번(발행 여부 소유자 결정)이다. → **그 판단은 2026-08-14 에 나왔다: 발행 안 함 (각주 0).**

## 1.5 버전 등급 판단 — `!` 는 무엇에 대한 breaking 인가

> **이 절이 등급 판단의 정본이다** (v1.3.0, TASK-2026-08-20-main-007).
> `wk release-status` 는 미발행 커밋에서 등급을 **파생**하고 breaking 이 있으면
> `requires_decision` 을 세워 사람에게 넘긴다. 도구는 근거를 모으고 **판단은
> 여기 적힌 기준으로** 한다 — 기준이 없으면 같은 모양의 커밋에서 매번 다시 헤맨다.

conventional commit 의 `!` 는 "무언가 깨진다" 는 표시일 뿐, **무엇이** 깨지는지는
말하지 않는다. 우리가 SemVer 로 보장하는 것은 **이 패키지의 공개 API** 다
(v0.8.0 stable freeze, v2.0.0 까지 2년 보장 — §4 회귀표). 그래서 등급은 다음을
본다:

| 질문 | major | minor/patch |
|---|---|---|
| 공개 Python API 시그니처가 바뀌었나 | 예 | 아니오 |
| 진입점(console script / `wk` 명령)이 **사라졌나** | 예 | 남아 있고 rc=0 이면 아니오 |
| 우리 산출물을 읽던 소비자가 **못 읽게 되나** | 예 | legacy 형태가 남아 읽히면 아니오 |
| 외부 spec 의 버전이 올랐나 | — | **그것만으로는 major 가 아니다** |

**적용 사례 — v1.3.0 의 `feat(okf)!` (ADR-026, OKF v0.1 → v0.2).**
`!` 를 달았지만 major 로 올리지 않았다. 근거 넷:

1. 공개 Python API 시그니처 변경 **0**.
2. 은퇴한 진입점 2종(`emit_wiki_l2_body`, `refresh_wiki_memory --refresh-raw`)은
   **남아 있고 rc=0** 이다 — 옛 인자도 계속 받고, 왜 아무것도 안 했는지 말한다.
   호출자가 죽지 않는다.
3. 우리 번들이 legacy 형태(`timestamp`, 본문 `# Citations`)를 **유지**하므로
   v0.1 소비자도 그대로 읽는다. 소비자가 잃는 것이 없다.
4. OKF SPEC §13 자신이 v0.2 를 *"a minor version bump"* 로 규정한다.

즉 그 `!` 가 가리킨 것은 **외부 spec 버전**이지 우리 API 가 아니었다. 반대로
진입점을 **정말 지우거나** 산출물을 v0.1 소비자가 못 읽게 바꾸는 날에는 major 다.

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

`wk release-pipeline dist --apply`는 Python wheel/sdist와 함께 Codex·Claude Code native plugin ZIP을 생성한다. `release`는 두 ZIP이 없으면 중단하며, 존재하면 GitHub Release asset으로 같이 첨부한다.

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

# GitHub Release에 같이 첨부할 Codex·Claude Code native plugin ZIP
.venv-build/bin/python -m workflow_kit.plugin_distribution \
  --output-dir dist \
  --version <X>.<Y>.<Z>
#   → dist/plugins/{codex,claude-code}/<X>.<Y>.<Z>/*.zip
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
  workflow-source/dist/standard_ai_workflow-<X>.<Y>.<Z>.tar.gz \
  workflow-source/dist/plugins/codex/<X>.<Y>.<Z>/standard-ai-workflow-codex-plugin-<X>.<Y>.<Z>.zip \
  workflow-source/dist/plugins/claude-code/<X>.<Y>.<Z>/standard-ai-workflow-claude-code-plugin-<X>.<Y>.<Z>.zip
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
| v1.0.0~v1.2.1 | v1.0.0 정식 진입 + 플러그인 채널 전환 + stable 표기 정리 | ✅ | tag 에서 `-beta` 접미사 제거 (§2.2). `v1.2.0-beta` 가 옛 표기의 마지막 |
| v1.3.0 | 배포 일관성·멱등성 gap 4개 + wiki L2 축 + OKF v0.2 이행 | ✅ (2026-08-20) | `feat(okf)!` 를 **minor** 로 판단한 첫 사례 — 근거는 §1.5 |
| v1.4.0 | 소유권 4번째 분류 '포크됨' + 혼합 표기 축 완결(생성기·코퍼스) + CI red 2건 해소 | ✅ (2026-08-24) | `!` 3건에 §1.5 4문항 적용 → **minor**. 공개 시그니처 변경 0 · 진입점 제거 0 · 별칭 17/17 유지 |
| v1.5.0 | ADR-027 로드맵·마일스톤·WBS 층 + SDLC 온보딩 기본 + overlay 위임 선언 | ✅ (2026-08-25) | `feat(roadmap)!` 에 §1.5 4문항 적용 → **minor**. 동결 표면 밖 · 옛 인자 rc=0 수용 · 출력 key 유지 · roadmap 부재 additive |
| v1.6.0 | Windows 플랫폼 결함 축 — emit 해석기 플랫폼 분기(`python_launcher`) + emit PYTHONPATH target 레이아웃 판정 + doctor `kit_resolution` + `safe_relpath` POSIX | ✅ (2026-08-25) | 커밋 타입은 전부 fix 지만 §1.5 판정 **minor** — 새 공개 모듈 + doctor 신기능 + payload 키 추가. 시그니처 파괴 0 · 진입점 제거 0 · 산출물 소비 불가 0. 체크인 payload 는 posix 고정 (Windows 플러그인 채널은 `python3` 별칭 필요) |
| v1.7.0 | 계층별 회귀 실행 계약 축 (ADR-028) — meta-watch 러너 내장(채취+판정) + `WATCHES_ALL_REASON` 어휘 + 좁은 선언 7건 소탕 + mcp 2.1.1 대응(importlib 동적 해석, latest_2x 핀 2.1.1) | ✅ (2026-08-28) | §1.5 판정 **minor** — 러너 신기능 + 새 공개 모듈(`meta_watch`) + 어휘 신설. 시그니처 파괴 0 · 진입점 제거 0 · runner JSON 은 `meta_watch` 키 추가만. 게이트는 축소하지 않는다 (main-004 기각 불변) |

> 회귀 표의 시점은 *적용 release* 기준. *GHRelease 본문 작성일*은 `gh release view` 로 확인 권장. v0.7.x follow-up batch 와 v0.8.x mypy 격상 구간은 follow-up batch 단위로 통합 표기.

## 다음에 읽을 문서

- [릴리스 노트 디렉토리](https://github.com/ykylee/standard_ai_workflow/tree/main/workflow-source/releases/)
- [현재 릴리스 노트 v1.2.0](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/releases/Beta-v1.2.0.md)
- [Maturity Matrix](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/maturity_matrix.json)
- [설치·사용 가이드](./INSTALLATION_AND_USAGE.md)
- [Project Profile](./PROJECT_PROFILE.md)
