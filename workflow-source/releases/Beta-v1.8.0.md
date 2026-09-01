# Beta v1.8.0 (2026-08-31)

> **상태: 릴리스 준비.** package `1.8.0`, runtime `__version__ = 1.8.0`, tag `v1.8.0`.
> **minor release** — 지원 하네스 개편(gemini-cli 종료 · antigravity 신설) +
> 탐침이 자기 침묵을 걷어낸 사이클.
>
> 등급 근거 (§1.5): 아래 §0.1 에 **반대 근거까지** 적었다. 이 사이클에는
> 소비자에게 보이는 축소(gemini-cli)가 있어 등급이 자동으로 서지 않는다.

## 0. 릴리스 판정

이 사이클의 주제는 **"침묵과 존재가 통과로 읽히는 자리"** 다. v1.7.0 이
선택 실행(meta-watch)을 넣었다면, v1.8.0 은 그 선택과 배포 탐침이 **실제로
무엇을 못 보고 있었는지**를 걷어낸다. 8건이 같은 모양이었다 — red 가 아니라
**아무 줄도 없었다**, 혹은 **뭔가 있으니 맞다고 셌다**.

발단은 매번 실측이었다. grok 캐시가 v1.4.0 에 멈춰 있는데 doctor 가 정상이라
했고(§2.4), codex 플러그인이 사흘 뒤 사라질 임시 경로에 매달려 있는데 캐시는
in-sync 였으며(§2.5), 문서가 5개 minor 낡은 설치 명령을 배포하는데 검사는
green 이었다(§2.7). 마지막으로 **탐침 자신**이 저장소와 갈라진 사본으로
돌면서 그 사실을 말하지 않았다(§2.6).

### 0.1 등급 근거 — minor 로 판정하되, 반대 근거를 같이 남긴다

**minor 인 근거** (§1.5 표):

1. 공개 Python API **시그니처** 변경 0. `SUPPORTED_HARNESSES` 는 상수 *값*이
   13→12 로 줄었지만 시그니처가 아니다.
2. console script / `wk` 명령 제거 **0** — 모든 명령이 그대로 있고 rc=0 이다.
3. 우리 산출물을 읽던 소비자가 못 읽게 되는 일 **0**. 이미 생성된
   `GEMINI.md` · `gemini-extension.json` 은 디스크에 그대로 있고 계속 읽힌다 —
   우리가 **재생성**을 안 할 뿐이다.

**반대 근거 (기록해 둔다)**: `--harness gemini-cli` 는 **rc=0 → rc=2** 로 바뀐다
(실측: `error: argument --harness: invalid choice: 'gemini-cli'`). §1.5 표의
2행이 "남아 있고 rc=0 이면 아니오" 라고 쓰므로, **그 인자를 쓰던 스크립트에
한해서는** 2행이 major 쪽을 가리킨다. minor 로 판정한 이유는 (a) 진입점 자체는
살아 있고 나머지 12개 하네스에서 rc=0 이며, (b) 제거가 소유자 지시였고
(c) 대상 하네스의 upstream 자체가 종료됐기 때문이다. **이 판단을 뒤집으려면
버전만 바꾸면 된다** — 근거는 여기 있다.

## 1. 릴리스 요약

- 범위: `v1.7.0..HEAD` (13 commit). 이 중 4건(`a69d83bf` · `4d7a78da` ·
  `818e199d` · `1f67f8e0`)은 **v1.7.0 발행 마무리**가 태그 뒤에 착지한 것이라
  실질 내용은 9 commit 이다.
- 누적 smoke **276/276 PASS** (전량 2축 · case 합계 552, FAIL 0, 좁은 선언 0),
  mypy strict 0 errors
- 검사 신설 1종(`check_self_location_resolution`) + 기존 검사에 case 다수 추가
  (총 276 파일)
- 지원 하네스 **13 → 12** (gemini-cli 종료, antigravity 신설)

## 2. 소비자 가시 변경

### 2.1 feat(harness) — gemini-cli 지원 종료 + antigravity 채널 신설 (`35a7a859`)

소유자 지시로 지원 하네스를 개편했다. **양쪽 다 실측에서 출발했다.**

- **gemini-cli 종료**: 정본 레지스트리(`SUPPORTED_HARNESSES` 13→12)에서
  시작해 renderers · paths · `__main__` · mcp · wiki · discovery · constants →
  doctor 4 레지스트리 → payload(`gemini-extension.json` · `GEMINI.md` 은퇴,
  VERSION_BEARING 4→3장) → 검사 11종 → 문서 전 계층까지 걷었다.
  `mcp_installation` §6.3 은 **결번** 처리했다 — §6.5.2 참조가 코드·문서에
  살아 있어 번호 재부여가 더 위험했다.
- **antigravity 신설**: Antigravity(`agy` CLI)는 Claude 호환 플러그인을
  **디렉터리째** 설치한다 — `~/.gemini/config/plugins/<name>/` 에 **무버전
  사본**, 재실행은 디렉터리를 갈아엎지 않는 병합 복사(marker 생존 실증),
  uninstall 은 통째 제거. 인식 계약은 payload 루트 관례 파일(`skills/` 4종 +
  `mcp_config.json`)이고, 이를 위해 payload 에 `mcp_config.json` = `mcp.json`
  **동일 사본**을 신설했다(검사가 동일성을 강제한다).
  루트 `hooks.json` 은 **일부러 안 넣었다** — 파일 인식까지만 실측이고 이벤트
  어휘 호환이 미실측이라, 모름을 안전으로 세지 않는다.

> **소비자 주의**: gemini-cli 로 bootstrap 하던 스크립트는 rc=2 로 실패한다
> (§0.1). 이미 생성된 파일은 그대로 쓸 수 있다.

### 2.2 feat(meta-watch) — 선언 보급 완주 (`c3c8634f`, `18d8e369`)

v1.7.0 이 meta-watch 를 넣었고, 이번에 **선언을 실제로 채웠다**. 추측이 아니라
채취에서 뽑았다 — 러너에 `--meta-watch-dump DIR` 을 신설해(판정 불변) 전량 1축이
276개 검사의 실접근을 채취하고, `judge` 와 **같은 필터**로 표면을 뽑아 디렉터리
glob 로 한 단계 넓혀 선언했다.

- 국소 **8 → 198** / 전역 10 / 미분류 68, **좁은 선언 0** (2축 모두)
- 선택 정확도 실측: memory·문서 전용 변경의 skip 이 **6건(2%) → 76건(28%)**
- 저장소 전체를 걷는 7건은 국소가 아니라 **전역 선언**으로 판정했다
  (접근 2076건 — 릴리스 파이프라인·스캐폴드 계열)
- **남은 68건은 일부러 미분류로 둔다.** 표면이 `workflow-source` 트리 전체라
  선언해도 선택 이득이 0 이고, 지표를 올리려고 옮기면 관찰 지표 자신이 망가진다.

### 2.3 fix(paths) — '자기 위치 오인' 결함족 전수 마감 (`cffce266`)

진입점 7건이 자기 위치를 잘못 잡거나 자식을 리터럴 `python3` 로 spawn 하고
있었다. `sys.executable` 파생으로 교정하고 **정적 게이트**
(`check_self_location_resolution`)를 신설해 결함족을 닫았다.

증상이 고약했다 — 이 호스트의 bare `python3` 이 **옛 worktree 의 stale editable
설치**로 우연히 돌고 있어서, 단독 실행은 green 이고 러너에서만 red 였다.
남은 동족은 MCP emit 1건(Windows 실측 대기)뿐이다.

### 2.4 fix(doctor) — grok 설치본을 이름이 아니라 선언으로 찾는다 (`6efc45ec`)

`PLUGIN_INSTALL_CACHES` 의 grok glob 이 `*standard-ai-workflow*` 였는데, grok 은
설치 디렉터리를 **플러그인 이름이 아니라** `plugin-<hash>` 로 짓고 매핑을
`registry.json` 에 적는다. 이름 glob 은 **원리적으로** 이 채널을 못 찾는다 —
디렉터리 이름 규칙은 하네스의 것이지 우리 것이 아니다.

claude-code 전용 특수분기였던 선언 읽기를 `INSTALL_PATH_DECLARATIONS` 표로
일반화했다. **켜자마자 진짜를 잡았다** — grok 설치본이 `35a7a859` 가 추가한
`mcp_config.json` 을 빠뜨린 것을 DRIFT 로 적발했다.

같은 커밋에서 **사본 0 채널의 침묵**도 걷었다. 사본이 0 인 채널은 출력에 아무
줄도 안 남겨서 '설치 안 됨' 과 '못 찾음' 이 똑같이 보였다. 이제
`= <채널>: 사본 0 — <사유>` 로 남기고, **글로벌 선언이 있는데 사본이 0 이면
발견**으로 센다.

### 2.5 fix(doctor) — codex marketplace 의 휘발 경로 (`6d9ad763`)

`config.toml` 의 marketplace `source` 가 **사흘 전 끝난 세션의 임시 디렉터리**를
가리키고 있었다. 설치 캐시는 in-sync 여서 `content_drift` 는 통과라고 말했다 —
**사본과 경유지는 따로 깨진다.**

`_codex_marketplace_sources` + 휘발 경로 판정을 넣었다. **판정은 경로 규칙으로
한다** — 존재 여부만 보면 비워지기 전에는 늘 통과다. 단 **탐침 대상 홈 안쪽은
휘발이 아니다** (홈은 하네스의 거처라 같은 수명).

### 2.6 fix(doctor) — 탐침이 자기 자신의 낡음을 잰다 (`c88c0890`)

doctor 는 배포 페이로드에 대해 '버전은 같고 내용만 낡음' 을 해시로 잡으면서
**자기 자신**에겐 그 규율을 안 썼다. 그 결과 릴리스 휠로 도는 `wk` 가 저장소
소스와 갈라진 채 **지원 종료된 채널을 '막힘' 으로, 신설 채널을 부재로** 보고했고
출력엔 `kit version` 한 줄뿐이었다.

`environment` 절에 **`kit 사본` 줄**이 생겼다 — 돌고 있는 사본의 출처와 저장소
소스의 `.py` 내용 일치를 판정으로 남기고, 갈라짐은 발견으로 센다.

```
  kit 사본    : 1.8.0 — **버전은 같은데 내용이 다르다** (.py 2개 어긋남)
    어긋난 파일: deploy_doctor.py, upgrade_diff.py
```

잰 단위 둘이 이 절의 성패를 갈랐다. **사본의 버전은 사본 옆에서 읽는다** —
설치 메타데이터로 떨어지면 무관한 배포본의 값이 사본 버전으로 둔갑하고, 그
순간 판정이 '버전 다름' 으로 갈려 잡으려던 자리에 영영 도달하지 못한다.
**대조는 `.py` 만** 한다 — 자산은 채널마다 담기는 것이 달라 포장 차이가 내용
차이로 샌다. 버전을 모르면 모름으로 남긴다.

> cross-host federation 의 선행 조건이기도 하다. 여러 호스트의 상태를 합치려면
> '같은 버전' 이 같은 내용이라는 보장이 있어야 하고, 그 보장은 버전 문자열이
> 아니라 이 대조에서 나온다.

### 2.7 fix(backlog-update) — update 가 이전 세션 기록을 지우던 것 (`6d9ad763`)

**데이터 손실 수정이다.** `wk backlog-update --mode update` 로 열거 필드를
넘기면 파일의 기존 값과 합쳐지지 않고 **통째 교체**됐다 (실측: 영향 문서 1건 +
완료 기준 2건 소실, 경고 0).

뿌리는 **성격이 다른 두 부류에 한 정책**이었다 — 완료 기준·영향 문서는 누적
사실이고 Progress·Status 는 현재값이다.

- 누적 필드(`affected_documents` · `done_criteria` · `result` · `risks` ·
  `follow_up`)는 이제 **기본이 병합**이다.
- 교체는 `--replace-field <이름>` 으로 **명시**해야 하고, 그때 버려지는 값을
  경고에 싣는다.
- `--progress-note` · `--next-step` 은 `action="append"` 로 받되 2회 이상이면
  **거부**한다 — 한 줄 필드라 구분자를 도구가 지어내면 그것도 추측이다.

정책은 CLI 층에 두고 `merge_task_file` 은 저수준 setter 로 남겨 **시그니처를
안 깼다**.

### 2.8 fix(docs) — 문서의 '현재 버전' 이 5개 minor 고착 (`6d9ad763`)

`docs/RELEASE.md` 가 `현재 package version: 1.2.0` 이라 적고 있었고,
`INSTALLATION_AND_USAGE.md` 의 **복사해 실행하는 설치 명령 3개**(휠 URL · git
태그 · pi 태그)가 1.1.8/1.2.0 을 가리켰다.

**왜 못 잡았나**: 검사가 '본문 어딘가에 버전 문자열 존재' 만 봤는데, 같은
문서의 **회귀 표가 발행된 모든 버전을 영구히 담는다** — 새 행이 생기는 순간
그 검사는 원리적으로 red 가 될 수 없었다. 명시 필드 대조로 교체하고 상태 줄 ·
현재 릴리스 노트 링크 · 설치 명령 고정에 각각 case 를 신설했다.

### 2.9 fix(release) — pi 매니페스트 version 을 kit 에 묶는다 (`0c86b51f`)

`plugin/package.json` 의 `version` 이 1.2.0 에 고착해 있었다. 원인은 pi.dev
자산을 렌더 대상에서 빼는 예외였는데, **그 예외 자체는 옳다** (손으로 유지하는
자산이라고 문서화된 결정). 결정을 뒤집지 않고 결함만 좁혔다 — **구조는 손
유지가 맞지만 version 은 kit 을 따라야 한다.** 대상 파일·필드가 없으면
**loud 실패**한다 (갱신 못 한 것을 성공으로 보고하지 않는다).

## 3. 업그레이드 안내

### 3.1 gemini-cli 사용자 — migration (guarantee §4 의 3가지 정공법)

upstream(Google Gemini CLI) 종료로 하네스 자체가 사라졌고, 소유자 지시로 지원을
종료했다. **지금 당장 깨지는 것은 없다** — 이미 생성된 `GEMINI.md` 와
`gemini-extension.json` 은 디스크에 그대로 남고 계속 읽힌다. 우리가 **재생성**을
안 할 뿐이다.

| 상황 | 정공법 |
|---|---|
| 파일을 그대로 쓰겠다 | **자연 fallback** — 아무것도 안 해도 된다. 기존 파일은 kit 이 건드리지 않는다 |
| 다른 하네스로 옮기겠다 | **명시 path** — `--harness antigravity` 로 다시 emit 한다. Antigravity 는 같은 `~/.gemini/` 아래 살아 이행 비용이 가장 낮다 |
| 스크립트가 `--harness gemini-cli` 를 넘긴다 | **opt-in 없음 — 인자를 지운다.** rc=0 → **rc=2** 로 바뀌므로 CI 가 실패한다. 이것이 이 릴리스의 유일한 소비자 파괴면이다 (§0.1) |

`stable_guarantee.md` §4 의 gemini-cli 행은 **지우지 않고 은퇴로 표시**했다 —
그 표는 현재 지원 목록이 아니라 약속의 이력이다.

### 3.2 그 밖의 채널

- **antigravity 사용자**: `agy plugin install <repo>/plugin` 로 설치한다.
  무버전 사본이라 **재설치가 곧 갱신**이다.
- **plugin ZIP asset**: codex · claude-code 두 종은 종전대로 Release 에
  attach 된다. antigravity · grok-build · pi.dev 는 저장소 `plugin/` 에서
  직접 설치한다.
- **`wk doctor` 를 한 번 돌려 볼 것**: 이번 버전의 탐침은 이전 버전이 침묵하던
  자리 4곳을 말한다 — 사본 0 채널 · grok 설치본 · codex 경유지 · **자기 자신**.

## Reference

- 이전 release note: `Beta-v1.7.0.md`
- 등급 판단 정본: `docs/RELEASE.md` §1.5
- 배포 탐침 정본: `workflow-source/core/workflow_deployment_idempotency.md`

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-08-31T15:00:02Z)_

- total wiki pages: **95**
- total memory entries: **15**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
