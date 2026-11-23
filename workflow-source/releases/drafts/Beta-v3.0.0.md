# DRAFT — NOT READY — Beta v3.0.0 — Go 런타임 전환 (2026-11-23)

> 본 release note 는 `tools/release_pipeline.py note-draft` 의 *skeleton*.
> commit hash / 본문 / Reference 등을 *수동 편집* 후 `docs/v<X>.<Y>.<Z>-release.md` 로 commit.
> 범위: `v2.1.0..HEAD` (18 commit)

## TL;DR

- 2.x 허브 · 공유 판정 · PC 중계의 Go 구현과 Python/Go 적합성 검사를 포함한다.
- 3.x 패키지에는 Python wheel/sdist와 Go 런타임 6종 바이너리 및 `SHA256SUMS`를 싣는다.
- **출시 보류 초안**: Go 전환 S2 하네스 실측과 S3 상시 운영 전환·복구 리허설이 아직 완료되지 않았다.
- 범위: `v2.1.0..HEAD`; 릴리즈 파이프라인/노트 자체의 미커밋 변경은 이 범위에 포함되지 않는다.

## Highlights

- **Go PC relay**: 동일한 relay 설정·프로토콜로 Linux/macOS/Windows용 단일 바이너리 기반을 마련했다. Linux에서 Claude Code와 Codex 실제 어댑터 흐름을 측정했다.
- **Go hub and judge**: SQLite 저장소·MCP/HTTP 서버·CLI와 `judge/1` 순수 판정을 Go로 구현하고 Python 판과 차분 검사한다.
- **Session orchestration**: 세션·인박스·lease·assignment·승인 흐름을 Go에 추가하고 HTTP 실사용 흐름을 양쪽 구현에서 검사한다.
- **Release assets**: 3.x dist 경로가 Linux/macOS/Windows × amd64/arm64 바이너리와 SHA256SUMS를 준비하고 GitHub Release 첨부를 요구한다.

## Release readiness

이 문서는 출시 노트 초안이며 현재 릴리즈 승인이나 발행을 뜻하지 않는다. 출시 전에 아래 항목을 완료하고 결과를 기록한다.

- [ ] Go S2: 허브 적합성·차분 검사를 전부 통과시키고 요구된 테스트베드 요청 대조 및 4개 하네스 실측을 완료한다.
- [ ] Go S3: 상시 허브를 Go 판으로 전환하고 동일 DB를 사용한 Python 복구 리허설을 통과시킨다.
- [ ] M-039/WBS-39.1~39.4의 남은 안정화 범위와 2.x → 3.x 자기 적용/프로젝트 이전 범위를 로드맵에서 정리한다.
- [ ] 3.0.0 버전으로 실제 dist를 빌드하고 6개 바이너리의 체크섬 및 GitHub Release dry-run asset 목록을 확인한다.
- [ ] 깨끗한 HEAD에서 전체 릴리즈 게이트를 통과시키고 그 뒤 별도 발행 결정을 받는다.

## 핵심 추가

### feat

- `08f9bd40` feat(hub-go): port sessions and orchestration (M-056)
- `8d1c2840` feat(judge): judge/1 CLI 프로토콜 및 plan.lint · plan.states · task.status Python·Go 순수 판정 구현 (M-054 WBS-54.1, TASK-2026-11-22-main-036)
- `1cfe442a` feat(ui): 중앙 허브 2.1 오케스트레이션·로드맵·워크벤치 UX 및 PC 중계(Python·Go) 무깜빡임 로컬 화면 완성 (M-053 WBS-53.1~53.2, TASK-2026-11-22-main-034~035)
- `7aff454b` feat(hub-go): check_hub_relay 구현 스위치(python·go) + Go 중계 실제 어댑터 실측 — M-052 S1 완료 (WBS-52.3, TASK-2026-11-22-main-033)
- `5bd6baf5` feat(hub-go): PC 중계 Go 판 — CLI · 설정 · 긴 폴링 · 어댑터 3종 · 로컬 화면 (M-052 WBS-52.2, TASK-2026-11-22-main-032)
- `4cd322e3` feat(hub-go): hub-go 모듈 뼈대 · cmd/workflow-hub · check_go_build 6 대상 크로스 빌드 (M-052 WBS-52.1, TASK-2026-11-22-main-031)
- `99664b10` feat(hub): mcp 2.x 지원 — [hub] 상한 <3, lowlevel 처리기 등록형 · SDK 매트릭스가 허브 MCP 경로를 밟는다 (TASK-2026-11-22-main-022)

### chore

- `6c3acd07` chore(memory): record M-056 push gate
- `71954d44` chore(memory): 141차 세션 종료 — M-052~M-055 Go 전환 S1·UI·S2-a·S2-b 반영, 다음 S2-c/d
- `07db4a9b` chore(memory): 140차 세션 종료 — v2.1.0 발행 · mcp 2.x · Go 전환 concept/requirements/design 반영, 다음 M-052 S1 중계

### docs

- `0199b6db` docs: Go 전환 design 확정 — DG1~DG5 권고안 · ADR-035 Accepted · PURPOSE Go 런타임 예외 · M-051 done · M-052 S1 중계 선언 (TASK-2026-11-22-main-030)
- `bf1116dd` docs(core): 허브 Go 판 설계 hub_go_spec — hub-go 배치 · 순수 판정 op · judge/1 CLI · 차분 · 적합성 검사 · S1 중계 · 빌드 · DG1~DG5 (M-050 done · M-051, TASK-2026-11-22-main-024~030)
- `01d562fd` docs(planning): 2.x 전면 Go 전환 requirements R25~R35 · 계약 표면 실측 · 정할 것 Q1~Q6 · ADR-035 Proposed (M-050, TASK-2026-11-22-main-024 · 025 · 026)
- `30199b4d` docs(planning): Go 전환 결정 — R1 전면 Go(허브 · 공유 판정 · 중계), 나머지 권고안 · M-049 done · M-050 requirements 선언 (TASK-2026-11-22-main-021 · 023)
- `ddfa5321` docs(planning): 허브 · PC 중계 Go/Rust 전환 concept — SDK · 탐침 실측 · 이식량 · 선택지 A~D · 권고 B(중계만 Go) (M-049, TASK-2026-11-22-main-021)

## Commit

| Hash | Subject |
|---|---|
| `6c3acd07` | chore(memory): record M-056 push gate |
| `08f9bd40` | feat(hub-go): port sessions and orchestration (M-056) |
| `71954d44` | chore(memory): 141차 세션 종료 — M-052~M-055 Go 전환 S1·UI·S2-a·S2-b 반영, 다음 S2-c/d |
| `7d7986cb` | hub-go: implement hub core db, assets, store, tools, mcpserver, httpapi, CLI (M-055) |
| `468ff6eb` | M-054 WBS-54.2~54.3: complete 7 pure judge/1 ops, corpus, and parity gate |
| `8d1c2840` | feat(judge): judge/1 CLI 프로토콜 및 plan.lint · plan.states · task.status Python·Go 순수 판정 구현 (M-054 WBS-54.1, TASK-2026-11-22-main-036) |
| `1cfe442a` | feat(ui): 중앙 허브 2.1 오케스트레이션·로드맵·워크벤치 UX 및 PC 중계(Python·Go) 무깜빡임 로컬 화면 완성 (M-053 WBS-53.1~53.2, TASK-2026-11-22-main-034~035) |
| `7aff454b` | feat(hub-go): check_hub_relay 구현 스위치(python·go) + Go 중계 실제 어댑터 실측 — M-052 S1 완료 (WBS-52.3, TASK-2026-11-22-main-033) |
| `5bd6baf5` | feat(hub-go): PC 중계 Go 판 — CLI · 설정 · 긴 폴링 · 어댑터 3종 · 로컬 화면 (M-052 WBS-52.2, TASK-2026-11-22-main-032) |
| `4cd322e3` | feat(hub-go): hub-go 모듈 뼈대 · cmd/workflow-hub · check_go_build 6 대상 크로스 빌드 (M-052 WBS-52.1, TASK-2026-11-22-main-031) |
| `07db4a9b` | chore(memory): 140차 세션 종료 — v2.1.0 발행 · mcp 2.x · Go 전환 concept/requirements/design 반영, 다음 M-052 S1 중계 |
| `0199b6db` | docs: Go 전환 design 확정 — DG1~DG5 권고안 · ADR-035 Accepted · PURPOSE Go 런타임 예외 · M-051 done · M-052 S1 중계 선언 (TASK-2026-11-22-main-030) |
| `bf1116dd` | docs(core): 허브 Go 판 설계 hub_go_spec — hub-go 배치 · 순수 판정 op · judge/1 CLI · 차분 · 적합성 검사 · S1 중계 · 빌드 · DG1~DG5 (M-050 done · M-051, TASK-2026-11-22-main-024~030) |
| `01d562fd` | docs(planning): 2.x 전면 Go 전환 requirements R25~R35 · 계약 표면 실측 · 정할 것 Q1~Q6 · ADR-035 Proposed (M-050, TASK-2026-11-22-main-024 · 025 · 026) |
| `99664b10` | feat(hub): mcp 2.x 지원 — [hub] 상한 <3, lowlevel 처리기 등록형 · SDK 매트릭스가 허브 MCP 경로를 밟는다 (TASK-2026-11-22-main-022) |
| `30199b4d` | docs(planning): Go 전환 결정 — R1 전면 Go(허브 · 공유 판정 · 중계), 나머지 권고안 · M-049 done · M-050 requirements 선언 (TASK-2026-11-22-main-021 · 023) |
| `ddfa5321` | docs(planning): 허브 · PC 중계 Go/Rust 전환 concept — SDK · 탐침 실측 · 이식량 · 선택지 A~D · 권고 B(중계만 Go) (M-049, TASK-2026-11-22-main-021) |
| `46320576` | release(v2.1.0): 발행 완료 — tag v2.1.0 (a423d21d) · GitHub Release Latest (wheel · sdist) · M-048 done · M-049 Go/Rust 전환 concept 등록 |

## Reference

- 이전 release note: `Beta-v2.1.0.md`
- memory entry: 추후 추가

---

<!-- Auto-generated by workflow_kit/tools/release_pipeline.py note-draft --from=v2.1.0 --to=3.0.0 -->
