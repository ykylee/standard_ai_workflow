# Release Procedure (v0.5.7+)

> **최종 갱신**: 2026-06-08
> **변경 이력**: PyPI/TestPyPI 업로드 정책 폐기 → **GitHub Releases 만** 사용.
> **이유**: 토큰 회전 부담, 외부 공개 단계 미도달, downstream 은 `pip install <wheel>` 로 로컬 검증.

---

## 1. 채널 정책

| 채널 | 상태 | 비고 |
|---|---|---|
| GitHub Releases (wheel + sdist) | ✅ **유일한 공식 채널** | `gh release create` 한 줄로 끝 |
| TestPyPI | ❌ 사용 안 함 | (v0.5.7 부터) |
| PyPI | ❌ 사용 안 함 | (v0.5.7 부터, 이전부터 보류) |
| Docker / brew / system pkg | ❌ 해당 없음 | (Python wheel 만 다룸) |

**v0.5.7 부터** 모든 release 는 GitHub Releases 페이지에 wheel + sdist 가 attach 된 형태.
release 본문은 `workflow-source/releases/Beta-v<X>.<Y>.<Z>.md` 가 그대로 들어감.

## 2. 절차 (한 사람이 직접 실행)

### 2.1 사전 점검

```bash
cd /Users/yklee/repos/standard_ai_workflow_minimax
git status                 # clean 트리 확인
git log --oneline -3       # 머지된 release squash 커밋 확인
gh auth status             # gh CLI 로그인 확인 (keyring)
```

### 2.2 버전 박기 (pyproject.toml)

`workflow-source/pyproject.toml`:

```toml
name = "standard-ai-workflow"
version = "<X>.<Y>.<Z>-beta"   # ← 매 release 마다 수동으로 올림
```

**PEP 440 note**: `0.5.7-beta` → wheel 파일명은 `0.5.7b0` 으로 normalize 됨 (정상).

### 2.3 빌드

```bash
cd workflow-source
# 빌드 venv (없으면 생성)
python3 -m venv .venv-build
.venv-build/bin/pip install --upgrade pip build twine

# wheel + sdist 산출
.venv-build/bin/python -m build
.venv-build/bin/twine check dist/*
#   → Checking dist/standard_ai_workflow-<X>.<Y>.<Z>b0-...whl: PASSED
#   → Checking dist/standard_ai_workflow-<X>.<Y>.<Z>b0.tar.gz: PASSED
```

### 2.4 로컬 smoke (fresh venv)

```bash
python3 -m venv /tmp/sawsmoke
/tmp/sawsmoke/bin/pip install dist/standard_ai_workflow-<X>.<Y>.<Z>b0-py3-none-any.whl
/tmp/sawsmoke/bin/python -c "
from workflow_kit.contract_v1 import choose_role, choose_roles, validate_fanin_output, recommend_model_tier
# ... spec-strict smoke (sub_task 5필드 + artifact_kind enum)
"
```

spec 의 strict validation 이 red 로 빨개지면 그대로 멈추고 fix → 재빌드.

### 2.5 GitHub Release 생성 + asset attach

```bash
cd /Users/yklee/repos/standard_ai_workflow_minimax
gh release create v<X>.<Y>.<Z>-beta \
  --repo ykylee/standard_ai_workflow \
  --title "Beta v<X>.<Y>.<Z> — <한 줄 요약>" \
  --notes-file workflow-source/releases/Beta-v<X>.<Y>.<Z>.md \
  --target main \
  --verify-tag \
  workflow-source/dist/standard_ai_workflow-<X>.<Y>.<Z>b0-py3-none-any.whl \
  workflow-source/dist/standard_ai_workflow-<X>.<Y>.<Z>b0.tar.gz
```

확인:

```bash
gh release view v<X>.<Y>.<Z>-beta --repo ykylee/standard_ai_workflow
#   asset: standard_ai_workflow-<X>.<Y>.<Z>b0-py3-none-any.whl
#   asset: standard_ai_workflow-<X>.<Y>.<Z>b0.tar.gz
```

### 2.6 downstream 안내 (선택)

릴리스 직후 본인 사용 프로젝트 (Devhub_example, my_harness 등) 의 dep 박스를
`standard-ai-workflow @ https://github.com/ykylee/standard_ai_workflow/releases/download/v<X>.<Y>.<Z>-beta/standard_ai_workflow-<X>.<Y>.<Z>b0-py3-none-any.whl`
형태로 pin 하거나, requirements.txt 에 git+ 형태 사용.

## 3. 트러블슈팅

### 3.1 `workflow_kit/contract_v1` 가 wheel 에 포함 안 됨

원인: `pyproject.toml` 의 `tool.setuptools.packages` 누락.
확인:

```bash
unzip -l dist/standard_ai_workflow-*.whl | grep contract_v1
#   → "workflow_kit/contract_v1/__init__.py"   ← 반드시 있어야 함
```

수정 후 재빌드.

### 3.2 `twine check` 가 README 파싱 실패

원인: `readme = "README.md"` 인데 빌드 시점에 README 가 표준 CommonMark 가 아님 (v0.5.7 기준 OK).
해결: README.md 의 표/코드블록 CommonMark 호환 점검.

### 3.3 Release page 가 draft 로 생성됐을 때

```bash
gh release edit v<X>.<Y>.<Z>-beta --repo ykylee/standard_ai_workflow --draft=false
```

## 4. 회귀 (Reference)

| release | wheel / sdist | release page |
|---|---|---|
| v0.5.0-beta | local only | ✅ |
| v0.5.1 / 5.2 / 5.3 / 5.4 | (wheel build 까지만, 미배포) | (release page 없음) |
| v0.5.5-beta | tag only, release page 없음 | ❌ (소급 정정 가능) |
| v0.5.6-beta | tag only, release page 없음 | ❌ (소급 정정 가능) |
| v0.5.7-beta | **GitHub Release + wheel/sdist** | ✅ (2026-06-08) |
