#!/bin/bash

if [ -n "$BASH_VERSION" ]; then
    complete -F _obd_complete_func obd
fi

function _obd_complete_func   
{  
    local cur prev cmd obd_cmd cluster_cmd tenant_cmd mirror_cmd test_cmd devmode_cmd
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    obd_cmd="mirror cluster test update repo"
    cluster_cmd="autodeploy tenant start deploy redeploy restart reload destroy stop edit-config list display upgrade chst check4ocp change-repo"
    tenant_cmd="create drop"
    mirror_cmd="clone create list update enable disable"
    repo_cmd="list"
    test_cmd="mysqltest sysbench tpch"
    if [ -f "${OBD_HOME:-"$HOME"}/.obd/.dev_mode" ]; then
        obd_cmd="$obd_cmd devmode"
        devmode_cmd="enable disable"
    fi

    if [[ ${cur} == * ]] ; then
        case "${prev}" in
            obd);&
            test);&
            cluster);&
            tenant);&
            mirror);&
            devmode);&
            repo)
                cmd=$(eval echo \$"${prev}_cmd")
                COMPREPLY=( $(compgen -W "${cmd}" -- ${cur}) )
            ;;
            clone);&
            -p|--path);&
            -c|--config)
                filename=${cur##*/}
                dirname=${cur%*$filename}
                res=`ls -p $dirname 2>/dev/null | sed "s#^#$dirname#"`
                compopt -o nospace
                COMPREPLY=( $(compgen -o filenames -W "${res}" -- ${cur}) )
            ;;
            *)
                if [ "$prev" == "list" ]; then
                    return 0
                else
                    prev="${COMP_WORDS[COMP_CWORD-2]}"
                    obd_home=${OBD_HOME:-~}
                    if [[ "$prev" == "cluster" || "$prev" == "test" || "$prev" == "tenant" ]]; then
                        res=`ls -p $obd_home/.obd/cluster 2>/dev/null | sed "s#/##"`
                        compopt -o nospace
                        COMPREPLY=( $(compgen -o filenames -W "${res}" -- ${cur}) )
                    fi
                fi
        esac
        return 0
    fi
}

