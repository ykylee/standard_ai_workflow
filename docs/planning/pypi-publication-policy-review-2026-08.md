# PyPI 발행 정책 검토

- 문서 목적: v1.2.0 이 기술 제약을 없앤 뒤 남은 **정책 층**을 판단 가능한 형태로 정리한다 (TASK-2026-08-13-main-006).
- 범위: 이름 가용성, 공개 전 필수 수리, 비가역성, 정책 정본 위치, 대안 비교, 권고안
- 대상 독자: 배포 정책 소유자, maintainer
- 상태: **종결 (2026-08-14)** — 소유자 최종 결정 = **PyPI 발행 안 함**. 정책 정본은 [`../RELEASE.md`](../RELEASE.md) §1 각주 0 이고, 본 문서는 그 결정의 **근거 자료**로만 남는다
- 최종 수정일: 2026-09-04
- 관련 문서: [`./cli-distribution-review-2026-08.md`](./cli-distribution-review-2026-08.md) (§2 기술 제약 — v1.2.0 해소), [`../RELEASE.md`](../RELEASE.md), [`../../workflow-source/core/stable_guarantee.md`](../../workflow-source/core/stable_guarantee.md)

## 0. 한 줄 결론

> ⛔ **결정 완료 (2026-08-14, 소유자): 발행하지 않는다.** 배포는 이 저장소의 GitHub
> Releases 하나로 간다. 토큰·OIDC 운영 비용을 상시로 지는 대신 얻는 것이 지금 없고,
> 공개는 되돌릴 수 없는 2년 backward compat 약속을 낯선 소비자에게 지운다.
> **아래 §6 의 "실행 순서" 는 더 이상 계획이 아니다** — 3(TestPyPI 리허설)·4(발행 결정)
> 은 취소됐다. 재검토 조건은 `RELEASE.md` §1 **각주 0** 의 트리거 3개뿐이고, 그것이
> 성립하기 전에는 이 안건을 다시 올리지 않는다. 이 문서의 나머지는 그 판단의 근거다.


**기술적으로는 오늘 발행할 수 있다. 그러나 지금 발행하면 안 된다** — 공개 배포에
부적합한 결함 3건이 남아 있고, 그중 둘은 PyPI 의 **비가역성** 때문에 나중에 고칠 수
없는 자리(라이선스 전문 부재 / 버전 체계)다. 순서는 **수리 → TestPyPI 리허설 →
정책 결정 → 발행**이다.

> ✅ **수리 완료 (2026-08-13, TASK-2026-08-13-main-007)**: §2 의 3건이 전부 닫혔다
> (소유자 결정 = 버전은 **stable 정리**, 이메일은 **GitHub noreply**). wheel 실측:
> `licenses/LICENSE` 동봉 + `License-File: LICENSE` / `Development Status :: 5 -
> Production/Stable` / `Author-email: ykylee@users.noreply.github.com` /
> `__version__ == importlib.metadata.version(...) == "1.2.0"`.
> §4 의 정책 정본도 `docs/RELEASE.md §1` 로 이관했다.
> ~~**남은 단계는 §6 의 3(TestPyPI 리허설) 과 4(발행 여부 소유자 결정) 뿐이다.**~~
> → **둘 다 2026-08-14 에 닫혔다** — 4번의 답은 *발행 안 함* 이고, 그래서 3번은 취소됐다 (§0).

## 1. 현황 — 전부 실측 (2026-08-13, v1.2.0-beta 기준)

| 항목 | 실측값 | 판정 |
|---|---|---|
| 이름 `standard-ai-workflow` (PyPI) | HTTP 404 | **미점유 — 발행 가능** |
| 이름 (TestPyPI) | HTTP 404 | 미점유 |
| wheel top-level | `['workflow_kit']` | ✅ v1.1.8 까지의 차단 사유 해소 |
| 소비자 경로 (격리 venv 에 wheel 만 설치) | `wk --help` 정상, console script **37개** | ✅ 동작 |
| 런타임 의존성 | pydantic / anyio 계열 6개 | ✅ 가볍다 |
| sdist 내용물 | 221 파일 (`workflow_kit` 204 + 메타) | ✅ 메모리 계층·비밀 유출 **0** |
| `twine check` | PASSED (whl + sdist) | ✅ |
| CI publish job | 없음 | Trusted Publishing 미구성 |

기술 준비도는 [`cli-distribution-review-2026-08.md`](./cli-distribution-review-2026-08.md)
§2 가 남긴 유일한 blocker(일반명 top-level `tools`/`bootstrap_lib`)가 v1.2.0 의
2nd deprecation cycle 로 사라지면서 충족됐다. 재유입은
`check_packaging.FORBIDDEN_IMPORTS` 가 wheel 실측으로 막는다.

## 2. 공개 전 반드시 고쳐야 하는 것 (실측으로 나온 결함 3건)

### 2.1 LICENSE 파일이 없다 — 공개 배포 blocker

`pyproject.toml` 은 `license = "MIT"` 를 선언하고 wheel 메타에도
`License-Expression: MIT` 가 들어간다. 그런데 **저장소에 LICENSE 파일이 없고,
배포물 안에도 라이선스 전문이 없다** (wheel 내 `LICENSE`/`COPYING` 검색 결과 0건).

MIT 라이선스 본문은 "저작권 고지와 본 허가 고지를 소프트웨어의 모든 사본에
포함해야 한다" 를 조건으로 한다. 전문이 배포물에 없으면 **그 조건을 이행할 수단
자체가 없고**, 재배포자는 무엇을 포함해야 하는지 알 수 없다. 통제된 반경(사내
clone) 에서는 드러나지 않던 문제가 공개 배포에서 곧바로 실질이 된다.

→ 저장소 루트에 `LICENSE` 추가 + `pyproject.toml` 이 배포물에 싣도록 선언.

### 2.2 버전 체계가 스스로와 모순된다 — PyPI 가 이 모순을 강제로 드러낸다

같은 릴리스가 표면마다 다른 성숙도를 주장한다:

| 표면 | 값 | 의미 |
|---|---|---|
| 배포 파일명 / PyPI 버전 | `1.2.0` | **final release** (pip 이 기본으로 잡는다) |
| 런타임 `workflow_kit.__version__` | `v1.2.0-beta` | beta |
| git tag / GH Release 제목 | `v1.2.0-beta` / "Beta v1.2.0" | beta |
| pyproject classifier | `Development Status :: 4 - Beta` | beta |
| `core/stable_guarantee.md` | **v1.0.0 stable 진입 (2026-07-20), 2년 보증** | stable |

GitHub Releases 에서는 이 모순이 무해했다 — 태그 이름이 곧 라벨이고 소비자는
릴리스 페이지를 읽는다. **PyPI 에서는 무해하지 않다**: `pip install
standard-ai-workflow` 는 pre-release 를 기본으로 건너뛰므로, `1.2.0` 으로 올리면
"스스로 beta 라 부르는 물건이 stable 로 배포"되고, `1.2.0b0` 으로 올리면
`--pre` 없이는 아무도 못 받는다. 둘 중 하나를 **정하는 것**이 발행의 전제다.

부수 발견 — **문서가 실물과 갈라져 있다**: `docs/RELEASE.md` 는 산출물 예시를
`standard_ai_workflow-<X>.<Y>.<Z>b0-py3-none-any.whl` 로 적는데(4곳),
실제 릴리스 asset 은 **v1.0.0 · v1.1.4 · v1.1.8 · v1.2.0 어디에도 `b0` 가 없다**
(GH Release asset 실측). 하필 이번 결정의 핵심 지점에서 문서가 사실이 아니다.

→ 소유자 결정 필요: **(a) stable 로 정직하게 간다** (`-beta` 접미사 정리 +
classifier `5 - Production/Stable` — `stable_guarantee.md` 가 이미 그렇게 선언했다)
**vs (b) pre-release 로 간다** (`1.2.1b0` 형식 + `-beta` 유지). 어느 쪽이든
`RELEASE.md` 의 `b0` 예시는 실물에 맞춰 정정한다.

### 2.3 저자 이메일이 영구 공개된다

wheel 메타: `Author-email: yklee <ddn777@hotmail.com>`. PyPI 프로젝트 페이지와
JSON API 에 **영구 노출**되며, 발행 후 메타를 고쳐도 이미 올라간 버전의 메타는
바꿀 수 없다(2.4 참조). 개인 메일을 공개할 의사가 없다면 발행 **전에** 별칭 주소나
프로젝트 주소로 교체해야 한다.

## 3. 비가역성 — 이 결정의 핵심

PyPI 는 GitHub Releases 와 되돌리기 성질이 다르다. 정책 판단은 여기에 걸린다.

- **같은 (이름, 버전, 파일명) 재업로드 불가.** 잘못 올린 파일을 고쳐 덮어쓸 수 없다.
- **삭제해도 그 버전 번호는 영구 소각.** 지운 뒤 같은 번호로 다시 올릴 수 없다.
- **yank 는 취소가 아니다.** 새 설치에서 숨겨질 뿐, 이미 핀을 박은 소비자는 계속 받는다.
- **공개는 약속을 낯선 사람에게 구속시킨다.** `stable_guarantee.md` 의 2년
  backward compat(2026-07-20 ~ 2028-07-20, 25 entries) 은 지금은 통제된 반경 안의
  약속이다. PyPI 공개는 이 약속의 수신자를 "우리가 모르는 사람" 으로 바꾼다.
- 반대 방향의 비가역성도 있다: **이름은 선점된다.** `standard-ai-workflow` 는 현재
  미점유이고, 이는 기회이자 **스쿼팅 노출**이다.

즉 되돌릴 수 있는 것은 "발행하지 않기로 한 결정" 뿐이고, 발행은 되돌릴 수 없다.
→ 그래서 §2 의 3건은 **발행 전에** 끝나야 한다.

## 4. 정책의 정본이 저장소 밖에 있다

`workflow_kit/tools/release_pipeline.py` 가 정책을 이렇게 인용한다:

```
PyPI/TestPyPI 업로드 ❌ (memory #5 의 release 채널 정책 — GitHub Releases 만).
- memory #5 standard-ai-workflow.md (release 채널 정책: GitHub Releases 만)
```

**`memory #5` 는 에이전트 메모리 파일이지 저장소 문서가 아니다.** 소비자도, 새
에이전트도, 미래의 maintainer 도 열어볼 수 없는 자리에 정책 정본이 있다. 저장소
안의 선언은 `docs/RELEASE.md` §1 (채널 표 — PyPI/TestPyPI ❌, v0.5.7 부터) 이므로,
**정본은 그쪽으로 옮기고 코드 주석은 그것을 가리키게** 해야 한다. 정책을 바꾸든
유지하든, 바꿀 자리가 하나여야 한다.

## 5. 대안 비교

| # | 방식 | 되돌리기 | 얻는 것 | 비용/리스크 |
|---|---|---|---|---|
| A | **현상 유지** (GH Releases 만) | — | 정책 변경 0, 절차 이미 6회 검증 | 이름 스쿼팅에 계속 노출. 소비자는 긴 URL |
| B | **TestPyPI 리허설만** | 가능 (이름 예약 아님) | 업로드 경로·메타 렌더링 실측, 결함이 진짜 PyPI 전에 드러남 | 거의 없음 — §2 수리의 검증 수단 |
| C | **이름만 선점** (0.0.0 placeholder 발행) | 사실상 불가 | 스쿼팅 차단 | 빈 패키지가 영구히 남는다. 인상이 나쁘고 §2 미해결 상태로 공개됨 |
| D | **정식 발행** | **불가** | 도달성 최대, `uv tool install standard-ai-workflow` | §2 3건 선행 필수 + 2년 보증이 대외 구속력 + 유지 부담 |

C 는 권하지 않는다 — 선점 이득보다 "빈 패키지를 영구히 남긴다" 는 비용이 크고,
§2 를 면제해 주지도 않는다 (v1.1.8 검토가 "이름 예약이 §2 를 면제하지 않는다" 고
쓴 것과 같은 논리).

## 6. 권고안

**지금 소유자가 결정할 것은 "발행이냐" 가 아니라 아래 두 가지다.**

1. **버전 정체성** (§2.2): stable 로 갈 것인가, pre-release 로 갈 것인가.
   `stable_guarantee.md` 는 이미 stable 을 선언했으므로 **(a) stable 정리**가
   일관적이다 — 이건 PyPI 와 무관하게 지금 정리할 가치가 있다.
2. **공개 의사**: 2년 backward compat 약속을 낯선 소비자에게 지는 것을 받아들이는가.

**실행 순서 (권고)**

1. §2 수리 3건 — LICENSE 추가 / 버전 체계 확정 + `RELEASE.md` 의 `b0` 예시 정정 /
   저자 이메일 확인. **PyPI 결정과 무관하게 지금 해도 손해가 없다** (전부 GitHub
   Releases 소비자에게도 이득).
2. §4 정책 정본 이관 — `docs/RELEASE.md` 를 정본으로, 코드 주석은 참조로.
3. **B (TestPyPI 리허설)** — `wk release-dist` 가 명령을 이미 출력한다. 이름 예약이
   아니므로 정책 변경 없이 실행 가능하고, §1 의 "적기 전에 실측한다" 관행에 맞다.
4. 그 다음에 **D 를 소유자가 결정**. 발행한다면:
   - **Trusted Publishing (OIDC)** 로 구성한다 — API 토큰을 저장소/CI 에 두지 않는다.
   - 첫 발행은 **낮은 위험 버전**으로 (예: 다음 patch) — 첫 업로드에서 메타 결함이
     드러나도 소각되는 번호가 최신 minor 가 아니게 한다.

## 6.1 TestPyPI 리허설 결과 (2026-08-13, TASK-2026-08-13-main-008)

> ⛔ **취소 (2026-08-14)**: 이 리허설의 목적은 *PyPI 발행 여부 판단*의 사전 검증이었다.
> 발행하지 않기로 결정됐으므로 목적이 사라졌다. **업로드는 실행되지 않았고 앞으로도
> 하지 않는다.** 아래 표(업로드 직전까지의 실측)는 **이력으로 보존**한다 — GitHub
> Releases 소비자에게도 유효한 검증이기 때문이다 (README 렌더링·메타데이터·이름 해석·
> 라이선스 동봉·진입점). 아래 "남은 것" 의 토큰 발급 절차는 **더 이상 할 일이 아니다.**

소유자 지시로 리허설에 착수했다. **업로드 직전까지의 검증은 전부 통과**했고,
업로드 자체는 자격 증명 부재로 **미실행**이다 (당시 status: blocked → 2026-08-14 취소).

| 검증 | 방법 | 결과 |
|---|---|---|
| README 렌더링 (PyPI 거부 1순위) | `twine check --strict` (twine 6.2.0) | whl·sdist **PASSED** |
| 메타데이터 완결성 | wheel METADATA 실측 | Name/Version/Summary/3 Project-URL/`Description-Content-Type: text/markdown`/의존 12줄 |
| **이름으로** 인덱스 해석 | `pip install --find-links dist --extra-index-url pypi.org/simple "standard-ai-workflow==1.2.0"` | 정상 (파일 경로가 아니라 **이름** 해석 경로 — TestPyPI 소비자와 같은 축) |
| extras 해석 | 같은 방식 `[mcp-sdk]` | 정상 (mcp 2.0.0 해석 + 브리지 import) |
| 라이선스 동봉 | 설치본 metadata `files` | `…dist-info/licenses/LICENSE` |
| 진입점 | 격리 venv `wk --help` | 정상 |
| **PEP 639 서버 수용** | pypi.org JSON API 실측 | Warehouse 가 `license_expression`/`license_files` 를 **서빙한다** → Metadata 2.4 아티팩트 수용됨 |
| 업로드 엔드포인트 | `https://test.pypi.org/legacy/` | HTTP 200 |

**~~남은 것 — 소유자만 할 수 있다.~~** — ⛔ 2026-08-14 취소. 아래는 이력이다.

1. **TestPyPI API 토큰.** 이 환경에 자격 증명이 없다 (`~/.pypirc` 부재,
   `TWINE_*`/`UV_PUBLISH_TOKEN` 전부 미설정). 토큰은
   <https://test.pypi.org/manage/account/token/> 에서 발급한다.
   ⚠️ **토큰을 에이전트 세션에 붙여넣지 말 것** — 세션 기록에 남는다.
   본인 터미널에서 실행하거나 `~/.pypirc` (chmod 600) 에 둔다.

   ```bash
   cd /home/yklee/repos/standard_ai_workflow/workflow-source
   TWINE_USERNAME=__token__ TWINE_PASSWORD='<TestPyPI 토큰>' \
     ../.venv/bin/python -m twine upload \
       --repository-url https://test.pypi.org/legacy/ \
       dist/standard_ai_workflow-1.2.0-py3-none-any.whl \
       dist/standard_ai_workflow-1.2.0.tar.gz
   ```

   업로드 후 소비자 경로 확인 (TestPyPI 에는 pydantic/anyio 가 없으므로
   `--extra-index-url` 이 **필수**다 — 이번 리허설에서 같은 해석 동학을 실측했다):

   ```bash
   python3 -m venv /tmp/tpy && /tmp/tpy/bin/pip install \
     --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple \
     "standard-ai-workflow==1.2.0"
   /tmp/tpy/bin/wk --help
   ```

2. ~~**정책 행 처리.**~~ — ✅ **해소 (2026-08-13, 소유자 결정 = (a) 1회 한정 허용)**.
   [`../RELEASE.md`](../RELEASE.md) §1 의 TestPyPI 행이 **⚠️ 1회 한정 허용
   (리허설 목적)** 으로 갱신됐고, 같은 절의 **각주 1** 이 범위를 좁게 고정한다:
   `1.2.0` 아티팩트 1회 업로드만, 다른 버전·상시 편입·실사용 PyPI 는 범위 밖,
   TestPyPI 링크를 설치 경로로 문서에 싣지 않음, 1회가 끝나면 각주도 만료.
   **공식 배포 채널은 여전히 GitHub Releases 하나다** — 이 허용은 채널 추가가
   아니라 발행 전 검증 1회를 여는 것이다.

**비가역성 주의**: TestPyPI 도 같은 (이름, 버전, 파일명) 재업로드가 불가하다.
`1.2.0` 을 올리면 TestPyPI 에서 그 번호는 소각된다 (실사용 PyPI 이름 예약과는
무관 — 별개 인덱스다). 결함이 발견되면 다음 번호로 다시 리허설한다.

## 7. 이번에 하지 않은 것

- **PyPI/TestPyPI 실업로드** — 하지 않았다. 발행은 소유자 결정이고 비가역이다.
  TestPyPI 리허설은 §6.1 대로 **업로드 직전까지** 진행했고 업로드만 남았다.
- §2 결함 3건의 수리 — 본 검토는 판정까지다. 수리는 별건 task 로 등록한다.
- Trusted Publishing 워크플로 작성 — 발행 결정 이후의 일.
- `wk` 콘솔 스크립트 이름 충돌 조사 — PyPI 에 `wk` 라는 **별개 패키지**가 존재한다
  (v1.0, sdist only). 권장 설치 경로가 uv/pipx 격리라 실사용 충돌 가능성은 낮다고
  보지만, 같은 venv 설치 시나리오는 미실측으로 남긴다.
