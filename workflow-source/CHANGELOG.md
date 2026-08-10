# Changelog

- 문서 목적: 저장소의 모든 주요 변경을 release 단위로 기록한다 (Keep a Changelog 형식).
- 범위: git log 에서 추출한 release 별 Added / Changed / Fixed 항목.
- 대상 독자: maintainer, 릴리스 매니저, 외부 consumer
- 상태: stable (자동 생성물)
- 최종 수정일: 2026-08-10
- 관련 문서: [`./releases/`](./releases/) (release note), [`../docs/RELEASE.md`](../docs/RELEASE.md) (릴리스 절차)

All notable changes to this project will be documented in this file.

본 파일은 `tools/release_pipeline.py changelog-gen` 으로 자동 생성됩니다 (v0.7.14+).
수동 편집은 다음 생성 시 덮어써진다 — 형식/metadata 변경은 생성기를 고칠 것.

## [Unreleased] - 2026-08-10

### Added

- feat(memory): ADR-006 W-4 지표 재정의 — utilization_3tuple north-star (TASK-2026-08-10-main-014) (91e1551)
- feat(memory): ADR-006 W-3 entry 간 링크 — related_ids + expansion 첫 발동 (TASK-2026-08-10-main-013) (713faec)
- feat(memory): ADR-006 W-2 질의 다양화 — 컨텍스트 유래 query + telemetry 질의 내용 기록 (TASK-2026-08-10-main-012) (1e50701)
- feat(memory): ADR-006 회고 (P2-1) + W-1 write-path advisory 루프 (TASK-2026-08-10-main-010, -011) (051e41a)
- feat(drift): title drift 임계 0.6 실측 캘리브레이션 + registry 비-loopback bind 실측 (TASK-2026-08-10-main-008, -009) (41b98db)
- feat(quality): TST-WF-01 측정 재설계 — AST verification-signal, partial 예외 제거 (ff744b4)
- feat(release): cmd_release 사용성 회복 — pre_check 만성 실패 3뿌리 + dry-run 기본값 (e741de6)
- feat(release): 릴리스 절차에 노트 누적 수치 검증 자리 (step 3.4) (268ede7)
- feat(skill): memory-index-query beta → stable (14/14, 잔여 beta 0) (fd612ad)
- feat(telemetry): AC2 acceptance 를 윈도 기반 지표로 (c5b69d6)
- feat(cli,registry,safety,drift): 다음 후보 축 4건 close — wk / HTTP server / branch protection / title drift v2 (ad3ab02)
- feat(cli): [project.scripts] entry points (CLI 化 A안, v1.1.1+) (029ee39)
- feat(safety): pre-push hook — --force server-side 이중화 (3-layer defense, §0.8 #4) (2b5969c)
- feat(drift): scope drift detection (병합 시점, §0.8 #3) (c687dee)
- feat(tools): operational MCP tool 4종 CLI wrapper (dual mode, TASK-017) (8b94db8)
- feat(registry): federation HTTP pull + dashboard 통합 (§7.4 *읽기* 마무리, TASK-016) (1de3c81)
- feat(registry): federation 정공법 — multi-host registry 합치기 (표준 §0.8 #1) (c32b336)
- feat(registry): in-flight 워크스페이스 신뢰도 표시 (표준 §0.8 #2, §5A.3) (9326a9c)
- feat(smoke): mavis attach e2e 회귀 자동화 (§2.68 자동 검증 닫음, TASK-013) (e4470e5)
- feat(registry): endpoint 기반 mavis alias command/url 합성 (838b12f)
- feat(registry): RegistryEntry env 필드 + sync_mavis env 합성 (e0cdebe)
- feat(registry): registry ↔ mavis 글로벌 양방향 동기 (TASK-2026-08-08-main-009) (a51f683)
- feat(registry): seed_workspace_memory self-register (TASK-2026-08-08-main-008) (29c3e4b)
- feat(bootstrap): mavis 데스크탑 harness 신규 등록 + 글로벌 mcp.json 자동 emit (322a792)
- feat(registry): workspace registry 신규 (표준 §10.2 §7.1, §5A.3) (a3a9442)
- feat(dashboard): `_branch_state_paths` 복수 root 취합 (표준 §10.2 §7.3) (f97a9b1)
- feat(tools): 워크스페이스 선점 도구 — 표준 §10.2 플로우 완결 (c51d052)
- feat(tools): 원격 워크스페이스 현황 조회 — 표준 §10.2 1~3단계 (e547942)
- feat(tools): 워크스페이스 메모리 seed 도구 — 표준 §10.2 자동화 1단계 (9751cc5)
- feat(standard)!: 다중 작업·팀웍 워크플로우를 표준에 정식 반영 (§10 + §1) (8a2a7a9)
- ... (81 more)

### Changed

- chore(backlog): TASK-2026-08-10-main-015 등록 — v1.1.6-beta 발행 착수 (87d80ae)
- docs(memory): TASK-2026-08-10-main-003 등록 — v1.1.4-beta cmd_release 발행 (3236bca)
- docs(phase13): P0-2 close — telemetry 4 source 수렴 + 문서 정정 (87d0ea2)
- docs(memory): 2026-08-09 세션 close — 세션 기록 + state/handoff 최종 동기 (49a2b54)
- docs(memory): 정합성 정리 — backlog status/링크 + task 상태 + state/handoff 동기 (4e31d8c)
- docs(memory): session close — v1.1.1-beta + state/handoff final sync (c0224c6)
- docs(memory): §2.68 cycle 완전 close — TASK-012 갈래2 trust 채택 (5fc1b6e)
- docs(memory): §2.68 cycle close + baseline 통일 (838b12f) (4e85bab)
- chore(mcp): §2.68 mavis 글로벌 mcp.json 표준 register attach (이전 축) (27010a5)
- chore(red): 사전 존재 red 2건 정리 (회귀 정합 회복) (a845c31)
- docs(memory): 세션 close-out — 다중 워크스페이스 오케스트레이션 + 사전 red 2건 정리 (2d2199f)
- docs(memory): handoff L12 baseline hash 명시 (§2.67 c63b54e) (9ef3cd8)
- chore(mcp): §2.67 — mavis attach 안 붙음 진단, 1차 출처 보강 (§6.5.2) (c63b54e)
- docs(presentation): 발표자료 32번 장표 1행 5컬럼 레이아웃 개편 및 37번 장표 카드 테마 통일 (d9b87d4)
- chore(memory): Update session handoff, state & backlog for TASK-2026-08-06-main-003 (6fe7692)
- style(slide): Fix vertical content alignment and lock header baselines across 38 slides (8479cef)
- chore(backlog): Add TASK-2026-08-06-main-002 to daily backlog (05cf955)
- chore(memory): Update session handoff & state for TASK-2026-08-06-main-002 (3dc7231)
- docs: Add master HTML deck & update AI Agent Onboarding presentation design v2.4 (3f3aaaa)
- docs(presentation): 학습회 발표 설계 v2 — 인과 사슬 재설계 + 세션 종료 memory 갱신 (c0acc70)
- docs(memory): 세션 종료 — §2.59~§2.66 세션 기록 + 다음 시작 포인트 정리 (1cafb87)
- docs(memory): 기준선을 0f53458 로 갱신 (트리거된 CI 5종 green 실측) (76db79c)
- refactor(mcp)!: transport_ready 를 wire 에서 제거했다 (§6.2 완료, §2.66) (0f53458)
- docs(memory): 기준선을 0ceca6b 로 갱신 (§2.62 커밋의 트리거 3종 green 실측) (e6e4623)
- refactor(mcp): 세 번째 사본을 접었다 — 이미 갈라져 있었다 (§2.62) (0ceca6b)
- docs(memory): 기준선을 8e4dccb 로 갱신 (§2.61 커밋의 트리거 3종 green 실측) (2ffd4c9)
- refactor(mcp): grok 의 하드코딩된 MCP 블록을 정본으로 접었다 + TOML 키 결함 (§2.61) (8e4dccb)
- docs(memory): 기준선을 6ebbd8b 로 갱신 (§2.60 커밋의 트리거 3종 green 실측) (efca8b6)
- docs(memory): 기준선을 33424fc 로 갱신 (커밋 2건 각각 트리거된 CI 3종 green 실측) (4bfbc20)
- docs(memory): 기준선을 c58111d 로 갱신 (트리거된 CI 6종 전부 green 실측) (7d18f2f)
- ... (220 more)

### Fixed

- fix(tests): dashboard timeline 검사 2건 — 살아있는 저장소/registry 상태 대신 결정적 fixture (2661359)
- fix(release): dist 기본값 dry-run 반전 — release 와 정합 (TASK-2026-08-10-main-005) (4c7895f)
- fix(tests): doctor exit-on-fail 테스트 — 살아있는 저장소 상태 대신 결정적 fixture (c0ad1a6)
- fix(tests): mavis e2e 호스트 사본 제거 + 세션 close memory 갱신 (4b67621)
- fix(tests): smoke_trend 판정 복원 — 검사가 맞았고 내 진단이 틀렸다 (15d5a22)
- fix(phase13,harness): 문서 전반 실측 대조 + harness 정본 정의 확정 (6a1ecf7)
- fix(changelog,docs): Phase 13 P1 close — 세 항목 모두 문서가 실제와 달랐다 (aeafaab)
- fix(tests): dist skip 전제를 cmd_dist 와 같은 기준으로 (63d2366)
- fix(release): 릴리스 도구 결함 2건 + 릴리스 없이 잡히는 회귀 검사 (ca3c9c6)
- fix(tools): memory 경로 조립을 정본 API 로 + v1.1.2 릴리스 노트 초안 (6652ba6)
- fix(mypy,tests): 남은 red 4건 close — FULL mypy strict 128 files clean 복구 (c6fba3c)
- fix(rotation,docs): rotate 도구 순서 규약 통일 + 사전 존재 red 정리 (6cfb168)
- fix(test): 새 검사가 mcp 2.0.0 에서 죽었다 — isError 는 1.x 이름이다 (§2.63 후속) (c6f31ff)
- fix(claude-code): slash command 설명 자리에 버전 마커가 앉아 있었다 (§2.59 후속) (33424fc)
- fix(claude-code): 자기 harness 를 부분만 적용하고 있었다 + 마커가 frontmatter 를 깨고 있었다 (§2.59) (227219e)
- fix(okf): 검사가 처음 돌자 나온 URL 2건 — 죽은 링크가 아니라 태어난 적 없는 링크 (§2.58) (c58111d)
- fix(cli): 오래 red 인 스케줄 workflow 2건 — 둘 다 원인이 딴 데 있었다 (§2.57) (7b076f8)
- fix(tests): 슬래시 브랜치에서 깨지던 것들 — 셋이었고 원인이 서로 달랐다 (§2.55) (dda0825)
- fix(tools): 생성물인지를 이름으로 가르고 있었다 — 정본은 .gitignore 다 (§2.54) (99eb05a)
- fix(tools): 조사가 어디까지 보는지를 선언하고 있었다 — 포함 목록을 없앤다 (§2.53) (710ccea)
- fix(dashboard): 모든 panel 의 기준이 자기 근거를 안 내고 있었다 (§2.51) (1b52b85)
- fix(tests): 검사가 CI 에서 무력화되고 있었다 — branch env 우선 규칙 (§2.50) (15ee104)
- fix(paths): 세 번째를 찾으러 갔더니 다른 축에 있었다 — branch 해석기 합의 (§2.50) (d6a23fe)
- fix(doctor): 같은 결함이 CLI 에도 있었다 — 기준 경로와 설정 출처 (§2.49) (607b84c)
- fix(maturity): 검사가 처음 돌자 나온 2건 — 하나는 진짜, 하나는 위양성 (§2.48) (2e13931)
- fix(linter): 기준 경로가 한 칸 어긋나 있었다 — 설정과 maturity (§2.47) (14cd792)
- fix(state): 파생물의 상한과 포인터 — 쓰는 쪽이 규약을 모르고 있었다 (§2.46) (72bfbe0)
- fix(server): lowlevel 도 1.x/2.x 를 해석한다 — 상한 핀 해제 (§2.43) (1f1881c)
- fix(ci): 인스펙터가 서버 인자를 삼키고 있었다 — 도구도 의존성이다 (§2.42) (7b1404b)
- fix(deps): 상한 핀 복원 — 이관 범위를 파일 하나로 잡았다 (§2.41 정정) (7469fb1)
- ... (69 more)

## [1.1.6] - 2026-08-10

### Changed

- chore(release): v1.1.6-beta 준비 — 노트 + 파생물 선재생성 + stamp (TASK-2026-08-10-main-015) (25e09d4)

## [1.1.5] - 2026-08-10

### Changed

- docs(release): v1.1.5-beta 발행 후처리 + 세션 close memory (4e68c2e)
- chore(release): v1.1.5-beta 준비 — 노트 + 파생물 선재생성 + stamp (6e77c14)

## [1.1.4] - 2026-08-10

### Changed

- docs(release): v1.1.4-beta 발행 후처리 + 세션 close memory (ea7687b)
- chore(release): v1.1.4-beta 준비 — 노트 + stamp 정합 (7a12490)

### Fixed

- fix(release): v1.1.4 파생물 재생성 — 릴리스 직후 전량 재실행이 잡은 9건 (890521f)

## [1.1.3] - 2026-08-10

### Changed

- docs(memory): v1.1.3-beta 발행 기록 + 릴리스 파이프라인 후속 2건 (e956f22)
- chore(release): v1.1.3-beta 준비 — 노트 + version bump + stamp (6cadcca)

## [1.1.2] - 2026-08-09

### Changed

- docs(memory): v1.1.2-beta 발행 기록 + 릴리스 도구 결함 2건 (74161f8)
- chore(release): v1.1.2-beta — federation 쓰기 / wk dispatcher / 3rd layer / drift v2 (b688a06)

## [1.1.1] - 2026-08-08

### Changed

- docs(memory): v1.1.1-beta release 반영 — baseline + current_axis 갱신 (678806f)
- chore(release): v1.1.1-beta — [project.scripts] 29 entry points (CLI 化 A안) (6b92a60)

## [1.1.0] - 2026-08-08

### Changed

- docs(memory): v1.1.0-beta release 반영 — baseline + current_axis + handoff 갱신 (02f80f2)
- chore(release): v1.1.0-beta — §0.8 4건 close + dual mode CLI + federation *읽기* (564ce36)

## [1.0.0] - 2026-07-22

### Changed

- docs(memory): v1.0.0 사이클 close-out — task SSOT 3건 + 세션 + state.json 재생성 (3f017a2)
- docs(v1.0.0): 릴리스 노트 §2.15 — auto-bump dry-run 결함 (릴리스 후 발견) 기록 (08391f2)
- docs(v1.0.0): 릴리스 노트 확정 — 보류/초안 → 릴리스, 본 사이클 해소 내역 §2.9~2.14 추가 (2e6ae44)
- docs(v1.0.0): dashboard snapshot + CHANGELOG 재생성 + 검증 수치 실측 정합 (17c3cb6)
- docs(v1.0.0): smoke 카운트 199 정합 + 릴리스 노트 검증 섹션 실측 기록 (5c690b9)
- chore(v1.0.0): version bump 1.0.0 + 버전 스탬프 정합 + Phase 13 진입 (릴리스 미완) (e574bf9)
- docs(v1.0.0): Gate 1 ✅ PASS — Panel 5 items_total=11 (Break Point #1 close-out) (01838d0)
- docs(v1.0.0): Gate 1 ✅ PASS — Panel 5 items_total=11 (Break Point #1 close-out) (6e24b81)

## [0.15.21] - 2026-07-21

### Added

- feat(release): v0.15.21 — Phase 13 follow-up 1차 (AC2 telemetry 다양성 + CHANGELOG lockdown) (8a93afa)

### Changed

- chore(dashboard): v0.15.21 post-release snapshot refresh (37233c9)

## [0.15.20] - 2026-07-20

### Fixed

- fix(release): v0.15.20 — v1.0.0 pre-release final (stable API + SemVer 2-year guarantee) (ab202d8)

## [0.15.19] - 2026-07-20

### Fixed

- fix(release): v0.15.19 — cross-panel final 정합 (v1.0.0 pre-release anchor) (0d87147)
- fix(release): v0.15.19 — cross-panel final 정합 (v1.0.0 pre-release anchor) (271f96b)

## [0.15.18] - 2026-08-10

### Changed

- chore(tests): v0.15.18 dummy wrapper 물리 제거 — 153개/60파일 (TASK-2026-08-10-main-007) (f7b5217)

### Fixed

- fix(test): v0.15.18 — TST-WF-01 historical smoke 보강 + v1.0.0 Break Point #2 해소 (e5225a9)
- fix(test): v0.15.18 — TST-WF-01 historical smoke 보강 + v1.0.0 Break Point #2 해소 (a5c0cfc)

## [0.15.16] - 2026-07-20

### Added

- feat(harness): v0.15.16 — Grok Build (xAI CLI TUI) 11번째 harness + cross-check discipline anchor 확장 (v0.15.16~v0.15.19) (370cb23)
- feat(harness): v0.15.16 — Grok Build (xAI CLI TUI) 11번째 harness + cross-check discipline anchor 확장 (v0.15.16~v0.15.19) (dc64d2f)
- feat(harness): v0.15.16 — Grok Build (xAI CLI TUI) 11번째 harness + cross-check discipline anchor 확장 (v0.15.16~v0.15.19) (fc834d1)

### Changed

- chore(release): v0.15.16 정식 release — Beta note 신규 + version bump (09825f3)

## [0.15.15] - 2026-07-18

### Changed

- docs(release): v0.15.15 정식 release 정합 + Beta-v0.10.4 release note 신규 (d9aa69e)
- chore(release): v0.15.15 정식 version bump (94a0174)
- docs(planning): v0.15.15 baseline + draft → stable 격상 + maturity last_updated 갱신 (b3db12c)
- docs(release): v0.15.15 baseline + 회귀 표 + PROJECT_PROFILE canonical path 반영 (3765033)
- docs(quickstart): v0.15.15 QUICKSTART.md cross-check smoke + 2 in-scope issue 정정 (3d59da8)

## [0.15.14] - 2026-07-17

### Changed

- docs(install): v0.15.14 INSTALLATION_AND_USAGE.md cross-check smoke + stale text 정정 (e1e0a54)

## [0.15.13] - 2026-07-17

### Added

- feat(harness): v0.15.13 Harness apply_guide.md content cross-check smoke (56c3991)

## [0.15.12] - 2026-07-17

### Changed

- docs(readme): v0.15.12 README.md cross-check smoke + stale text 정정 (4dce84d)

## [0.15.11] - 2026-07-17

### Fixed

- fix(release): v0.15.11 sample tool_version housekeeping + 3-way cross-check smoke (586424f)

## [0.15.10] - 2026-07-17

### Changed

- docs(adr): v0.15.10 MICROSOFT_MEMORA_EVALUATION close-out — Memora-inspired metadata 도입 종결 (0ad13bd)

## [0.15.9] - 2026-07-17

### Added

- feat(harness): v0.15.9 Harness verification smoke — 10 harness cross-check discipline anchor (2fd858e)

## [0.15.8] - 2026-07-17

### Added

- feat(dashboard): v0.15.8 Panel 1+2 maturity_distribution cross-validation smoke (cb46874)

## [0.15.7] - 2026-07-17

### Added

- feat(dashboard): v0.15.7 Panel 3 memory_index cross-validation smoke (b5901b5)

## [0.15.6] - 2026-07-17

### Added

- feat(dashboard): v0.15.6 Panel 6/8 telemetry cross-validation smoke (c0bce15)

## [0.15.5] - 2026-07-17

### Added

- feat(dashboard): v0.15.5 Panel 4 cross-validation smoke — cross-check discipline anchor (5c13c7b)

## [0.15.4] - 2026-07-17

### Changed

- docs(adr): v0.15.4 ADR-007 close-out — 3rd deprecation cycle accepted no-op (861267c)

## [0.15.3] - 2026-07-17

### Added

- feat(release): v0.15.3 release_error 시에만 maturity refresh (v0.14.6 out-of-scope 2 해소) (5cec8e8)

## [0.15.2] - 2026-07-17

### Added

- feat(release): v0.15.2 legacy_memory strict opt-out + v0.15.1 dashboard 정합 (단일 commit) (a4749f3)

## [0.15.1] - 2026-07-17

### Fixed

- fix(dashboard): v0.15.1 Panel 4 SMOKE_COUNT_PATTERN N+ 표기 parse + 8 panel 정합 (abe071e)

## [0.15.0] - 2026-07-17

### Added

- feat(memory): v0.15.0 ⚠️ BREAKING — 2nd deprecation cycle 종결 (work_backlog.md.bak drop) (d7109ef)

### Changed

- chore(state): v0.15.0 ⚠️ BREAKING push + audit fix memory cycle (2aed584)
- chore(release): v0.15.0 push prep — README header sync, drift G2 fix, panel 7 stage branch (b31beb2)

## [0.14.7] - 2026-07-16

### Added

- feat(dashboard): v0.14.7 HTML renderer Panel 6/7/8 + Panel 6 git reflog (Phase 15 follow-up) (3a27480)

## [0.14.6] - 2026-07-16

### Added

- feat(workflow): v0.14.6 refresh-maturity dispatcher + cmd_release auto-wire (Task 3 follow-up) (d8eeae7)

## [0.14.5] - 2026-07-16

### Added

- feat(memory): v0.14.5 2nd deprecation cycle 시작 — --legacy-memory flag (49ac3f7)

## [0.14.3] - 2026-07-16

### Added

- feat(dashboard): v0.14.3 Phase 15 신규 Panel 6/7/8 (north-star + deprecation + telemetry) (ec9d389)

## [0.14.2] - 2026-07-16

### Added

- feat(mcp): v0.14.2 MCP 2nd batch stable — apply_robust_patch (쓰기 MCP 정공법) (5602f63)

## [0.14.1] - 2026-07-16

### Added

- feat(mcp): v0.14.1 MCP 1st batch stable + workflow_log_rotator 정리 (Phase 14 MCP close-out) (27d2178)
- feat(memory): v0.14.1 deprecation cycle 1st 종결 — .bak deprecation warning emit (3afb9ef)

## [0.14.0] - 2026-07-16

### Added

- feat(dashboard): v0.14.0 Panel 1 freshness 보강 — maturity_last_updated stale warning + helper (2c52c59)
- feat(memory): v0.14.0 67-file path string 갱신 + governance layout 명세 (Phase 14 AC3 close-out) (104d028)
- feat(memory): v0.14.0 builder/cache 신규 layout 입력 확장 (Phase 14 AC2 close-out) (5a6b069)
- feat(memory): v0.14.0 1st deprecation cycle — append-only + rebuild layout (Phase 14 AC1 close-out, 93 entries split) (8c53c4a)

### Changed

- docs(release): v0.14.0 Phase 14 close-out — Beta release note + daily backlog (22b3eeb)
- chore(release): v0.14.0 housekeeping — version bump + sample regen + dashboard refresh (3ade29d)
- test(memory): v0.14.0 신규 smoke check_appendonly_memory_layout.py 6/6 (Phase 14 AC4 close-out) (5549d7c)

## [0.13.0] - 2026-07-09

### Added

- feat(dashboard): v0.13.0-beta HTML snapshot (GitHub Pages publish) (b55fcad)
- feat(dashboard): v0.13.0~2 quality dashboard — 5 panel data + CLI + drift guard inline + HTML renderer (b781168)
- feat(dashboard): v0.13.0~2 quality dashboard — 5 panel data + CLI + drift guard inline + HTML renderer (3a81281)

### Changed

- chore(release): v0.13.0-beta dashboard snapshot (auto-emit) (772ae09)

## [0.11.25] - 2026-07-03

### Added

- feat(mcp): stdio-sdk 정식 stable 승격 (v0.11.25) (b8d7bde)

## [0.11.24] - 2026-07-03

### Added

- feat(skill): git-conflict-resolver --apply 구현 + 11/11 stable milestone (v0.11.24) (b227656)
- feat(skill): automated-repro-scaffold + git-conflict-resolver stable/beta 승격 (v0.11.24) (ac7c17b)

## [0.11.22] - 2026-07-02

### Changed

- chore(state): v0.11.22 release memory cycle — 8 phase + ADR-006 retrospective anchor + 3 skill wiring 3/3 (ea013a2)
- chore(state): v0.11.22 ADR-006 retrospective 자리 memory cycle (a42cf61)
- chore(state): v0.11.22 Phase 3d backlog-update wiring memory cycle (skill wiring 3/3 완료) (d89beae)
- chore(state): v0.11.22 Phase 3c doc-sync wiring memory cycle (a598706)
- chore(state): v0.11.22 Phase 3b1 session-start wiring memory cycle (01ed22d)
- chore(state): v0.11.22 Phase 3 dispatcher entry memory cycle (2cc6179)
- chore(state): v0.11.22 Phase 2b BM25 fallback memory cycle (c90bde1)
- chore(state): v0.11.22 Phase 2 --merge opt-in memory cycle (a712c95)
- chore(state): v0.11.22 Phase 1.5 state.json hook memory cycle (fa0ac32)
- chore(state): v0.11.22 ADR-005 Phase 1 prototype memory cycle (348048c)

## [0.11.21] - 2026-07-02

### Changed

- chore(state): v0.11.21 release memory cycle (b378284)

## [0.11.20] - 2026-07-01

### Changed

- chore(state): v0.11.20 release memory cycle (a6c76bd)

## [0.11.19] - 2026-07-01

### Changed

- chore(state): v0.11.19 release memory cycle (143d2d3)

## [0.11.18] - 2026-07-01

### Changed

- chore(state): v0.11.18 release memory cycle (dfafdc4)
- chore(state): v0.11.18 release memory cycle (df506ed)

## [0.11.17] - 2026-06-30

### Changed

- chore(state): v0.11.17 release memory cycle (4d991e8)
- chore(v0.11.17): version bump + release note — mypy strict cumulative 25 error 격상 + schema drift housekeeping (3d3387d)

## [0.11.16] - 2026-06-27

### Added

- feat+chore(v0.11.16): cmd_release_status --auto-bump flag (read-only → opt-in write) (d81c639)

## [0.11.15] - 2026-06-26

### Added

- feat+chore(v0.11.15): release summary 1-line (jq-friendly verdict) (9ae4682)

## [0.11.14] - 2026-06-26

### Added

- feat+chore(v0.11.14): release-status dispatcher (신규 module mypy strict clean 2-layer defense 실증) (ed5148a)

## [0.11.13] - 2026-06-26

### Added

- feat+chore(v0.11.13): mypy CI cross-verify (Layer 1 ↔ Layer 2 정합 advisory) (b3075ef)

## [0.11.12] - 2026-06-26

### Added

- feat+chore(v0.11.12): mypy strict release-time gate (cmd_release pre-check 확장) (731b202)

## [0.11.11] - 2026-06-26

### Added

- feat+chore(v0.11.11): mypy strict CI 통합 (GH Actions mypy-strict workflow) (0994f14)

## [0.11.10] - 2026-06-26

### Changed

- chore(v0.11.10): mypy strict 단계적 격상 25-26단계 (project_docs + profiling) — FULL STRICT 도달 (b73799b)

## [0.11.9] - 2026-06-26

### Changed

- chore(v0.11.9): mypy strict 단계적 격상 23-24단계 (testing + runner) (41ef022)

## [0.11.8] - 2026-06-26

### Changed

- chore(v0.11.8): mypy strict 단계적 격상 21-22단계 (read_only_mcp_sdk + workflow_writes) (ae4058a)

## [0.11.7] - 2026-06-26

### Changed

- chore(v0.11.7): mypy strict 단계적 격상 19-20단계 (workflow_kit_cli + doc_sync) (5c82bc3)

## [0.11.6] - 2026-06-26

### Changed

- chore(v0.11.6): mypy strict 단계적 격상 17-18단계 (session_outputs + read_only_bundle) (c82bf72)

## [0.11.5] - 2026-06-26

### Changed

- chore(v0.11.5): mypy strict 단계적 격상 15-16단계 (decorators + linter) (1a7e665)

## [0.11.4] - 2026-06-26

### Changed

- chore(v0.11.4): mypy strict 단계적 격상 13-14단계 (output_contracts + milestones) (6f6bf38)

## [0.11.3] - 2026-06-26

### Changed

- chore(v0.11.3): mypy strict 단계적 격상 11-12단계 (purpose_ingest + purpose_graph) (bfbd100)

## [0.11.2] - 2026-06-26

### Added

- feat+chore(v0.11.2): cycle 4 deferred 통합 (graph_insights schema + 3 skill context load) (372b153)

## [0.11.1] - 2026-06-26

### Added

- feat+chore(v0.11.1): graph insights (R-A follow-up cycle 4) (fef6374)

## [0.11.0] - 2026-06-26

### Added

- feat+chore(v0.11.0): two-step CoT ingest (R-A follow-up cycle 3) (f71dde8)

### Changed

- docs(v0.11.0): plan two-step CoT ingest (R-A follow-up cycle 3) (f4eeba2)

## [0.10.4] - 2026-07-03

### Added

- feat: CodeWhale harness support (v0.10.4) - HARNESS_SPECS+SUPPORTED_HARNESSES+builder registration - single SKILL.md overlay (Constitution handles verification/parallelism/context) - additive rules only: session start, Korean output, backlog mgmt - harness docs + apply guide + distribution spec (cf0060d)

## [0.10.3] - 2026-06-24

### Added

- feat+chore(v0.10.3): wiki file deletion cascade cleanup (R-A follow-up cycle 2) (3ca3a49)

## [0.10.2] - 2026-06-24

### Added

- feat+chore(v0.10.2): delivery layer 확장 (claude-code 진입점 정정 + aider/goose/custom + self-bootstrap) (c657853)

## [0.10.1] - 2026-06-24

### Added

- feat+chore(v0.10.1): skill-only entry mode + claude-code adapter (SemVer minor) (afccdab)

## [0.10.0] - 2026-06-24

### Added

- feat+chore(v0.10.0): deprecation 1st + 2nd cycle 동시 종료 (SemVer major) (c5fb94c)

## [0.9.6] - 2026-06-24

### Added

- feat+chore(v0.9.6): R-A follow-up part 3 (wiki-event-sync R-A trigger) (09282b0)

## [0.9.5] - 2026-06-24

### Added

- feat+chore(v0.9.5): R-A follow-up part 2 (skill context load integration) (96f9715)

## [0.9.4] - 2026-06-19

### Added

- feat+chore(v0.9.4): R-A follow-up part 1 (state.json.purpose_digest 1-line 자동 생성) (48a3380)

## [0.9.3] - 2026-06-19

### Added

- feat+chore(v0.9.3): deprecation 2nd cycle (build_default_sources_v4) (7e38e6f)

## [0.9.2] - 2026-06-19

### Added

- feat+chore(v0.9.2): purpose.md concept 흡수 (외부 reference 차용 정공법 1차 적용) (51e7bec)

## [0.9.1] - 2026-06-18

### Added

- feat+chore(v0.9.1): mypy workflow_kit_cli strict + release --full-auto + deprecation contract (50c688f)

## [0.9.0] - 2026-06-18

### Added

- feat+chore(v0.9.0): spec drift patch + release note + Phase 11 close (a1f8463)
- feat(v0.9.0): deprecation 1st cycle - phishing_federation_v4 DeprecationWarning (bf03b95)

## [0.8.15] - 2026-06-17

### Added

- feat+chore(v0.8.15): release-dist 1-command + housekeeping (spec §9 9/12) (841329f)

## [0.8.0] - 2026-06-17

### Added

- feat(v0.8.0): Stable API frozen + mypy strict + generated JSON Schema SSOT (5042df1)

### Fixed

- fix: v0.8.0 hotfix + v0.8.8 mypy strict 4 file + v0.8.9 dispatcher 29/30 + release_pipeline SSOT (fcb4e8b)

## [0.7.59] - 2026-06-17

### Added

- feat(v0.7.59): cmd_consumer_metrics in-process refactor (dispatcher 27 정합) (f2b92cf)

## [0.7.58] - 2026-06-17

### Added

- feat(v0.7.58): consumer feedback metrics tool + dispatcher subcommand 27 (38fe32a)

### Changed

- merge: v0.7.58 release (757d51b)
- merge: v0.7.58 release (bcc0e99)
- chore(v0.7.58): version bump 0.7.57 → 0.7.58 + release note + state sync (1c7d8e9)

### Fixed

- fix(state): v0.7.58 chore commit hash 동기화 (1c7d8e9) (d0c7c53)

## [0.7.57] - 2026-06-16

### Added

- feat(v0.7.57): mkdocs cross-link audit + 1 broken link fix (cbcaaad)
- feat(v0.7.57): <in-memory> cleanup + dispatcher 23 → 26 (cache format interop) (ec1223c)

### Changed

- merge: v0.7.57 release (364b12a)
- docs(v0.7.57): v0.7.57 release note + wiki log + memory log (1c83b6f)
- chore(v0.7.57): .gitignore 에 /site/ 추가 (mkdocs build output) (654e21e)

## [0.7.56] - 2026-06-16

### Added

- feat(v0.7.56): cache-lfu-decay-persist CSV in-place + dispatcher --inplace (7b4d6b7)
- feat(v0.7.56): release_pipeline wrapper 7 추가 + dispatcher 16 → 23 (fb6ebc4)
- feat(v0.7.56): score-wiki-trend in-process + dispatcher 16+ (c3ef125)

### Changed

- merge: v0.7.56 release (6 follow-up 통합) (79ace23)
- docs(v0.7.56): v0.7.56 release note + wiki log entry (094cc2c)
- docs(v0.7.56): GH Pages 외부 consumer feedback loop + FEEDBACK.md (1c5c1df)
- test(v0.7.56): OKF strict mode lint rule coverage 7 신규 (audit 3차) (58e2ac0)

## [0.7.55] - 2026-06-16

### Changed

- test(v0.7.55): tools/release_pipeline_lib wrapper test 2 신규 (cmd_validate) (428a2d2)
- docs(wiki): v0.7.55 release entry (release-doctor in-process + cache-migrate split + 3 subcommand L/M/N) (6cda10f)
- chore(v0.7.55): version bump 0.7.54 → 0.7.55 + release note (0436eb3)
- test(v0.7.55): tools/release_pipeline_lib wrapper test 2 신규 (cmd_validate) (3ba61e8)
- refactor(v0.7.55): release-doctor in-process + cache-migrate LRU/LFU split + 3 subcommand (14 subcommand) (4b64b20)

## [0.7.54] - 2026-06-16

### Added

- feat(v0.7.54): workflow_kit_cli — okf-validate / cache-migrate / release-doctor (11 subcommand) (97adc0c)

### Changed

- docs(wiki): v0.7.54 release entry (dispatcher 11 subcommand: I/J/K) (0d976d0)
- chore(v0.7.54): version bump 0.7.53 → 0.7.54 + release note (58fbb32)
- test(v0.7.54): dispatcher test 4 신규 (okf-validate × 2 + cache-migrate + release-doctor) (cde0a45)

## [0.7.53] - 2026-06-16

### Added

- feat(v0.7.53): mkdocs 셋업 (GH Pages in-repo, public-facing consumer guide) (fda611b)
- feat(v0.7.53): workflow_kit_cli — okf-export / okf-import subcommand 추가 (a910988)

### Changed

- docs(wiki): v0.7.53 release entry (3 follow-up: F dispatcher + G audit + H mkdocs) (4af30bb)
- chore(v0.7.53): version bump 0.7.52 → 0.7.53 + release note (3d7e232)
- test(v0.7.53): url_validity test file 추가 (12 test, audit 2차 갭 해소) (0562931)

## [0.7.52] - 2026-06-16

### Added

- feat(v0.7.52): cache analytics snapshot diff (1/1 PASS) (f4adf8c)
- feat(v0.7.52): cache analytics alerting CLI (--alert, zero-dep, 2/2 PASS) (fbbd254)

### Changed

- docs(wiki): v0.7.52 release cut supersedes prior audit decision (ee59070)
- chore(v0.7.52): version bump 0.7.6 → 0.7.52 + release note (b0491d0)
- docs(v0.7.52): log entry for retrospective consolidation cleanup (ee63739)
- refactor(v0.7.52): collapse 6 CLI modules into workflow_kit_cli dispatcher (6/6 PASS) (71bf15d)
- refactor(v0.7.52): inline v_r13_commit_diff_integration + v_r13_layer2_pipeline into v_r13_commit_diff (6/6 PASS) (25c7c1a)
- refactor(v0.7.52): consolidate cache_dashboard_export into cache_dashboard module (87f77bd)
- refactor(v0.7.52): remove v2/v3/v4/v5 federation module + test files (081b72c)
- refactor(v0.7.52): consolidate phishing_federation_v2/v3/v4/v5 into one module (4/4 PASS) (0d5a2c7)

## [0.7.51] - 2026-06-16

### Added

- feat(v0.7.51): phishing federation v5 CLI (--federate-v5, 2/2 PASS, FREE tier) (85be71c)
- feat(v0.7.51): cache dashboard export CLI (--dashboard-export --output=PATH, 2/2 PASS) (8810695)
- feat(v0.7.51): cache trend chart CLI (--trend-chart --snapshots=PATH, 2/2 PASS) (4c579ad)
- feat(v0.7.51): LFU decay score automatic aging (decay_age_scores, 2/2 PASS, no regression) (4247589)
- feat(v0.7.51): cache analytics threshold-based alerting (2/2 PASS) (5186836)

### Changed

- release(v0.7.51): cache alerting + decay aging + trend chart CLI + dashboard export CLI + federation v5 CLI (201/201 PASS, FREE tier) (22541e2)

## [0.7.50] - 2026-06-16

### Added

- feat(v0.7.50): LFU decay score CSV export/import (cross-process, 2/2 PASS, no regression) (17e9da9)
- feat(v0.7.50): phishing federation v5 (3 source weighted voting, FREE-tier 3rd source, 2/2 PASS) (5057e77)
- feat(v0.7.50): cache dashboard HTML export (2/2 PASS, no regression) (24939df)
- feat(v0.7.50): cache trend ASCII chart (zero-dep visualization, 2/2 PASS) (7e41eaa)
- feat(v0.7.50): V-R13 layer 2 CLI (one-call URL verification, 2/2 PASS) (5b6c6f6)

### Changed

- release(v0.7.50): layer 2 CLI + trend ASCII chart + dashboard HTML + federation v5 + decay CSV (191/191 PASS) (00d2de4)

## [0.7.49] - 2026-06-16

### Added

- feat(v0.7.49): cache dashboard export (JSON + Markdown, 2/2 PASS) (5834a9a)
- feat(v0.7.49): cache analytics trend (snapshot over time, 2/2 PASS) (00a255d)
- feat(v0.7.49): V-R13 layer 2 full pipeline (one-call parse+dispatch+format, 2/2 PASS) (5726fc0)
- feat(v0.7.49): per-URL LFU decay score persistence (cache_lfu_decay_persist, 2/2 PASS) (d9e050b)
- feat(v0.7.49): phishing federation v4 (weighted voting, 2/2 PASS) (bd7c8cb)

### Changed

- release(v0.7.49): federation v4 + decay persistence + layer 2 pipeline + cache trend + dashboard export (181/181 PASS) (4093fcc)

## [0.7.48] - 2026-06-16

### Added

- feat(v0.7.48): CLI --cache-dashboard flag (cache_dashboard_cli module, 2/2 PASS) (83ee37a)
- feat(v0.7.48): phishing federation v3 (cross-source verification, 2/2 PASS) (ffacc80)
- feat(v0.7.48): per-strategy cache dashboard (cache_dashboard module, 2/2 PASS) (6d9ca13)
- feat(v0.7.48): LFUConfig + _save_cache full refactor (save_cache_lfu_decay_full, 2/2 PASS) (d27004f)
- feat(v0.7.48): V-R13 layer 2 commit-level diff integration (2/2 PASS) (9461ed1)

### Changed

- release(v0.7.48): V-R13 commit diff integration + LFU full refactor + cache dashboard + federation v3 + CLI flag (171/171 PASS) (74e3d59)

## [0.7.47] - 2026-06-16

### Added

- feat(v0.7.47): per-strategy eviction trigger by size cap (evict_lru/lfu_over_size, 2/2 PASS) (1c92875)
- feat(v0.7.47): per-strategy cross-strategy analytics (cache_analytics module, 2/2 PASS) (90f83fb)
- feat(v0.7.47): LFUConfig + _save_cache direct integration (cache_lfu_decay module, 2/2 PASS) (1a606ea)
- feat(v0.7.47): V-R13 layer 2 commit-level diff (cross-vendor, 2/2 PASS) (75be24c)

### Changed

- release(v0.7.47): V-R13 commit diff + LFU decay + ADR formal + analytics + eviction trigger (159/159 PASS) (a4e1522)
- docs(v0.7.47): ADR-023/024/025 revision log v0.2.1 (1 release cycle 운영 evidence) (1475374)

## [0.7.46] - 2026-06-16

### Added

- feat(v0.7.46): multi-source phishing federation v2 (extensible, 2/2 PASS) (e7a5919)
- feat(v0.7.46): Bitbucket v2 API commit history support (2/2 PASS) (cff0f2c)
- feat(v0.7.46): LFUConfig + temporal decay integration (4/4 PASS) (d5b1ddc)
- feat(v0.7.46): per-strategy cache size comparison (2/2 PASS) (0dffe7f)

### Changed

- release(v0.7.46): CLI test fix + cache size + LFU decay + Bitbucket v2 + federation v2 (149/149 PASS) (92d9c2d)
- test(v0.7.46): CLI --per-strategy + --cache-stats-strategy flag tests (2/2 PASS) (f4f0200)

## [0.7.45] - 2026-06-16

### Added

- feat(v0.7.45): CLI --per-strategy + --cache-stats-strategy flags (V-R10 v4) (c01d4f6)
- feat(v0.7.45): cache_stats_per_strategy_with_hit_rate (39/39 PASS) (1fde081)
- feat(v0.7.45): LRU/LFU split in cache_migration (split_to_per_strategy, 2/2 PASS) (5073cf7)
- feat(v0.7.45): multi-source phishing federation (PhishTank + OpenPhish, 2/2 PASS) (6533a4d)

### Changed

- release(v0.7.45): multi-source phishing federation + LRU/LFU split + hit rate + CLI --per-strategy (137/137 PASS) (43a0322)
- docs(v0.7.45): OKF quick-start walkthrough output examples + verification table (227e1e8)

## [0.7.44] - 2026-06-16

### Added

- feat(v0.7.44): cache_migration module (migrate v0.7.41 -> per-strategy, 1/1 PASS) (6726577)
- feat(v0.7.44): OpenPhish API integration (fetch_openphish_feed, 2/2 PASS) (27793af)
- feat(v0.7.44): lfu_integration module (LFUConfig + _save_cache, 2/2 PASS) (8eb116c)

### Changed

- release(v0.7.44): ADR-025 formal + OKF quick-start + LFUConfig + OpenPhish + cache migration (134/134 PASS) (d107dd3)

## [0.7.43] - 2026-06-16

### Added

- feat(v0.7.43): lfu_config module (V-R10 v3 LFU threshold tuning, 2/2 PASS) (53f774a)
- feat(v0.7.43): cache_stats_per_strategy (cross-strategy compare, 39/39 PASS) (e289b19)
- feat(v0.7.43): PhishTank API integration (fetch_phishtank_feed, 13/13 PASS) (df088ee)

### Changed

- release(v0.7.43): ADR-023/024 formal + ADR-025 quick-start draft + PhishTank API + cache_stats_per_strategy + lfu_config (129/129 PASS) (62a6507)

## [0.7.42] - 2026-06-16

### Added

- feat(v0.7.42): per-strategy cache file (cache_file_for_strategy helper, 38/38 PASS) (e80cca8)
- feat(v0.7.42): R-2 audit precise (git log --oneline, 16/16 PASS) (386d68c)
- feat(v0.7.42): V-R13 check 5 per-host extension (GitLab + Bitbucket API, 25/25 PASS) (64ca96c)

### Changed

- release(v0.7.42): ADR-023/024 formal + V-R13 per-host + V-R12 composite + R-2 audit precise + per-strategy cache (124/124 PASS) (f592bff)
- test(v0.7.42): V-R12 layer 1+2 composite URL emission (18/18 PASS) (77b0b87)

## [0.7.41] - 2026-06-16

### Added

- feat(v0.7.41): V-R12 composite layer 1+2 verification (check_url_semantic_composite, 23/23 PASS) (6a480ac)
- feat(v0.7.41): R-2 batch compliance audit (audit_r2_batch_history, 15/15 PASS) (a595fbb)
- feat(v0.7.41): V-R10 v3 per-strategy eviction metric (evictions_lru/evictions_lfu, 36/36 PASS) (46b6b7a)
- feat(v0.7.41): V-R13 ?range=A..B commit-level diff (git diff subprocess, 21/21 PASS) (6fcda94)

### Changed

- release(v0.7.41): ADR-020/021/022 formal + V-R13 range diff + per-strategy metric + R-2 audit + V-R12 composite (118/118 PASS) (62d6e9a)

## [0.7.40] - 2026-06-16

### Added

- feat(v0.7.40): R-2 batch compliance warning (5-15 page heuristic, 14/14 PASS) (85ecff6)
- feat(v0.7.40): CLI --semantic/--perform-head/--perform-github flags (18/18 PASS) (f4cf909)
- feat(v0.7.40): okf_export per-page ?range=<sha>..<sha> emission (V-R12 layer 2, 17/17 PASS) (e365168)
- feat(v0.7.40): V-R13 full 8/8 check (HEAD + GitHub API, 16/16 PASS) (7c69789)

### Changed

- release(v0.7.40): ADR-021/022 formal + V-R13 full 8/8 + V-R12 layer 2 + R-2 batch (110/110 PASS) (b98e1eb)

## [0.7.39] - 2026-06-16

### Added

- feat(v0.7.39): okf_export per-page ?hash=sha256:... emission (ADR-019 layer 1, 16/16 PASS) (dd8c177)
- feat(v0.7.39): phishing_keywords module + 11 tests (V-R11 v2 PoC, 11/11 PASS) (e1904fd)
- feat(v0.7.39): LFU eviction strategy + access_count tracking (34/34 PASS) (eab4d2e)
- feat(v0.7.39): check_url_semantic() PoC (6/8 check, 13/13 PASS) (563ac5c)

### Changed

- release(v0.7.39): V-R13 PoC + LFU cache + PhishTank + V-R12 carrier (102/102 PASS) (863c3b6)

## [0.7.38] - 2026-06-16

### Added

- feat(v0.7.38): _CacheLock stale lock file orphan cleanup (32/32 PASS) (9f622d3)
- feat(v0.7.38): cache gzip compression (4KB threshold, 31/31 PASS) (2e1a541)
- feat(v0.7.38): okf-bundle.yaml emit (per-bundle vcs_commit + integrity_hash, 15/15 PASS) (c3a0f24)
- feat(v0.7.38): _CacheLock timeout + advisory wait (30/30 PASS) (fbf93b5)
- feat(v0.7.38): per-page frontmatter vcs_commit + vcs_ref (12/12 PASS) (96b6ef0)
- feat(v0.7.38): cache_stats session evictions + last_eviction_timestamp (29/29 PASS) (d06053a)

### Changed

- release(v0.7.38): V-R13 formal + okf-bundle.yaml + cache gzip + lock orphan + OKF consumer guide (a04cf56)

## [0.7.37] - 2026-06-16

### Added

- feat(v0.7.37): okf_export vcs_commit integration (ADR-018, 11/11 PASS) (2eac0d3)
- feat(v0.7.37): --body CLI flag + --timeout flag (28/28 PASS) (1da10ef)
- feat(v0.7.37): cache_stats() extension (bytes + evictions_total, 27/27 PASS) (8e88b47)
- feat(v0.7.37): V-R12 commit-pinned URL (ADR-018 + 3 new tests, 9/9 PASS) (7aec7cf)
- feat(v0.7.37): V-R11 body content audit (ADR-017 + 5 new tests, 27/27 PASS) (9ec0aad)
- feat(v0.7.37): GHA actions/cache for cross-PR cache (ADR-016) (6a622ee)
- feat(v0.7.37): V-R10 v3 file lock (ADR-015 + 2 new tests, 22/22 PASS) (735beac)
- feat(v0.7.37): V-R10 v3 cache LRU (ADR-014 + 4 new tests, 20/20 PASS) (3349e79)

### Changed

- ci(v0.7.37): --body + --vcs-commit CI integration (f1a7bd3)

## [0.7.36] - 2026-06-16

### Added

- feat(v0.7.36): V-R10 v2 cache (ADR-013 + 4 new tests, 16/16 PASS) (5fec664)

### Changed

- chore(v0.7.36): version bump v0.7.35 to v0.7.36 + log entry for follow-up bundle (208042d)
- ci(v0.7.36): .github/workflows/okf-validate.yml (V-R10 online + cache + weekly cron) (c26349f)

## [0.7.35] - 2026-06-16

### Added

- feat(v0.7.35): V-R10 online HEAD layer (ADR-012 + 6 new tests, 12/12 PASS) (515a352)
- feat(v0.7.35): ADR-011 + OKF version auto-detect (5 new tests, 12/12 PASS) (e0f2ffc)
- feat(v0.7.35): ADR-010 + V-R10 URL validity lint (offline 8 check, 6/6 PASS) (077b5a4)

## [0.7.34] - 2026-06-16

### Added

- feat(v0.7.34): bundle root index.md auto-emit + test 10 (10/10 PASS) (2fb014e)
- feat(v0.7.34): ADR-008 accepted + path_resolver.py PoC + okf_export --no-resolve (24f8589)
- feat(v0.7.34): ADR-007 accepted + workflow_kit/okf_import.py PoC (7/7 PASS) (9e8b06d)

## [0.7.33] - 2026-06-16

### Added

- feat(v0.7.33): TASK-V0733-001 atomic rotation (3-step crash safety) + TASK-V0734-001 yearly aggregation + 10 smoke (5-run stable) (9648a6e)

### Changed

- chore(v0.7.33): version bump 0.7.32 → 0.7.33 (auto-sync verified) + Beta-v0.7.33.md + state/work_backlog sync (f3ef05b)
- chore(v0.7.33): ADR-006 accepted + Beta-v0.7.33 release note + version bump (00942ef)

### Fixed

- fix(state): v0.7.33 2nd hash sync (1c8d54b)

## [0.7.32] - 2026-06-16

### Added

- feat(v0.7.32): TASK-V0731-001 log rotation + TASK-V0732-001 metrics aggregation + 10 smoke (5-run stable) (75a8b4c)

### Changed

- chore(v0.7.32): version bump 0.7.31 → 0.7.32 (auto-sync verified) + Beta-v0.7.32.md + state/work_backlog sync (ec72360)

### Fixed

- fix(state): v0.7.32 2nd hash sync (1348a3c)

## [0.7.31] - 2026-06-16

### Added

- feat(v0.7.31): TASK-V0729-001 run-time metrics + TASK-V0730-001 install-cron idempotency + 10 smoke (a9b510e)

### Changed

- chore(v0.7.31): version bump 0.7.30 → 0.7.31 (auto-sync verified) + Beta-v0.7.31.md + state/work_backlog sync (6732f48)

### Fixed

- fix(state): v0.7.31 2nd hash sync (fae9157)

## [0.7.30] - 2026-06-15

### Added

- feat(v0.7.30): TASK-V0728-001 archive_stale_memory cron integration (mavis cron create/disable/list) + 5 smoke (57d996d)

### Changed

- chore(v0.7.30): version bump 0.7.29 → 0.7.30 (auto-sync verified) + Beta-v0.7.30.md + state/work_backlog sync (23a2078)

### Fixed

- fix(state): v0.7.30 2nd hash sync (264ab5c)

## [0.7.29] - 2026-06-15

### Added

- feat(v0.7.29): TASK-V0727-001 post-step 2-phase + amend integration (1 commit 통합, 33% 감소) + 5 smoke (850b798)

### Fixed

- fix(state): v0.7.29 backlog = 2ee6dbf (본 release 의 fix(state) hash, v0.7.21 정공법) (fda9379)
- fix(state): v0.7.29 2nd hash sync (6830993)
- fix(v0.7.29): rev-parse 2-step fix (full SHA → short=7) + state.json + backlog 정합 (2ee6dbf)

## [0.7.28] - 2026-06-15

### Added

- feat(v0.7.28): TASK-V0726-004 detached HEAD memory dir age-based auto-archive + 5 smoke (b1b32f1)

### Fixed

- fix(state): v0.7.28 squash + state.json + backlog = chore commit hash (7bb6259, v0.7.21 정공법) (ca7d385)

## [0.7.27] - 2026-06-15

### Added

- feat(v0.7.27): TASK-V0726-003 sync_release_hash post-step (release_pipeline.py version-bump auto-call) + 5 smoke (2aa1efa)

### Fixed

- fix(state): v0.7.27 version-bump + state.json 정합 (v0.7.21 정공법, 2aa1efa = 본 release 의 feat commit) (66c18e7)
- fix(state): v0.7.27 squash + 본 release 의 본 release 의 hash 정합 (v0.7.21 정공법, 2aa1efa = feat commit) (8ef94d6)

## [0.7.26] - 2026-06-15

### Added

- feat(v0.7.26): F-7 branch detection (detached HEAD → 7-char SHA) + F-7+ automated hash sync (infinite fix(state) loop 회피) + 10 smoke (e5fbd2b)

### Changed

- chore(v0.7.26): version bump 0.7.25 → 0.7.26 (auto-sync verified) + Beta-v0.7.26.md + state/work_backlog sync (ecb6ce1)

### Fixed

- fix(state): v0.7.26 squash + 본 release 의 본 release 의 hash 정합 (v0.7.21 정공법, ecb6ce1 = chore commit) (9413697)

## [0.7.25] - 2026-06-15

### Added

- feat(v0.7.25): tools/migrate_legacy_l2.py (F-6 closure, 15 legacy L2 page → in-repo mirror) + 5 smoke (8a61bd3)

### Changed

- chore(v0.7.25): version bump 0.7.24 → 0.7.25 (auto-sync verified) + Beta-v0.7.25.md + state/work_backlog sync (96a919d)

### Fixed

- fix(state): v0.7.25 본 release hash (96a919d) 로 정합 (v0.7.21 정공법) (00e7ca8)
- fix(state): v0.7.25 hash 동기화 (squash 8 commits → 1) (2f5945d)

## [0.7.24] - 2026-06-15

### Added

- feat(v0.7.24): cmd_release --notes-template flag (5 template: default/detailed/simple/changelog/custom) + 5 smoke (1dfa8fb)

### Changed

- chore(v0.7.24): version bump 0.7.23 → 0.7.24 (auto-sync verified) + Beta-v0.7.24.md + state/work_backlog sync (2c38d07)

### Fixed

- fix(state): v0.7.24 backlog.commit 을 fix(state) hash(ef13691) 로 동기화 (6e302c1)
- fix(state): v0.7.24 chore commit hash 동기화 (e802e56 → 2c38d07 amend 후 hash) (ef13691)

## [0.7.23] - 2026-06-15

### Added

- feat(v0.7.23): tools/wiki_emit.py 1-command wrapper (3-step cycle: refresh_raw + emit_l2 + reemit_stubs) + 5 smoke (b4936a2)

### Changed

- chore(v0.7.23): version bump 0.7.22 → 0.7.23 (auto-sync verified) + Beta-v0.7.23.md + state/work_backlog sync (8e33940)

### Fixed

- fix(state): v0.7.23 chore commit hash 동기화 (98442d1)

## [0.7.22] - 2026-06-15

### Changed

- chore(v0.7.22): version bump 0.7.21 → 0.7.22 (auto-sync verified) + Beta-v0.7.22.md + state/work_backlog sync (2d3cdbc)

### Fixed

- fix(state): v0.7.22 chore commit hash 동기화 (8b02fe9)
- fix(v0.7.22): workflow_kit/common/linter.py .resolve() → .absolute() (mavis data dir 격리 환경 + macOS /var symlink fix) + 3 smoke (3c12950)

## [0.7.21] - 2026-06-15

### Changed

- chore(v0.7.21): version bump 0.7.20 → 0.7.21 (auto-sync verified) + Beta-v0.7.21.md + state/work_backlog sync (f014d59)

### Fixed

- fix(state): v0.7.21 chore commit hash 동기화 (amend 후 hash drift 보정) (fa329b1)
- fix(v0.7.21): cmd_release --allow-existing-tag flag + tag push 자동화 (pre-check + release coupling) (0ef97db)

## [0.7.20] - 2026-06-15

### Changed

- chore(v0.7.20): Beta-v0.7.20.md release note (release coordination observability + auto-bump chain) (5758657)
- chore(v0.7.20): version bump 0.7.19 → 0.7.20 (auto-bump chain) (556eb04)

## [0.7.19] - 2026-06-15

### Changed

- chore(v0.7.19): version bump 0.7.18 → 0.7.19 (release coordination auto-bump) (8ada0f1)

## [0.7.18] - 2026-06-15

### Added

- feat(v0.7.18): release coordination observability (_check_remote_tag + next_available_version + --auto-bump) + 7 smoke (07bf145)

### Changed

- chore(v0.7.18): version bump 0.7.17 → 0.7.18 (auto-sync verified) + Beta-v0.7.18.md + state/work_backlog sync (46066c3)

## [0.7.17] - 2026-06-15

### Added

- feat(v0.7.17): wiki in-repo storage isolation (5 file redirect + ai-workflow/wiki/sources/ 신규 + 11 smoke) (6f6f1af)

### Changed

- chore(v0.7.17): version bump 0.7.16 → 0.7.17 (auto-sync verified) + Beta-v0.7.17.md + state/work_backlog sync (4d09dee)

## [0.7.16] - 2026-06-15

### Added

- feat(v0.7.16): [tool.workflow-doctor] config thresholds/excluded_paths 적용 (B-1/B-2/B-3) + linter IndentationError fix + 9 smoke (33f5243)

### Changed

- chore(v0.7.16): version bump 0.7.15 → 0.7.16 (auto-sync verified) + Beta-v0.7.16.md + state/work_backlog sync (f012601)

## [0.7.15] - 2026-06-15

### Added

- feat(v0.7.15): atomic_write helper + changelog-gen --from-tag/--to-tag filter + 5 smoke (8d7acc4)
- feat(v0.7.15): atomic_write helper + changelog-gen --from-tag/--to-tag filter + 5 smoke (5cd1fe1)

### Changed

- merge: v0.7.15 fix 3 commit (Beta-v0.7.15.md commit table 정합) + v0.7.16 작업 보존 (d9f1866)
- chore(v0.7.15): version bump 0.7.14 → 0.7.15 (auto-sync verified) + Beta-v0.7.15.md (0dc813a)
- chore(v0.7.15): state sync (atomic_write 적용) + 1 daily backlog (3049651)
- chore(v0.7.15): version bump 0.7.14 → 0.7.15 (auto-sync verified) + Beta-v0.7.15.md (a369e7c)

### Fixed

- fix(v0.7.15): Beta-v0.7.15.md Commit table 정상화 (Deferred 표에서 중복 row 제거 + 4 commit hash) (68b0ae9)
- fix(v0.7.15): Beta-v0.7.15.md Commit section + 3 commit hash (3dfb5a1)

## [0.7.14] - 2026-06-15

### Added

- feat(v0.7.14): cmd_version_bump auto-sync workflow_kit/__init__.py + cmd_changelog_gen subcommand + 8 smoke (23eb7fd)

### Changed

- chore(v0.7.14): version bump 0.7.13 → 0.7.14 (auto-sync verified) + Beta-v0.7.14.md + CHANGELOG.md + state/work_backlog sync (63ab483)

### Fixed

- fix(v0.7.14): Beta-v0.7.14.md Commit + Reference section 정상화 (line 정렬 + 헤더) (29af65d)
- fix(v0.7.14): Beta-v0.7.14.md commit table TBD → 23eb7fd + 63ab483 (a01c7b4)

## [0.7.13] - 2026-06-15

### Added

- feat(v0.7.13): cmd_release --version flag (staging backfill, pyproject 일시 patch 불필요) (922ebc0)

### Changed

- chore(v0.7.13): state sync (v0.7.12 + v0.7.13 backfill) + 2 daily backlog (afc685a)
- chore(v0.7.13): version bump 0.7.11 → 0.7.13 + __version__ sync + Beta-v0.7.13.md (628bf93)

### Fixed

- fix(v0.7.13): Beta-v0.7.13.md Commit section + 3 commit hash (727c59c)

## [0.7.12] - 2026-06-15

### Added

- feat(v0.7.12): refresh_wiki_memory REPO_ROOT auto-detect (CLI flag > env var > git rev-parse > legacy fallback) + 4 smoke (63080ba)

### Changed

- chore(v0.7.12): v0.7.5~v0.7.10 release backfill (6 wheel/sdist + 6 git tag + 6 GH release) + Beta-v0.7.12.md 갱신 (89b7af5)

### Fixed

- fix(v0.7.12): Beta-v0.7.12.md commit table TBD → 89b7af5 (5b8e730)
- fix(v0.7.12): Beta-v0.7.12.md commit table TBD → 63080ba (0b3e704)

## [0.7.11] - 2026-06-15

### Added

- feat(v0.7.11): release_pipeline Phase 3 (dist subcommand) + state sync + 8 smoke (b2650f5)

### Changed

- chore(v0.7.11): version bump 0.7.10 → 0.7.11 + __version__ sync (ec407f1)

### Fixed

- fix(v0.7.11): cmd_verify --json field names (tag → tagName, createdAt → publishedAt) + release note commit table (aa4e837)

## [0.7.10] - 2026-06-14

### Added

- feat(v0.7.10): release_pipeline Phase 2 (release / verify / rollback) + 8 smoke test (fdf8159)

### Changed

- docs(v0.7.10): release note backfill + refresh_wiki_memory v0.7.10 tracking (fc87fdd)
- chore(v0.7.10): version bump 0.7.9 → 0.7.10 + release note (67d4a37)

## [0.7.9] - 2026-06-14

### Added

- feat(v0.7.9): release_pipeline tool 정식화 (validate / version-bump / note-draft) + 8 smoke test (cb0a892)

### Changed

- docs(v0.7.9): release note backfill + refresh_wiki_memory v0.7.9 tracking (283823e)
- chore(v0.7.9): version bump 0.7.8 → 0.7.9 + release note (d39be44)

## [0.7.8] - 2026-06-14

### Added

- feat(v0.7.8): refresh_wiki_memory 에 v0.7.8 release tracking 추가 (662bead)
- feat(v0.7.8): state-aware evaluate_compliance + config actual apply (d3235ad)

### Changed

- docs(v0.7.8): release note commit hash backfill (b67af83) (f444e68)
- chore(v0.7.8): version bump 0.7.7 → 0.7.8 + release note (b67af83)

## [0.7.7] - 2026-06-14

### Added

- feat(v0.7.7): refresh_wiki_memory 에 v0.7.7 release tracking 추가 (fd18288)
- feat(v0.7.7): workflow_kit.cli.doctor 에 load_config + should_fail integration (022672f)

### Changed

- docs(v0.7.7): release note commit hash backfill (3300e73) (7581dd2)
- chore(v0.7.7): version bump 0.7.6 → 0.7.7 + release note (3300e73)

## [0.7.6] - 2026-06-14

### Added

- feat(v0.7.6): refresh_wiki_memory 에 v0.7.6 release tracking 추가 (1fefdfd)
- feat(v0.7.6): workflow_kit.metadata (pyproject.toml [tool.workflow-doctor] loader) + 10 smoke test (0daf6da)
- feat(v0.7.6): run_all_checks 통합 runner + 10 smoke test (53d5dc8)

### Changed

- docs(v0.7.6): release note commit hash backfill (b9ede19) (7a5c56e)
- chore(v0.7.6): version bump 0.7.5 → 0.7.6 + release note (b9ede19)

## [0.7.5] - 2026-06-14

### Added

- feat(v0.7.5): refresh_wiki_memory 에 v0.7.5 release tracking 추가 (150ee32)
- feat(v0.7.5): refresh_wiki_memory tool 정식화 + 10 smoke test (Wiki 운영 자동화) (0741775)

### Changed

- docs(v0.7.5): release note commit hash backfill (c2a75f8) (51edde5)
- chore(v0.7.5): version bump 0.7.4 → 0.7.5 + release note (c2a75f8)
- test(v0.7.5): 4 sub-cat dispatcher runtime test 보강 (12 → 16) (9e1f206)

## [0.7.4] - 2026-06-13

### Added

- feat(v0.7.4): CLI wrapper (workflow doctor) + @graceful_shutdown + optional dep (hypothesis/objgraph) (22e7750)

### Changed

- chore(v0.7.4): score history v0.7.4 entry (Overall 4.67 A 유지) (cfb09fb)
- docs(v0.7.4): wiki log v0.7.4-beta entry 추가 (1818dd6)

## [0.7.3] - 2026-06-13

### Added

- feat(v0.7.3): 4 runtime helper (auth/testing/profiling/resiliency) + 7 baseline dispatcher (d03348a)

### Changed

- chore(v0.7.3): score history v0.7.2/v0.7.3 entry 추가 (Overall 4.66→4.67 A 유지) (c732c0f)
- docs(v0.7.3): wiki log v0.7.3-beta entry 추가 (be49e0f)

## [0.7.2] - 2026-06-13

### Added

- feat(v0.7.2): Extension sub-cat + 4종 (resiliency) 본 구현 (179 test PASS) (3bffba3)

### Changed

- docs(v0.7.2): wiki log commit hash TBD → 3bffba3 갱신 (7cae496)

## [0.7.1] - 2026-06-13

### Added

- feat(v0.7.1): follow-up 4건 + wiki 개선 4건 묶음 (158 test PASS, GH release) (f09034d)

### Changed

- docs(v0.7.1): wiki log commit hash TBD → 0224a76 갱신 (9935e06)
- docs(v0.7.1): wiki log commit hash TBD → 99e299f 갱신 (d8c981c)
- docs(v0.7.1): wiki log commit hash TBD → f09034d 갱신 (bad14d8)

## [0.7.0] - 2026-06-13

### Changed

- docs(v0.7.0): wiki log commit hash TBD → c72bdc3 갱신 (bdc6ceb)
- docs(v0.7.0): wiki log commit hash TBD → 49dfc78 갱신 (471fee2)
- docs(v0.7.0): wiki log commit hash 갱신 TBD-pending → 7a4dbae (b375951)
- docs(v0.7.0): wiki log commit hash TBD → 021ec16 갱신 (ac75d72)
- docs(wiki): v0.7.0 5 concept page + L2 emit helper + drift smoke test (021ec16)
- docs(v0.7.0): wiki log entry header 에 commit hash 7자 prefix 명시 (3fcd480)
- docs(v0.7.0): release note follow-up section 추가 (Task 3+2+1) (8818cbe)
- chore(v0.7.0): version bump 0.6.3 → 0.7.0 (390a6e0)
- docs(v0.7.0): Release notes + wiki log entry (15 commit, ~3,200 line, 130 test PASS) (dff0aae)
- wiki: v0.7.0 step 9 — Unit of Work 3-layer template (17 test PASS) (b7641e3)
- wiki: v0.7.0 step 10 — Audit Log 표준화 (1 spec + 1 helper fix + 13 test) (2458cf8)
- wiki: v0.7.0 step 1 — stage_completion required 격상 (8 test PASS) (6148c0f)

## [0.6.6] - 2026-06-12

### Added

- feat(v0.6.6): 5 SKILL.md-only skill runtime 통합 (12/12 spec+runtime 일관성) (6a9126c)

### Changed

- wiki: v0.6.6 follow-up #1 — 5 SKILL.md-only skill runtime (12/12 일관성) (8ae9102)

## [0.6.5] - 2026-06-12

### Added

- feat(v0.6.5): batch stage_completion integration — 6 spec 보유 skill (10/11 완료) (ca7a685)
- feat(v0.6.5): pilot stage_completion integration — automated-repro-scaffold (2fab835)
- feat(v0.6.5): Stage Gate Runtime helper + migration guide (3 file, 13 test PASS) (dd98e69)
- feat(v0.6.5): StageCompletion field 11종 skill spec + catalog 보강 (13 file) (5b16517)

### Changed

- wiki: v0.6.5 release — AIDLC 패턴 차용 (10 commit, ~2,600 line) (46e4d1f)
- release(v0.6.5): AIDLC 패턴 차용 (Question File Format + Stage Gate) (3897da7)
- wiki: v0.6.5 batch runtime — 6 spec stage_completion (10/11, +72 line) (0ae8d4a)
- wiki: v0.6.5 pilot runtime — automated-repro-scaffold stage_completion (1/11, +44 line) (fbe9673)
- wiki: v0.6.5 runtime — stage-gate-pattern §12 + log entry (35 test PASS) (fbc8370)
- wiki: v0.6.5 — stage-gate-pattern §8 + log entry (StageCompletion 11종 적용 추적) (0001782)

## [0.6.4] - 2026-06-12

### Added

- feat(v0.6.4): Question Format + Stage Gate 코드 (2 module + 2 smoke test) (bc16d91)
- feat(v0.6.4): Question File Format + Stage Gate 명시화 (4 doc) (25756bb)

### Changed

- wiki: v0.6.4 신규 concept 2종 (Question File Format + Stage Gate Pattern) (d32226b)

### Fixed

- fix(v0.6.4): V-R9 skip marker — naive grep false-positive 17 → 0 (30183c5)

## [0.6.3] - 2026-06-12

### Added

- feat(v0.6.3): P4 memory/log.md + harness overlay consistency check (3261e20)

### Changed

- release(v0.6.3): final v0.6.x series release — all 4 milestones complete (1923705)

### Fixed

- fix(v0.6.3): P6 phase-6 backfill — INGEST_GUIDE path 정정 + log 보강 (1d7ca77)
- fix(v0.6.3): broken relative links after memory/active/ rename + fix bootstrap test leniency (6b2bf00)

## [0.6.2] - 2026-06-12

### Added

- feat(v0.6.2): P3 T2 work_backlog anchor + T3 ingest atomicity (2713059)

## [0.6.1] - 2026-06-12

### Added

- feat(v0.6.1): P2 R8 freeze + R10 freeze lint + T1 memory lint 4종 + R7 merge-res ext (0620373)

## [0.5.11] - 2026-06-09

### Added

- feat(v0.5.11): Mavis engine hook (§6.5) + 회귀 test 강화 (4ce3635)

### Changed

- docs(v0.5.11): Beta-v0.5.11.md release note — 릴리스 일자 표현 정정 (5bd4c4f)
- chore(v0.5.11): bump version to 0.5.11-beta (cfde435)
- docs(v0.5.11): Beta-v0.5.11 release note (cb0f698)
- docs(v0.5.11): governance 갱신 — 1인 dev 환경, 24h cool-down 명시 (c89971d)
- docs(v0.5.11): --no-interactive 비대화형 가이드 보강 (7329dbe)

### Fixed

- fix(v0.5.11): bootstrap MCP env — wheel install 시 PYTHONPATH omit (e388366)
- fix(v0.5.11): MCP initialize response — protocolVersion 추가 (677bcff)

## [0.5.10] - 2026-06-08

### Fixed

- fix(v0.5.10): choose_roles sub.delegation_id parent-prefix spec 정합 (8359cfc)

## [0.5.9] - 2026-06-08

### Changed

- docs(v0.5.9): wire 가이드 §7/§8/§9 보강 — sub.delegation_id parent prefix 룰 명시 (1006ff0)

## [0.5.8] - 2026-06-08

### Added

- feat(v0.5.8): interactive --harness picker + packaging smoke automation (6213dcc)

## [0.5.7] - 2026-06-08

### Added

- feat(v0.5.7): contract v1 §4.2/§5.2 multi-component fan-out/in + §6.3 cross-ref row (#21) (ebf7e7c)

## [0.5.6] - 2026-06-07

### Added

- feat(v0.5.6): contract v1 §5/§6 P0 enforcement (validator + delegator) (#20) (79f3bec)

### Changed

- docs(v0.5.6): mark TASK-V056-001 done post-merge (731787b)

## [0.5.5] - 2026-06-07

### Added

- feat(v0.5.5): Phase 11 본격 pilot (Devhub Example × Contract v1) (#19) (1f095ec)

### Changed

- docs(v0.5.5): mark TASK-V055-001 done post-merge (75a3fc6)

## [0.5.4] - 2026-06-07

### Added

- feat(v0.5.4): orchestrator ↔ sub-agent delegation contract v1 (closes #1) (#18) (7737e14)

## [0.5.3] - 2026-06-07

### Added

- feat(v0.5.3): antigravity MCP config 표준화 + cross-language stack 표시 (#17) (b6ae73a)

### Changed

- docs(v0.5.3): mark tasks done + release notes for Beta v0.5.3 (a961fa0)

## [0.5.2] - 2026-06-06

### Changed

- refactor(v0.5.2): bootstrap_workflow_kit.py → bootstrap_lib/ 6-module package (#16) (9497a35)

## [0.5.1] - 2026-06-06

### Added

- feat(v0.5.1): end-to-end MCP round-trip smoke (#15) (73f8f2f)
- feat(v0.5.1): per-harness MCP install + auto-emit + guide (#14) (c3c9a90)
