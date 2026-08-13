# 33차 세션 — PyPI 발행 준비 (2026-08-13)

- 문서 목적: TASK-2026-08-13-main-004·006·007·008 기록. v1.2.0 발행 직후 이어진 세션.
- 상태: done (008 만 blocked — 소유자 토큰 대기)
- 관련: [PyPI 검토](../../../../docs/planning/pypi-publication-policy-review-2026-08.md), [채널 정책 §1](../../../../docs/RELEASE.md)

## 요약

v1.2.0 이 기술 제약을 없앤 뒤, **PyPI 발행을 판단 가능한 상태까지** 밀었다.
결론: 기술 준비는 끝났고 **남은 것은 발행 여부라는 정책 결정 하나**다.

## TASK-004 — mypy flake 재발 확인 (관찰 1차, 계속 열림)

**재발 0건. 그러나 close 하지 않았다** — 5회 green 은 아무것도 증명하지 못한다.

조사 중 **기록이 실제보다 적다는 것을 발견**했다: task 는 1회로 적었지만 실제로는
**3회**였다 (2026-08-11 `4929aa5` check_mypy_strict_ci / 08-12 `f7209f4` ·
08-13 `2de04e8` release_gate, 전부 native 셀 단독). CI 로그는 만료됐지만
**annotation 은 남아** 검사 이름을 확인할 수 있었다.

3건이 transient 임을 실측했다 — 해당 커밋을 worktree 로 꺼내 지금 mypy 를 돌리면
clean 이고, 특히 `f7209f4`(red) → `e93e3b2`(green) 사이에는 **`.py` 변경이 0** 이다.

**핵심 계산**: 발생률 3/34 = run 당 8.8%. 개선이 **전혀 없어도** 5회 연속 green 이
나올 확률이 **63%** 다. 95% 신뢰에는 약 33 run 이 필요하다 → 완료 기준을 그
수치로 task 에 고정했다. 부수: 캐시 경합 가설 기각(`--no-incremental`), 검사
무력화 아님 확인.

## TASK-006 — PyPI 발행 정책 검토

산출물: `docs/planning/pypi-publication-policy-review-2026-08.md`.

판정: **기술적으로는 오늘 발행 가능하나 지금 발행하면 안 된다.** 이름은 미점유
(PyPI/TestPyPI 404), wheel top-level 은 `workflow_kit` 하나, 소비자 설치·sdist
유출 0·twine PASS 전부 실측. 그러나 공개 부적합 결함 3건이 있었고, **PyPI 는
비가역**이라 사후 수리가 불가능한 자리였다.

부수 발견: **정책 정본이 저장소 밖(agent memory)에 있었다** — 소비자도 새
기여자도 열어볼 수 없는 자리.

## TASK-007 — 공개 배포 전 필수 수리 3건

소유자 결정: 버전 = **stable 정리**, 이메일 = **GitHub noreply**.

1. **LICENSE** — `license = "MIT"` 선언만 있고 전문이 없어 MIT 의 "고지 포함"
   조건을 이행할 수단이 없었다. 루트 정본 + build root 사본 + `license-files`,
   wheel 에 `licenses/LICENSE` 동봉 실측. 사본 드리프트는 drift-prevention
   **case 7** 이 되주입 실증으로 고정.
2. **버전 체계** — `stable_guarantee.md` 는 2026-07-20 에 stable 진입을 선언했는데
   배포 표면만 beta 라벨이었다. `__version__` 이 PEP 440 그대로가 되어
   `importlib.metadata` 와 일치(격리 venv 실측), classifier 5-Production/Stable,
   tag·제목 `v<X.Y.Z>`. `RELEASE.md` 의 **사실이 아니던** `b0` 예시 8곳 정정
   (v1.0.0 이후 어느 asset 에도 b0 는 없었다).
   → 형식 단정 **10개 검사**가 한꺼번에 red 가 됐고 전량이 전부 잡았다.
3. **저자 이메일** → `ykylee@users.noreply.github.com`.

부수 3건: 정책 정본을 `docs/RELEASE.md §1` 로 이관 / `write_workflow_kit_version`
의 **무음 skip → loud raise** (포맷이 바뀌면 조용히 안 고치고 "갱신했다" 를
반환하던 자리) / drift-prevention 요약의 하드코딩 `6/6` → 실행 결과 파생
(case 를 더해도 빼도 6/6 이라 보고했다 — 내가 case 7 을 넣고 발견).

## TASK-008 — TestPyPI 리허설 (blocked)

업로드 직전까지 **8종 전부 통과**: twine check --strict / **이름으로** 인덱스 해석
설치 / extras `[mcp-sdk]` / LICENSE discoverable / wk 진입점 / 메타 완결성 /
**PEP 639 서버 수용 실측**(Warehouse 가 `license_expression` 서빙 → Metadata 2.4
수용) / 엔드포인트 200.

업로드 미실행 — 자격 증명이 이 환경에 없다. 정책 차단은 소유자 결정으로 해소:
`RELEASE.md §1` TestPyPI 행 = **⚠️ 1회 한정 허용** + **각주 1** 이 범위 고정
(1.2.0 1회만 / 다른 버전·상시 편입·실사용 PyPI 는 범위 밖 / 설치 경로로 문서화
금지 / 1회 종료 시 만료).

부수: `release_pipeline`·`release_pipeline_dist` 가 정책을 **재진술**하던 문안을
순수 포인터로 교체 — §1 이 바뀌자 "GitHub Releases only" 라는 재진술이 그 자리에서
거짓이 됐다. **사본은 갈라진다가 몇 분 만에 실증됐다.**

## 검증

전량 2축 **252/252 ×2 green** (세션 중 6회) + mypy strict 192 files 0 +
SDK 매트릭스 3/3 + push 후 CI green (커밋별 5~6 워크플로).

## 다음 축

- **TestPyPI 업로드** — 소유자 토큰만 남았다 (명령은 검토 §6.1). 토큰을 세션에
  붙여넣지 않는다.
- 그 다음 **PyPI 발행 여부 소유자 결정** (검토 §6-4). 발행 시 Trusted Publishing.
- TASK-004 관찰 계속 (33 run 기준, 현재 5).
