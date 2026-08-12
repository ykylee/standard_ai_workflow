r"""mkdocs plugin: docs/* 의 '- 최종 수정일: <date>' 헤더를 build-time 에 git log 로 자동 갱신.

v0.11.23+ 신규 (drift prevention P3). mkdocs serve / build 시 on_page_markdown hook 에서
page.file.abs_src_path 의 git last-commit date 를 읽어 source markdown 의 '- 최종 수정일: <old>'
라인을 '- 최종 수정일: <git-date>' 로 patch 한다.

본 plugin 의 의의:
  - docs/ 하위 markdown 의 header 가 *항상* git 진실과 정합. release --apply 의
    doc-headers-update 가 'src-side' 갱신을 보장한다면, 본 plugin 은 'site-side' 의
    *최종 검증선* 으로 작용 (수동 편집 / merge conflict 로 header 가 stale 해져도
    build 결과물은 항상 git-derived 정합).
  - workflow-source/core/*.md + README.md 는 mkdocs docs_dir 외부이므로 본 plugin 대상 ❌.
    본 plugin 은 docs/*.md 만 cover. core/README 는 doc-headers-update --apply 로
    src-side 갱신 유지.

CI integration:
  - .github/workflows/mkdocs.yml 의 Build step 직전 `PYTHONPATH=workflow-source` env 추가.
  - mkdocs.yml 의 plugins: 섹션에 `- tools.mkdocs_git_dates:GitDatesPlugin` 추가.

설계 노트:
  - PyYAML / external dep 0개. stdlib 만 사용.
  - on_page_markdown 만 hook. theme template 변경 ❌.
  - regex: r'^- 최종 수정일:\s*\S+(.*)$' (line-anchored, MULTILINE) — 가장 마지막 1 건만 patch
    (count=1). 본 markdown header 의 첫 번째 `- 최종 수정일:` 만 의미 있다고 가정.
  - plugin 자체 fail 시 silent skip (mkdocs build 가 깨지지 않도록). 본 policy 는 mkdocs 의
    다른 plugin 들 (e.g. material search) 의 fail-mode 와 정합.
"""
from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Any

LOG = logging.getLogger("mkdocs.plugins.git_dates")

# '- 최종 수정일: <old>' line. '<old>' 는 non-whitespace string (ISO date 또는 "unknown").
# 본 regex 는 본 markdown header 의 *첫 번째* 매치만 patch (count=1) — header 가 본문에
# 반복되는 경우 (예: changelog 의 "최종 수정일: 2026-07-03" 가 여러번 등장) 의 false positive 방지.
DATE_HEADER_DATE_RE = re.compile(
    r"^(- 최종 수정일:\s*)(\S+)([ \t]*)$",
    re.MULTILINE,
)


class GitDatesPlugin:
    """mkdocs plugin: page markdown 의 '- 최종 수정일' 헤더를 git log 로 자동 patch.

    Plugin config (mkdocs.yml):
        plugins:
          - search
          - tools.mkdocs_git_dates:GitDatesPlugin:
              enabled: true  # default: true

    Args (mkdocs plugin config):
      enabled: bool (default True) — 일시 disable 시 false.
    """

    def __init__(self) -> None:
        self.enabled: bool = True
        self._git_root_cache: Path | None = None

    # ------------------------------------------------------------------
    # mkdocs plugin lifecycle
    # ------------------------------------------------------------------

    def on_config(self, config: Any) -> None:
        """Plugin config 의 'enabled' 키 honor (default: True)."""
        plugin_cfg = config.get("plugins", {}).get("git-dates", {}) if isinstance(config, dict) else {}
        # mkdocs 는 plugins 의 dict 형식 vs list 형식 모두 받음. dict 면 config 직접 read.
        if hasattr(config, "plugins"):
            try:
                entries = config.plugins
                for entry in entries:
                    if getattr(entry, "name", None) == "git-dates":
                        self.enabled = bool(getattr(entry, "config", {}).get("enabled", True))
                        break
            except Exception:  # noqa: BLE001
                pass

    def on_page_markdown(self, markdown: str, page: Any, **kwargs: Any) -> str:
        """각 page 의 source markdown 에 대해 '- 최종 수정일' 헤더를 git log date 로 patch."""
        if not self.enabled:
            return markdown
        try:
            src_path = Path(page.file.abs_src_path)
        except Exception as exc:  # noqa: BLE001
            LOG.debug("could not resolve page file path: %s", exc)
            return markdown

        date = self._git_last_modified_date(src_path)
        if date is None:
            return markdown

        # search vs sub 분기 — new == markdown 가 *이미 정합* 일 수도 있음 (replacement == match).
        match = DATE_HEADER_DATE_RE.search(markdown)
        if match:
            return DATE_HEADER_DATE_RE.sub(rf"\g<1>{date}\g<3>", markdown, count=1)
        # 기존 header 가 없는 file — 첫 line 으로 prepend.
        # 단, docs/* 만 본 plugin 의 적용 대상. workflow-source/core/*, README.md 는
        # docs_dir 외부이므로 skip. mkdocs 가 본 plugin 에게 전달하는 모든 page 는
        # docs/ 하위이므로 본 prepend 는 항상 적절.
        LOG.debug("page %s: no 기존 - 최종 수정일: header, prepend '%s'", src_path.name, date)
        return f"- 최종 수정일: {date}\n\n{markdown}"

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _git_root(self) -> Path | None:
        """git repo root 를 1회 cache. abs_src_path 의 부모 chain 을 따라 .git/ 이 있는 dir."""
        if self._git_root_cache is not None:
            return self._git_root_cache
        # page.file.abs_src_path 는 보통 docs/<file>.md. 부모는 docs/ 그 부모는 repo root.
        try:
            cur = Path(__file__).resolve()
            for _ in range(6):  # workflow-source/tools/mkdocs_git_dates.py 에서 위로 6 단계 까지.
                cur = cur.parent
                if (cur / ".git").exists():
                    self._git_root_cache = cur
                    return cur
        except Exception:  # noqa: BLE001
            pass
        return None

    def _git_last_modified_date(self, src_path: Path) -> str | None:
        """git log 의 마지막 commit date 를 'YYYY-MM-DD' 로 반환. 실패 시 None."""
        git_root = self._git_root()
        if git_root is None:
            return None
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%cs", "--", str(src_path)],
                cwd=str(git_root),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                LOG.debug("git log failed for %s: %s", src_path, result.stderr.strip())
                return None
            date = result.stdout.strip()
            # YYYY-MM-DD 형식 verify (10자). 아니면 None.
            if len(date) >= 10 and date[4] == "-" and date[7] == "-":
                return date[:10]
            return None
        except subprocess.TimeoutExpired:
            LOG.warning("git log timeout for %s", src_path)
            return None
        except Exception as exc:  # noqa: BLE001
            LOG.debug("git log exception for %s: %s", src_path, exc)
            return None

# ---------------------------------------------------------------------------
# mkdocs `hooks:` 진입점 (v1.0.1+)
# ---------------------------------------------------------------------------
#
# **왜 plugin 이 아니라 hook 인가.** mkdocs 는 `plugins:` 항목을 `mkdocs.plugins`
# **entry point 이름** 으로만 해석한다 (`plugins.get_plugins()` → `entry_points(group=...)`).
# 즉 `- tools.mkdocs_git_dates:GitDatesPlugin` 은 import 경로가 아니라 *이름* 으로
# 취급되고, 설치된 배포판이 그 이름을 등록하지 않았으므로
# `The "..." plugin is not installed` config error 로 build 가 중단된다.
# `PYTHONPATH` 를 아무리 맞춰도 해결되지 않는다 — 실제로 mkdocs workflow 는 이 이유로
# 최근 100회 실행 중 성공이 0회였고, 문서 사이트가 한 번도 배포되지 못했다.
# (덧붙여 `GitDatesPlugin` 은 `BasePlugin` 을 상속하지도 않아, entry point 를
# 등록했더라도 mkdocs 가 거부했을 것이다.)
#
# `hooks:` 는 **파일 경로**로 모듈을 읽어 module-level 함수를 event handler 로 쓴다.
# 저장소 로컬 훅을 패키징 없이 붙이라고 있는 수단이고, 이 경우에 정확히 들어맞는다
# (`tools` 를 wheel 에 넣으면 소비자에게 저장소 내부 도구가 배포된다).
#
# 기존 `GitDatesPlugin` 클래스는 로직의 정본으로 남기고 아래에서 위임한다.

_HOOK = GitDatesPlugin()


def on_page_markdown(markdown: str, **kwargs: Any) -> str:
    """mkdocs `hooks:` event — page markdown 의 '- 최종 수정일' 을 git date 로 patch.

    `MKDOCS_GIT_DATES=off` 로 끌 수 있다 (구 plugin config `enabled: false` 대체).
    """
    import os

    if os.environ.get("MKDOCS_GIT_DATES", "").lower() in {"off", "0", "false"}:
        return markdown
    try:
        return _HOOK.on_page_markdown(markdown, **kwargs)
    except Exception as exc:  # noqa: BLE001 — hook 실패가 build 를 깨지 않는다
        LOG.debug("git-dates hook skipped: %s", exc)
        return markdown
