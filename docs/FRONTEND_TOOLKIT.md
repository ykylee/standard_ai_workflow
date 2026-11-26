# 하네스 중립 프론트엔드 툴셋

- 문서 목적: AI 코딩 에이전트가 화면을 만들고 고치고 확인할 때 쓸 도구 조합과 사용 순서를, 특정 하네스(Claude 등)나 개인 스킬에 기대지 않게 정리한다
- 범위: 열린 형식 3가지(DESIGN.md · Agent Skills · MCP), 기본 조합과 설치 스크립트, 작업 순서, 선택 층, 보안 · 부작용, 실측 결과, 후보 목록
- 대상 독자: 화면이 있는 저장소의 주인, AI 에이전트
- 상태: beta
- 최종 수정일: 2026-11-26
- 관련 문서: [`frontend-toolkit/setup.sh`](./frontend-toolkit/setup.sh), [`frontend-toolkit/DESIGN.template.md`](./frontend-toolkit/DESIGN.template.md), [`HUB_OPERATIONS.md`](./HUB_OPERATIONS.md)

출발점은 허브 아이디어 IDEA-0001(2026-11-25 소유자)이다. 조건은 "Claude 나 개인 내장 스킬에 의존하지 않고, GitHub 에서 널리 쓰이는 것으로"다.

## 1. 한눈에

세 가지 열린 형식 위에 도구를 얹는다. 형식이 열려 있으니 하네스를 바꿔도 같은 파일 · 같은 명령이 남는다.

| 층 | 기본 도구 | 형식 | 하네스 없이도 |
|---|---|---|---|
| 디자인 규약 | `DESIGN.md` (+ `@google/design.md` lint) | DESIGN.md | lint · diff · 토큰 내보내기는 CLI 만으로 |
| 감각 · 리뷰 | [impeccable](https://github.com/pbakaus/impeccable) | Agent Skills (SKILL.md) | `npx impeccable detect` — 규칙 62개, LLM 없음 |
| 눈으로 확인 | [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) | MCP | — (대안 [agent-browser](https://github.com/vercel-labs/agent-browser) 는 셸 CLI) |
| 회귀 고정 | 저장소의 렌더 검사 (이 저장소는 `check_hub_screens`) | — | 그렇다 |

선택 층(§5): React 면 shadcn MCP, Figma 원본이 있으면 Figma MCP, 원본이 없으면 Stitch 시안.

## 2. 고정 판 (2026-11-26)

| 도구 | 판 | 라이선스 | 별 (GitHub API 실측) |
|---|---|---|---|
| `impeccable` | 4.11.0 | Apache-2.0 | 116.9k |
| `@google/design.md` | 0.4.0 | Apache-2.0 | 29.1k (`google-labs-code/design.md`) |
| `chrome-devtools-mcp` | 1.14.0 | Apache-2.0 | 59.4k |

`setup.sh` 맨 위 세 줄이 정본이다. 판을 올릴 때는 §7 순서를 따른다. impeccable 은 npm 판을 고정해도 **엔진 바이너리는 고정되지 않는다** — 같은 4.11.0 으로 두 번 설치했더니 엔진은 0.1.30 과 0.1.31 이었다(§6).

## 3. 설치

대상 프로젝트 뿌리에서 돌린다. 이 저장소를 클론해 둔 경로를 쓴다:

```sh
bash <이 저장소>/docs/frontend-toolkit/setup.sh                 # 기본: --harness claude,codex
bash <이 저장소>/docs/frontend-toolkit/setup.sh --dry-run       # 무엇을 할지만 보인다
bash <이 저장소>/docs/frontend-toolkit/setup.sh --harness codex,cursor,gemini --no-hooks
```

하는 일은 셋이다.

1. `DESIGN.md` 가 없으면 [템플릿](./frontend-toolkit/DESIGN.template.md)을 놓고 lint 한다 — 오류가 있으면 멈춘다.
2. impeccable 을 프로젝트 범위로 설치한다(`--providers` 는 `--harness` 그대로). 스킬은 `.claude/skills/` · `.agents/skills/` 등 하네스별 폴더에, 디자인 hook 은 `.claude/settings.local.json` · `.codex/hooks.json` 에 쓴다.
3. 브라우저 확인 MCP 를 연결한다.
   - **Claude Code**: `.mcp.json` 에 `chrome-devtools` 를 병합한다. 다른 서버는 건드리지 않는다.
   - **Codex**: 프로젝트 `.codex/` 설정은 신뢰한 프로젝트에서만 읽힌다(실측: 신뢰 전 `codex exec` 는 "Untrusted project-local configuration is disabled" 경고를 내고 무시). 스크립트는 실행마다 붙이는 `-c` 인자와 사용자 범위 `codex mcp add` 명령을 **보이기만** 한다.
   - **그 밖**: 서버 명령(`npx -y chrome-devtools-mcp@1.14.0 --headless --isolated --no-usage-statistics`)을 보인다. 그 하네스의 MCP 설정에 넣는다.

사용자 범위 설정(`~/.claude` · `~/.codex`)은 쓰지 않는다. 그래도 바깥에 남는 것이 있다 — §6.

## 4. 작업 순서

1. **규약을 정한다.** `DESIGN.md` 의 토큰(YAML)과 글(이유)을 이 제품에 맞게 고친다. 이미 화면이 있으면 에이전트에게 `/impeccable document`(Codex `$impeccable document`)로 지금 모습을 받아 적게 한다. 고친 뒤 `npx -y @google/design.md@0.4.0 lint DESIGN.md`.
2. **제품 맥락을 한 번 적는다.** `/impeccable init` 이 코드를 읽고 모르는 것만 물어 `PRODUCT.md` 를 쓴다.
3. **좁게 시킨다.** 페이지 전체보다 한 구역이 낫다 — `/impeccable critique the onboarding flow` · `polish settings` · `harden checkout`. 명령 24개는 [impeccable README](https://github.com/pbakaus/impeccable#24-commands).
4. **결정적 검사로 거른다.** 에이전트 없이:
   ```sh
   npx -y impeccable@4.11.0 detect src/                        # 소스 — 패턴 규칙
   npx -y impeccable@4.11.0 detect http://localhost:5173       # 렌더된 페이지 — 대비 · 작은 글자 등
   ```
   종료 코드 `2` = 지적 있음, `1` = 대상을 못 읽음(통과가 아니다). CI 에서는 `--sarif` 또는 `--github`.
5. **눈으로 확인한다.** 에이전트에게 브라우저 도구로 페이지를 열어 콘솔 오류 · 390px 폭 가로 스크롤 · 스크린샷을 보게 한다. "확인했다"는 말 대신 도구 호출 기록을 본다(§8 이 그렇게 쟀다).
6. **회귀를 고정한다.** MCP 브라우저 확인은 개발용이다. 고친 것이 다시 깨지지 않게 저장소의 렌더 검사(Playwright 테스트 · 헤드리스 Chrome DOM 검사 등)에 case 로 남긴다.

## 5. 선택 층

| 상황 | 더할 것 | 메모 |
|---|---|---|
| React · Tailwind 앱 | [shadcn/ui](https://github.com/shadcn-ui/ui) 공식 MCP — `npx shadcn@latest mcp` ([문서](https://ui.shadcn.com/docs/mcp)) | 레지스트리 단위로 컴포넌트를 찾아 넣는다. `shadcn.io` 는 비공식 |
| Figma 원본이 있음 | Figma 공식 원격 MCP, 또는 [Figma-Context-MCP](https://github.com/GLips/Figma-Context-MCP)(비공식, MIT, ★16.3k) | 쓰기(디자인 수정) 범위는 출처가 엇갈린다 — 미측정 |
| 원본이 없음 | Google Stitch 로 시안 → `DESIGN.md` 로 받기 ([stitch-sdk](https://github.com/google-labs-code/stitch-sdk) ★1.9k) | Windows 연결 실패 사례가 보고돼 있다 — 미측정 |
| 브라우저를 셸로 | [agent-browser](https://github.com/vercel-labs/agent-browser) (★54.0k, Apache-2.0) | MCP 가 없는 하네스에서도 셸 명령으로 돈다 — 미측정 |
| 사람이 화면에서 직접 | [onlook](https://github.com/onlook-dev/onlook) (★28.0k) | 에이전트 도구가 아니라 사람용 편집기 |

## 6. 보안 · 부작용

impeccable 은 강력한 만큼 자동으로 하는 일이 많다. 설치 전에 읽는다.

- **바깥에 남는 것.** `--scope=project` 여도 엔진은 `~/.impeccable/bin/<판>/` 에 받는다. Chrome 네이티브 메시징 호스트 `~/.config/google-chrome/NativeMessagingHosts/style.impeccable.browser.json` 도 등록한다(실측 — README 에는 없다). 호스트는 impeccable 확장(Chrome 웹 스토어 ID 두 개)만 부를 수 있다. 확장을 깔지 않으면 쓰이지 않는다.
- **엔진 판이 떠다닌다.** npm 판을 고정해도 엔진은 받을 때의 최신이다. 재현이 필요하면 [git submodule + `npx impeccable link`](https://github.com/pbakaus/impeccable#installation) 로 원본을 고정한다.
- **hook 은 모델 승인 밖에서 돈다.** Claude Code 는 모델의 명령을 거절해도 설치된 command hook 은 실행한다. 사람 없이 돌리는 실행에서는 hook 을 검토하거나 `--settings '{"disableAllHooks": true}'` 로 끈다. hook 이 싫으면 `setup.sh --no-hooks`.
- **live 모드는 권한을 우회해 에이전트를 띄운다.** 채팅 세션이 없을 때 `codex --dangerously-bypass-approvals-and-sandbox` 또는 `claude --permission-mode bypassPermissions` 를 PATH 에서 실행한다. live 모드를 쓰려면 시작하는 환경에 `IMPECCABLE_LIVE_COPY_AGENT=chat`(또는 `off`)을 둔다. 배포된 사이트에는 쓰지 않는다.
- **원격 요청.** 새 디자인을 시작하면 impeccable.style 에서 시각 방향 목록을 받는다(텔레메트리를 꺼도). 사용 기록은 `DO_NOT_TRACK=1` 로 끈다 — `setup.sh` 가 켠다. chrome-devtools-mcp 의 사용 통계는 `--no-usage-statistics` 로 끈다(기본 켜짐).
- **브라우저 MCP 는 열린 페이지를 다 본다.** `--isolated` 로 매번 빈 프로필을 쓴다. 로그인된 실사용 프로필에 붙이지 않는다.

정리하려면: `rm -rf ~/.impeccable ~/.config/google-chrome/NativeMessagingHosts/style.impeccable.browser.json` 와 프로젝트의 `.claude/skills/impeccable` · `.agents/skills/impeccable` · hook 항목.

## 7. 판 올리기

1. `npm view <패키지> version time.modified` 로 새 판과 날짜를 본다. 나온 지 얼마 안 된 판은 하루 이틀 기다린다(공급망 사고 대비).
2. 빈 실험 저장소에서 `setup.sh` 를 돌리고 §8 과 같은 과제를 하네스 둘에서 다시 잰다.
3. `setup.sh` 맨 위 세 줄과 §2 표를 함께 고친다.

## 8. 실측 (2026-11-26, 이 저장소의 허브 화면)

대상: 허브 3.6.0 정적 화면(`index.html` · `hub.css` · `hub.js`)과 로컬로 띄운 `/ui/`. 같은 과제를 두 하네스에 줬다 — impeccable 로 critique, chrome-devtools MCP 로 페이지를 열어 콘솔 오류와 390px 가로 스크롤 확인, 파일은 고치지 않는다.

| | 결정적 CLI (에이전트 없음) | Codex 0.171.0 | Claude Code 2.1.332 |
|---|---|---|---|
| 스킬을 실제로 읽음 | — | `SKILL.md` 읽고 `impeccable context` 실행 | Skill 도구 1회, `context` · `detect` 실행 |
| 브라우저 MCP 호출 | — | `new_page` · `resize_page` · `evaluate_script` · `list_console_messages` · `take_screenshot` | 같은 종류 10회 + 서브에이전트 1 |
| 콘솔 오류 · 390px 가로 스크롤 | — | 2건(로그인 없이 연 화면의 401) · 없음 | 2건 · 없음 |
| 지적 | 소스 2건, 렌더 1건(한쪽 두꺼운 테두리 + 둥근 모서리) | 3건 | P1~P2 다섯 갈래(자동 갱신이 포커스를 날림 · 칩 대비 4.24/4.38 · 라벨 없는 입력 · 넓은 표 · primary 단추 중복) |

- Claude 없이 성립함: Codex 실행이 같은 스킬 파일 · 같은 MCP 로 같은 판정(콘솔 2 · 가로 스크롤 없음)을 냈다. 결정적 CLI 두 개(`design.md lint` · `impeccable detect`)는 어떤 하네스도 없이 돌았다.
- 비용: Claude Code 실행 1회 $1.53. Codex 는 토큰 76,391.
- `DESIGN.template.md` lint: 오류 0 · 경고 0. 허브 토큰으로 쓴 시험용 DESIGN.md 는 경고 10 — `primary` 이름이 없고 컴포넌트가 참조하지 않는 색이 많아서다. 템플릿이 그 규약을 따른다.
- 재지 않은 것: Gemini CLI(이 호스트는 모델 호출이 막혀 있다) · Cursor · Codex 에서 hook 이 실제로 도는지(`/hooks` 승인 필요) · agent-browser · Figma · Stitch · shadcn.

## 9. 후보와 뺀 것 (2026-11-26 GitHub API)

| 저장소 | ★ | 라이선스 | 판단 |
|---|---|---|---|
| `nextlevelbuilder/ui-ux-pro-max-skill` | 154.2k | MIT | impeccable 대안. 디자인 결정 목록이 넓다. `npx ui-ux-pro-max-cli init --ai <하네스>` |
| `Leonxlnx/taste-skill` | 121.6k | MIT | 대안. 브라우저 마감 점검 포함 |
| `addyosmani/agent-skills` | 120.4k | MIT | 화면 전용이 아닌 엔지니어링 스킬 묶음 |
| `VoltAgent/awesome-design-md` | 129.1k | MIT | 브랜드별 DESIGN.md 예시 — 템플릿을 고를 때 참고 |
| `vercel-labs/agent-skills` | 34.9k | (GitHub 미판독) | 웹 인터페이스 지침 감사. 라이선스 확인 전 가져오지 않는다 |
| `vercel-labs/skills` (`npx skills`) | 40.9k | MIT | SKILL.md 설치기 — 다른 스킬을 하네스 여러 곳에 깔 때 |
| `microsoft/playwright-mcp` | 40.2k | Apache-2.0 | 접근성 스냅샷 · 결정적 조작. chrome-devtools-mcp 대안 |
| `anthropics/skills` (frontend-design) | 200.6k | (GitHub 미판독) | Claude 중심이라 기본에서 뺐다. impeccable 이 여기서 출발했다 |
| `21st-dev/magic-mcp` | 6.7k | ISC | 9월 이후 push 없음 — 뺐다 |
| `storybookjs/mcp` · `vercel/v0-sdk` | 272 · 517 | MIT · — | 아직 작거나 서비스에 묶임 — 뺐다 |

별 수는 품질이 아니라 쓰는 사람의 수다. 지원 하네스는 각 README 기준이다.
