# 즉시 진단 — 사용자가 본인 환경에서 실행

## Step 1: `mcp.opencode.json` (또는 사용자의 `opencode.json`) 의 최상위 key 확인

```bash
cat mcp.opencode.json  # bootstrap 이 emit 한 파일
# 또는
cat opencode.json      # 사용자가 merge 했을 수도
```

**기대**: 최상위에 `"mcp"` key 만. 예:
```json
{
  "mcp": {
    "standardAiWorkflowReadOnly": { ... }
  }
}
```

**문제 시나리오**: `"mcp_servers"` 또는 다른 key 가 최상위에 있음. 예:
```json
{
  "mcp_servers": {  // ❌ Codex 형식 — OpenCode 가 인식 못 함
    "standardAiWorkflowReadOnly": { ... }
  }
}
```

또는
```json
{
  "mcp": {...},
  "mcp_servers": {...}  // ❌ 둘 다 있음 — 어느 것이 우선인지 모호
}
```

## Step 2: 잘못된 key 이면 fix

**Option A**: `mcp_servers` → `mcp` 로 rename:
```bash
python3 -c "
import json
with open('mcp.opencode.json') as f: d = json.load(f)
if 'mcp_servers' in d and 'mcp' not in d:
    d['mcp'] = d.pop('mcp_servers')
    with open('mcp.opencode.json', 'w') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    print('Renamed mcp_servers -> mcp')
"
```

**Option B**: bootstrap 재실행 (자동으로 올바른 key emit):
```bash
python3 -m bootstrap_lib --target-root . --harness opencode --no-interactive --enable-mcp --force
```

## Step 3: OpenCode 재시작

```bash
# OpenCode 가 이미 떠 있으면 종료 후 재시작
# config 변경은 재시작 후 반영
```

## Step 4: verify

```bash
# OpenCode 가 정상 동작 시 5/5 success.
# 그래도 fail 이면 stdout/stderr 로그 확인
```

## 다른 가능성: `Codex` 형식 그대로 옮긴 경우

`workflow-source/mcp_servers/read_only_bundle.md` 가 **Codex 용 fixture** (line 17:
```
# [mcp_servers.standardAiWorkflowReadOnly]
# command = "python3"
# args = ["-m", "workflow_kit.server.read_only_jsonrpc", "--stdio-lines"]
```

이건 **주석** (snippet 예시). **Codex (TOML) 형식**이라 그대로 사용하면 안 됨. **OpenCode 는 JSON, 최상위 `"mcp"` key**. 

만약 사용자가 opencode.json 에 이 fixture 를 그대로 옮겼다면:
```json
{
  "mcp_servers": {  // ❌ TOML 형식 그대로
    "standardAiWorkflowReadOnly": {
      "command": "python3",
      "args": ["-m", "workflow_kit.server.read_only_jsonrpc", "--stdio-lines"]
    }
  }
}
```

→ Step 2 Option A 로 fix.
