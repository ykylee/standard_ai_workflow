#compdef wk
# zsh completion for `wk` (CLI 化 B안, v1.1.2+)
#
# 설치:
#   fpath=(/path/to/workflow-source/tools/completions $fpath)
#   autoload -Uz compinit && compinit
#
# bash 판과 같은 원칙 — 커맨드 목록은 `wk --list-commands` 에서 받는다. 하드코딩하면
# tool 이 늘 때마다 두 곳을 고쳐야 하고, 한쪽을 잊는 순간 completion 이 거짓말을 한다.

_wk() {
    local -a commands
    local cache_policy

    zstyle -s ":completion:${curcontext}:" cache-policy cache_policy
    if [[ -z "$cache_policy" ]]; then
        zstyle ":completion:${curcontext}:" cache-policy _wk_cache_policy
    fi

    if ! _retrieve_cache wk_commands; then
        commands=( ${(f)"$(wk --list-commands 2>/dev/null)"} )
        _store_cache wk_commands commands
    fi

    _arguments -C \
        '(- *)--list-commands[list every command name, one per line]' \
        '(- *)'{-h,--help}'[show usage]' \
        '1: :->command' \
        '*:: :->args'

    case "$state" in
        command)
            _describe -t commands 'wk command' commands
            ;;
        args)
            # 각 tool 의 flag 는 그쪽 argparse 가 정본이다. 여기서 흉내내지 않고
            # 파일 완성만 준다.
            _files
            ;;
    esac
}

_wk_cache_policy() {
    # 하루 지나면 다시 받는다 — tool 이 늘어도 하루 안에 따라잡는다.
    local -a oldp
    oldp=( "$1"(Nmh+24) )
    (( $#oldp ))
}

_wk "$@"
