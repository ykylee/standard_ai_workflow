# 환경 기록 — plex (federation 주 호스트)

- 문서 목적: plex 호스트의 federation serving 구성 기록 (TASK-2026-08-12-main-001).
- 상태: active
- 최종 수정일: 2026-08-12

## 환경 및 호스트 정보

- 호스트명: plex (`wk workspace-registry host-id` = `plex`)
- OS 유형: Linux
- Python: 시스템 python3 (3.13) / 개발 venv `.venv` (dev,release,mcp-sdk extras)
- 프로젝트 루트: `/home/yklee/repos/standard_ai_workflow`
- LAN IP: `192.168.0.121`

## Federation serving (상시 가동, 2026-08-12~)

| 항목 | 값 |
|---|---|
| systemd user unit | `~/.config/systemd/user/wk-registry.service` (`systemctl --user status wk-registry`) |
| unit 생성 명령 | `wk host-serve-registry --print-systemd-unit --bind 0.0.0.0 --port 8765 --token-env WK_REGISTRY_TOKEN` |
| endpoint | `http://192.168.0.121:8765/registry.json` (+ `/healthz`, 그 외 404) |
| 인증 | `Authorization: Bearer <WK_REGISTRY_TOKEN>` — 값은 `~/.config/workflow_kit/registry_server.env` (0o600, 커밋 금지) |
| 성격 | read-only (쓰기 405), registry 부재 시 빈 registry (404 아님) |
| registry 파일 | `~/.cache/workflow_kit/registry.json` — entry: `main @ /home/yklee/repos/standard_ai_workflow` |

실측 (2026-08-12): LAN 주소로 `healthz` 200 / 무토큰 401 / 토큰 200 (entry 반환) /
POST 405.

## 두 번째 호스트 합류 절차 (darwin homelab 등 — 호스트 결정은 사용자)

합류 호스트에서:

```bash
# 1. plex 를 known host 로 등록 (토큰 값은 같은 이름의 환경변수로 준비)
wk host-pull-registry add-known-host --host-id plex \
    --endpoint http://192.168.0.121:8765/registry.json \
    --token-env WK_REGISTRY_TOKEN --apply

# 2. pull + merge 확인
wk host-pull-registry pull --host plex
wk host-pull-registry merge

# 3. (양방향이면) 그 호스트도 자기 unit 을 세우고, plex 에서 역방향 add-known-host
wk host-serve-registry --print-systemd-unit --bind 0.0.0.0 --port 8765 \
    --token-env WK_REGISTRY_TOKEN   # darwin 은 launchd 라 unit 은 참고용 — 수동 기동 또는 launchd plist 로 이식
```

## 검증 도구 상태

- [x] git / python3 / pip / gh (CI 감시)
- [x] `.venv` — mypy strict + mcp SDK + build (release 게이트는 venv 에서)

## 특이 사항

- `TMPDIR` 주의: 전량 검사는 `--tmp-dir` 실디스크 경로 필수 (tmpfs OOM 선례).
- 잔여 미실측 (두 번째 호스트 필요): 진짜 cross-host pull / 방화벽 / reverse proxy / TLS 종단.
