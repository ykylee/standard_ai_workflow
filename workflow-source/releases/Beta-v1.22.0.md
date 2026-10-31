# Beta v1.22.0 (2026-10-31)

> **상태: 릴리스 준비.** package `1.22.0`, runtime `__version__ = 1.22.0`, tag `v1.22.0`.
> **minor release** — 한글 Windows(cp949 로캘) 프로필 확립 · Windows 격차 52건 해소 · 게이트 러너 Windows 결함 수리 · pre-push 삭제 push 차단.
>
> 등급 근거 (§1.5): `wk release-status` 의 파생 근거는 feat 1 · fix 3 · breaking 0 — **minor**.
> 공개 Python API 시그니처 변경 0, 진입점 제거 0. 새 모듈 `workflow_kit.common.file_lock` 이 **추가**다 (옛 소비자가 못 읽게 되는 변경 0).

## 0. 릴리스 판정

v1.21.0 이후 10커밋이 발행되지 않은 채 쌓였다. 코드 커밋은 넷이고 — 하나는 기능이고 셋은 수리다.

핵심은 **한글 Windows 에서 이 저장소가 처음부터 끝까지 돌게 만든 것** 이다. v1.21.0 시점에도 게이트의 정본 호스트는
Linux·macOS 였고 Windows 는 '미측정' 이었다. 이번 판에서 Windows(로캘 cp949) 호스트 하나에서 **전량 게이트
309 × native/slash 가 rc 0** 이 되고 그 증거가 커밋에 붙었다.

세 가지가 겹쳐 있었다. **① 인코딩** — `text=True` 서브프로세스 캡처는 **로캘(cp949)** 로 디코딩하는데, kit CLI 는
`common/stdio.force_utf8_stdio()` 로 UTF-8 을 강제하고 git 도 UTF-8 을 낸다 → 부모가 cp949 로 읽으면
UnicodeDecodeError → reader thread 가 죽고 `proc.stdout=None` → **AttributeError**. 증상이 '출력이 비었다' 가 아니라
무의미한 예외라 원인을 한참 헤맨다. **② CRLF** — 저장소가 CRLF 로 체크아웃돼 있었고, 툴이 `write_text` 로 쓴 파일은
Windows 에서 CRLF 가 되어 산출물 바이트가 호스트마다 달랐다. **③ POSIX 전제** — `fcntl` 파일 락, POSIX 권한비트 기대,
`/var/tmp`, 심볼릭 링크, POSIX 셸, `python3` 하드코딩 스폰.

이 셋은 **따로 고쳐도 남았다** — 그래서 근거를 나눠 하나씩 만들었다. 자식 환경은 `common/child_process.py` 한 곳에,
홈 해석은 `common/paths.py` 한 곳에, 파일 락은 `common/file_lock.py` 한 곳에 모았다.

## 1. 릴리스 요약

- 범위: `v1.21.0..` 발행 준비 직전까지 **10 commit** — 세션 기록 5건 · 직전 발행 마무리 1건을 빼면 실질 **4 commit** (feat 1 · fix 3).
- 누적 smoke **309/309 PASS** (로컬 `--branch-context=all` = 309 × native/slash, 발행 준비 커밋에서 실행).
- 검사 수 309 → 309 (새 검사 파일 0 — 기존 검사의 기대값·환경을 손봤다).

## 2. 소비자에게 보이는 변화

### 2.1 게이트 러너가 Windows 에서 죽지 않는다 (`46701fda`, TASK-2026-10-31-main-002)

`run_all_checks.py` 의 `_kill_process_group` 가 POSIX 전용 `os.getpgid`/`os.killpg` 를 쓰는데 이 함수는 매 검사
**완료 직후**에도 호출된다 → `AttributeError` 로 러너 전체가 죽어 **어떤 검사도 결과를 내지 못했다**(단일 검사
`--filter` 로도 동일 crash). Windows 는 `taskkill /PID <pid> /T /F` 로 트리를 정리하고 POSIX 경로는 그대로였다.

### 2.2 자식 프로세스가 "집을 못 찾는다" 로 죽지 않는다 (`b5148946` · `712e9414`, TASK-2026-10-31-main-003)

최소 환경(`env={"PYTHONPATH":…, "PATH":…}`)으로 띄운 자식에 `HOME`/`USERPROFILE` 이 없으면 `Path.home()` 이
`RuntimeError("Could not determine home directory.")` → **`import workflow_kit` 자체가 죽는다**(도구가 아무것도 못 한다).
`common/paths.py` 에 `user_home()`(`Path.home()` → RuntimeError → USERPROFILE → HOME → `tempfile.gettempdir()`)를
두고 kit 안 `Path.home()` **실제 호출 15줄**을 교체했다 — 발행 준비 시점 잔여 `Path.home()` 6건은 폴백 구현 1건과
주석·docstring 5건이라 **실제 호출은 0건**이다. 자식 환경 정본은 `common/child_process.py` 의
`home_env`·`tool_path`·`platform_child_env`·`platform_env` 다.

### 2.3 서브프로세스 출력이 UTF-8 로 읽힌다 (`b5148946` · `712e9414` + 발행 준비 추가 수리)

`text=True` 는 로캘(cp949) 로 디코딩한다 — kit CLI 와 git 이 UTF-8 을 내는 한 이것은 **반드시 깨진다**.
kit 안 `text=True` **114곳 전부**에 `encoding="utf-8", errors="replace"` 를 명시한다(발행 준비 시점 AST 실측 —
누락 0건). 검사 쪽 `text=True` **282곳도 282곳 전부** 명시한다. 러너는 자식에 `PYTHONUTF8=1` 을 고정한다.

> 발행 준비 중 **10곳이 더 발견·수리**되었다 — 앞선 수리가 `subprocess.run` 직접 호출만 세고 별칭 호출
> (`subprocess_run = _sp.run` · `sp.run`) 을 놓쳤었다. 3곳은 kit(`okf_import` · `archive_stale_memory` ·
> `url_validity`), 7곳은 검사(`check_code_index_update` 2 · `check_v0_7_24_release_notes_template` 1 ·
> `check_watch_transient_writer` 4)였다. 판정·기대값 변경이 아니라 **실측된 결함** 수리다.

### 2.4 저장소가 CRLF 를 기억하지 않는다 (`b5148946` · `712e9414` + 발행 준비 LF 스윕)

`.gitattributes` 에 `* text=auto eol=lf` + Windows 셸 스크립트만 `eol=crlf` 예외 + `*.sh`·`.githooks/**` LF,
저장소-local `core.autocrlf=false`. 정본 쓰기 헬퍼 `atomic_write_text`/`atomic_write_json` 은 `newline="\n"` 으로 고정 —
Windows 텍스트 모드의 CRLF 번역이 **산출물 바이트를 호스트마다 다르게** 만들었기 때문이다.

발행 준비에서 kit 안 `Path.write_text` **85건 전부**에 `newline="\n"` 을 명시했다. 이게 없으면 Windows 에서
`write_text` 가 CRLF 로 써서 **산출물이 호스트마다 달라진다** — `plugin/` payload 가 그 사례다.

> **드리프트 검사가 이걸 못 잡는 이유** — `plugin_payload` 의 drift 비교는 `read_text`(유니버설 newline) 라
> CRLF 이 **보이지 않는다**. 조용히 통과한다. 반면 `minimax_plugin` 은 `shutil.copyfile` **바이트 복사** +
> 바이트 대조라, 소스가 CRLF 면 설치본과 어긋나고 `content_drift` 가 영영 잡히지 않는다. 발행 준비에서
> 저장소 worktree CRLF **27개 파일**을 바이트 수준으로 LF 정규화하고, payload 24개 파일이 생성물과
> **바이트 일치**함을 확인했다.

### 2.5 저장소 상대경로는 항상 POSIX 다 (`712e9414`)

`str(Path.relative_to(…))` 는 Windows 에서 `\` 를 낸다 — 판정·기록·노트 경로가 갈라진다. 23줄을 `.as_posix()` 로
접었고(현재 사용 56곳), `release_pipeline` 의 note-draft `output_path` 가 `releases\Beta-v0.7.9.md` 로 나가던
문제도 같이 갔다.

### 2.6 파일 락이 Windows 에서도 실제로 막는다 (`712e9414`)

`common/file_lock.py` 를 신설했다 — Windows 는 `msvcrt.locking`, POSIX 는 `fcntl.flock`. 실측으로 확정된 함정 둘:
**락 영역과 보유자 정보 영역이 겹치면** contender 가 정보를 못 읽는다(OSError 13), **빈 파일**은 크기 0 뒤쪽을 잠갔을 때
파일 전체가 읽히지 않는다 → 락 전 최소 1바이트 확보(`prepare_lock_file`).

### 2.7 mypy 판정 기준이 배포 대상에 고정된다 (`712e9414`)

`[tool.mypy]` 에 `platform = "linux"` 를 고정했다 — 배포 대상은 POSIX 다. Windows 로컬 실행도 CI 와 같은 결과를 낸다
(227 source files · no issues).

### 2.8 pre-push 가 main · 태그의 삭제 push 를 막는다 (`dd8beb36`, TASK-2026-10-19-main-007)

기능 브랜치 삭제는 통과시키고 `main`·`master`·태그의 삭제만 막는다 — 복구 비용이 큰 것만 (소유자 결정 2026-10-19).

### 2.9 발행 사전점검이 Windows 에서도 통과한다 (발행 준비 중 추가 수리)

`release --apply` 의 사전점검 `packaging` 은 임시 venv 를 만들어 휠을 심는다 — 그런데 그 venv 의 `pip` 를
**`venv/bin/pip`** 로 고정했다. `python -m venv` 는 Windows 에서 `Scripts/pip.exe` 를 만든다 → 파일명이
틀려서 `pip install --upgrade pip` 가 **FileNotFoundError** 로 죽고 사전점검이 red 였다(휠 자체는 멀쩡했다).
**저장소에서 처음 시도한 Windows 발행**이라 여기서 처음 드러난 결함이다.

같은 자리에서 두 번째 결함이 이어졌다 — `pip.exe install --upgrade pip` 은 Windows venv 에서 **자기 자신을
고칠 수 없다**("To modify pip, please run: python -m pip install --upgrade pip") → rc 1. 정본 형식은
`python -m pip` 다 — POSIX/Windows 을 가리지 않는다.

`common/paths.py` 에 `venv_executable()` 를 정본으로 두고 `check_packaging` · `interpreter_matrix` ·
`sdk_matrix` 가 함께 쓴다 — POSIX 고정 경로가 세 곳에 복제돼 있었다.

## 3. 검증

- **전량 게이트** `--branch-context=all` — native 309/309 · slash 309/309 · rc 0. 발행 준비 커밋의 clean tree 에서
  실행하고, 결과는 발행 기록(게이트 증거 파일)에 남긴다.
- **커밋 전** `--changed` 게이트 — 변경 파일에 대응하는 검사만 돌려 red 가 없다는 것을 확인한다. 결과는 발행 기록에 남긴다.
- **스모크** `check_self_application` 8/8 rc 0.
- **발행 사전점검 `packaging`** — 1.22.0 휠을 **Windows 임시 venv** 에 심어 13개 서브패키지 import smoke ·
  `bootstrap_lib --help` 에 `--no-interactive` 존재 · `pip show` 메타데이터 — PASS. (§2.9 의 두 결함을 고친 뒤 실측)
- **mypy** 227 source files · no issues.
- **게이트 증거** `<git common dir>/gate_evidence/<sha>.json` — 발행 게이트가 HEAD sha 를 대조한다.
  기록은 **커밋 후 깨끗한 트리에서** 필터 없이 전량을 돌려 exit 0 일 때만 생긴다.

## 4. 알려진 한계 (감추지 않는다)

- **POSIX(Linux/macOS) 회귀 게이트는 Windows 호스트에서 돌릴 수 없다.** 이 판의 증거는 Windows(host
  DESKTOP-DGPLBF7) 하나다 — Linux·macOS 의 309×2 는 별도 호스트에서 확인해야 한다.
- **해석기 매트릭스는 Python 3.13 셀에서 3건이 red 였다.** 실패 3건은 모두 **저장소 게이트에서는 PASS 인 검사**
  (`check_watch_transient_writer` · `check_writer_reader_roundtrip` · `check_workspace_registry`) 라 격리
  매트릭스 환경 차이(저장소 밖 `--tmp-dir` · 격리 venv 의 workspace root · 좁은 meta-watch 선언)로 판정된다.
  Python 3.11 셀은 해석기 미설치로 **UNMEASURED** 다. 매트릭스 venv 경로(`bin/python`)의 POSIX 고정은
  §2.9 로 고쳤지만, 이 호스트엔 3.11 이 없어 **여전히 UNMEASURED** 다 — 통과가 아니다.
- **case 수 선언 대조 축 75건은 미측정**이다(개수 선언 없음 71 · case 줄 없음 4) — 통과가 아니라 미측정으로 남긴다.
- `common/auth.py` `_chmod_600()` · `common/bootstrap_lib/mcp.py` 의 `os.chmod(tmp, 0o600)` 는 Windows 에서 모드비트가
  무의미하다 — 판정을 바꾸지는 않고 기록만 남긴다.
- `common/atomic_write.py` 에는 Windows 재시도·고정 tmp 이름이 없다 — 이번 판의 watch 도구는 자체 구현으로 우회했다.
- `doctor` 의 `runtime_load` 절이 `ps` 를 못 부르면 프로세스 목록을 못 얻는다(Windows 한계) — `hosts_seen: 0` 은
  통과가 아니라 **해당 없음** 이다.
- **PyPI 업로드는 하지 않는다**(§1 각주 0 — 2026-08-14 소유자 최종 결정). 배포는 GitHub Releases 하나다.
