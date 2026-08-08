# bash completion for `wk` (CLI 化 B안, v1.1.2+)
#
# 설치:
#   source /path/to/workflow-source/tools/completions/wk.bash
#   (또는 ~/.bash_completion.d/ 에 심볼릭 링크)
#
# 커맨드 목록을 하드코딩하지 않는다 — `wk --list-commands` 가 정본
# (`workflow_kit_cli.COMMANDS`) 을 그대로 흘린다. 새 tool 이 늘면 여기는 안 고쳐도
# 된다. 목록은 첫 호출에 한 번만 받아 캐시한다 (매 <TAB> 마다 python 기동은 느리다).

_wk_completions() {
    local cur prev
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # 첫 번째 인자만 커맨드 이름. 그 뒤는 각 tool 의 argparse 영역이라
    # 파일 경로 기본 완성에 맡긴다 (tool 별 flag 를 여기서 흉내내면 곧 갈라진다).
    if [ "$COMP_CWORD" -gt 1 ]; then
        case "$cur" in
            -*) COMPREPLY=() ;;
             *) COMPREPLY=( $(compgen -f -- "$cur") ) ;;
        esac
        return 0
    fi

    if [ -z "$_WK_COMMAND_CACHE" ]; then
        _WK_COMMAND_CACHE="$(wk --list-commands 2>/dev/null)"
    fi

    COMPREPLY=( $(compgen -W "$_WK_COMMAND_CACHE --list-commands --help" -- "$cur") )
    return 0
}

complete -F _wk_completions wk
