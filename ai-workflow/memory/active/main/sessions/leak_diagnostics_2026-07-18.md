# Session — 2026-07-18 / leak_diagnostics_2026-07-18

- 문서 목적: v0.15.15 release + follow-up 직후 python 프로세스 누적 / RSS 누수 진단 종합.
- 날짜: 2026-07-18
- 주제: `leak_diagnostics_2026-07-18`
- 출처: `[[active/leak_diagnostics_2026-07-18.md]] {#active-leak-diagnostics-2026-07-18}`
- 상태: stable

## 📋 Session Summary

v0.15.15 정식 release 직전 "python 프로세스가 누적되어 메모리가 가득 찬다" 는 보고가 있어 6개 운영 경로에서 누수 진단 수행. **누적 0건, RSS drift 0 MB** 확인. 본 워크플로우 패키지의 정상 운영 경로에서는 누수 발생 안 함. 운영 환경 외부 (외부 MCP client / 다른 Python application / OS-level daemon) 가능성 우선 점검 권장.

## 🛠️ Detail

### 측정 환경

- 워크스페이스: `/home/yklee/repos/standard_ai_workflow` (release v0.15.15-beta, 2026-07-18)
- 측정 도구: `ps -eo pid,rss,args` + `/proc/<pid>/status` VmRSS sampling + `PERF-MEM-02` 정공법 (1000회 반복 ≤ 10 MB baseline)
- 측정 대상 6개 경로:
  1. dispatcher 단발 호출 (`workflow_kit.workflow_kit_cli --command=...`)
  2. 빈발 short-lived 호출 (drift-prevention smoke × N)
  3. release pipeline (`release-doctor` + `refresh-maturity` + self-recovery)
  4. long-lived stdio MCP server (`mcp_v1_server.py` invoke_tool 1000회)
  5. subprocess 직접 호출 (`consumer_metrics.py` 의 gh API 4종)
  6. 통합 release pipeline + tag push + gh release create

### 측정 결과

| phase | 측정 항목 | 결과 |
|---|---|---|
| 위크플로우 시작 베이스라인 | python PID | 2 (system daemons 만) |
| 100+ 회 dispatcher 호출 | python PID 누적 | **0** (베이스라인 2 유지) |
| 50 회 dashboard long-run | RSS delta | +0.02 MB (안정) |
| **1000회 cache-dashboard (long-lived server)** | **RSS drift** | **+0.00 MB** (PERF-MEM-02 ≤ 10 MB 정합) |
| 30 회 drift-prevention (빈발) | 누적 PID | 0 |
| consumer_metrics gh API ×15 | 누적 PID | 0 |
| release-doctor (release fork 2~3) | 누적 PID | 0 |
| 종합 종료 + 5초 대기 | python PID | 2 (베이스라인 유지) |

### 발견된 fork 패턴 (누수 아님, 정상)

`release-doctor` 호출 시 두 개의 subprocess fork:
1. `tools/check_packaging.py` (0.20s 시점, RSS 12MB) — release packaging 검증
2. `workflow_kit.cli.doctor --json` (4.30s 시점, RSS 24MB) — doctor subcommand

둘 다 부모의 `subprocess.communicate()` 로 wait 하고 종료 시 함께 정리.

### 결론

이 워크플로우 패키지의 모든 운영 경로에서 **누적 누수 0건, RSS drift 0 MB** 확인.

**누수 의심 환경 안내**:
- 만약 운영 환경에서 누적 발생 시, 다음 가능성 우선 점검:
  1. 외부 MCP client (Grok CLI / Codex / OpenCode 등) 의 stdio 연결 관리
  2. 다른 Python application (workflow_kit 사용 consumer)
  3. OS-level daemon (systemd, cron, Docker 등)
- 이 워크플로우 패키지 자체의 코드 경로 (dispatcher / smoke / release pipeline / stdio server) 는 모두 안정 확인됨.

### 검증 산출물

- 100+ 회 subprocess 호출 후에도 베이스라인 2 PIDs 유지
- 1000회 cache-dashboard 호출 RSS drift 0 MB (PERF-MEM-02 baseline 0%)
- 11종 smoke 회귀 모두 PASS (4+5+5+5+4+4+3+6+4+4+4 = 48/48)
- AST 검증: dead-after-return 0건 (후속 cleanup 에서 dead code 3건 제거 완료)

### 후속 작업

- 본 진단 결과를 `state.json recent_done_items` 에 5개 항목 추가 (release + follow-up 3건 + 본 진단)
- 누수 진단 결과를 본 session 파일로 영구 보존 (본 문서)
- 운영 환경에서 누적 발생 시 본 session 파일 + `extensions/performance-baseline.md` PERF-WF-03 정공법 (`gc.collect()` 후 잔여 객체 0) 을 cross-reference
- v0.15.20+ 후속 후보: `check_memory_baseline.py` smoke 신규 작성 (PERF-MEM-02 정공법 자동화)

## ✅ Outcome

- v0.15.15 정식 release 의 운영 안정성 확인
- 6개 운영 경로 모두 누적 0건 / RSS drift 0 MB 확인
- 본 워크플로우 패키지 코드 자체에는 누수 정공법이 이미 적용되어 있음 (in-process refactor v0.7.55~59)
- 운영 환경의 다른 시스템 가능성 우선 안내
