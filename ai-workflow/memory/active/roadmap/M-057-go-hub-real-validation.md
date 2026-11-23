---
id: M-057
title: Go 허브 실전 검증과 사용 가능한 3.0 전환
sdlc_phase: stabilization
status: in_progress
order: 57
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - workflow-source/core/hub_go_spec.md
  - docs/RELEASE.md
goals: [G1, G3, G5]
---

# M-057 — Go 허브 실전 검증과 사용 가능한 3.0 전환

## 목적 및 완료 기준

Go 허브를 실제 테스트베드와 지원 하네스에서 검증하고, 데이터 보존 및 Python 복구 경로까지 확인한 뒤 3.0.0을 사용 가능하게 배포한다. 기존 Python 테스트베드 데이터는 보호하고 전환 전후 요청·DB 결과를 증거로 남긴다.

## WBS

- **WBS-57.1** Linux 테스트베드 복제본에서 Python/Go shadow 요청·DB 결과 비교 — 산출물: 차분 검사 결과, 무불일치 보고
- **WBS-57.2** Go 허브 화면·API·PC 중계 HTTP 계약 구현 — 산출물: Python/Go 경로·응답·권한 parity
- **WBS-57.3** Claude Code·Codex·MiniMax Code·Antigravity 하네스 4종에서 Go 허브 실측 — 산출물: 하네스별 setup 완료 및 결과 기록
- **WBS-57.4** macOS·Windows 실측과 배포 정책 확정 — 산출물: OS별 실행 증거 및 서명·notarization 결정
- **WBS-57.5** 동일 DB로 Go 상시 전환 및 Python rollback 리허설 — 산출물: 전환·복구 실행 기록
- **WBS-57.6** 릴리즈 게이트 통과 후 Go 3.0.0 배포 — 산출물: 검증된 GitHub Release 및 설치·운영 안내
