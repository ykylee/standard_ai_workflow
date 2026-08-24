# CLI 툴 (`wk`) 배포 방법 검토

- 문서 목적: 소비자가 `wk` CLI 를 설치하는 경로의 현황과 대안을 비교하고 권고안을 기록한다 (TASK-2026-08-12-main-004).
- 범위: 배포 채널 (GitHub Releases / PyPI / VCS 직설치), 설치 도구 (pip / pipx / uv), 패키징 제약
- 대상 독자: maintainer, 배포 정책 소유자
- 상태: 검토 완료 — 권고안 제시 (채널 변경은 소유자 결정)
- 최종 수정일: 2026-08-24
- 관련 문서: [`../RELEASE.md`](../RELEASE.md), [`../INSTALLATION_AND_USAGE.md`](../INSTALLATION_AND_USAGE.md), `workflow-source/pyproject.toml`

## 1. 현황 (v1.1.7-beta 기준, 전부 실측)

- 패키지: `standard-ai-workflow` — `[project.scripts]` 로 `wk` + `workflow-*` 40여
  개 binary 를 노출. wheel 은 `check_packaging` 이 격리 venv 에서 설치·import 를
  검증한다 (TASK-027 부터 `tools` 포함).
- **배포 채널: GitHub Releases 만** (whl + sdist 첨부). PyPI 미배포는 명시적 정책.
- 소비자의 실제 설치 경로 (문서화된 것):
  1. 저장소 clone → `pip install -e "./workflow-source[dev,release,mcp-sdk]"` (개발/자기 적용)
  2. GitHub Release 의 wheel 을 받아 `pip install <파일>`

## 2. 발견 — PyPI 공개 전 반드시 풀어야 하는 제약

**wheel 의 top-level 패키지가 `workflow_kit` / `bootstrap_lib` / `tools` 3개다 (실측).**
`tools` 와 `bootstrap_lib` 는 극히 일반적인 이름이라, PyPI 로 공개 배포하면 같은
top-level 을 쓰는 다른 패키지와 **site-packages 충돌**을 일으킨다 (pip 는 마지막
설치가 조용히 이긴다). 지금까지 문제가 안 된 이유는 배포 반경이 통제돼 있었기
때문이다 (전용 venv / pipx 격리 전제).

→ PyPI 경로를 열려면 `tools` → `workflow_kit.tools`, `bootstrap_lib` →
`workflow_kit.bootstrap` 격상이 선행돼야 한다. 이는 `[project.scripts]` 40여 개
entry point + `TOOL_MODULES` + 검사 다수를 건드리는 **별도 마이그레이션 task** 다
(deprecation cycle 필요).

> ✅ **해소 (v1.2.0, TASK-2026-08-13-main-005)**: 격상은 v1.1.8 에서 완료
> (TASK-2026-08-12-main-006·007), 구경로 shim 은 2nd deprecation cycle 로
> v1.2.0 에서 drop 됐다. wheel top-level 은 이제 `workflow_kit` 하나이고
> `check_packaging` 의 FORBIDDEN_IMPORTS 가 일반명 top-level 재유입을 막는다.
> **PyPI 발행의 기술 제약은 없다 — 남은 것은 정책 (소유자 결정) 뿐이다.**

## 3. 대안 비교

| # | 방식 | 명령 (소비자) | 장점 | 단점/제약 |
|---|---|---|---|---|
| A | **현상 유지** — GH Release wheel | `pip install https://github.com/ykylee/standard_ai_workflow/releases/download/v1.1.7-beta/standard_ai_workflow-1.1.7-py3-none-any.whl` | 정책 변경 없음, 릴리스 절차 이미 검증됨 | URL 이 길고 버전 갱신 수동. 전용 venv 안 쓰면 §2 충돌 위험 |
| B | **pipx / uv tool + GH Release wheel** | `uv tool install <A 의 URL>` / `pipx install <URL>` | **CLI 배포의 정석** — 격리 venv + PATH 에 `wk` 자동 등록, §2 충돌이 원천 차단 | 소비자에게 uv/pipx 필요 (요즘은 표준 장비) |
| C | **pipx / uv tool + git 직설치** | `uv tool install "git+https://github.com/ykylee/standard_ai_workflow@v1.1.7-beta#subdirectory=workflow-source"` | 릴리스 asset 없이 tag 만으로 설치, 항상 원본 추적 | 설치 시 git+빌드 필요 (느림). private repo 면 인증 |
| D | **PyPI 발행** | `uv tool install standard-ai-workflow` | 도달성 최대, 이름 예약, 버전 해석 자동 | **§2 네임스페이스 선행 필수** + 정책 변경 (소유자 결정) + 공개 유지 부담 |
| E | curl 설치 스크립트 / Homebrew tap | - | - | 현 단계 과함 (기각) |

## 4. 권고안

1. **단기 (즉시, 정책 변경 없음): B 를 공식 설치 경로로 문서화한다.**
   `INSTALLATION_AND_USAGE.md` 상단에 uv/pipx 한 줄 설치를 명시하고, 릴리스 노트에
   설치 명령을 싣는다. 격리가 기본이 되므로 §2 의 이름 충돌도 실사용에서 차단된다.
   C 는 부수 경로로 병기 (tag 만으로 설치 가능).
2. ~~**중기 (소유자 결정): PyPI 는 §2 네임스페이스 정리와 한 묶음으로만 재검토한다.**~~
   → ⛔ **종결 (2026-08-14, 소유자 최종 결정): PyPI 발행 안 함.** 전제였던 §2
   네임스페이스 정리는 v1.2.0 에서 끝났지만(wheel top-level = `workflow_kit` 하나),
   **정책 쪽이 닫혔다.** 배포는 GitHub Releases + 위 1번(B: uv/pipx) 로 간다.
   근거와 재검토 트리거는 [`../RELEASE.md`](../RELEASE.md) §1 **각주 0** 이 정본이다 —
   그 트리거가 성립하기 전에는 이 안건을 다시 올리지 않는다.
3. **검증 관행**: 설치 문서에 적는 명령은 적기 전에 실측한다 — 이번 검토에서 wheel
   설치·entry point 는 `check_packaging` 실측으로, uv/pipx 는 동일 메커니즘
   (wheel + venv + scripts) 임을 확인했다. PyPI 경로는 미실측 (열지 않았으므로).

## 5. 이번에 하지 않은 것

- PyPI/TestPyPI 실발행 — ⛔ 2026-08-14 **하지 않기로 확정** (`RELEASE.md` §1 각주 0)
- `tools`/`bootstrap_lib` 네임스페이스 격상 (별도 task 후보 — §2)
- Homebrew/설치 스크립트 (기각)
