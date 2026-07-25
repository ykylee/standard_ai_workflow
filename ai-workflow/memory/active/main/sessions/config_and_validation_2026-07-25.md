# Session — 2026-07-25 / 선언과 사실을 맞춘다 (§2.29~§2.30)

- 문서 목적: 특정 세션의 단기 메모리 (영구 보존은 wiki/topics/ 와 함께).
- 날짜: 2026-07-25
- 주제: generic (설정 정합 + 검사 층 신설)
- 상태: stable

## 📋 Session Summary

직전 세션이 남긴 미결 3건(Pages / pyproject 3중 불일치 / 릴리스 제목)을 순서대로
집었다. 관통한 결함은 하나 — **선언이 사실과 다른데 그것을 볼 수단이 없었다.**
Pages 는 스위치가 꺼져 있었고, mypy strict 는 2개월간 적용된 적이 없었으며, YAML 을
읽는 유일한 코드는 결함 있는 자체 정규식 파서였다. 셋 다 초록불이었다.

## 🛠️ Detail

**시작 상태**: `main = 03cbfb0`, worktree `tubesnout`, clean, smoke 211 파일.

### 1. mkdocs 3층의 맨 아래 — Pages 활성화 (`c9849a8`)

`gh api -X POST .../pages -f build_type=workflow` → run `30159275873` 에서
build ✅ / **deploy ✅ 9s**. 그때까지 deploy 는 한 번도 성공한 적이 없었다.

게시 범위를 먼저 점검했다. 저장소가 이미 public 이므로 Pages 는 새로 공개하는 게
아니라 렌더링된 사이트를 더하는 것이고, 대상은 nav 9개 문서 1,624줄뿐이다. IP/홈경로/
이메일/토큰 패턴으로 훑어 유출 후보 0건(걸린 것은 전부 `v0.5.7.1` 같은 버전 번호가
IP 정규식에 잡힌 위양성).

> **덤**: `hooks:` 전환(`7b1d63e`)이 *의도한 변환까지* 수행함이 처음 산출물로 확인됐다.
> 배포된 적이 없어 그때까지 확인할 수단이 없었다. 원본 헤더가 stale 한 3건이 게시본에서
> git log 날짜로 덮여 있다 — `index` 06-17→07-22 / `CODE_INDEX` 07-21→07-23 /
> `FEEDBACK` 06-17→07-22. **로드되는가와 일하는가는 다른 층이다.**

### 2. §2.29 — mypy strict 는 v0.11.11 이래 적용된 적이 없다 (`3a7bd37`)

```
mypy --no-incremental workflow-source/workflow_kit/    # cwd = REPO_ROOT
→ LOG:  Config File:            Default
```

헤더 주석은 "workflow-source/ 의 pyproject `[tool.mypy] strict=true` read" 라고 적고
있었다. mypy 의 config 탐색은 **cwd 기준**이고 REPO_ROOT 의 `pyproject.toml` 에는
`[tool.mypy]` 가 없어, 탐색이 전부 실패하고 Default 로 떨어졌다.

| 실행 | Config | 결과 |
|---|---|---|
| CI 가 하던 것 | **Default** | 0 errors / 117 files → green |
| 선언된 strict | `workflow-source/pyproject.toml` | **4 errors** |

**AST 로 전수 조사하니 mypy 호출 지점이 23곳, 그 중 21곳이 config 없이** 돌고 있었다 —
CI, release gate, Layer 2 gate, 그리고 `check_mypy_strict_v0_11_3~10` 등 "strict clean"
을 이름에 단 smoke 9종 전부. 처음엔 3곳인 줄 알고 목록을 손으로 적었다가 AST 로 훑고
나서야 규모를 알았다. **손으로 유지하는 목록은 반드시 빠진다.**

곁들여 `exclude` 결함: `"schemas/.*"` 는 anchor 가 없어 경로 어디서든 매치했다. 의도한
대상 `workflow-source/schemas/` 는 실은 `.py` 가 0개였고, 실제로 잘라낸 것은
`workflow_kit/common/schemas/` 의 **실소스 20 file** 이었다 (117 → 97).

가장 나쁜 층은 재발 방지 test 였다. `check_mypy_strict_ci_v0_11_11` case 8 은 CI
invocation 을 **충실히 재현**하고 exit 0 을 확인했다. 깨진 실행을 정확히 복제했으니
green 이었다. **재현은 검증이 아니다** — 무엇을 재현하는지도 함께 봐야 한다.

### 3. 5·6번 — 루트 scaffold 이름 충돌 + sub-package 제거

- 루트 `pyproject.toml` 의 `name` 을 `standard-ai-workflow-root` 로. `uv lock` 재생성,
  **딱 한 줄만** 변경. `eb62f37` 의 "별개 namespace" 의도를 실제 이름으로 실현.
- `workflow_kit/pyproject.toml` 제거. 배포판으로서 **모든 모드에서 깨져 있었다** —
  wheel 은 최상위에 `common`/`server`/`harness` 만(117 중 51 파일), editable 은
  `server`/`harness` 만 올라와 `import workflow_kit` 이 실패한다. CI 가 지금껏 돈 것은
  mypy 에 target 을 *경로* 로 주기 때문이었다.
- 딸려서 mypy 버전 갈라짐 해소 — v0.11.11 이 선언한 pin 통일 규약이 **sub-package 에만**
  걸려 있었고, 정작 smoke 가 설치하는 정본은 하한 지정이라 2.3.0 이 깔렸다.

### 4. §2.30 — YAML·스킬·MCP 검사 층 신설

`_read_yaml_simple` 의 fallback 정규식 `r"mypy[^\\n]*..."` 은 raw string 이라
`[^\n]`(줄바꿈 제외)이 아니라 **`[^\\n]`(역슬래시와 문자 `n` 제외)** 로 해석됐다.
게다가 fallback 이 도는 조건(PyYAML 부재)이 곧 CI 였다.

| 층 | 산출물 | case |
|---|---|---|
| 구문·스키마·파서금지·errexit | `check_yaml_surfaces.py` | 4 |
| 스킬 frontmatter (skill-lint 규칙) | `check_harness_skill_frontmatter.py` | 4 |
| MCP tool 정의 | `check_mcp_tool_descriptors.py` | 4 |
| 워크플로우 셸 | `.github/workflows/actionlint.yml` | — |
| MCP 동작 | `.github/workflows/mcp-inspector.yml` | — |

**실측**: 살아 있는 MCP 서버 tool 13개가 커밋된 descriptor 13개와 `inputSchema` 까지
완전 일치. harness frontmatter 7종 모두 유효한 YAML, 보간 0건.

## ✅ Outcome

| 항목 | 시작 | 종료 |
|---|---|---|
| GitHub Pages | 미활성 (deploy 100% 실패) | **게시 완료** |
| mypy strict | 2개월간 미적용 (Default) | 호출 23곳 전부 config 명시 |
| 검사 대상 file | 97 (20개 조용히 제외) | **117** |
| 자체 정규식 YAML 파서 | 3곳 | **0곳** |
| smoke 파일 | 211 | **215** |
| 전량 (미푸시 HEAD) | — | **213/215** (2건 `ci_stale`) |

주입 검증 총 **13건** 전부 FAIL 확인. actionlint 이 도입 시점에 기존 결함 6건 발견.

## 🔁 이번 사이클에서 내가 낸 오류 5건 (지우지 않고 남긴다)

1. **루트 pyproject 를 "uv init 잔여물"로 규정** — `eb62f37` + README:118 이 명시한
   *의도된 placeholder* 였다. 결함을 설명할 때 남의 의도까지 규정하지 말 것 (`db744f4`).
2. **mypy 2.3.0 크래시 오진** — 실제로는 내 스크래치 venv 의 pyenv 3.12.9 가 `_sqlite3`
   없이 빌드된 탓. 지난 세션의 "과잉 제약 시뮬레이션"과 같은 부류.
3. **actionlint 이 §2.27 사고를 잡는다고 적음 — 틀렸다.** 재현 결과 exit 0. shellcheck
   에 "errexit 때문에 이 줄에 닿지 못한다"는 규칙이 없다. 그 부류의 유일한 방어선은
   `check_yaml_surfaces` 4번 case 다.
4. **`git checkout` 으로 주입을 되돌리다 커밋하지 않은 수정을 날렸다.** 복구 후 전수
   grep 으로 잔재 없음 확인.
5. **전량 실행 중에 주입 테스트를 돌려 측정을 오염시켰다.** 그 실행은 폐기하고 트리를
   고정한 채 다시 쟀다. 이번 사이클 주제와 정확히 같은 부류다.

## ⏭️ Next Actions

- [ ] **게이트가 손으로 적은 숫자를 읽는다** — `smoke_trend_cross` / `quality_dashboard`
      Panel 4 는 실행 결과가 아니라 릴리스 노트의 수치로 판정한다. 이번에도 노트에
      215/215 인 상태에서 실제는 213/215 였는데 green 이었다. 산출물을 직접 세도록 옮길 것.
- [ ] **환경 공유 체크아웃 설계** (검토 완료, 결정 대기) — A층(실행 코드·MCP 서버)은
      이미 참조 모델로 가능(도구가 경로를 인자로 받는다). B층(harness 산출물)은 복사
      모델이라 재적용 필요하되 smart-update + VERSION 이 이미 있으므로 트리거만 붙이면
      된다. 결정 2건: `STANDARD_AI_WORKFLOW_ROOT` 의 의미 확정, 버전 pin 수단.
- [ ] `STANDARD_AI_WORKFLOW_ROOT` 3중 불일치 — 독스트링은 "서버가 kit root 를 찾게",
      실제 값은 프로젝트 루트, 유일한 reader 는 kit root 로 해석, **서버는 읽지 않는다.**
- [ ] 릴리스 제목 형식 4종 혼재 + `v1.0.0-beta` 제목의 "199/199 PASS"
- [ ] `okf-validate` V-R10 온라인 URL 검증 / `consumer-metrics-digest` 이슈 포스팅
- [ ] ponytail 채택 A1 / B1~B3
- [ ] `check_release_pipeline_lib` 의 `dist/` 공유 경로 경합

## ⚠️ Risks & Blockers

- **`ci_stale` 2건**은 푸시 후 같은 SHA 의 CI run 이 생겨야 풀린다 — 코드 결함이 아니다.
- 전량 수치를 적을 때는 **어디서·어떤 조건으로 쟀는지**를 함께 적을 것. 이번에는
  "실행 중 트리 무수정"이 추가 조건이었다.
