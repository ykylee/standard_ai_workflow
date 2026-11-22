# Workflow Hub — PC 중계 (VS Code 확장 껍데기)

- 문서 목적: 워크플로우 허브 2.1 의 PC 중계 화면을 VS Code 안에 띄우는 확장의 설치 · 사용법
- 범위: `editors/vscode/` — 빌드 없는 JavaScript 껍데기. wheel 에 실리지 않는다
- 대상 독자: 중계를 쓰는 PC 의 사람
- 상태: draft (M-047, 2026-11-22) — 실제 VS Code 로드는 아직 미측정 (이 저장소의 게이트는 stub `vscode` 로 활성화를 잰다)
- 최종 수정일: 2026-11-22
- 관련 문서: [`hub_orchestration_spec.md`](../../workflow-source/core/hub_orchestration_spec.md) §9 · §10

확장은 **껍데기**다 — 화면은 중계(`python -m workflow_kit hub relay serve --ui-port 8771`)가 그리고, 확장은 그것을 webview 로 띄우고
상태 표시줄에 중계 상태(세션 수 · 일시정지)를 보인다. 승인은 owner 권한이라 중앙 허브 화면에서 한다.

## 설치 (빌드 없음)

```bash
# 이 폴더를 VS Code 확장 폴더에 링크한다 (Windows 는 %USERPROFILE%\.vscode\extensions 에 복사)
ln -s "$(pwd)/editors/vscode" ~/.vscode/extensions/standard-ai-workflow.workflow-hub-relay-0.1.0
```

VS Code 를 다시 시작하고 명령 팔레트에서 **Workflow Hub: 중계 화면 열기**. 포트는 설정 `workflowHub.relayPort` (기본 8771).

## 하지 않는 것

- 화면을 직접 그리지 않는다 — iframe 하나. 판정 · HTML 생성은 중계(Python) 쪽 한 벌이다.
- 토큰을 읽거나 저장하지 않는다. 중계 화면은 `127.0.0.1` 에서만 열리고, 이 확장의 webview 말고 다른 사이트는 프레임에 넣을 수 없다.
