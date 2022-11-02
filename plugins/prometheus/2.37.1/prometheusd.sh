home_path=$(pwd)
prometheusd_path=$home_path/run/prometheusd.pid
prometheus_path=$home_path/run/prometheus.pid

function _run() {
    mkdir -p $home_path/run


    cat $prometheusd_path | xargs kill -9

    echo $$ > $prometheusd_path
    if [ $? != 0 ]; then
        exit $?
    fi

    pid=`cat $prometheus_path`
    if [[ "$pid" != "" ]]
    then
      ls /proc/$pid > /dev/null
      if [ $? != 0 ]; then
          exit $?
      fi
      kill -9 $pid > /dev/null
    fi

    while [ 1 ];
    do
        sleep 1
        ls /proc/$pid > /dev/null
        if [[ $? != 0 || "$pid" == "" ]]; then
            cd $home_path || exit 1
            start
        fi
    done
}

function start() {
    $home_path/prometheus$args > $home_path/log/prometheus.log 2>&1 &
    pid=`ps -aux | egrep "$home_path/prometheus$args$" | grep -v grep | awk '{print $2}'`
    echo $pid > $prometheus_path
    if [ $? != 0 ]; then
        exit $?
    fi
}

function run() {
  mkdir -p $home_path/{run,log}
  args=""
  while true; do
    case $1 in
      --daemon) daemon=1; shift ;;
      --start-only) start_only=1; shift ;;
      "") break ;;
      *) args="$args $1"; shift ;;
      esac
  done
  if [ "$daemon" == "1" ]
  then
      _run
  elif [ "$start_only" == "1" ]
  then
      pid=`cat $prometheus_path`
      if [[ "$pid" != "" ]]
      then
        kill -9 $pid > /dev/null
      fi
      start
  else
      bash $0 $args --daemon > $home_path/log/prometheusd.log 2>&1 &
  fi
}


run "$@"
