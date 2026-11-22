---
id: M-047
title: 허브 오케스트레이션 — implementation 4 (VS Code 확장 껍데기)
sdlc_phase: implementation
status: done
order: 47
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - editors/vscode/extension.js
  - workflow-source/tests/check_vscode_shell.py
goals: [G1, G5]
---

# M-047 — VS Code 확장 껍데기

계약 정본: `workflow-source/core/hub_orchestration_spec.md` §10 · 요구 R22.3 · 결정 O8 · DO12 (PURPOSE 예외 — 껍데기만).
확장은 중계 로컬 화면을 webview 로 띄우고 상태 표시줄에 중계 상태를 보이는 것까지 — 화면 로직은 Python 한 벌. wheel 에 싣지 않는다.

**종결 (2026-11-22)**: TASK-2026-11-22-main-015 — check_vscode_shell 6/6 · 되주입 6/6. 실제 VS Code 로드는 미측정 (다른 호스트).

## WBS

- **WBS-47.1** `editors/vscode/` 확장 (빌드 없는 JavaScript) · 중계 화면 프레임 정책(VS Code webview 만) · 게이트 검사(stub `vscode` 로 활성화 · 명령 · webview · 상태 표시줄 · wheel 밖) — 산출물: `editors/vscode/` · `tests/check_vscode_shell.py`
