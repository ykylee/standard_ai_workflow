# 14차 세션 — federation self-host add (2026-08-12)

- 문서 목적: TASK-2026-08-12-main-001 종결 기록. plex 가 federation 의 첫 상시 참여자가 됐다.
- 상태: done
- 관련: [TASK-001](../backlog/tasks/TASK-2026-08-12-main-001.md), `multi_workspace_orchestration.md` §7.4, [환경 기록 plex](../../environments/plex.md)

## 요약

지금까지 federation 은 "명령이 있는 것" 이지 "돌고 있는 것" 이 아니었다 — serving 을
손으로 띄워야 했고 아무도 안 띄우고 있었다. 이제 plex 에서 registry serving 이
**상시 가동**된다.

| 단계 | 내용 |
|---|---|
| registry 위생 | stale `feat-dead` entry 정리, `main @ <repo>` 등록 (endpoint 포함) |
| `--print-systemd-unit` 신설 | 상시 가동의 **실행 가능한 경로** (산문 절차의 손 unit 사본 방지 — §11 과 같은 원리). 토큰은 unit 에 값이 남지 않게 `EnvironmentFile` (0o600) 로 실행 시점 공급 |
| plex 가동 | `wk-registry` systemd user unit, `0.0.0.0:8765` + Bearer 토큰, `enable --now` → active |
| LAN 실측 | healthz 200 / 무토큰 401 / 토큰 200 (main entry) / POST 405 |
| 합류 절차 | `environments/plex.md` — 두 번째 호스트는 `add-known-host` + `pull` 두 명령이면 합류 (darwin 은 launchd 라 unit 은 참고용) |
| 검사 | `check_registry_server` case 11 — unit 계약 고정 (토큰 미설정에도 출력 성공, 인자 반영, `EnvironmentFile` 은 `--token-env` 시에만) |

검증: registry 계열 7검사 green (11/11 포함), 전량 2축 251/251 ×2, mypy strict 0.

## 남긴 것

- **cross-host 실측은 두 번째 호스트 결정(사용자) 후** — 방화벽 / reverse proxy /
  TLS 종단은 그때. 합류는 environments/plex.md 절차 두 명령.
- 토큰 파일과 unit 은 호스트 로컬 (커밋 밖) — 환경 기록이 그 존재와 재생성 명령을
  가리킨다.
