# MCP Server Diagnostic — OpenCode 가 "4 of 5 requests failed" 시

OpenCode 가 `standardAiWorkflowReadOnly` MCP server 를 호출할 때 4 of 5 가 fail 하면, 다음을 순서대로 실행해 주세요.

## 1. 새 wheel 의 protocolVersion 노출 확인

OpenCode 가 사용 중인 venv 의 `python3` 로:

```bash
# 1) 어떤 venv 인지 확인
which python3
# OpenCode 의 config 가 가리키는 python3 — 일반적으로 OpenCode 가 자체 venv 사용

# 2) OpenCode 의 opencode.json (또는 mcp.opencode.json) 의
#    command 필드 그대로 실행
$(jq -r '.mcp.standardAiWorkflowReadOnly.command' opencode.json) \
  $(jq -r '.mcp.standardAiWorkflowReadOnly.args | join(" ")' opencode.json)

# (또는 bootstrap 가 emit 한 mcp.opencode.json 사용)
```

server 가 stdio 모드에서 stdin 대기. 직접 request 보내려면:

```bash
# Server 가 정상인지 확인 (initialize → tools/list → tools/call)
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","clientInfo":{"name":"test","version":"0.0.1"}}}' \
  | PYTHONPATH="" \
  $(jq -r '.mcp.standardAiWorkflowReadOnly.command' opencode.json) \
  $(jq -r '.mcp.standardAiWorkflowReadOnly.args | join(" ")' opencode.json) \
  --stdio-lines
# (PYTHONPATH="" 로 source shadow 차단)
```

기대 출력:
```json
{"id":1,"jsonrpc":"2.0","result":{"capabilities":{"tools":{"listChanged":false}},"protocolVersion":"2025-03-26","serverInfo":{"name":"workflow_read_only_bundle","version":"v0.5.11-beta"}}}
```

`protocolVersion: 2025-03-26` 이 보여야 정상. 안 보이면:
- OpenCode 가 다른 venv 의 옛 workflow_kit 사용
- 또는 env.PYTHONPATH 가 source repo 가리킴 (그 경우 응답에 protocolVersion 없음)

## 2. OpenCode 의 opencode.json env 확인

```bash
# OpenCode 의 opencode.json 또는 mcp.opencode.json 의 env.PYTHONPATH
cat opencode.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
env = d.get('mcp', {}).get('standardAiWorkflowReadOnly', {}).get('env', {})
print('env.PYTHONPATH:', env.get('PYTHONPATH', '(unset)'))
print('env.STANDARD_AI_WORKFLOW_ROOT:', env.get('STANDARD_AI_WORKFLOW_ROOT', '(unset)'))
"
```

**`PYTHONPATH` 가 source repo 경로 (`/.../workflow-source`) 가리키면 — 그것이 1차 원인.** 해당 줄 삭제 후 OpenCode 재시작.

## 3. OpenCode 가 사용하는 venv 의 workflow_kit version 확인

OpenCode 가 호출하는 python3 으로:

```bash
PYTHONPATH="" python3 -c "
import sys
print('executable:', sys.executable)
import workflow_kit
print('version:', workflow_kit.__version__)
print('file:', workflow_kit.__file__)
"
```

`__version__: v0.5.11-beta` + `file: .../site-packages/workflow_kit/__init__.py` 여야 정상. 만약:
- `v0.5.0-beta` 또는 `v0.5.10-beta` 였음 → `pip install --upgrade standard-ai-workflow` 필요
- `file: .../workflow-source/workflow_kit/__init__.py` 였음 → OpenCode 의 env.PYTHONPATH 가 source shadow (case 2)

## 4. OpenCode 로그 확인

OpenCode 가 MCP server 의 stderr 를 로그에 capture. stderr 만 출력:

```bash
PYTHONPATH="" \
$(jq -r '.mcp.standardAiWorkflowReadOnly.command' opencode.json) \
$(jq -r '.mcp.standardAiWorkflowReadOnly.args | join(" ")' opencode.json) \
--stdio-lines \
2>/tmp/mcp_stderr.log
# 5초 후 Ctrl-C
cat /tmp/mcp_stderr.log
```

stderr 에 python traceback 이 있으면 공유해 주세요.

## 5. 빠른 fix (OpenCode 측)

**opencode.json 의 env.PYTHONPATH 라인 삭제** 후 OpenCode 재시작. 이게 가장 흔한 원인.

```json
"standardAiWorkflowReadOnly": {
  "command": "python3",
  "args": ["-m", "workflow_kit.server.read_only_jsonrpc", "--stdio-lines"],
  "env": {
    "STANDARD_AI_WORKFLOW_ROOT": "/path/to/repo"
    // ❌ "PYTHONPATH": "/path/to/workflow-source"  ← 이 줄 삭제
  }
}
```

## 6. 더 빠른 fix (bootstrap 재실행)

```bash
python3 -m bootstrap_lib --target-root . --harness opencode --no-interactive --enable-mcp --force
```

이제 bootstrap 이 wheel install 환경 감지 → `PYTHONPATH` omit. 새 `mcp.opencode.json` 생성.

---

## 위 진단 결과를 알려주시면

- **version + file path**: wheel 정상 설치 여부
- **env.PYTHONPATH**: source shadow 여부
- **stderr 로그**: server 의 python traceback (있다면)

중 무엇이 잘못된 것인지 정확히 짚어드립니다.
