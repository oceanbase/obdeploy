#!/bin/bash

if [ -n "$BASH_VERSION" ]; then
    complete -F _obd_complete_func obd
fi

function _obd_complete_func   
{  
    local cur prev cmd obd_cmd cluster_cmd mirror_cmd test_cmd
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    obd_cmd="mirror cluster test update"
    cluster_cmd="start deploy redeploy restart reload destroy stop edit-config list display upgrade"
    mirror_cmd="clone create list update"
    test_cmd="mysqltest"
    if [[ ${cur} == * ]] ; then
        case "${prev}" in
            obd);&
            test);&
            cluster);&
            mirror)
                cmd=$(eval echo \$"${prev}_cmd")
                COMPREPLY=( $(compgen -W "${cmd}" -- ${cur}) )
            ;;
            clone);&
            -p|--path);&
            -c|--config)
                filename=${cur##*/}
                dirname=${cur%*$filename}
                res=`ls -a -p $dirname 2>/dev/null | sed "s#^#$dirname#"`
                compopt -o nospace
                COMPREPLY=( $(compgen -o filenames -W "${res}" -- ${cur}) )
            ;;
        esac
        return 0
    fi
}

