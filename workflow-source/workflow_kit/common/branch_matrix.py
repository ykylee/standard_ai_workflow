"""smoke 가 밟는 **브랜치 컨텍스트** 정본 (TASK-2026-08-10-main-017).

`ai-workflow/memory/active/<branch>/` 는 브랜치 이름으로 경로가 갈린다. 슬래시가
들어간 브랜치(`feature/x`)는 *중첩* 디렉터리가 되어 경로 깊이와 이름 파싱이 전부
달라지는데, main 에서 재면 그 차이가 0이다. 그래서 smoke 는 두 컨텍스트를 밟는다
(§2.56).

이 registry 가 존재하는 이유는 **재현 수단의 비대칭** 이다:

    CI 는 두 컨텍스트를 돌고, 로컬 전량 검사는 native 하나만 돈다.

TASK-016 이 그 대가를 실측했다 — `check_release_pre_check_gates` case 7 이
살아있는 브랜치의 `state.json` 존재를 전제해 slash 셀에서만 red 였고, **15연속
red 인 동안 로컬은 계속 green 이었으며 handoff 는 내내 "전량 검사 green" 을
기록했다.** 열흘 가까이 걸린 이유는 결함이 어려워서가 아니라 로컬에 그 축을
밟을 방법이 없었기 때문이다. `mcp` SDK 매트릭스와 같은 모양이고
(`sdk_matrix.py` 참조), 대응도 같다 — **정본을 한 곳에 두고 CI 와 로컬이 그것을
읽는다.**

    CI:    smoke.yml 의 prepare job 이 `--github-matrix` 로 주입
    로컬:  `run_all_checks.py --branch-context=all`

이 파일에 컨텍스트를 추가하면 CI 셀과 로컬 재현이 **함께** 늘어난다. yml 에
문자열을 복제하지 않는 것이 요점이다 — 복제하면 갈라지고, 갈라진 쪽이 조용히
이긴다.

Stdlib only — CI prepare job 이 의존성 설치 없이 실행한다.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

from workflow_kit.common.paths import BRANCH_ENV_KEYS

OVERRIDE_ENV_KEY = BRANCH_ENV_KEYS[0]
"""브랜치를 덮는 env key. `BRANCH_ENV_KEYS` 의 **최우선** 키를 그대로 쓴다.

`GITHUB_REF_NAME` 을 덮지 않는 이유: 그것은 러너의 실제 컨텍스트라, 덮으면
checkout / actions 까지 함께 거짓말을 하게 된다.
"""


@dataclass(frozen=True)
class BranchContext:
    """smoke 가 전량 검사를 한 번 돌리는 브랜치 컨텍스트 하나."""

    label: str
    """CI 셀 이름 겸 `--branch-context` 인자."""

    workflow_branch: str
    """덮어쓸 브랜치 이름. **빈 문자열 = 덮지 않는다** (러너/로컬의 실제 브랜치).

    빈 값을 env 로 *주입* 하면 안 된다 — `_usable_branch_name` 이 None 을 내고
    다음 env 키로 흘러가, "native 를 쟀다" 와 "빈 값이라 흘렀다" 가 같은 모양이
    된다. 주입 여부 판단은 `env_override()` 가 맡는다.
    """

    reason: str
    """왜 이 컨텍스트를 밟는가."""


BRANCH_CONTEXTS: tuple[BranchContext, ...] = (
    BranchContext(
        label="native",
        workflow_branch="",
        reason=(
            "러너/개발자의 실제 브랜치. 평소 개발이 거의 main 에서 이뤄지므로 "
            "이것이 기본 경로다 — 슬래시 없는 단일 depth."
        ),
    ),
    BranchContext(
        label="slash",
        workflow_branch="feature/ci-slash-probe",
        reason=(
            "슬래시가 든 브랜치. `active/feature/ci-slash-probe/` 라는 중첩 "
            "디렉터리가 되어 경로 깊이·이름 파싱이 달라지고, **그 브랜치의 "
            "state.json 은 존재하지 않는다** — 부재 경로를 밟는 유일한 셀이다 "
            "(TASK-016 의 15연속 red 가 정확히 이 자리였다)."
        ),
    ),
)


def contexts() -> tuple[BranchContext, ...]:
    return BRANCH_CONTEXTS


def labels() -> tuple[str, ...]:
    return tuple(ctx.label for ctx in BRANCH_CONTEXTS)


def context_for(label: str) -> BranchContext | None:
    for ctx in BRANCH_CONTEXTS:
        if ctx.label == label:
            return ctx
    return None


def apply_context(env: dict[str, str], ctx: BranchContext) -> dict[str, str]:
    """`ctx` 로 돌리기 위한 env (원본은 건드리지 않고 사본을 낸다).

    native 는 **상속된 오버라이드를 제거** 한다. 단순히 "주입하지 않는" 것으로는
    부족하다 — 부모 env 에 이미 `OVERRIDE_ENV_KEY` 가 있으면 native 를 명시적으로
    요청해도 그 값이 이겨서, 요청한 것과 다른 축을 재게 된다. 이 함수의 첫 구현이
    정확히 그랬고, `check_branch_context_matrix` 의 end-to-end 케이스가
    `--branch-context=all` 의 slash 패스에서 그것을 잡았다 (native 를 요청했는데
    slash 결과가 나왔다).

    빈 문자열을 *주입* 하는 것과도 다르다: 빈 값은 `_usable_branch_name` 이 None 을
    내어 다음 env 키로 흘러가므로, "native 를 쟀다" 와 "빈 값이라 흘렀다" 가 같은
    모양이 된다. 그래서 넣지 않고 **지운다**.

    `BRANCH_ENV_KEYS` 의 나머지 키(`GITHUB_REF_NAME` 등)는 건드리지 않는다 —
    그것은 러너/로컬의 실제 컨텍스트이고, native 가 재려는 것이 바로 그것이다.
    """
    out = dict(env)
    if ctx.workflow_branch:
        out[OVERRIDE_ENV_KEY] = ctx.workflow_branch
    else:
        out.pop(OVERRIDE_ENV_KEY, None)
    return out


def github_matrix_json() -> str:
    """smoke.yml 의 `fromJSON` 이 먹는 매트릭스 JSON."""
    return json.dumps(
        [{"label": ctx.label, "workflow_branch": ctx.workflow_branch}
         for ctx in BRANCH_CONTEXTS],
        ensure_ascii=False,
    )


def render_summary() -> str:
    lines = ["| label | workflow_branch | 이유 |", "| --- | --- | --- |"]
    for ctx in BRANCH_CONTEXTS:
        branch = f"`{ctx.workflow_branch}`" if ctx.workflow_branch else "(덮지 않음)"
        lines.append(f"| `{ctx.label}` | {branch} | {ctx.reason} |")
    lines.append("")
    lines.append(f"오버라이드 env key: `{OVERRIDE_ENV_KEY}`")
    lines.append("")
    lines.append("로컬 재현: `python3 workflow-source/tests/run_all_checks.py --branch-context=all`")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--github-matrix", action="store_true",
        help="smoke.yml 의 fromJSON 이 먹는 매트릭스 JSON 을 출력",
    )
    group.add_argument("--labels", action="store_true", help="label 을 한 줄에 하나씩 출력")
    group.add_argument("--summary", action="store_true", help="registry 를 표로 출력")
    args = parser.parse_args(argv)

    if args.github_matrix:
        print(github_matrix_json())
    elif args.labels:
        for label in labels():
            print(label)
    else:
        print(render_summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
