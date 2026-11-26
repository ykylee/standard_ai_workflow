# Beta v3.6.0 — 허브 계정 관리자 권한 (2026-11-26)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- 허브 계정에 관리자 권한을 줄 수 있다(`hub_account.is_admin`). 관리자 계정은 로그인만으로 관리 화면(하네스 제보 검토 · 사람 명부 · 계정 관리자 권한 · 콜사인 정리)을 admin 토큰과 같은 권한으로 연다.
- 프로젝트 화면은 그 프로젝트에 연결된 사람 콜사인이 있으면 콜사인 권한, 없으면 관리자로 읽는다.
- 첫 관리자는 서버에서 정한다: `hub admin --db <DB> account admin --username <계정> --grant` (`--revoke` · `account list`). Python · Go 같다.
- 관리 화면에 **계정 관리자 권한** 표를 더했다 — 관리자(토큰 또는 관리자 계정)가 주고 거둔다. 권한은 요청마다 DB 에서 읽어 거두면 다음 요청부터 일반 계정이다.
- 바꿀 때마다 `grant_admin` · `revoke_admin` 이벤트와 행위자(`admin:hub` · `admin:<토큰 이름>` · `account:<계정>`)가 남는다.

## 검증

- 누적 smoke **360/360 PASS**
- `check_hub_ui` case 19 가 Python · Go 실프로세스를 같은 시나리오로 잰다(부여 전 403 · CLI 부여 · 관리 API · 화면에서 주고 거둠 · 즉시 반영 · 이벤트 행위자).
- `check_hub_screens` 가 실제 Chrome 으로 관리자 계정의 토큰 없는 관리 화면과 단추로 권한 거두기를 두 런타임에서 잰다.
- 되주입 4건(모든 계정을 관리자로 · 권한 API 의 관리자 확인 제거 · 화면의 관리자 계정 경로 끄기 Python/Go 렌더)이 모두 red.

## 운영 범위

- **DB 판이 20 → 21로 오른다** — 3.5.x 실행 파일은 이관된 DB를 열지 못하므로 되돌리려면 배포 전 백업을 쓴다.
- 계정 비활성화 · 마지막 관리자 보호는 없다 — admin 토큰과 서버 CLI 가 늘 남는 복구 경로다. PostgreSQL 은 재지 않았다.
