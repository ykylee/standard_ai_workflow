#!/bin/sh
# pre-push hook — `git push --force` 거부 (§0.8 #4, TASK-2026-08-08-main-019).
#
# 표준 §5D.4 의 *3-layer defense* — 사람 / 스크립트가 `git push --force` 를 직접 실행할
# 때 client-side 에서 차단. POSIX `sh` (bash ❌). macOS default `sh` 정합.
#
# 감지: --force, -f, --force-with-lease, --force-if-includes (전부 force 변형).
# 거절: stderr 메시지 + exit 1.
# 통과: exit 0 (그 외 모든 push — normal / dry-run / mirror 등).
#
# §0.8 #4 spec 결정:
#   - §5D.4 (1st layer): `claim_workspace.py` 가 --force option *없음*
#   - 이 hook (2nd layer): 사람 / 외부 스크립트의 직접 `git push --force` 차단
#   - server branch protection (3rd layer, 가이드만): GitHub / Gitea 설정

set -eu

# git push 가 호출하는 *모든* 인자 점검. "$@" 그대로.
# `git push --force origin main` → "$@" = "origin main --force" 또는
#   "origin main +force=true" 등. 우리는 첫 token + 나머지 token 양쪽 모두 확인.
# (git 의 hook interface 는 인자 그대로 전달.)

found_force=0
for arg in "$@"; do
    case "$arg" in
        --force|-f|--force-with-lease|--force-if-includes)
            found_force=1
            break
            ;;
    esac
done

# 추가: refspec 에 `+` prefix 가 있으면 force 로 간주 (e.g., `git push origin +main`).
# 단, `git push` 가 *전체* 인자열에 `+` 가 있는 경우는 별로 없으니 안전.
for arg in "$@"; do
    # refspec 형식 = `+local:remote` 또는 `+local`. "+" 로 시작하면 force.
    if [ "${arg#+}" != "$arg" ]; then
        found_force=1
        break
    fi
done

if [ "$found_force" = "1" ]; then
    cat >&2 <<'EOF'
ERROR: `git push --force` 가 감지되었습니다.
  (--force / -f / --force-with-lease / --force-if-includes / refspec + prefix)

이 hook 은 §0.8 #4 의 client-side 이중화 정공법입니다 (TASK-2026-08-08-main-019).
표준 §5D.4 — *되돌릴 수 없는 작업은 사람 / 명시적 확인 후*.

해결책:
  1. 일반 push 사용: `git push origin <branch>` (no --force)
  2. 정말 force 가 필요하면 hook 일시 해제:
       mv .git/hooks/pre-push .git/hooks/pre-push.disabled
       (작업 후 다시 mv 로 복원)
  3. Server-side branch protection 도 권고 (GitHub / Gitea repo settings).
EOF
    exit 1
fi

# 그 외 모든 push (normal / dry-run / tags / mirror) → 통과
exit 0
