# Beta v3.5.1 — 환경 변수 없이 허브 MCP 에 붙기 (2026-11-26)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- 셋업이 Claude Code `.mcp.json` 에 `headersHelper: "python3 .workflow-hub/hub_client.py mcp-headers"` 를 더한다. 헬퍼가 `.workflow-hub/env` 의 콜사인 토큰으로 `Authorization` 헤더를 내므로 셸에 `WORKFLOW_HUB_TOKEN` 을 올리지 않아도 붙는다.
- 정적 헤더 `Bearer ${WORKFLOW_HUB_TOKEN}` 는 그대로 둔다 — 헬퍼를 모르는 하네스는 이 참조로 붙는다. 토큰 값은 어떤 설정 파일에도 쓰지 않는다.
- `hub_client.py mcp-headers` — 이 파일 옆 `env` 를 읽어 헤더 JSON 한 줄을 낸다. 토큰이 없으면 이유를 남기고 0 아닌 코드로 끝난다.

## 검증

- 실측(claude 2.1.332, 변수 없음): 헬퍼면 허브 도구 전체와 `hub_session_start` 가 보이고, 변수 참조만이면 부트스트랩 도구 6종만 보인다. 헬퍼와 정적 헤더를 함께 두면 헬퍼가 이긴다.
- `check_hub_client` case 6 · `check_hub_bootstrap` case 3 · `check_hub_harness_intake` · Go `TestSetupMCPJSONHeadersHelper` 가 새 계약을 잰다. 되주입 3건(Python 셋업 헬퍼 끄기 · 클라이언트 명령 이름 바꾸기 · Go 셋업 헬퍼 끄기)이 모두 red.

## 운영 범위

- DB 판은 20 그대로다.
- 이미 셋업된 저장소는 `.workflow-hub/hub_client.py` 를 새로 받고(`GET /v1/bootstrap/hub_client.py`) `.mcp.json` 에 `headersHelper` 줄을 더하면 된다. 그 하네스의 local scope 에 옛 `workflow-hub` 항목이 있으면 그것이 이긴다 — `claude mcp get workflow-hub` 로 범위를 본다.
- 재지 않은 것: MiniMax Code 가 모르는 칸 `headersHelper` 를 무시하는지, `python3` 이 없는 Windows.
