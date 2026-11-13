# Baselines (rolled off)

- 문서 목적: `session_handoff.md` §1 에서 롤오프된 기준선 줄을 이력으로 보존한다.
- 범위: 과거 세션의 기준선 산문 (최신이 위)
- 대상 독자: AI agent, 저장소 관리자
- 상태: append-only
- 관련 문서: [session_handoff.md](./session_handoff.md)

> 이 파일은 **읽기 대상이 아니라 조회 대상**이다. 세션 시작에 읽지 않는다 —
> handoff §1 이 최근 4개만 들고 있고, 그 이전이 필요할 때만 여기를 본다.

## 롤오프 2026-11-13

- claude/remote-sync-check-234c32 워크스페이스 — `main@826af874` 에서 이어받음 (2026-11-12). 이 브랜치의 작업은 아직 없다. 모 브랜치 기준선: **122차 세션 (2026-10-31, Windows 호스트 DESKTOP-DGPLBF7) — v1.22.0 발행 완료 (minor: feat 1 · fix 3 · breaking 0).** main 은 `v1.22.0` 태그 커밋 `a44b7d31` + 발행 완료 커밋 — **origin/main 에 push 완료**, GitHub Release `v1.22.0` 생성(draft=false · prerelease=false) · asset 5종(whl · sdist · claude-code · codex · minimax-code plugin ZIP). **저장소에서 처음 시도한 Windows 발행**이라 발행 경로 격차가 2건 더 드러났다 — ①**pre_check `packaging`** — 임시 venv 의 `pip` 를 `venv/bin/pip` 로 고정(Windows 는 `Scripts/pip.exe`) → FileNotFoundError ②같은 자리에서 `pip.exe install --upgrade pip` 이 Windows venv 에서 자기수정을 거부 → `python -m pip` 로 교체. `common/paths.py` 에 `venv_executable()` 정본 신설(복제돼 있던 POSIX 고정 3곳 정리). 추가로 **서브프로세스 `text=True` encoding 누락 10곳**(별칭 호출로 앞선 수리가 놓쳤던 것) 과 **drift_ledger append 의 CRLF** 수리. 전량 게이트 native·slash 309×2 rc 0(증거 `a44b7d31…json` · 커밋 후 clean tree) · mypy 227 files 0 errors · packaging 사전점검 PASS(1.22.0 휠을 Windows 임시 venv 에 심어 13 서브패키지 import smoke). **미해결**: ①**POSIX(Linux/macOS) 회귀 게이트는 이 호스트에서 돌릴 수 없다** — 309×2 는 별도 호스트 확인 필요 ②해석기 매트릭스 3.11 셀 UNMEASURED(해석기 미설치) ③case 수 선언 대조 75건 미측정 ④§2.8 소비채널 재적용은 발행 완료 커밋 뒤에 남음.
