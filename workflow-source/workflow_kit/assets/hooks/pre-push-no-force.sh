#!/bin/sh
# pre-push hook — 원격 이력을 덮어쓰는 push(force / non-fast-forward) 거부
# (§0.8 #4, TASK-2026-08-08-main-019 · 판정 재작성 TASK-2026-09-25-main-002).
#
# 표준 §5D.4 의 *3-layer defense* 중 2nd layer — 사람 / 스크립트가 `git push --force`
# 를 직접 실행할 때 client-side 에서 차단. POSIX `sh` (bash ❌). macOS default `sh` 정합.
#
# **git 이 hook 에 넘기는 것**: 인자는 `<remote name> <remote url>` 둘뿐이고, push 옵션
# (`--force` 등)은 **넘기지 않는다**. 대신 stdin 으로 ref 마다 한 줄:
#     <local ref> <local sha> <remote ref> <remote sha>
# 이전 판정은 인자에서 `--force` 를 찾았다 — 실제 `git push --force` 에서는 한 번도
# 발화하지 않았다 (2026-09-25 실측: non-fast-forward 가 `(forced update)` 로 통과).
# 검사도 스크립트에 `--force` 를 직접 넘겨 인터페이스를 재지 않았다.
#
# 판정 (ref 마다):
#   - remote sha 가 0 (원격에 새 ref) → 통과. 덮어쓸 이력이 없다.
#   - local sha 가 0 (원격 ref 삭제) → 통과. force 가 아니다 (이 hook 의 범위 밖).
#   - remote sha 가 local sha 의 조상이 아님 → **거부**. 원격 이력을 덮어쓴다.
#     `--force` 를 줘도 fast-forward 면 덮어쓰는 것이 없으므로 통과한다.
#   - remote sha 를 이 저장소가 모름 (fetch 안 함) → **거부**. 조상인지 모르면
#     fast-forward 라는 근거가 없다 — 모름은 통과가 아니다.

set -u

rejected=""
while read -r local_ref local_sha remote_ref remote_sha; do
    [ -n "${local_ref:-}" ] || continue
    case "$remote_sha" in *[!0]*) ;; *) continue ;; esac
    case "$local_sha" in *[!0]*) ;; *) continue ;; esac
    if git merge-base --is-ancestor "$remote_sha" "$local_sha" 2>/dev/null; then
        continue
    fi
    if git cat-file -e "${remote_sha}^{commit}" 2>/dev/null; then
        why="원격 $remote_sha 가 로컬 $local_sha 의 조상이 아니다 (non-fast-forward)"
    else
        why="원격 $remote_sha 를 이 저장소가 모른다 — fast-forward 인지 확인할 수 없다 (fetch 후 다시)"
    fi
    rejected="${rejected}
  - ${local_ref} → ${remote_ref}: ${why}"
done

if [ -n "$rejected" ]; then
    cat >&2 <<EOF
ERROR: 원격 이력을 덮어쓰는 push 가 감지되었습니다 (${1:-remote}).${rejected}

이 hook 은 §0.8 #4 의 client-side 이중화 정공법입니다 (TASK-2026-08-08-main-019).
표준 §5D.4 — *되돌릴 수 없는 작업은 사람 / 명시적 확인 후*.

해결책:
  1. 원격을 받아 합친 뒤 일반 push: \`git pull --rebase\` 후 \`git push\`
  2. 정말 덮어써야 하면 사람이 확인한 뒤 이 한 번만 hook 을 건너뛴다:
       git push --force --no-verify <remote> <branch>
  3. Server-side branch protection 도 권고 (GitHub / Gitea repo settings).
EOF
    exit 1
fi
exit 0
