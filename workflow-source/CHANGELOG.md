# Changelog

- 문서 목적: 저장소의 모든 주요 변경을 release 단위로 기록한다 (Keep a Changelog 형식).
- 범위: git log 에서 추출한 release 별 Added / Changed / Fixed 항목.
- 대상 독자: maintainer, 릴리스 매니저, 외부 consumer
- 상태: stable (자동 생성물)
- 최종 수정일: 2026-08-25
- 관련 문서: [`./releases/`](./releases/) (release note), [`../docs/RELEASE.md`](../docs/RELEASE.md) (릴리스 절차)

All notable changes to this project will be documented in this file.

본 파일은 `tools/release_pipeline.py changelog-gen` 으로 자동 생성됩니다 (v0.7.14+).
수동 편집은 다음 생성 시 덮어써진다 — 형식/metadata 변경은 생성기를 고칠 것.

## [Unreleased] - 2026-08-25

### Added

- feat(harness): overlay 위임 선언(plugin-only) 신설 — 이 저장소 claude-code 채널 플러그인 단일화 (main-010) (caffb013)
- feat(roadmap)!: ADR-027 로드맵 층 — 스키마·파서·상태 생성기·배선·게이트·bootstrap 씨앗 (M-002~M-005) (9dc91713)
- feat(session-start): 부재 진입점을 스스로 채운다 — 낡음은 보고만 (main-006) (b119d68b)
- feat(handoff): §5 를 부류별로 가른다 — 산문이 SSOT 를 복제하던 자리 (main-001) (51cfa9ad)
- feat(deploy)!: 소유권 4번째 분류 '포크됨' + codex 채널 정리 (main-011, -012) (00d30914)
- feat(task-ssot)!: 본문 라벨을 영어로 전환한다 — 4단계 (main-009) (47c84ad4)
- feat(doctor): runtime_load — 노출 미측정 한 칸을 측정으로 옮긴다 (main-009 close) (deb74b82)
- feat(okf)!: v0.2 이행 — legacy 를 남긴 채 정규 필드를 더한다 (ADR-026, main-003) (8ead8bf7)
- feat(doctor): 환경 pre-flight — 배포 축 gap 4개가 전부 닫혔다 (main-019) (c92d3c7b)
- feat(doctor): 드리프트를 마커가 아니라 페이로드 해시로 본다 (main-005) (2f68fb2e)
- feat(entrypoint): AGENTS.md 를 공유 진입점으로 합친다 (main-001, 08-18) (c55631f4)
- feat(deploy): wk doctor — 배포 post-apply 탐침 (main-016, 컨셉 gap 1) (3b50ae95)
- feat(plugin): pi.dev (pi-coding-agent) 11번째 분배 채널 정식 등록 (main-012) (6f2b5435)
- feat(plugin): Grok Build 훅 관례 경로와 설치 채널을 연다 (ae9e1a73)
- feat(memory): task SSOT 4단계 준비 — 정본 표 누락 라벨 보강 + 검사 범위 확대 (43fe58ce)
- feat(memory): task SSOT 3단계 — 라벨을 바꿀 수 있는 상태로 (전환은 다음 release) (a576e92b)
- feat(memory): task SSOT 2단계 — 소실과 중복은 같은 뿌리였다 (0f63ddc0)
- feat(memory): task SSOT 1단계 — 읽는 쪽을 하나로 (index 20개가 조용히 0이었다) (21e96bf0)
- feat(memory): handoff 기준선 롤오프 — 자르지 않고 이관한다 (ab07bafe)
- feat(checks): 무거운 7개에 WATCHES 선언 + check_changed_selection 계약 9 cases (0fa23bab)
- feat(checks): run_all_checks --changed 기전 (WATCHES 선언 기반, 미선언은 항상 실행) (49da7655)
- feat(memory): seed 가 state.json 까지 만들어 끝을 맺는다 + 절반짜리 가드 강화 (96bfb700)
- feat(memory): 아카이브를 이동에서 이관으로 — 미완료 소실 + 참조 끊김 차단 (9b600efb)
- feat(smoke): 브랜치 메모리 네임스페이스 가드 신설 + 정본 창구 정정 (d818625e)
- feat(dist): ship native Codex and Claude plugin archives (51e04eb3)
- feat(dist)!: 2nd deprecation cycle 완결 — 구경로 shim drop + --bundle 기본 read-only (TASK-2026-08-13-main-005) (7fed4158)
- feat(plugin): SessionStart 조건부 규칙 주입 — rules.md + 마커 감지 hook (TASK-2026-08-13-main-003) (573f3138)
- feat(plugin): P3 멀티 하네스 어댑터 — gemini/goose/opencode + 수렴 판정 (TASK-2026-08-12-main-016) (7eb11c30)
- feat(plugin): P4 릴리스 게이트 + session-end 스킬 (TASK-2026-08-12-main-017·020) (2cf95764)
- feat(plugin): Claude Code 채널 개통 — 어댑터 + marketplace + 자기 적용 (TASK-2026-08-12-main-015) (35473da9)
- ... (123 more)

### Changed

- chore(memory): main-004 close 기준 확정 — 격리 후 완료 run 33건에서 mypy 게이트 실패 0 (62차 소유자 결정) (de0f8307)
- chore(memory): 60차 세션 종료 — ADR-027 로드맵 층 완결 + v1.5.0 발행 (61차 병합 + main 생성물 치유) (6ecdeaa2)
- chore(memory): 61차 세션 종료 — Windows 플랫폼 결함 축 착수 (Oh My Pi) (3866c188)
- docs(work_logs): 2026-08-25 세션 기록 — 원격 동기화 + 플러그인 설치 검증(발견 3건) (b00b4a18)
- chore(memory): 60차 — M-006 close, v1.5.0 발행·재적용 완료, 로드맵 ADR-027 축 완결 (M-001~M-006 전부 done) (ff0ac3cc)
- chore(memory): 60차 진행분 — ADR-027 로드맵 층 M-001~M-005 close + mypy flake 관찰 6차 + memory_index 승격 2건 (379913b9)
- chore(schemas): output sample contracts 재생성 — SessionStartOutput.roadmap_context 반영 (b6afe828)
- docs(adr): ADR-027 — 로드맵·마일스톤·WBS 층과 SDLC 온보딩 기본 (M-001) (881c2cec)
- chore(memory): 59차 세션 종료 — doctor pip 오탐 수리 + memory_index 저점 고착 3회째 (4e4e8963)
- chore(memory): 58차 세션 종료 — OKF 매니페스트 잔재 수리 + mypy flake 관찰 5차 (ef5418fe)
- chore(memory): 57차 세션 종료 — v1.4.0 발행 + 혼합 표기 축 완결 + mypy flake 원인 규명 (b35fe6cf)
- chore(harness): 자기 적용 산출물을 v1.4.0 으로 재적용 — 낡은 마커 5 → 0 (69e35a8b)
- refactor(memory)!: 레거시 task 라벨 마이그레이션 — 도구로, 파싱 동일성을 잠금장치로 (main-004) (64a5370f)
- docs(decision): 혼합 표기 결정 재료 — 실측이 질문을 다시 세웠다 (main-002, -003) (dd682224)
- chore(memory): 53차 세션 종료 — 탐침 7절 + installPath 선언 + 라벨 영어 전환 (201f5a8e)
- chore(memory): 51차 세션 종료 — v1.3.0 발행 + 관찰 축 실측 + 채널 파리티 (75e9275a)
- chore(memory): 51차 세션 종료 — v1.3.0 발행 + 관찰 축 3개 실측 (main-004~007) (17847a0d)
- refactor(wiki): L2 계약을 memory 파생 4종으로 좁힌다 (main-001) (51b14113)
- chore(memory): 48차 세션 종료 — 배포 축 gap 4개 전부 닫힘 + OKF 상호운용 실측 (9a837e73)
- chore(memory): 47차 세션 종료 — 플러그인 설치 + 배포 축 gap 1·2 해소 + 결함 3건 (d25ed659)
- docs(deploy): 채널별 재실행 계약 4채널 실측 (main-017, 컨셉 gap 2) (c952dd64)
- chore(memory): 46차 세션 종료 — main-016 wk doctor 착수·구현 지점 조사 완료 (구현 미착수) (b6b91b85)
- chore(memory): 45차 세션 종료 — 배포 멱등성 컨셉 문서 + gap 4 task 등록 (main-015) (c59a9ade)
- docs(distribution): 배포 채널×하네스 매트릭스 정리 (main-014) (0e29bdbc)
- Merge pull request #28 from ykylee/worktree/clear-field-f112 (59ad6d43)
- Merge main into worktree/clear-field-f112 — case 19 충돌 해소 (Grok 19 · pi 20 공존) (7571f40d)
- docs(release): 현재 package version 표기 동기화 1.1.8 → 1.2.0 (PR #26 대체) (120a83ea)
- docs(harness): 배포 정책 문서 흠 2건 수리 — §번호 중복 + 누락 타겟 6종 (main-012) (2f0fde65)
- chore(memory): worktree/brave-field-3f50 브랜치 메모리 seed (표준 §10.2) (a8932689)
- docs(plugin): 정직화 — pi v0.84.2 가 MCP 미지원임을 명시 (main-012) (ce595693)
- ... (343 more)

### Fixed

- fix(mcp): Windows 플랫폼 결함 축 — emit 해석기 플랫폼 분기 + PYTHONPATH target 레이아웃 교정 + doctor kit_resolution 탐침 (62차) (24b75e2a)
- fix(docs): work log 의 docs 밖 markdown 링크 2건 제거 — mkdocs strict build red 수리 (95fadfc2)
- fix(state): safe_relpath POSIX 정규화 — Windows 호스트 state.json 백슬래시 제거 (TASK-2026-08-25, cross-host 형식 결함) (bcb05cfb)
- fix(doctor): pip 부재 판정이 선언을 읽는다 — uv tool venv 의 부재는 설계다 (main-009) (4461e08e)
- fix(okf): 매니페스트 버전을 정본 파생으로 — 한 번들이 두 버전을 말하고 있었다 (main-008) (b09bbf16)
- fix(mypy)!: 캐시를 전용 경로로 격리 — 빈 문자열은 격리가 아니었다 (main-007) (19e40ac9)
- fix(mypy): 캐시 격리 — no-incremental 은 읽기만 끄고 디렉터리는 만든다 (main-007) (8454e4eb)
- fix(gate): 절단이 트레이스백 결론을 자르지 않게 — 범인이 지목됐다 (main-004 관찰 4차 후속) (ffe4bc77)
- fix(gate): mypy 게이트에 --show-traceback — 4차까지 증거가 없던 이유 (main-004 관찰 4차) (579e2f17)
- fix(bootstrap): daily backlog 를 정본 작성기로 조립한다 — 사본을 없앴다 (main-003) (6a2c94ad)
- fix(tests): watch_transient flake — 이벤트 1건은 완결본을 뜻하지 않는다 (main-001) (900c9455)
- fix(ci): consumer-metrics-digest 가 실재하는 경로를 부른다 (main-017) (8b2c6ebb)
- fix(ci): okf-validate 가 okf_version 을 정본에서 파생한다 (main-016) (72ecff6c)
- fix(entrypoint): 산문 목록 파생 + 사라지던 planned + 포크 병합 (main-013, -014, -015) (cd0ff943)
- fix(doctor): 어느 사본이 설치본인지 선언을 읽는다 — 갱신이 보고를 나쁘게 만들던 자리 (main-010) (151627ee)
- fix(harness): session-end 를 bootstrap 채널에도 — 두 채널의 스킬 집합이 갈라져 있었다 (main-008, -009) (43168b34)
- fix(release): next_version 을 커밋에서 파생한다 — 개수는 세고 판정은 안 세던 자리 (main-006) (40e86dc2)
- fix(observability): 관찰 축 3개 실측 — mypy 원인 계열 확정 + 승격 루프 배선 (main-004, -005) (a36c5edf)
- fix(linter): in_progress 대조의 세 번째 출처를 task SSOT 로 (main-002) (e64b4812)
- fix(wiki): L2 파이프라인 회생 — 화석 은퇴와 파생 뷰 재정의 (main-004) (3bd45c10)
- fix(okf): 상호운용을 자기 선언이 아니라 실측으로 (main-006) (426da99c)
- fix(deploy): 패키지가 체크아웃 레이아웃에 기대던 결함 (main-003) (2bd5417b)
- fix(rollover): 롤오프 포인터가 실행마다 쌓이던 결함 (main-002) (666424b2)
- fix(smoke): check_deprecation_3rd_cycle 의 죽어 있던 제외 목록 (main-003) (30369739)
- fix(backlog): 날짜 롤오버 시 진행 중 task 의 갱신이 사라지던 결함 (main-001) (d02d9663)
- fix(standard): 정본의 다중 줄 bullet 이 추출에서 잘리던 결함 수리 (main-002) (f3e9d0cc)
- fix(checks): timeout 선언 누락 3건 + 내장 worktree 스캔 제외 (main-011) (28f12ed1)
- fix(memory): seed 가 첫 세션 기록을 쓴다 — 갓 seed 한 브랜치가 layout green (main-005) (f9b374ee)
- fix(memory): 아카이브가 살아 있는 대상 상대 링크를 안 고치던 결함 수리 (main-006) (098386c0)
- fix(memory): 검증 결과 주입이 작업 결과 묶음을 가르던 결함 수리 (main-010) (0b2ef9b3)
- ... (126 more)

## [1.6.0] - 2026-08-25

### Changed

- release(v1.6.0): 발행 준비 — Windows 플랫폼 결함 축, 등급은 §1.5 판정으로 minor (62953fb8)

## [1.5.0] - 2026-08-25

### Changed

- release(v1.5.0): 파생물 정합 2차 — bump 후 낡은 버전 스탬프 전수 갱신 (CI red 수리) (9feabcd8)
- release(v1.5.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + 파생물 정합 (main-014) (9e7b2645)
- release(v1.5.0): 발행 준비 — ADR-027 로드맵 층 사이클, 등급은 §1.5 4문항으로 minor (8520dc13)

## [1.4.0] - 2026-08-24

### Changed

- release(v1.4.0): 발행 완료 — 태그 push + GitHub Release + 파생물 정합 (main-005 close) (7343bddd)
- release(v1.4.0): 16 커밋 누적분 발행 준비 — 등급은 §1.5 4문항으로 minor (main-005) (7fa37940)
- chore(backlog): v1.4.0 릴리스 task 등록 — 등급 판단 근거 기록 (main-005) (e346243f)

## [1.3.0] - 2026-08-20

### Changed

- docs(release): v1.3.0 노트의 태그 표기를 RELEASE.md §2.2 규약에 맞춘다 (1f33a958)
- release(v1.3.0): 101 커밋 누적분 발행 준비 + 버전 등급 판단 기준 정본화 (main-007) (c61b2237)

## [1.1.6] - 2026-08-10

### Changed

- docs(release): v1.1.6-beta 발행 후처리 (TASK-2026-08-10-main-015) (c51d973e)
- chore(release): v1.1.6-beta 준비 — 노트 + 파생물 선재생성 + stamp (TASK-2026-08-10-main-015) (25e09d4a)

## [1.1.5] - 2026-08-10

### Changed

- docs(release): v1.1.5-beta 발행 후처리 + 세션 close memory (4e68c2e8)
- chore(release): v1.1.5-beta 준비 — 노트 + 파생물 선재생성 + stamp (6e77c14e)

## [1.1.4] - 2026-08-10

### Changed

- docs(release): v1.1.4-beta 발행 후처리 + 세션 close memory (ea7687be)
- chore(release): v1.1.4-beta 준비 — 노트 + stamp 정합 (7a12490a)

### Fixed

- fix(release): v1.1.4 파생물 재생성 — 릴리스 직후 전량 재실행이 잡은 9건 (890521f5)

## [1.1.3] - 2026-08-10

### Changed

- docs(memory): v1.1.3-beta 발행 기록 + 릴리스 파이프라인 후속 2건 (e956f221)
- chore(release): v1.1.3-beta 준비 — 노트 + version bump + stamp (6cadcca1)

## [1.1.2] - 2026-08-09

### Changed

- docs(memory): v1.1.2-beta 발행 기록 + 릴리스 도구 결함 2건 (74161f89)
- chore(release): v1.1.2-beta — federation 쓰기 / wk dispatcher / 3rd layer / drift v2 (b688a065)

## [1.1.1] - 2026-08-08

### Changed

- docs(memory): v1.1.1-beta release 반영 — baseline + current_axis 갱신 (678806f2)
- chore(release): v1.1.1-beta — [project.scripts] 29 entry points (CLI 化 A안) (6b92a602)

## [1.1.0] - 2026-08-11

### Changed

- docs(memory): v1.1.0·v1.1.1 노트 누적 표기 미삽입 확정 — backlog 14건 종결 (TASK-2026-08-11-main-014) (5e6ca22a)
- docs(memory): v1.1.0-beta release 반영 — baseline + current_axis + handoff 갱신 (02f80f29)
- chore(release): v1.1.0-beta — §0.8 4건 close + dual mode CLI + federation *읽기* (564ce36b)

## [1.0.0] - 2026-07-22

### Changed

- docs(memory): v1.0.0 사이클 close-out — task SSOT 3건 + 세션 + state.json 재생성 (3f017a2b)
- docs(v1.0.0): 릴리스 노트 §2.15 — auto-bump dry-run 결함 (릴리스 후 발견) 기록 (08391f26)
- docs(v1.0.0): 릴리스 노트 확정 — 보류/초안 → 릴리스, 본 사이클 해소 내역 §2.9~2.14 추가 (2e6ae449)
- docs(v1.0.0): dashboard snapshot + CHANGELOG 재생성 + 검증 수치 실측 정합 (17c3cb63)
- docs(v1.0.0): smoke 카운트 199 정합 + 릴리스 노트 검증 섹션 실측 기록 (5c690b97)
- chore(v1.0.0): version bump 1.0.0 + 버전 스탬프 정합 + Phase 13 진입 (릴리스 미완) (e574bf9d)
- docs(v1.0.0): Gate 1 ✅ PASS — Panel 5 items_total=11 (Break Point #1 close-out) (6e24b81d)

## [0.15.21] - 2026-07-21

### Added

- feat(release): v0.15.21 — Phase 13 follow-up 1차 (AC2 telemetry 다양성 + CHANGELOG lockdown) (8a93afa4)

### Changed

- chore(dashboard): v0.15.21 post-release snapshot refresh (37233c9f)

## [0.15.20] - 2026-07-20

### Fixed

- fix(release): v0.15.20 — v1.0.0 pre-release final (stable API + SemVer 2-year guarantee) (ab202d8c)

## [0.15.19] - 2026-07-20

### Fixed

- fix(release): v0.15.19 — cross-panel final 정합 (v1.0.0 pre-release anchor) (0d871478)
- fix(release): v0.15.19 — cross-panel final 정합 (v1.0.0 pre-release anchor) (271f96b8)

## [0.15.18] - 2026-08-10

### Changed

- chore(tests): v0.15.18 dummy wrapper 물리 제거 — 153개/60파일 (TASK-2026-08-10-main-007) (f7b5217e)

### Fixed

- fix(test): v0.15.18 — TST-WF-01 historical smoke 보강 + v1.0.0 Break Point #2 해소 (e5225a9c)
- fix(test): v0.15.18 — TST-WF-01 historical smoke 보강 + v1.0.0 Break Point #2 해소 (a5c0cfcb)

## [0.15.16] - 2026-07-20

### Added

- feat(harness): v0.15.16 — Grok Build (xAI CLI TUI) 11번째 harness + cross-check discipline anchor 확장 (v0.15.16~v0.15.19) (370cb237)
- feat(harness): v0.15.16 — Grok Build (xAI CLI TUI) 11번째 harness + cross-check discipline anchor 확장 (v0.15.16~v0.15.19) (dc64d2fe)
- feat(harness): v0.15.16 — Grok Build (xAI CLI TUI) 11번째 harness + cross-check discipline anchor 확장 (v0.15.16~v0.15.19) (fc834d1f)

### Changed

- chore(release): v0.15.16 정식 release — Beta note 신규 + version bump (09825f35)

## [0.15.15] - 2026-07-18

### Changed

- docs(release): v0.15.15 정식 release 정합 + Beta-v0.10.4 release note 신규 (d9aa69ef)
- chore(release): v0.15.15 정식 version bump (94a0174a)
- docs(planning): v0.15.15 baseline + draft → stable 격상 + maturity last_updated 갱신 (b3db12ce)
- docs(release): v0.15.15 baseline + 회귀 표 + PROJECT_PROFILE canonical path 반영 (37650331)
- docs(quickstart): v0.15.15 QUICKSTART.md cross-check smoke + 2 in-scope issue 정정 (3d59da88)

## [0.15.14] - 2026-07-17

### Changed

- docs(install): v0.15.14 INSTALLATION_AND_USAGE.md cross-check smoke + stale text 정정 (e1e0a54a)

## [0.15.13] - 2026-07-17

### Added

- feat(harness): v0.15.13 Harness apply_guide.md content cross-check smoke (56c39919)

## [0.15.12] - 2026-07-17

### Changed

- docs(readme): v0.15.12 README.md cross-check smoke + stale text 정정 (4dce84d3)

## [0.15.11] - 2026-07-17

### Fixed

- fix(release): v0.15.11 sample tool_version housekeeping + 3-way cross-check smoke (586424f8)

## [0.15.10] - 2026-07-17

### Changed

- docs(adr): v0.15.10 MICROSOFT_MEMORA_EVALUATION close-out — Memora-inspired metadata 도입 종결 (0ad13bd9)

## [0.15.9] - 2026-07-17

### Added

- feat(harness): v0.15.9 Harness verification smoke — 10 harness cross-check discipline anchor (2fd858e9)

## [0.15.8] - 2026-07-17

### Added

- feat(dashboard): v0.15.8 Panel 1+2 maturity_distribution cross-validation smoke (cb468740)

## [0.15.7] - 2026-07-17

### Added

- feat(dashboard): v0.15.7 Panel 3 memory_index cross-validation smoke (b5901b5f)

## [0.15.6] - 2026-07-17

### Added

- feat(dashboard): v0.15.6 Panel 6/8 telemetry cross-validation smoke (c0bce15f)

## [0.15.5] - 2026-07-17

### Added

- feat(dashboard): v0.15.5 Panel 4 cross-validation smoke — cross-check discipline anchor (5c13c7b9)

## [0.15.4] - 2026-07-17

### Changed

- docs(adr): v0.15.4 ADR-007 close-out — 3rd deprecation cycle accepted no-op (861267ce)

## [0.15.3] - 2026-07-17

### Added

- feat(release): v0.15.3 release_error 시에만 maturity refresh (v0.14.6 out-of-scope 2 해소) (5cec8e84)

## [0.15.2] - 2026-07-17

### Added

- feat(release): v0.15.2 legacy_memory strict opt-out + v0.15.1 dashboard 정합 (단일 commit) (a4749f39)

## [0.15.1] - 2026-07-17

### Fixed

- fix(dashboard): v0.15.1 Panel 4 SMOKE_COUNT_PATTERN N+ 표기 parse + 8 panel 정합 (abe071eb)

## [0.15.0] - 2026-07-17

### Added

- feat(memory): v0.15.0 ⚠️ BREAKING — 2nd deprecation cycle 종결 (work_backlog.md.bak drop) (d7109ef8)

### Changed

- chore(state): v0.15.0 ⚠️ BREAKING push + audit fix memory cycle (2aed584e)
- chore(release): v0.15.0 push prep — README header sync, drift G2 fix, panel 7 stage branch (b31beb2a)

## [0.14.7] - 2026-07-16

### Added

- feat(dashboard): v0.14.7 HTML renderer Panel 6/7/8 + Panel 6 git reflog (Phase 15 follow-up) (3a274808)

## [0.14.6] - 2026-07-16

### Added

- feat(workflow): v0.14.6 refresh-maturity dispatcher + cmd_release auto-wire (Task 3 follow-up) (d8eeae77)

## [0.14.5] - 2026-07-16

### Added

- feat(memory): v0.14.5 2nd deprecation cycle 시작 — --legacy-memory flag (49ac3f7b)

## [0.14.3] - 2026-07-16

### Added

- feat(dashboard): v0.14.3 Phase 15 신규 Panel 6/7/8 (north-star + deprecation + telemetry) (ec9d3890)

## [0.14.2] - 2026-07-16

### Added

- feat(mcp): v0.14.2 MCP 2nd batch stable — apply_robust_patch (쓰기 MCP 정공법) (5602f631)

## [0.14.1] - 2026-07-16

### Added

- feat(mcp): v0.14.1 MCP 1st batch stable + workflow_log_rotator 정리 (Phase 14 MCP close-out) (27d21786)
- feat(memory): v0.14.1 deprecation cycle 1st 종결 — .bak deprecation warning emit (3afb9ef9)

## [0.14.0] - 2026-07-16

### Added

- feat(dashboard): v0.14.0 Panel 1 freshness 보강 — maturity_last_updated stale warning + helper (2c52c590)
- feat(memory): v0.14.0 67-file path string 갱신 + governance layout 명세 (Phase 14 AC3 close-out) (104d028a)
- feat(memory): v0.14.0 builder/cache 신규 layout 입력 확장 (Phase 14 AC2 close-out) (5a6b0692)
- feat(memory): v0.14.0 1st deprecation cycle — append-only + rebuild layout (Phase 14 AC1 close-out, 93 entries split) (8c53c4a1)

### Changed

- docs(release): v0.14.0 Phase 14 close-out — Beta release note + daily backlog (22b3eeb6)
- chore(release): v0.14.0 housekeeping — version bump + sample regen + dashboard refresh (3ade29d4)
- test(memory): v0.14.0 신규 smoke check_appendonly_memory_layout.py 6/6 (Phase 14 AC4 close-out) (5549d7c5)

## [0.13.0] - 2026-07-09

### Added

- feat(dashboard): v0.13.0-beta HTML snapshot (GitHub Pages publish) (b55fcad2)
- feat(dashboard): v0.13.0~2 quality dashboard — 5 panel data + CLI + drift guard inline + HTML renderer (b7811686)
- feat(dashboard): v0.13.0~2 quality dashboard — 5 panel data + CLI + drift guard inline + HTML renderer (3a81281c)

### Changed

- chore(release): v0.13.0-beta dashboard snapshot (auto-emit) (772ae091)

## [0.11.25] - 2026-07-03

### Added

- feat(mcp): stdio-sdk 정식 stable 승격 (v0.11.25) (b8d7bdea)

## [0.11.24] - 2026-07-03

### Added

- feat(skill): git-conflict-resolver --apply 구현 + 11/11 stable milestone (v0.11.24) (b227656b)
- feat(skill): automated-repro-scaffold + git-conflict-resolver stable/beta 승격 (v0.11.24) (ac7c17ba)

## [0.11.22] - 2026-07-02

### Changed

- chore(state): v0.11.22 release memory cycle — 8 phase + ADR-006 retrospective anchor + 3 skill wiring 3/3 (ea013a26)
- chore(state): v0.11.22 ADR-006 retrospective 자리 memory cycle (a42cf61e)
- chore(state): v0.11.22 Phase 3d backlog-update wiring memory cycle (skill wiring 3/3 완료) (d89beae7)
- chore(state): v0.11.22 Phase 3c doc-sync wiring memory cycle (a5987063)
- chore(state): v0.11.22 Phase 3b1 session-start wiring memory cycle (01ed22d9)
- chore(state): v0.11.22 Phase 3 dispatcher entry memory cycle (2cc61798)
- chore(state): v0.11.22 Phase 2b BM25 fallback memory cycle (c90bde1e)
- chore(state): v0.11.22 Phase 2 --merge opt-in memory cycle (a712c957)
- chore(state): v0.11.22 Phase 1.5 state.json hook memory cycle (fa0ac324)
- chore(state): v0.11.22 ADR-005 Phase 1 prototype memory cycle (348048ca)

## [0.11.21] - 2026-07-02

### Changed

- chore(state): v0.11.21 release memory cycle (b378284e)

## [0.11.20] - 2026-07-01

### Changed

- chore(state): v0.11.20 release memory cycle (a6c76bdc)

## [0.11.19] - 2026-07-01

### Changed

- chore(state): v0.11.19 release memory cycle (143d2d3d)

## [0.11.18] - 2026-07-01

### Changed

- chore(state): v0.11.18 release memory cycle (dfafdc4b)
- chore(state): v0.11.18 release memory cycle (df506ed2)

## [0.11.17] - 2026-06-30

### Changed

- chore(state): v0.11.17 release memory cycle (4d991e84)
- chore(v0.11.17): version bump + release note — mypy strict cumulative 25 error 격상 + schema drift housekeeping (3d3387de)

## [0.11.16] - 2026-06-27

### Added

- feat+chore(v0.11.16): cmd_release_status --auto-bump flag (read-only → opt-in write) (d81c6397)

## [0.11.15] - 2026-06-26

### Added

- feat+chore(v0.11.15): release summary 1-line (jq-friendly verdict) (9ae46829)

## [0.11.14] - 2026-06-26

### Added

- feat+chore(v0.11.14): release-status dispatcher (신규 module mypy strict clean 2-layer defense 실증) (ed5148a1)

## [0.11.13] - 2026-06-26

### Added

- feat+chore(v0.11.13): mypy CI cross-verify (Layer 1 ↔ Layer 2 정합 advisory) (b3075efa)

## [0.11.12] - 2026-06-26

### Added

- feat+chore(v0.11.12): mypy strict release-time gate (cmd_release pre-check 확장) (731b2029)

## [0.11.11] - 2026-06-26

### Added

- feat+chore(v0.11.11): mypy strict CI 통합 (GH Actions mypy-strict workflow) (0994f147)

## [0.11.10] - 2026-06-26

### Changed

- chore(v0.11.10): mypy strict 단계적 격상 25-26단계 (project_docs + profiling) — FULL STRICT 도달 (b73799b8)

## [0.11.9] - 2026-06-26

### Changed

- chore(v0.11.9): mypy strict 단계적 격상 23-24단계 (testing + runner) (41ef022c)

## [0.11.8] - 2026-06-26

### Changed

- chore(v0.11.8): mypy strict 단계적 격상 21-22단계 (read_only_mcp_sdk + workflow_writes) (ae4058ad)

## [0.11.7] - 2026-06-26

### Changed

- chore(v0.11.7): mypy strict 단계적 격상 19-20단계 (workflow_kit_cli + doc_sync) (5c82bc3a)

## [0.11.6] - 2026-06-26

### Changed

- chore(v0.11.6): mypy strict 단계적 격상 17-18단계 (session_outputs + read_only_bundle) (c82bf72c)

## [0.11.5] - 2026-06-26

### Changed

- chore(v0.11.5): mypy strict 단계적 격상 15-16단계 (decorators + linter) (1a7e6658)

## [0.11.4] - 2026-06-26

### Changed

- chore(v0.11.4): mypy strict 단계적 격상 13-14단계 (output_contracts + milestones) (6f6bf38a)

## [0.11.3] - 2026-06-26

### Changed

- chore(v0.11.3): mypy strict 단계적 격상 11-12단계 (purpose_ingest + purpose_graph) (bfbd1001)

## [0.11.2] - 2026-06-26

### Added

- feat+chore(v0.11.2): cycle 4 deferred 통합 (graph_insights schema + 3 skill context load) (372b153c)

## [0.11.1] - 2026-06-26

### Added

- feat+chore(v0.11.1): graph insights (R-A follow-up cycle 4) (fef6374a)

## [0.11.0] - 2026-06-26

### Added

- feat+chore(v0.11.0): two-step CoT ingest (R-A follow-up cycle 3) (f71dde8e)

### Changed

- docs(v0.11.0): plan two-step CoT ingest (R-A follow-up cycle 3) (f4eeba23)

## [0.10.4] - 2026-07-03

### Added

- feat: CodeWhale harness support (v0.10.4) - HARNESS_SPECS+SUPPORTED_HARNESSES+builder registration - single SKILL.md overlay (Constitution handles verification/parallelism/context) - additive rules only: session start, Korean output, backlog mgmt - harness docs + apply guide + distribution spec (cf0060d6)

## [0.10.3] - 2026-06-24

### Added

- feat+chore(v0.10.3): wiki file deletion cascade cleanup (R-A follow-up cycle 2) (3ca3a497)

## [0.10.2] - 2026-06-24

### Added

- feat+chore(v0.10.2): delivery layer 확장 (claude-code 진입점 정정 + aider/goose/custom + self-bootstrap) (c657853a)

## [0.10.1] - 2026-06-24

### Added

- feat+chore(v0.10.1): skill-only entry mode + claude-code adapter (SemVer minor) (afccdab3)

## [0.10.0] - 2026-06-24

### Added

- feat+chore(v0.10.0): deprecation 1st + 2nd cycle 동시 종료 (SemVer major) (c5fb94c5)

## [0.9.6] - 2026-06-24

### Added

- feat+chore(v0.9.6): R-A follow-up part 3 (wiki-event-sync R-A trigger) (09282b0e)

## [0.9.5] - 2026-06-24

### Added

- feat+chore(v0.9.5): R-A follow-up part 2 (skill context load integration) (96f97152)

## [0.9.4] - 2026-06-19

### Added

- feat+chore(v0.9.4): R-A follow-up part 1 (state.json.purpose_digest 1-line 자동 생성) (48a3380e)

## [0.9.3] - 2026-06-19

### Added

- feat+chore(v0.9.3): deprecation 2nd cycle (build_default_sources_v4) (7e38e6f5)

## [0.9.2] - 2026-06-19

### Added

- feat+chore(v0.9.2): purpose.md concept 흡수 (외부 reference 차용 정공법 1차 적용) (51e7becd)

## [0.9.1] - 2026-06-18

### Added

- feat+chore(v0.9.1): mypy workflow_kit_cli strict + release --full-auto + deprecation contract (50c688f8)

## [0.9.0] - 2026-06-18

### Added

- feat+chore(v0.9.0): spec drift patch + release note + Phase 11 close (a1f8463f)
- feat(v0.9.0): deprecation 1st cycle - phishing_federation_v4 DeprecationWarning (bf03b95e)

## [0.8.15] - 2026-06-17

### Added

- feat+chore(v0.8.15): release-dist 1-command + housekeeping (spec §9 9/12) (841329ff)

## [0.8.0] - 2026-06-17

### Added

- feat(v0.8.0): Stable API frozen + mypy strict + generated JSON Schema SSOT (5042df1c)

### Fixed

- fix: v0.8.0 hotfix + v0.8.8 mypy strict 4 file + v0.8.9 dispatcher 29/30 + release_pipeline SSOT (fcb4e8b6)

## [0.7.59] - 2026-06-17

### Added

- feat(v0.7.59): cmd_consumer_metrics in-process refactor (dispatcher 27 정합) (f2b92cfb)

## [0.7.58] - 2026-06-17

### Added

- feat(v0.7.58): consumer feedback metrics tool + dispatcher subcommand 27 (38fe32ae)

### Changed

- merge: v0.7.58 release (757d51b5)
- merge: v0.7.58 release (bcc0e99a)
- chore(v0.7.58): version bump 0.7.57 → 0.7.58 + release note + state sync (1c7d8e95)

### Fixed

- fix(state): v0.7.58 chore commit hash 동기화 (1c7d8e9) (d0c7c538)

## [0.7.57] - 2026-06-16

### Added

- feat(v0.7.57): mkdocs cross-link audit + 1 broken link fix (cbcaaadc)
- feat(v0.7.57): <in-memory> cleanup + dispatcher 23 → 26 (cache format interop) (ec1223c5)

### Changed

- merge: v0.7.57 release (364b12ad)
- docs(v0.7.57): v0.7.57 release note + wiki log + memory log (1c83b6f7)
- chore(v0.7.57): .gitignore 에 /site/ 추가 (mkdocs build output) (654e21e6)

## [0.7.56] - 2026-06-16

### Added

- feat(v0.7.56): cache-lfu-decay-persist CSV in-place + dispatcher --inplace (7b4d6b7f)
- feat(v0.7.56): release_pipeline wrapper 7 추가 + dispatcher 16 → 23 (fb6ebc45)
- feat(v0.7.56): score-wiki-trend in-process + dispatcher 16+ (c3ef1255)

### Changed

- merge: v0.7.56 release (6 follow-up 통합) (79ace23a)
- docs(v0.7.56): v0.7.56 release note + wiki log entry (094cc2ce)
- docs(v0.7.56): GH Pages 외부 consumer feedback loop + FEEDBACK.md (1c5c1dfd)
- test(v0.7.56): OKF strict mode lint rule coverage 7 신규 (audit 3차) (58e2ac0d)

## [0.7.55] - 2026-06-16

### Changed

- test(v0.7.55): tools/release_pipeline_lib wrapper test 2 신규 (cmd_validate) (428a2d20)
- docs(wiki): v0.7.55 release entry (release-doctor in-process + cache-migrate split + 3 subcommand L/M/N) (6cda10fe)
- chore(v0.7.55): version bump 0.7.54 → 0.7.55 + release note (0436eb3f)
- test(v0.7.55): tools/release_pipeline_lib wrapper test 2 신규 (cmd_validate) (3ba61e87)
- refactor(v0.7.55): release-doctor in-process + cache-migrate LRU/LFU split + 3 subcommand (14 subcommand) (4b64b206)

## [0.7.54] - 2026-06-16

### Added

- feat(v0.7.54): workflow_kit_cli — okf-validate / cache-migrate / release-doctor (11 subcommand) (97adc0c8)

### Changed

- docs(wiki): v0.7.54 release entry (dispatcher 11 subcommand: I/J/K) (0d976d00)
- chore(v0.7.54): version bump 0.7.53 → 0.7.54 + release note (58fbb326)
- test(v0.7.54): dispatcher test 4 신규 (okf-validate × 2 + cache-migrate + release-doctor) (cde0a45b)

## [0.7.53] - 2026-06-16

### Added

- feat(v0.7.53): mkdocs 셋업 (GH Pages in-repo, public-facing consumer guide) (fda611b6)
- feat(v0.7.53): workflow_kit_cli — okf-export / okf-import subcommand 추가 (a9109882)

### Changed

- docs(wiki): v0.7.53 release entry (3 follow-up: F dispatcher + G audit + H mkdocs) (4af30bb7)
- chore(v0.7.53): version bump 0.7.52 → 0.7.53 + release note (3d7e232e)
- test(v0.7.53): url_validity test file 추가 (12 test, audit 2차 갭 해소) (05629312)

## [0.7.52] - 2026-06-16

### Added

- feat(v0.7.52): cache analytics snapshot diff (1/1 PASS) (f4adf8cc)
- feat(v0.7.52): cache analytics alerting CLI (--alert, zero-dep, 2/2 PASS) (fbbd2549)

### Changed

- docs(wiki): v0.7.52 release cut supersedes prior audit decision (ee59070d)
- chore(v0.7.52): version bump 0.7.6 → 0.7.52 + release note (b0491d05)
- docs(v0.7.52): log entry for retrospective consolidation cleanup (ee63739c)
- refactor(v0.7.52): collapse 6 CLI modules into workflow_kit_cli dispatcher (6/6 PASS) (71bf15da)
- refactor(v0.7.52): inline v_r13_commit_diff_integration + v_r13_layer2_pipeline into v_r13_commit_diff (6/6 PASS) (25c7c1a9)
- refactor(v0.7.52): consolidate cache_dashboard_export into cache_dashboard module (87f77bdd)
- refactor(v0.7.52): remove v2/v3/v4/v5 federation module + test files (081b72cc)
- refactor(v0.7.52): consolidate phishing_federation_v2/v3/v4/v5 into one module (4/4 PASS) (0d5a2c73)

## [0.7.51] - 2026-06-16

### Added

- feat(v0.7.51): phishing federation v5 CLI (--federate-v5, 2/2 PASS, FREE tier) (85be71c0)
- feat(v0.7.51): cache dashboard export CLI (--dashboard-export --output=PATH, 2/2 PASS) (88106953)
- feat(v0.7.51): cache trend chart CLI (--trend-chart --snapshots=PATH, 2/2 PASS) (4c579adc)
- feat(v0.7.51): LFU decay score automatic aging (decay_age_scores, 2/2 PASS, no regression) (42475898)
- feat(v0.7.51): cache analytics threshold-based alerting (2/2 PASS) (51868363)

### Changed

- release(v0.7.51): cache alerting + decay aging + trend chart CLI + dashboard export CLI + federation v5 CLI (201/201 PASS, FREE tier) (22541e23)

## [0.7.50] - 2026-06-16

### Added

- feat(v0.7.50): LFU decay score CSV export/import (cross-process, 2/2 PASS, no regression) (17e9da96)
- feat(v0.7.50): phishing federation v5 (3 source weighted voting, FREE-tier 3rd source, 2/2 PASS) (5057e774)
- feat(v0.7.50): cache dashboard HTML export (2/2 PASS, no regression) (24939df2)
- feat(v0.7.50): cache trend ASCII chart (zero-dep visualization, 2/2 PASS) (7e41eaaf)
- feat(v0.7.50): V-R13 layer 2 CLI (one-call URL verification, 2/2 PASS) (5b6c6f62)

### Changed

- release(v0.7.50): layer 2 CLI + trend ASCII chart + dashboard HTML + federation v5 + decay CSV (191/191 PASS) (00d2de4e)

## [0.7.49] - 2026-06-16

### Added

- feat(v0.7.49): cache dashboard export (JSON + Markdown, 2/2 PASS) (5834a9a7)
- feat(v0.7.49): cache analytics trend (snapshot over time, 2/2 PASS) (00a255d4)
- feat(v0.7.49): V-R13 layer 2 full pipeline (one-call parse+dispatch+format, 2/2 PASS) (5726fc07)
- feat(v0.7.49): per-URL LFU decay score persistence (cache_lfu_decay_persist, 2/2 PASS) (d9e050be)
- feat(v0.7.49): phishing federation v4 (weighted voting, 2/2 PASS) (bd7c8cb3)

### Changed

- release(v0.7.49): federation v4 + decay persistence + layer 2 pipeline + cache trend + dashboard export (181/181 PASS) (4093fcc6)

## [0.7.48] - 2026-06-16

### Added

- feat(v0.7.48): CLI --cache-dashboard flag (cache_dashboard_cli module, 2/2 PASS) (83ee37a5)
- feat(v0.7.48): phishing federation v3 (cross-source verification, 2/2 PASS) (ffacc800)
- feat(v0.7.48): per-strategy cache dashboard (cache_dashboard module, 2/2 PASS) (6d9ca13d)
- feat(v0.7.48): LFUConfig + _save_cache full refactor (save_cache_lfu_decay_full, 2/2 PASS) (d27004f5)
- feat(v0.7.48): V-R13 layer 2 commit-level diff integration (2/2 PASS) (9461ed14)

### Changed

- release(v0.7.48): V-R13 commit diff integration + LFU full refactor + cache dashboard + federation v3 + CLI flag (171/171 PASS) (74e3d596)

## [0.7.47] - 2026-06-16

### Added

- feat(v0.7.47): per-strategy eviction trigger by size cap (evict_lru/lfu_over_size, 2/2 PASS) (1c928751)
- feat(v0.7.47): per-strategy cross-strategy analytics (cache_analytics module, 2/2 PASS) (90f83fb9)
- feat(v0.7.47): LFUConfig + _save_cache direct integration (cache_lfu_decay module, 2/2 PASS) (1a606eac)
- feat(v0.7.47): V-R13 layer 2 commit-level diff (cross-vendor, 2/2 PASS) (75be24c9)

### Changed

- release(v0.7.47): V-R13 commit diff + LFU decay + ADR formal + analytics + eviction trigger (159/159 PASS) (a4e1522c)
- docs(v0.7.47): ADR-023/024/025 revision log v0.2.1 (1 release cycle 운영 evidence) (14753748)

## [0.7.46] - 2026-06-16

### Added

- feat(v0.7.46): multi-source phishing federation v2 (extensible, 2/2 PASS) (e7a5919a)
- feat(v0.7.46): Bitbucket v2 API commit history support (2/2 PASS) (cff0f2c4)
- feat(v0.7.46): LFUConfig + temporal decay integration (4/4 PASS) (d5b1ddc5)
- feat(v0.7.46): per-strategy cache size comparison (2/2 PASS) (0dffe7fe)

### Changed

- release(v0.7.46): CLI test fix + cache size + LFU decay + Bitbucket v2 + federation v2 (149/149 PASS) (92d9c2d0)
- test(v0.7.46): CLI --per-strategy + --cache-stats-strategy flag tests (2/2 PASS) (f4f02000)

## [0.7.45] - 2026-06-16

### Added

- feat(v0.7.45): CLI --per-strategy + --cache-stats-strategy flags (V-R10 v4) (c01d4f64)
- feat(v0.7.45): cache_stats_per_strategy_with_hit_rate (39/39 PASS) (1fde081a)
- feat(v0.7.45): LRU/LFU split in cache_migration (split_to_per_strategy, 2/2 PASS) (5073cf74)
- feat(v0.7.45): multi-source phishing federation (PhishTank + OpenPhish, 2/2 PASS) (6533a4db)

### Changed

- release(v0.7.45): multi-source phishing federation + LRU/LFU split + hit rate + CLI --per-strategy (137/137 PASS) (43a03227)
- docs(v0.7.45): OKF quick-start walkthrough output examples + verification table (227e1e8e)

## [0.7.44] - 2026-06-16

### Added

- feat(v0.7.44): cache_migration module (migrate v0.7.41 -> per-strategy, 1/1 PASS) (67265778)
- feat(v0.7.44): OpenPhish API integration (fetch_openphish_feed, 2/2 PASS) (27793aff)
- feat(v0.7.44): lfu_integration module (LFUConfig + _save_cache, 2/2 PASS) (8eb116cc)

### Changed

- release(v0.7.44): ADR-025 formal + OKF quick-start + LFUConfig + OpenPhish + cache migration (134/134 PASS) (d107dd38)

## [0.7.43] - 2026-06-16

### Added

- feat(v0.7.43): lfu_config module (V-R10 v3 LFU threshold tuning, 2/2 PASS) (53f774a8)
- feat(v0.7.43): cache_stats_per_strategy (cross-strategy compare, 39/39 PASS) (e289b198)
- feat(v0.7.43): PhishTank API integration (fetch_phishtank_feed, 13/13 PASS) (df088ee8)

### Changed

- release(v0.7.43): ADR-023/024 formal + ADR-025 quick-start draft + PhishTank API + cache_stats_per_strategy + lfu_config (129/129 PASS) (62a6507a)

## [0.7.42] - 2026-06-16

### Added

- feat(v0.7.42): per-strategy cache file (cache_file_for_strategy helper, 38/38 PASS) (e80cca83)
- feat(v0.7.42): R-2 audit precise (git log --oneline, 16/16 PASS) (386d68ce)
- feat(v0.7.42): V-R13 check 5 per-host extension (GitLab + Bitbucket API, 25/25 PASS) (64ca96c5)

### Changed

- release(v0.7.42): ADR-023/024 formal + V-R13 per-host + V-R12 composite + R-2 audit precise + per-strategy cache (124/124 PASS) (f592bff8)
- test(v0.7.42): V-R12 layer 1+2 composite URL emission (18/18 PASS) (77b0b873)

## [0.7.41] - 2026-06-16

### Added

- feat(v0.7.41): V-R12 composite layer 1+2 verification (check_url_semantic_composite, 23/23 PASS) (6a480aca)
- feat(v0.7.41): R-2 batch compliance audit (audit_r2_batch_history, 15/15 PASS) (a595fbb4)
- feat(v0.7.41): V-R10 v3 per-strategy eviction metric (evictions_lru/evictions_lfu, 36/36 PASS) (46b6b7ab)
- feat(v0.7.41): V-R13 ?range=A..B commit-level diff (git diff subprocess, 21/21 PASS) (6fcda94b)

### Changed

- release(v0.7.41): ADR-020/021/022 formal + V-R13 range diff + per-strategy metric + R-2 audit + V-R12 composite (118/118 PASS) (62d6e9a7)

## [0.7.40] - 2026-06-16

### Added

- feat(v0.7.40): R-2 batch compliance warning (5-15 page heuristic, 14/14 PASS) (85ecff60)
- feat(v0.7.40): CLI --semantic/--perform-head/--perform-github flags (18/18 PASS) (f4cf9090)
- feat(v0.7.40): okf_export per-page ?range=<sha>..<sha> emission (V-R12 layer 2, 17/17 PASS) (e365168a)
- feat(v0.7.40): V-R13 full 8/8 check (HEAD + GitHub API, 16/16 PASS) (7c69789f)

### Changed

- release(v0.7.40): ADR-021/022 formal + V-R13 full 8/8 + V-R12 layer 2 + R-2 batch (110/110 PASS) (b98e1eb3)

## [0.7.39] - 2026-06-16

### Added

- feat(v0.7.39): okf_export per-page ?hash=sha256:... emission (ADR-019 layer 1, 16/16 PASS) (dd8c177d)
- feat(v0.7.39): phishing_keywords module + 11 tests (V-R11 v2 PoC, 11/11 PASS) (e1904fd6)
- feat(v0.7.39): LFU eviction strategy + access_count tracking (34/34 PASS) (eab4d2e1)
- feat(v0.7.39): check_url_semantic() PoC (6/8 check, 13/13 PASS) (563ac5c9)

### Changed

- release(v0.7.39): V-R13 PoC + LFU cache + PhishTank + V-R12 carrier (102/102 PASS) (863c3b6e)

## [0.7.38] - 2026-06-16

### Added

- feat(v0.7.38): _CacheLock stale lock file orphan cleanup (32/32 PASS) (9f622d3c)
- feat(v0.7.38): cache gzip compression (4KB threshold, 31/31 PASS) (2e1a541c)
- feat(v0.7.38): okf-bundle.yaml emit (per-bundle vcs_commit + integrity_hash, 15/15 PASS) (c3a0f240)
- feat(v0.7.38): _CacheLock timeout + advisory wait (30/30 PASS) (fbf93b58)
- feat(v0.7.38): per-page frontmatter vcs_commit + vcs_ref (12/12 PASS) (96b6ef04)
- feat(v0.7.38): cache_stats session evictions + last_eviction_timestamp (29/29 PASS) (d06053a6)

### Changed

- release(v0.7.38): V-R13 formal + okf-bundle.yaml + cache gzip + lock orphan + OKF consumer guide (a04cf567)

## [0.7.37] - 2026-06-16

### Added

- feat(v0.7.37): okf_export vcs_commit integration (ADR-018, 11/11 PASS) (2eac0d3a)
- feat(v0.7.37): --body CLI flag + --timeout flag (28/28 PASS) (1da10efa)
- feat(v0.7.37): cache_stats() extension (bytes + evictions_total, 27/27 PASS) (8e88b47f)
- feat(v0.7.37): V-R12 commit-pinned URL (ADR-018 + 3 new tests, 9/9 PASS) (7aec7cf6)
- feat(v0.7.37): V-R11 body content audit (ADR-017 + 5 new tests, 27/27 PASS) (9ec0aad1)
- feat(v0.7.37): GHA actions/cache for cross-PR cache (ADR-016) (6a622ee0)
- feat(v0.7.37): V-R10 v3 file lock (ADR-015 + 2 new tests, 22/22 PASS) (735beac6)
- feat(v0.7.37): V-R10 v3 cache LRU (ADR-014 + 4 new tests, 20/20 PASS) (3349e792)

### Changed

- ci(v0.7.37): --body + --vcs-commit CI integration (f1a7bd39)

## [0.7.36] - 2026-06-16

### Added

- feat(v0.7.36): V-R10 v2 cache (ADR-013 + 4 new tests, 16/16 PASS) (5fec6646)

### Changed

- chore(v0.7.36): version bump v0.7.35 to v0.7.36 + log entry for follow-up bundle (208042dd)
- ci(v0.7.36): .github/workflows/okf-validate.yml (V-R10 online + cache + weekly cron) (c26349f9)

## [0.7.35] - 2026-06-16

### Added

- feat(v0.7.35): V-R10 online HEAD layer (ADR-012 + 6 new tests, 12/12 PASS) (515a352b)
- feat(v0.7.35): ADR-011 + OKF version auto-detect (5 new tests, 12/12 PASS) (e0f2ffc7)
- feat(v0.7.35): ADR-010 + V-R10 URL validity lint (offline 8 check, 6/6 PASS) (077b5a44)

## [0.7.34] - 2026-06-16

### Added

- feat(v0.7.34): bundle root index.md auto-emit + test 10 (10/10 PASS) (2fb014e9)
- feat(v0.7.34): ADR-008 accepted + path_resolver.py PoC + okf_export --no-resolve (24f85898)
- feat(v0.7.34): ADR-007 accepted + workflow_kit/okf_import.py PoC (7/7 PASS) (9e8b06d2)

## [0.7.33] - 2026-06-16

### Added

- feat(v0.7.33): TASK-V0733-001 atomic rotation (3-step crash safety) + TASK-V0734-001 yearly aggregation + 10 smoke (5-run stable) (9648a6e9)

### Changed

- chore(v0.7.33): version bump 0.7.32 → 0.7.33 (auto-sync verified) + Beta-v0.7.33.md + state/work_backlog sync (f3ef05bc)
- chore(v0.7.33): ADR-006 accepted + Beta-v0.7.33 release note + version bump (00942eff)

### Fixed

- fix(state): v0.7.33 2nd hash sync (1c8d54b8)

## [0.7.32] - 2026-06-16

### Added

- feat(v0.7.32): TASK-V0731-001 log rotation + TASK-V0732-001 metrics aggregation + 10 smoke (5-run stable) (75a8b4c4)

### Changed

- chore(v0.7.32): version bump 0.7.31 → 0.7.32 (auto-sync verified) + Beta-v0.7.32.md + state/work_backlog sync (ec723607)

### Fixed

- fix(state): v0.7.32 2nd hash sync (1348a3cf)

## [0.7.31] - 2026-06-16

### Added

- feat(v0.7.31): TASK-V0729-001 run-time metrics + TASK-V0730-001 install-cron idempotency + 10 smoke (a9b510e4)

### Changed

- chore(v0.7.31): version bump 0.7.30 → 0.7.31 (auto-sync verified) + Beta-v0.7.31.md + state/work_backlog sync (6732f488)

### Fixed

- fix(state): v0.7.31 2nd hash sync (fae91573)

## [0.7.30] - 2026-06-15

### Added

- feat(v0.7.30): TASK-V0728-001 archive_stale_memory cron integration (mavis cron create/disable/list) + 5 smoke (57d996db)

### Changed

- chore(v0.7.30): version bump 0.7.29 → 0.7.30 (auto-sync verified) + Beta-v0.7.30.md + state/work_backlog sync (23a20781)

### Fixed

- fix(state): v0.7.30 2nd hash sync (264ab5c9)

## [0.7.29] - 2026-06-15

### Added

- feat(v0.7.29): TASK-V0727-001 post-step 2-phase + amend integration (1 commit 통합, 33% 감소) + 5 smoke (850b7989)

### Fixed

- fix(state): v0.7.29 backlog = 2ee6dbf (본 release 의 fix(state) hash, v0.7.21 정공법) (fda9379f)
- fix(state): v0.7.29 2nd hash sync (68309937)
- fix(v0.7.29): rev-parse 2-step fix (full SHA → short=7) + state.json + backlog 정합 (2ee6dbf4)

## [0.7.28] - 2026-06-15

### Added

- feat(v0.7.28): TASK-V0726-004 detached HEAD memory dir age-based auto-archive + 5 smoke (b1b32f10)

### Fixed

- fix(state): v0.7.28 squash + state.json + backlog = chore commit hash (7bb6259, v0.7.21 정공법) (ca7d385f)

## [0.7.27] - 2026-06-15

### Added

- feat(v0.7.27): TASK-V0726-003 sync_release_hash post-step (release_pipeline.py version-bump auto-call) + 5 smoke (2aa1efa2)

### Fixed

- fix(state): v0.7.27 version-bump + state.json 정합 (v0.7.21 정공법, 2aa1efa = 본 release 의 feat commit) (66c18e7a)
- fix(state): v0.7.27 squash + 본 release 의 본 release 의 hash 정합 (v0.7.21 정공법, 2aa1efa = feat commit) (8ef94d61)

## [0.7.26] - 2026-06-15

### Added

- feat(v0.7.26): F-7 branch detection (detached HEAD → 7-char SHA) + F-7+ automated hash sync (infinite fix(state) loop 회피) + 10 smoke (e5fbd2b6)

### Changed

- chore(v0.7.26): version bump 0.7.25 → 0.7.26 (auto-sync verified) + Beta-v0.7.26.md + state/work_backlog sync (ecb6ce1b)

### Fixed

- fix(state): v0.7.26 squash + 본 release 의 본 release 의 hash 정합 (v0.7.21 정공법, ecb6ce1 = chore commit) (94136978)

## [0.7.25] - 2026-06-15

### Added

- feat(v0.7.25): tools/migrate_legacy_l2.py (F-6 closure, 15 legacy L2 page → in-repo mirror) + 5 smoke (8a61bd34)

### Changed

- chore(v0.7.25): version bump 0.7.24 → 0.7.25 (auto-sync verified) + Beta-v0.7.25.md + state/work_backlog sync (96a919d7)

### Fixed

- fix(state): v0.7.25 본 release hash (96a919d) 로 정합 (v0.7.21 정공법) (00e7ca88)
- fix(state): v0.7.25 hash 동기화 (squash 8 commits → 1) (2f5945db)

## [0.7.24] - 2026-06-15

### Added

- feat(v0.7.24): cmd_release --notes-template flag (5 template: default/detailed/simple/changelog/custom) + 5 smoke (1dfa8fb5)

### Changed

- chore(v0.7.24): version bump 0.7.23 → 0.7.24 (auto-sync verified) + Beta-v0.7.24.md + state/work_backlog sync (2c38d070)

### Fixed

- fix(state): v0.7.24 backlog.commit 을 fix(state) hash(ef13691) 로 동기화 (6e302c14)
- fix(state): v0.7.24 chore commit hash 동기화 (e802e56 → 2c38d07 amend 후 hash) (ef136910)

## [0.7.23] - 2026-06-15

### Added

- feat(v0.7.23): tools/wiki_emit.py 1-command wrapper (3-step cycle: refresh_raw + emit_l2 + reemit_stubs) + 5 smoke (b4936a27)

### Changed

- chore(v0.7.23): version bump 0.7.22 → 0.7.23 (auto-sync verified) + Beta-v0.7.23.md + state/work_backlog sync (8e339402)

### Fixed

- fix(state): v0.7.23 chore commit hash 동기화 (98442d12)

## [0.7.22] - 2026-06-15

### Changed

- chore(v0.7.22): version bump 0.7.21 → 0.7.22 (auto-sync verified) + Beta-v0.7.22.md + state/work_backlog sync (2d3cdbcb)

### Fixed

- fix(state): v0.7.22 chore commit hash 동기화 (8b02fe97)
- fix(v0.7.22): workflow_kit/common/linter.py .resolve() → .absolute() (mavis data dir 격리 환경 + macOS /var symlink fix) + 3 smoke (3c129502)

## [0.7.21] - 2026-06-15

### Changed

- chore(v0.7.21): version bump 0.7.20 → 0.7.21 (auto-sync verified) + Beta-v0.7.21.md + state/work_backlog sync (f014d59e)

### Fixed

- fix(state): v0.7.21 chore commit hash 동기화 (amend 후 hash drift 보정) (fa329b11)
- fix(v0.7.21): cmd_release --allow-existing-tag flag + tag push 자동화 (pre-check + release coupling) (0ef97db4)

## [0.7.20] - 2026-06-15

### Changed

- chore(v0.7.20): Beta-v0.7.20.md release note (release coordination observability + auto-bump chain) (57586577)
- chore(v0.7.20): version bump 0.7.19 → 0.7.20 (auto-bump chain) (556eb04b)

## [0.7.19] - 2026-06-15

### Changed

- chore(v0.7.19): version bump 0.7.18 → 0.7.19 (release coordination auto-bump) (8ada0f19)

## [0.7.18] - 2026-06-15

### Added

- feat(v0.7.18): release coordination observability (_check_remote_tag + next_available_version + --auto-bump) + 7 smoke (07bf145d)

### Changed

- chore(v0.7.18): version bump 0.7.17 → 0.7.18 (auto-sync verified) + Beta-v0.7.18.md + state/work_backlog sync (46066c3d)

## [0.7.17] - 2026-06-15

### Added

- feat(v0.7.17): wiki in-repo storage isolation (5 file redirect + ai-workflow/wiki/sources/ 신규 + 11 smoke) (6f6f1af2)

### Changed

- chore(v0.7.17): version bump 0.7.16 → 0.7.17 (auto-sync verified) + Beta-v0.7.17.md + state/work_backlog sync (4d09dee0)

## [0.7.16] - 2026-06-15

### Added

- feat(v0.7.16): [tool.workflow-doctor] config thresholds/excluded_paths 적용 (B-1/B-2/B-3) + linter IndentationError fix + 9 smoke (33f52431)

### Changed

- chore(v0.7.16): version bump 0.7.15 → 0.7.16 (auto-sync verified) + Beta-v0.7.16.md + state/work_backlog sync (f0126019)

## [0.7.15] - 2026-06-15

### Added

- feat(v0.7.15): atomic_write helper + changelog-gen --from-tag/--to-tag filter + 5 smoke (8d7acc4a)
- feat(v0.7.15): atomic_write helper + changelog-gen --from-tag/--to-tag filter + 5 smoke (5cd1fe11)

### Changed

- merge: v0.7.15 fix 3 commit (Beta-v0.7.15.md commit table 정합) + v0.7.16 작업 보존 (d9f1866d)
- chore(v0.7.15): version bump 0.7.14 → 0.7.15 (auto-sync verified) + Beta-v0.7.15.md (0dc813a5)
- chore(v0.7.15): state sync (atomic_write 적용) + 1 daily backlog (30496514)
- chore(v0.7.15): version bump 0.7.14 → 0.7.15 (auto-sync verified) + Beta-v0.7.15.md (a369e7c9)

### Fixed

- fix(v0.7.15): Beta-v0.7.15.md Commit table 정상화 (Deferred 표에서 중복 row 제거 + 4 commit hash) (68b0ae9d)
- fix(v0.7.15): Beta-v0.7.15.md Commit section + 3 commit hash (3dfb5a1d)

## [0.7.14] - 2026-06-15

### Added

- feat(v0.7.14): cmd_version_bump auto-sync workflow_kit/__init__.py + cmd_changelog_gen subcommand + 8 smoke (23eb7fd0)

### Changed

- chore(v0.7.14): version bump 0.7.13 → 0.7.14 (auto-sync verified) + Beta-v0.7.14.md + CHANGELOG.md + state/work_backlog sync (63ab483c)

### Fixed

- fix(v0.7.14): Beta-v0.7.14.md Commit + Reference section 정상화 (line 정렬 + 헤더) (29af65d8)
- fix(v0.7.14): Beta-v0.7.14.md commit table TBD → 23eb7fd + 63ab483 (a01c7b41)

## [0.7.13] - 2026-06-15

### Added

- feat(v0.7.13): cmd_release --version flag (staging backfill, pyproject 일시 patch 불필요) (922ebc08)

### Changed

- chore(v0.7.13): state sync (v0.7.12 + v0.7.13 backfill) + 2 daily backlog (afc685a1)
- chore(v0.7.13): version bump 0.7.11 → 0.7.13 + __version__ sync + Beta-v0.7.13.md (628bf934)

### Fixed

- fix(v0.7.13): Beta-v0.7.13.md Commit section + 3 commit hash (727c59cc)

## [0.7.12] - 2026-06-15

### Added

- feat(v0.7.12): refresh_wiki_memory REPO_ROOT auto-detect (CLI flag > env var > git rev-parse > legacy fallback) + 4 smoke (63080baa)

### Changed

- chore(v0.7.12): v0.7.5~v0.7.10 release backfill (6 wheel/sdist + 6 git tag + 6 GH release) + Beta-v0.7.12.md 갱신 (89b7af5e)

### Fixed

- fix(v0.7.12): Beta-v0.7.12.md commit table TBD → 89b7af5 (5b8e7301)
- fix(v0.7.12): Beta-v0.7.12.md commit table TBD → 63080ba (0b3e7040)

## [0.7.11] - 2026-06-15

### Added

- feat(v0.7.11): release_pipeline Phase 3 (dist subcommand) + state sync + 8 smoke (b2650f54)

### Changed

- chore(v0.7.11): version bump 0.7.10 → 0.7.11 + __version__ sync (ec407f1a)

### Fixed

- fix(v0.7.11): cmd_verify --json field names (tag → tagName, createdAt → publishedAt) + release note commit table (aa4e8379)

## [0.7.10] - 2026-06-14

### Added

- feat(v0.7.10): release_pipeline Phase 2 (release / verify / rollback) + 8 smoke test (fdf8159a)

### Changed

- docs(v0.7.10): release note backfill + refresh_wiki_memory v0.7.10 tracking (fc87fddf)
- chore(v0.7.10): version bump 0.7.9 → 0.7.10 + release note (67d4a37a)

## [0.7.9] - 2026-06-14

### Added

- feat(v0.7.9): release_pipeline tool 정식화 (validate / version-bump / note-draft) + 8 smoke test (cb0a8922)

### Changed

- docs(v0.7.9): release note backfill + refresh_wiki_memory v0.7.9 tracking (283823ed)
- chore(v0.7.9): version bump 0.7.8 → 0.7.9 + release note (d39be44f)

## [0.7.8] - 2026-06-14

### Added

- feat(v0.7.8): refresh_wiki_memory 에 v0.7.8 release tracking 추가 (662bead8)
- feat(v0.7.8): state-aware evaluate_compliance + config actual apply (d3235adc)

### Changed

- docs(v0.7.8): release note commit hash backfill (b67af83) (f444e688)
- chore(v0.7.8): version bump 0.7.7 → 0.7.8 + release note (b67af835)

## [0.7.7] - 2026-06-14

### Added

- feat(v0.7.7): refresh_wiki_memory 에 v0.7.7 release tracking 추가 (fd182882)
- feat(v0.7.7): workflow_kit.cli.doctor 에 load_config + should_fail integration (022672f3)

### Changed

- docs(v0.7.7): release note commit hash backfill (3300e73) (7581dd23)
- chore(v0.7.7): version bump 0.7.6 → 0.7.7 + release note (3300e73c)

## [0.7.6] - 2026-06-14

### Added

- feat(v0.7.6): refresh_wiki_memory 에 v0.7.6 release tracking 추가 (1fefdfdb)
- feat(v0.7.6): workflow_kit.metadata (pyproject.toml [tool.workflow-doctor] loader) + 10 smoke test (0daf6da9)
- feat(v0.7.6): run_all_checks 통합 runner + 10 smoke test (53d5dc89)

### Changed

- docs(v0.7.6): release note commit hash backfill (b9ede19) (7a5c56ea)
- chore(v0.7.6): version bump 0.7.5 → 0.7.6 + release note (b9ede19e)

## [0.7.5] - 2026-06-14

### Added

- feat(v0.7.5): refresh_wiki_memory 에 v0.7.5 release tracking 추가 (150ee320)
- feat(v0.7.5): refresh_wiki_memory tool 정식화 + 10 smoke test (Wiki 운영 자동화) (0741775e)

### Changed

- docs(v0.7.5): release note commit hash backfill (c2a75f8) (51edde58)
- chore(v0.7.5): version bump 0.7.4 → 0.7.5 + release note (c2a75f87)
- test(v0.7.5): 4 sub-cat dispatcher runtime test 보강 (12 → 16) (9e1f206c)

## [0.7.4] - 2026-06-13

### Added

- feat(v0.7.4): CLI wrapper (workflow doctor) + @graceful_shutdown + optional dep (hypothesis/objgraph) (22e77508)

### Changed

- chore(v0.7.4): score history v0.7.4 entry (Overall 4.67 A 유지) (cfb09fb1)
- docs(v0.7.4): wiki log v0.7.4-beta entry 추가 (1818dd64)

## [0.7.3] - 2026-06-13

### Added

- feat(v0.7.3): 4 runtime helper (auth/testing/profiling/resiliency) + 7 baseline dispatcher (d03348a2)

### Changed

- chore(v0.7.3): score history v0.7.2/v0.7.3 entry 추가 (Overall 4.66→4.67 A 유지) (c732c0fb)
- docs(v0.7.3): wiki log v0.7.3-beta entry 추가 (be49e0fb)

## [0.7.2] - 2026-06-13

### Added

- feat(v0.7.2): Extension sub-cat + 4종 (resiliency) 본 구현 (179 test PASS) (3bffba30)

### Changed

- docs(v0.7.2): wiki log commit hash TBD → 3bffba3 갱신 (7cae4961)

## [0.7.1] - 2026-06-13

### Added

- feat(v0.7.1): follow-up 4건 + wiki 개선 4건 묶음 (158 test PASS, GH release) (f09034dc)

### Changed

- docs(v0.7.1): wiki log commit hash TBD → 0224a76 갱신 (9935e06c)
- docs(v0.7.1): wiki log commit hash TBD → 99e299f 갱신 (d8c981cd)
- docs(v0.7.1): wiki log commit hash TBD → f09034d 갱신 (bad14d8a)

## [0.7.0] - 2026-06-13

### Changed

- docs(v0.7.0): wiki log commit hash TBD → c72bdc3 갱신 (bdc6ceb1)
- docs(v0.7.0): wiki log commit hash TBD → 49dfc78 갱신 (471fee2c)
- docs(v0.7.0): wiki log commit hash 갱신 TBD-pending → 7a4dbae (b3759519)
- docs(v0.7.0): wiki log commit hash TBD → 021ec16 갱신 (ac75d720)
- docs(wiki): v0.7.0 5 concept page + L2 emit helper + drift smoke test (021ec16c)
- docs(v0.7.0): wiki log entry header 에 commit hash 7자 prefix 명시 (3fcd4807)
- docs(v0.7.0): release note follow-up section 추가 (Task 3+2+1) (8818cbe3)
- chore(v0.7.0): version bump 0.6.3 → 0.7.0 (390a6e07)
- docs(v0.7.0): Release notes + wiki log entry (15 commit, ~3,200 line, 130 test PASS) (dff0aaec)
- wiki: v0.7.0 step 9 — Unit of Work 3-layer template (17 test PASS) (b7641e31)
- wiki: v0.7.0 step 10 — Audit Log 표준화 (1 spec + 1 helper fix + 13 test) (2458cf8c)
- wiki: v0.7.0 step 1 — stage_completion required 격상 (8 test PASS) (6148c0f8)

## [0.6.6] - 2026-06-12

### Added

- feat(v0.6.6): 5 SKILL.md-only skill runtime 통합 (12/12 spec+runtime 일관성) (6a9126c4)

### Changed

- wiki: v0.6.6 follow-up #1 — 5 SKILL.md-only skill runtime (12/12 일관성) (8ae91027)

## [0.6.5] - 2026-06-12

### Added

- feat(v0.6.5): batch stage_completion integration — 6 spec 보유 skill (10/11 완료) (ca7a6853)
- feat(v0.6.5): pilot stage_completion integration — automated-repro-scaffold (2fab8356)
- feat(v0.6.5): Stage Gate Runtime helper + migration guide (3 file, 13 test PASS) (dd98e699)
- feat(v0.6.5): StageCompletion field 11종 skill spec + catalog 보강 (13 file) (5b165170)

### Changed

- wiki: v0.6.5 release — AIDLC 패턴 차용 (10 commit, ~2,600 line) (46e4d1f5)
- release(v0.6.5): AIDLC 패턴 차용 (Question File Format + Stage Gate) (3897da7b)
- wiki: v0.6.5 batch runtime — 6 spec stage_completion (10/11, +72 line) (0ae8d4ab)
- wiki: v0.6.5 pilot runtime — automated-repro-scaffold stage_completion (1/11, +44 line) (fbe96730)
- wiki: v0.6.5 runtime — stage-gate-pattern §12 + log entry (35 test PASS) (fbc8370f)
- wiki: v0.6.5 — stage-gate-pattern §8 + log entry (StageCompletion 11종 적용 추적) (0001782b)

## [0.6.4] - 2026-06-12

### Added

- feat(v0.6.4): Question Format + Stage Gate 코드 (2 module + 2 smoke test) (bc16d914)
- feat(v0.6.4): Question File Format + Stage Gate 명시화 (4 doc) (25756bb1)

### Changed

- wiki: v0.6.4 신규 concept 2종 (Question File Format + Stage Gate Pattern) (d32226be)

### Fixed

- fix(v0.6.4): V-R9 skip marker — naive grep false-positive 17 → 0 (30183c51)

## [0.6.3] - 2026-06-12

### Added

- feat(v0.6.3): P4 memory/log.md + harness overlay consistency check (3261e20e)

### Changed

- release(v0.6.3): final v0.6.x series release — all 4 milestones complete (19237058)

### Fixed

- fix(v0.6.3): P6 phase-6 backfill — INGEST_GUIDE path 정정 + log 보강 (1d7ca77b)
- fix(v0.6.3): broken relative links after memory/active/ rename + fix bootstrap test leniency (6b2bf005)

## [0.6.2] - 2026-06-12

### Added

- feat(v0.6.2): P3 T2 work_backlog anchor + T3 ingest atomicity (2713059e)

## [0.6.1] - 2026-06-12

### Added

- feat(v0.6.1): P2 R8 freeze + R10 freeze lint + T1 memory lint 4종 + R7 merge-res ext (06203737)

## [0.5.11] - 2026-06-09

### Added

- feat(v0.5.11): Mavis engine hook (§6.5) + 회귀 test 강화 (4ce36353)

### Changed

- docs(v0.5.11): Beta-v0.5.11.md release note — 릴리스 일자 표현 정정 (5bd4c4f1)
- chore(v0.5.11): bump version to 0.5.11-beta (cfde435f)
- docs(v0.5.11): Beta-v0.5.11 release note (cb0f6986)
- docs(v0.5.11): governance 갱신 — 1인 dev 환경, 24h cool-down 명시 (c89971dd)
- docs(v0.5.11): --no-interactive 비대화형 가이드 보강 (7329dbe2)

### Fixed

- fix(v0.5.11): bootstrap MCP env — wheel install 시 PYTHONPATH omit (e388366f)
- fix(v0.5.11): MCP initialize response — protocolVersion 추가 (677bcff3)

## [0.5.10] - 2026-06-08

### Fixed

- fix(v0.5.10): choose_roles sub.delegation_id parent-prefix spec 정합 (8359cfc0)

## [0.5.9] - 2026-06-08

### Changed

- docs(v0.5.9): wire 가이드 §7/§8/§9 보강 — sub.delegation_id parent prefix 룰 명시 (1006ff0c)

## [0.5.8] - 2026-06-08

### Added

- feat(v0.5.8): interactive --harness picker + packaging smoke automation (6213dcc8)

## [0.5.7] - 2026-06-08

### Added

- feat(v0.5.7): contract v1 §4.2/§5.2 multi-component fan-out/in + §6.3 cross-ref row (#21) (ebf7e7c2)

## [0.5.6] - 2026-06-07

### Added

- feat(v0.5.6): contract v1 §5/§6 P0 enforcement (validator + delegator) (#20) (79f3bec2)

### Changed

- docs(v0.5.6): mark TASK-V056-001 done post-merge (731787b5)

## [0.5.5] - 2026-06-07

### Added

- feat(v0.5.5): Phase 11 본격 pilot (Devhub Example × Contract v1) (#19) (1f095ec5)

### Changed

- docs(v0.5.5): mark TASK-V055-001 done post-merge (75a3fc6c)

## [0.5.4] - 2026-06-07

### Added

- feat(v0.5.4): orchestrator ↔ sub-agent delegation contract v1 (closes #1) (#18) (7737e141)

## [0.5.3] - 2026-06-07

### Added

- feat(v0.5.3): antigravity MCP config 표준화 + cross-language stack 표시 (#17) (b6ae73aa)

### Changed

- docs(v0.5.3): mark tasks done + release notes for Beta v0.5.3 (a961fa04)

## [0.5.2] - 2026-06-06

### Changed

- refactor(v0.5.2): bootstrap_workflow_kit.py → bootstrap_lib/ 6-module package (#16) (9497a357)

## [0.5.1] - 2026-06-06

### Added

- feat(v0.5.1): end-to-end MCP round-trip smoke (#15) (73f8f2fa)
- feat(v0.5.1): per-harness MCP install + auto-emit + guide (#14) (c3c9a90c)
