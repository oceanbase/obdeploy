
path=$1
ip=$2
port=$3

function start() {
    obproxyd_path=$path/run/obproxyd-$ip-$port.pid
    obproxy_path=$path/run/obproxy-$ip-$port.pid

    cat $obproxyd_path | xargs kill -9

    echo $$ > $obproxyd_path
    if [ $? != 0 ]; then
        exit $?
    fi

    pid=`cat $obproxy_path`
    ls /proc/$pid > /dev/null
    if [ $? != 0 ]; then
        exit $?
    fi
    kill -9 $pid

    while [ 1 ]; 
    do 
        sleep 1
        ls /proc/$pid > /dev/null
        if [ $? != 0 ]; then
            cd $path
            $path/bin/obproxy --listen_port $port
            pid=`ps -aux | egrep "$path/bin/obproxy --listen_port $port$" | grep -v grep | awk '{print $2}'`
            echo $pid > $obproxy_path
            if [ $? != 0 ]; then
                exit $?
            fi
        fi
    done
}

if [ "$4" == "daemon" ]
then
    start
else
    nohup bash $0 $path $ip $port daemon > /dev/null 2>&1 &
fi