"""git 원격 주소 정규화 — 프로젝트 식별 키 (hub_spec §3.2, 요구 R3.2 · DS8).

허브는 이 주소를 **식별에만** 쓴다 — 접속하지 않는다 (요구 R3.7).
"""

from __future__ import annotations

import re
import secrets

from workflow_kit.hub.errors import HubError

#: 경로 대소문자를 구분하지 않는 호스트 — 경로를 소문자로 (DS8). 그 밖은 그대로 두고
#: 같은 저장소의 다른 표기는 소유자가 별칭으로 묶는다.
CASE_INSENSITIVE_HOSTS = frozenset({"github.com", "gitlab.com", "bitbucket.org"})

_SCP = re.compile(r"^(?P<user>[^@/\s]+@)?(?P<host>[^:/\s]+):(?P<path>(?!//)[^\s]+)$")
_URL = re.compile(r"^(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*)://(?P<rest>.+)$")


def invalid_remote(url: str, why: str) -> HubError:
    return HubError(400, "invalid_remote", f"git 원격 주소로 읽을 수 없다 ({why}): {url!r}", {"remote_url": url})


def normalize(url: str) -> str:
    """원격 주소 → ``host/path`` 키.

    >>> normalize("git@github.com:ykylee/standard_ai_workflow.git")
    'github.com/ykylee/standard_ai_workflow'
    """
    raw = (url or "").strip()
    if not raw:
        raise invalid_remote(url, "비었다")
    m = _URL.match(raw)
    if m:
        scheme = m.group("scheme").lower()
        if scheme == "file":
            raise invalid_remote(url, "로컬 경로는 원격이 아니다 — 원격을 먼저 만든다")
        rest = m.group("rest")
        authority, _, path = rest.partition("/")
        host = authority.rsplit("@", 1)[-1]
        host = re.sub(r":\d*$", "", host)
    else:
        if raw.startswith(("/", ".", "~")) or re.match(r"^[A-Za-z]:[\\/]", raw):
            raise invalid_remote(url, "로컬 경로는 원격이 아니다 — 원격을 먼저 만든다")
        s = _SCP.match(raw)
        if not s:
            raise invalid_remote(url, "스킴도 scp 형식도 아니다")
        host = s.group("host")
        path = s.group("path")
    host = host.strip().lower()
    if not host:
        raise invalid_remote(url, "호스트가 없다")
    path = re.sub(r"/+", "/", path.strip("/"))
    if path.endswith(".git"):
        path = path[: -len(".git")]
    path = path.strip("/")
    if not path:
        raise invalid_remote(url, "경로가 없다")
    if host in CASE_INSENSITIVE_HOSTS:
        path = path.lower()
    return f"{host}/{path}"


#: 원격 없는 프로젝트의 키 머리 — :func:`normalize` 의 결과(``host/path``, 호스트에 ``:`` 없음)와 겹치지 않는다.
LOCAL_PREFIX = "local:"


def local_key() -> str:
    """원격이 없는 저장소의 프로젝트 키 (소유자 2026-11-21) — 무작위, 주소 조회로는 닿지 않는다."""
    return LOCAL_PREFIX + secrets.token_hex(8)
