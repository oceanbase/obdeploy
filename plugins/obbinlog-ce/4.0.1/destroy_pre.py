# coding: utf-8
# Copyright (c) 2025 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import shlex


STOP_INSTANCE_SCRIPT = r'''
if ! pid_file=$(realpath -e -- "$1"); then
    echo "INVALID_PID_FILE:$1"
    exit 1
fi
if ! binlog_dir=$(realpath -e -- "$2"); then
    echo "INVALID_BINLOG_DIR:$2"
    exit 1
fi
if ! expected_work_dir=$(realpath -e -- "${pid_file%/*}"); then
    echo "INVALID_WORK_DIR:$pid_file"
    exit 1
fi
case "$expected_work_dir/" in
    "$binlog_dir"/*)
        ;;
    *)
        echo "WORK_DIR_OUTSIDE_BINLOG_DIR:$expected_work_dir"
        exit 1
        ;;
esac

if ! pid=$(cat -- "$pid_file"); then
    echo "READ_PID_FAILED:$pid_file"
    exit 1
fi
case "$pid" in
    ''|*[!0-9]*)
        echo "INVALID_PID:$pid_file"
        exit 1
        ;;
esac
if ! [ "$pid" -gt 1 ] 2>/dev/null; then
    echo "INVALID_PID:$pid_file"
    exit 1
fi

stat_path=/proc/$pid/stat
cmdline_path=/proc/$pid/cmdline
if [ ! -e "/proc/$pid" ]; then
    echo "PROCESS_NOT_FOUND:$pid"
    exit 0
fi
if [ ! -r "$stat_path" ] || [ ! -r "$cmdline_path" ]; then
    echo "READ_PROC_FAILED:$pid"
    exit 1
fi
if ! start_time=$(awk '{print $22}' "$stat_path"); then
    echo "READ_START_TIME_FAILED:$pid"
    exit 1
fi
if ! executable=$(readlink -f "/proc/$pid/exe") ||
   ! process_cwd=$(readlink -f "/proc/$pid/cwd"); then
    echo "READ_PROCESS_IDENTITY_FAILED:$pid"
    exit 1
fi
if ! exec 3< "$cmdline_path"; then
    echo "READ_CMDLINE_FAILED:$pid"
    exit 1
fi
if ! IFS= read -r -d '' argv0 <&3 ||
   ! IFS= read -r -d '' argv1 <&3; then
    exec 3<&-
    if [ ! -e "/proc/$pid" ]; then
        echo "PROCESS_NOT_FOUND:$pid"
        exit 0
    fi
    echo "READ_CMDLINE_FAILED:$pid"
    exit 1
fi
exec 3<&-
if ! argv1=$(realpath -e -- "$argv1"); then
    echo "PID_MISMATCH:$pid"
    exit 0
fi

if [ "${executable##*/}" != "binlog_instance" ] ||
   [ "${argv0##*/}" != "binlog_instance" ] ||
   [ "$argv1" != "$expected_work_dir" ] ||
   [ "$process_cwd" != "$expected_work_dir" ]; then
    echo "PID_MISMATCH:$pid"
    exit 0
fi
if ! current_start_time=$(awk '{print $22}' "$stat_path") ||
   [ "$current_start_time" != "$start_time" ]; then
    echo "PROCESS_CHANGED:$pid"
    exit 1
fi
if ! kill -9 "$pid"; then
    echo "KILL_FAILED:$pid"
    exit 1
fi

remaining_checks=20
while [ "$remaining_checks" -gt 0 ]; do
    if [ ! -e "/proc/$pid" ]; then
        echo "KILLED:$pid"
        exit 0
    fi
    if ! process_state=$(awk '{print $3 ":" $22}' "$stat_path"); then
        if [ ! -e "/proc/$pid" ]; then
            echo "KILLED:$pid"
            exit 0
        fi
        echo "READ_PROCESS_STATE_FAILED:$pid"
        exit 1
    fi
    state=${process_state%%:*}
    checked_start_time=${process_state#*:}
    if [ "$checked_start_time" != "$start_time" ] || [ "$state" = "Z" ]; then
        echo "KILLED:$pid"
        exit 0
    fi
    remaining_checks=$((remaining_checks - 1))
    sleep 0.1
done

echo "KILL_TIMEOUT:$pid"
exit 1
'''


def destroy_pre(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    success = True

    stdio.start_loading('Stop binlog instances before destroy')
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        client = clients[server]
        home_path = server_config['home_path']
        binlog_dir = server_config.get('binlog_dir') or '%s/run' % home_path
        find_result = client.execute_command(
            'if [ -d {path} ]; then '
            'find {path} -type f -name binlog_instance.pid -print; '
            'fi'.format(path=shlex.quote(binlog_dir))
        )
        if not find_result:
            find_error = (
                getattr(find_result, 'stderr', '') or
                getattr(find_result, 'stdout', '')
            ).strip()
            stdio.warn(
                '%s failed to scan binlog instance pid files: %s' %
                (server, find_error or binlog_dir)
            )
            success = False
            continue
        if not find_result.stdout.strip():
            continue

        for pid_path in find_result.stdout.strip().splitlines():
            stop_result = client.execute_command(
                'bash -c {script} -- {pid_path} {binlog_dir}'.format(
                    script=shlex.quote(STOP_INSTANCE_SCRIPT),
                    pid_path=shlex.quote(pid_path),
                    binlog_dir=shlex.quote(binlog_dir),
                )
            )
            result_message = (getattr(stop_result, 'stdout', '') or '').strip()
            error_message = (getattr(stop_result, 'stderr', '') or '').strip()
            if not stop_result:
                stdio.warn(
                    '%s binlog instance stop failed: %s' %
                    (server, result_message or error_message or pid_path)
                )
                success = False
            elif result_message.startswith('KILLED:'):
                stdio.verbose(
                    '%s binlog_instance[pid:%s] stopped' %
                    (server, result_message.split(':', 1)[1])
                )
            else:
                stdio.verbose('%s %s' % (server, result_message))

    stdio.stop_loading('succeed' if success else 'fail')
    plugin_context.set_variable("clean_dirs", ["home_path", "binlog_dir"])
    return plugin_context.return_true() if success else plugin_context.return_false()
