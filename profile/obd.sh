#!/bin/bash


if [ -n "$BASH_VERSION" ]; then
    complete -F _obd_complete_func obd
fi


function _obd_reply_current_files() {
    filename=${cur##*/}
    dirname=${cur%*$filename}
    res=`ls -a -p $dirname 2>/dev/null | sed "s#^#$dirname#"`
    compopt -o nospace
    COMPREPLY=( $(compgen -o filenames -W "${res}" -- ${cur}) )
}


function _obd_reply_deploy_names() {
    res=`ls -p $obd_home/.obd/cluster 2>/dev/null | sed "s#/##"`
    COMPREPLY=( $(compgen -o filenames -W "${res}" -- ${cur}) )
}

function _obd_reply_tool_commands() {
    cmd_yaml=$obd_home/.obd/plugins/commands/0.1/command_template.yaml
    sections=`grep -En '^[0-9a-zA-Z]:' $cmd_yaml`
    for line in sections
    do
      num=`echo $line | awk -F ':' '{print $1}'`
      section=`echo $line | awk -F ':' '{print $2}'`
      if [[ "$section" == "commands" ]];then
        start_num=num
      elif [[ "$start_num" != "" ]];then
        end_num=num
      fi
    done
    if [[ "$end_num" == "" ]]; then
      end_num=`cat $cmd_yaml | wc -l`
    fi
    total_num=$((end_num - start_num))
    res=`grep -E '^commands:' $cmd_yaml -A $total_num | grep name | awk -F 'name:' '{print $2}' | sort -u | tr '\n' ' '`
    COMPREPLY=( $(compgen -o filenames -W "${res}" -- ${cur}) )
}

function _obd_reply_primary_standby_tenant_names() {
    input=`cat $HOME/.obd/cluster/$1/inner_config.yaml|grep standby_relation`
    quotes_rx='^[^"]*"([^"]*)"(.*)$'

    quoted_strings=""
    while [[ $input =~ $quotes_rx ]]; do
      tmpvalue=${BASH_REMATCH[1]}
      if (( ! $(echo $tmpvalue | grep -c ":") ))
      then
          quoted_strings="$quoted_strings $tmpvalue"
      fi
        input=${BASH_REMATCH[2]}
    done
    COMPREPLY=($quoted_strings)

}

function _obd_complete_func
{

  local all_cmds
  declare -A all_cmds
  COMPREPLY=()
  obd_home=${OBD_HOME:-~}
  env_file=${obd_home}/.obd/.obd_environ
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev=${!#}

  all_cmds["obd"]="mirror cluster test update repo demo web obdiag display-trace binlog license pwd host pref"
  all_cmds["obd cluster"]="autodeploy tenant component start deploy redeploy restart reload destroy stop edit-config takeover export-to-ocp list display upgrade chst check4ocp reinstall scale_out init4env"
  all_cmds["obd cluster *"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant"]="create drop show create-standby switchover failover decouple optimize set-backup-config backup restore backup-show restore-show backup-cancel restore-cancel switch-log-source recover"
  all_cmds["obd cluster tenant *"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant create-standby *"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant switchover *"]="_obd_reply_primary_standby_tenant_names $prev"
  all_cmds["obd cluster tenant failover *"]="_obd_reply_primary_standby_tenant_names $prev"
  all_cmds["obd cluster tenant decouple *"]="_obd_reply_primary_standby_tenant_names $prev"
  all_cmds["obd cluster tenant create-standby"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant switchover"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant failover"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant decouple"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant backup"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant set-backup-config"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant restore"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant backup-show"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant restore-show"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant backup-cancel"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant restore-cancel"]="_obd_reply_deploy_names"
  all_cmds["obd cluster tenant switch-log-source"]="_obd_reply_deploy_names"
  all_cmds["obd clister tenant recover"]="_obd_reply_deploy_names"
  all_cmds["obd cluster component"]="add del"
  all_cmds["obd cluster component *"]="_obd_reply_deploy_names"
  all_cmds["obd license"]="load show"
  all_cmds["obd license *"]="_obd_reply_deploy_names"
  all_cmds["obd mirror"]="clone create clean list update enable disable"
  all_cmds["obd mirror clone"]="_obd_reply_current_files"
  all_cmds["obd repo"]="list"
  all_cmds["obd test"]="mysqltest sysbench tpch tpcc"
  all_cmds["obd test *"]="_obd_reply_deploy_names"
  all_cmds["obd web *"]="install upgrade"
  all_cmds["obd web install *"]="_obd_reply_deploy_names"
  all_cmds["obd web upgrade *"]="_obd_reply_deploy_names"
  all_cmds["obd obdiag"]="check gather deploy analyze rca update"
  all_cmds["obd obdiag gather"]="all log clog slog obproxy_log perf plan_monitor stack sysstat scene ash dbms_xplan parameter tabledump variable"
  all_cmds["obd obdiag gather scene"]="run list"
  all_cmds["obd obdiag gather scene *"]="_obd_reply_deploy_names"
  all_cmds["obd obdiag gather *"]="_obd_reply_deploy_names"
  all_cmds["obd obdiag analyze"]="log flt_trace index_space memory parameter queue variable"
  all_cmds["obd obdiag analyze *"]="_obd_reply_deploy_names"
  all_cmds["obd obdiag check"]="list run"
  all_cmds["obd obdiag check *"]="_obd_reply_deploy_names"
  all_cmds["obd obdiag rca"]="list run"
  all_cmds["obd obdiag rca *"]="_obd_reply_deploy_names"
  all_cmds["obd obdiag display scene"]="run list"
  all_cmds["obd obdiag display scene *"]="_obd_reply_deploy_names"
  all_cmds["obd binlog"]="create show start stop drop"
  all_cmds["obd binlog *"]="_obd_reply_deploy_names"
  all_cmds["obd binlog start"]="_obd_reply_deploy_names"
  all_cmds["obd binlog stop"]="_obd_reply_deploy_names"
  all_cmds["obd binlog drop"]="_obd_reply_deploy_names"
  all_cmds["obd binlog create"]="_obd_reply_deploy_names"
  all_cmds["obd binlog create *"]="_obd_reply_deploy_names"
  all_cmds["obd binlog start *"]="_obd_reply_deploy_names"
  all_cmds["obd binlog stop *"]="_obd_reply_deploy_names"
  all_cmds["obd binlog drop *"]="_obd_reply_deploy_names"
  all_cmds["obd tool"]="list install uninstall update"
  all_cmds["obd host"]="precheck init user"
  all_cmds["obd host user"]="init"
  all_cmds["obd pwd"]="encrypt set-epk"

  # if [ -f "$env_file" ] && [ "$(grep '"OBD_DEV_MODE": "1"' "$env_file")" != "" ]; then
  all_cmds["obd"]+=" devmode env tool"
  all_cmds["obd devmode"]="enable disable"
  all_cmds["obd tool"]+=" command db_connect dooba"
  all_cmds["obd tool db_connect"]="_obd_reply_deploy_names"
  all_cmds["obd tool dooba"]="_obd_reply_deploy_names"
  all_cmds["obd tool command"]="_obd_reply_deploy_names"
  all_cmds["obd tool command *"]="_obd_reply_tool_commands"
  all_cmds["obd env"]="set unset show clear"
  # fi
  case $prev in
  list)
    return 0
    ;;
  -p|--path);&
  -c|--config|-f|--file)
    _obd_reply_current_files
    ;;
  *)
    valid_len=$COMP_CWORD
    words=( ${COMP_WORDS[@]::valid_len} )
    index=$valid_len
    while (( index >= 1 )); do
        target="${words[*]}"
        cmd=${all_cmds[$target]}
        if [[ "$cmd" != "" ]]
        then
          if [[ $cmd =~ ^_obd_reply.* ]]
          then
            $cmd
            break
          else
            COMPREPLY=( $(compgen -W "${cmd}" -- ${cur}) )
            break
          fi
        fi
        index=$(( index - 1))
        tmp=${words[*]::index}
        [[ "$tmp" != "" ]] && parent_cmd=${all_cmds[$tmp]}
        if [[ "$parent_cmd" =~ ^_obd_reply.*  || " $parent_cmd " =~ " ${words[index]} " ]]; then
          words[index]='*'
        else
          break
        fi
    done
    ;;
  esac


}
