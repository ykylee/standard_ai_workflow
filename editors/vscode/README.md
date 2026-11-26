# Workflow Hub — PC 중계 (VS Code 확장 껍데기)

- 문서 목적: 워크플로우 허브 2.1 의 PC 중계 화면을 VS Code 안에 띄우는 확장의 설치 · 사용법
- 범위: `editors/vscode/` — 빌드 없는 JavaScript 껍데기. wheel 에 실리지 않는다
- 대상 독자: 중계를 쓰는 PC 의 사람
- 상태: draft (M-047 · M-048, 2026-11-22) — 실제 VS Code 1.147.0 (Linux · xvfb) 에서 활성화 · 상태 표시줄 · webview 안 중계 화면 · 일시정지 버튼 · `.vsix` 설치 실측 (TASK-2026-11-22-main-016). VS Code 1.148.0 에서 테마 전달 · 종료 두 번 누름 실측 (TASK-2026-11-26-claude-plex-010). macOS · Windows · VS Code 웹/원격은 미측정
- 최종 수정일: 2026-11-26
- 관련 문서: [`hub_orchestration_spec.md`](../../workflow-source/core/hub_orchestration_spec.md) §9 · §10

확장은 **껍데기**다 — 화면은 중계(`python -m workflow_kit hub relay serve --ui-port 8771`)가 그리고, 확장은 그것을 webview 로 띄우고
상태 표시줄에 중계 상태(활성 세션 수 · 일시정지)를 보인다. VS Code 테마(밝음 · 어두움 · 고대비)를 중계 화면에 넘긴다. 승인은 owner 권한이라 중앙 허브 화면에서 한다.

## 설치 (빌드 없음)

`.vsix` 로 묶어 설치한다 (Node 필요 — 묶는 도구만, 확장은 빌드가 없다):

```bash
cd editors/vscode
npx --yes @vscode/vsce@3.2.1 package --no-dependencies -o workflow-hub-relay.vsix
code --install-extension workflow-hub-relay.vsix
```

또는 폴더를 그대로 링크한다:

```bash
# 이 폴더를 VS Code 확장 폴더에 링크한다 (Windows 는 %USERPROFILE%\.vscode\extensions 에 복사)
ln -s "$(pwd)/editors/vscode" ~/.vscode/extensions/standard-ai-workflow.workflow-hub-relay-0.1.0
```

VS Code 를 다시 시작하고 명령 팔레트에서 **Workflow Hub: 중계 화면 열기**. 포트는 설정 `workflowHub.relayPort` (기본 8771).

## 하지 않는 것

- 화면을 직접 그리지 않는다 — iframe 하나. 판정 · HTML 생성은 중계(Python) 쪽 한 벌이다.
- 토큰을 읽거나 저장하지 않는다. 중계 화면은 `127.0.0.1` 에서만 열리고, VS Code 데스크톱 webview 말고 다른 사이트는 프레임에 넣을 수 없다.
- `confirm()` 같은 대화상자를 쓰지 않는다 — webview sandbox 에 `allow-modals` 가 없어 즉시 '취소' 가 된다. 종료는 같은 단추를 두 번 누른다.
- 껍데기 문서 자신은 스크립트를 돌리지 않는다 (CSP 에 `script-src` 없음). `enableScripts` 는 켜 두는데, 끄면 그 안에 담긴 중계 화면의 일시정지 버튼까지 죽기 때문이다.
