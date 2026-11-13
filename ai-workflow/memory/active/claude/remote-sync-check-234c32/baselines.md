# Baselines (rolled off)

- 문서 목적: `session_handoff.md` §1 에서 롤오프된 기준선 줄을 이력으로 보존한다.
- 범위: 과거 세션의 기준선 산문 (최신이 위)
- 대상 독자: AI agent, 저장소 관리자
- 상태: append-only
- 관련 문서: [session_handoff.md](./session_handoff.md)

> 이 파일은 **읽기 대상이 아니라 조회 대상**이다. 세션 시작에 읽지 않는다 —
> handoff §1 이 최근 4개만 들고 있고, 그 이전이 필요할 때만 여기를 본다.

## 롤오프 2026-11-13

- **124차 세션 (2026-11-12, Linux 호스트, 같은 브랜치를 checkout) — M-023 requirements 종결.** [`claim-plan-requirements-2026-11.md`](../../../../../docs/planning/claim-plan-requirements-2026-11.md) — 실측 3건(옛 리더는 모르는 `- Claims:` · `- Decisions:` 줄을 무시 · 보존 → 리더 · 라이터 같은 릴리스 / 주장 80자 / 응답 64KiB) + 요구 사항 R0~R13, 소유자 sign-off **Q1~Q7 전부 권고안** (문서 §12). 핵심: 결정 상태 = 보관된 응답 집합 + `answered` 기록의 함수(순서 무관 · 멱등), 다른 approver 의 반대는 `disputed` 로 결정을 다시 연다, 게이트는 상태 칸이 아니라 계산값으로 판정, 받은편지함은 gitignore. task -005 done (verifier 9회 — 기준 4 가 R6.3 에서 2~8차 매회 1건 FAIL → 수리, 9차 5/5 PASS). M-023 done · **M-026 [design] planned** (M-025 뒤). roadmap issues [].

## 롤오프 2026-11-13

- **123차 세션 (2026-11-12, macOS 호스트, worktree `claude/remote-sync-check-234c32`) — html-plan 개념 흡수 concept 종결.** 원격 동기화 확인(`origin/main@826af874` 와 동일) → 새 마일스톤 **M-022 [concept]** 선언 + TASK-…-002 (M-022/WBS-22.1) → concept 문서 [`html-plan-absorption-review-2026-11.md`](../../../../../docs/planning/html-plan-absorption-review-2026-11.md) 작성 (Anthropic 커뮤니티 html-plan 1.0.0 실측 · 안 A task Plan 주장·결정 계약 · 안 B plan-export/plan-import 브리지 · 소유자 선택지 D1~D5). **소유자 결정 = §7 기본값 D1~D5 전부 (문서 §10)** → M-022 done · **M-023 [requirements] planned** 선언 · 이어서 **M-024 워크벤치 concept 종결(W1~W5) → M-025 planned**, 하네스 중립 지시로 M-022 안 B 정정 · task -002 · -003 done (verifier 4/4 PASS). roadmap issues []. 두 수리(seed T1d · worktree check_docs)를 코드만 흡수 → 전량 게이트 native·slash 309×2 green → push (`origin/claude/remote-sync-check-234c32`).

## 롤오프 2026-11-13

- claude/remote-sync-check-234c32 워크스페이스 — `main@826af874` 에서 이어받음 (2026-11-12). 이 브랜치의 작업은 아직 없다. 모 브랜치 기준선: **122차 세션 (2026-10-31, Windows 호스트 DESKTOP-DGPLBF7) — v1.22.0 발행 완료 (minor: feat 1 · fix 3 · breaking 0).** main 은 `v1.22.0` 태그 커밋 `a44b7d31` + 발행 완료 커밋 — **origin/main 에 push 완료**, GitHub Release `v1.22.0` 생성(draft=false · prerelease=false) · asset 5종(whl · sdist · claude-code · codex · minimax-code plugin ZIP). **저장소에서 처음 시도한 Windows 발행**이라 발행 경로 격차가 2건 더 드러났다 — ①**pre_check `packaging`** — 임시 venv 의 `pip` 를 `venv/bin/pip` 로 고정(Windows 는 `Scripts/pip.exe`) → FileNotFoundError ②같은 자리에서 `pip.exe install --upgrade pip` 이 Windows venv 에서 자기수정을 거부 → `python -m pip` 로 교체. `common/paths.py` 에 `venv_executable()` 정본 신설(복제돼 있던 POSIX 고정 3곳 정리). 추가로 **서브프로세스 `text=True` encoding 누락 10곳**(별칭 호출로 앞선 수리가 놓쳤던 것) 과 **drift_ledger append 의 CRLF** 수리. 전량 게이트 native·slash 309×2 rc 0(증거 `a44b7d31…json` · 커밋 후 clean tree) · mypy 227 files 0 errors · packaging 사전점검 PASS(1.22.0 휠을 Windows 임시 venv 에 심어 13 서브패키지 import smoke). **미해결**: ①**POSIX(Linux/macOS) 회귀 게이트는 이 호스트에서 돌릴 수 없다** — 309×2 는 별도 호스트 확인 필요 ②해석기 매트릭스 3.11 셀 UNMEASURED(해석기 미설치) ③case 수 선언 대조 75건 미측정 ④§2.8 소비채널 재적용은 발행 완료 커밋 뒤에 남음.
