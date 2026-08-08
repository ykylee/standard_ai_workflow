"""branch protection 판정 — 3-layer defense 의 3rd layer (v1.1.2+, TASK-023)

TASK-019 가 1st (도구가 `--force` 를 제공하지 않음) 와 2nd (pre-push hook) 를 닫고
3rd (server-side branch protection) 는 *가이드* 로만 남겼다. 가이드는 지켜졌는지
아무도 확인하지 않으므로, 실제로는 layer 가 둘뿐인 것과 같았다. 본 모듈이 그
3rd layer 가 *실제로 켜져 있는지* 를 읽어서 판정한다.

**판정만 한다.** 보호를 켜지도, push 를 막지도 않는다 — branch protection 을 바꾸는
것은 저장소 소유자의 결정이고, 도구가 조용히 바꿔서는 안 되는 종류의 설정이다
(§5D.4: 되돌릴 수 없는 결정은 사람이 한다).

GitHub 의 protection JSON 은 **보호가 없으면 404** 이고, 있으면 필드가 중첩
dict 로 온다. 두 경우를 한 함수가 같은 모양으로 정규화한다.

Public API:
    ProtectionVerdict          — 판정 결과 (dataclass)
    evaluate_protection(...)   — protection JSON → 판정 (pure)
    REQUIRED_CHECKS            — 검사하는 항목과 그 이유
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final


#: 검사 항목 → 왜 보는가. `--force` 방어가 목적이므로 force push / 삭제가 핵심이고,
#: 나머지는 *참고* 로만 보고한다 (팀마다 정책이 다르다).
REQUIRED_CHECKS: Final[dict[str, str]] = {
    "allow_force_pushes": "force push 가 허용되면 1st/2nd layer 를 우회해 히스토리를 덮을 수 있다",
    "allow_deletions": "브랜치 삭제가 허용되면 force push 와 같은 결과를 다른 경로로 낸다",
}


@dataclass
class ProtectionVerdict:
    """branch protection 판정.

    Attributes:
        protected: protection 이 *존재* 하는가 (404 면 False).
        force_push_blocked: force push 가 막혀 있는가.
        deletion_blocked: 브랜치 삭제가 막혀 있는가.
        ok: 3rd layer 로서 충분한가 (위 둘이 모두 True).
        findings: 사람이 읽을 판정 근거.
        advisory: 참고 항목 (required reviews / status checks 등, 판정에 안 씀).
    """

    protected: bool
    force_push_blocked: bool = False
    deletion_blocked: bool = False
    findings: list[str] = field(default_factory=list)
    advisory: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.protected and self.force_push_blocked and self.deletion_blocked

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "protected": self.protected,
            "force_push_blocked": self.force_push_blocked,
            "deletion_blocked": self.deletion_blocked,
            "findings": list(self.findings),
            "advisory": dict(self.advisory),
        }


def _enabled(payload: dict[str, Any], key: str) -> bool | None:
    """`{"allow_force_pushes": {"enabled": false}}` 에서 bool 을 꺼낸다.

    GitHub 은 이 필드들을 `{"enabled": bool}` 로 감싸 준다. 다만 응답 모양이
    엔드포인트/권한에 따라 흔들려서, 평평한 bool 로 오는 경우도 방어한다.
    알 수 없으면 None — *모른다* 와 *꺼져 있다* 를 섞지 않는다.
    """
    raw = payload.get(key)
    if isinstance(raw, dict):
        value = raw.get("enabled")
        return bool(value) if isinstance(value, bool) else None
    if isinstance(raw, bool):
        return raw
    return None


def evaluate_protection(
    payload: dict[str, Any] | None,
    *,
    not_found: bool = False,
) -> ProtectionVerdict:
    """protection JSON 을 판정으로 바꾼다 (pure — 네트워크를 타지 않는다).

    Args:
        payload: `GET /repos/{owner}/{repo}/branches/{branch}/protection` 의 body.
        not_found: 404 였는가 (보호 자체가 없음).

    Returns:
        ProtectionVerdict
    """
    if not_found or payload is None:
        return ProtectionVerdict(
            protected=False,
            findings=[
                "branch protection 이 설정돼 있지 않다 (404). 3rd layer 가 비어 있다 — "
                "1st(도구)/2nd(pre-push hook)만으로는 hook 미설치 호스트를 막지 못한다."
            ],
        )

    findings: list[str] = []

    force_allowed = _enabled(payload, "allow_force_pushes")
    if force_allowed is None:
        findings.append(
            "allow_force_pushes 를 읽지 못했다 (권한 부족이거나 응답 형식이 다르다). "
            "판정을 *통과* 로 치지 않는다."
        )
        force_blocked = False
    else:
        force_blocked = not force_allowed
        if force_allowed:
            findings.append(f"allow_force_pushes=true — {REQUIRED_CHECKS['allow_force_pushes']}")

    del_allowed = _enabled(payload, "allow_deletions")
    if del_allowed is None:
        findings.append("allow_deletions 를 읽지 못했다. 판정을 *통과* 로 치지 않는다.")
        del_blocked = False
    else:
        del_blocked = not del_allowed
        if del_allowed:
            findings.append(f"allow_deletions=true — {REQUIRED_CHECKS['allow_deletions']}")

    advisory: dict[str, Any] = {}
    reviews = payload.get("required_pull_request_reviews")
    if isinstance(reviews, dict):
        advisory["required_approving_review_count"] = reviews.get(
            "required_approving_review_count"
        )
    checks = payload.get("required_status_checks")
    if isinstance(checks, dict):
        contexts = checks.get("contexts")
        advisory["required_status_checks"] = (
            len(contexts) if isinstance(contexts, list) else None
        )
    enforce_admins = _enabled(payload, "enforce_admins")
    if enforce_admins is not None:
        advisory["enforce_admins"] = enforce_admins
        if not enforce_admins:
            findings.append(
                "enforce_admins=false — 관리자는 보호를 우회한다 (판정에는 반영하지 않음, 참고)."
            )

    if not findings:
        findings.append("force push / 브랜치 삭제가 모두 차단돼 있다. 3rd layer 성립.")

    return ProtectionVerdict(
        protected=True,
        force_push_blocked=force_blocked,
        deletion_blocked=del_blocked,
        findings=findings,
        advisory=advisory,
    )
