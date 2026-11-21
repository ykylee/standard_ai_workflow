"""워크플로우 허브 (2.0) — 서버 쪽 kit.

계약 정본은 ``core/hub_spec.md`` 다. 이 패키지는 허브 프로세스 안에서만 돈다 —
작업 환경은 이 패키지를 깔지 않는다 (hub_spec §1-3, 요구 R0.4).

모듈 (hub_spec §2.2):
    errors  — 오류 형식 (§4.3)
    gitkey  — git 주소 정규화 (§3.2)
    db      — SQLite 스키마 · 이관 · 백업 (§3)
    store   — 등록 · 콜사인 · task · 이력 (§3.3)
    tools   — 도구 표 (MCP 와 HTTP 가 같은 함수를 부른다, DS5)
    app     — ASGI 앱 (``/healthz`` · ``/v1/tools/<name>`` · ``/mcp``)
"""

from __future__ import annotations

#: 도구 · HTTP 계약 판 (hub_spec §4.2).
CONTRACT = "hub/1"
