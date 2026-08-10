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

import datetime
import os.path
import shlex
import time

import const
import requests
from _types import Capacity
from ssh import get_root_permission_client
from tool import get_sudo_prefix


HEALTH_TIMEOUT_SECONDS = 900
UPGRADE_COMMAND_TIMEOUT_SECONDS = 900
RUNTIME_STATE_TIMEOUT_SECONDS = 300
COMMAND_TERMINATION_GRACE_SECONDS = 30
SSH_TIMEOUT_BUFFER_SECONDS = 30
BACKUP_COMPLETE_MARKER = '.obd_backup_complete'
RUNTIME_BACKUP_DIR = '.obd_runtime_backup'
DOCKER_TIMEOUT_WRAPPER_DIR = '.obd_bin'
DOCKER_TIMEOUT_WRAPPER_NAME = 'docker'


def build_hot_upgrade_inner_command(
        init_flag_path='/root/init_flag.txt',
        hot_upgrade_script='/root/docker_hot_update_init.sh'):
    init_flag_path = shlex.quote(init_flag_path)
    hot_upgrade_script = shlex.quote(hot_upgrade_script)
    return (
        f'rm -f {init_flag_path} || exit $?; '
        f'{hot_upgrade_script}; '
        f'test -s {init_flag_path}'
    )


def build_server_timeout_command(
        command,
        timeout_seconds=UPGRADE_COMMAND_TIMEOUT_SECONDS,
        termination_grace_seconds=COMMAND_TERMINATION_GRACE_SECONDS,
        sudo_prefix=''):
    """Run a command under a server-side deadline before SSH can time out."""
    return (
        f'{sudo_prefix}timeout --signal=TERM '
        f'--kill-after={termination_grace_seconds}s '
        f'{timeout_seconds}s bash -c {shlex.quote(command)}'
    )


def command_transport_timeout(
        timeout_seconds=UPGRADE_COMMAND_TIMEOUT_SECONDS,
        termination_grace_seconds=COMMAND_TERMINATION_GRACE_SECONDS):
    return (
        timeout_seconds + termination_grace_seconds +
        SSH_TIMEOUT_BUFFER_SECONDS
    )


def container_command_timeout(timeout_seconds):
    return max(
        1,
        timeout_seconds - COMMAND_TERMINATION_GRACE_SECONDS -
        SSH_TIMEOUT_BUFFER_SECONDS,
    )


def build_timed_container_command(
        container_name,
        command,
        sudo_prefix='',
        timeout_seconds=UPGRADE_COMMAND_TIMEOUT_SECONDS):
    container_timeout_command = build_server_timeout_command(
        command,
        timeout_seconds=container_command_timeout(timeout_seconds),
    )
    container_command = (
        f'docker exec {shlex.quote(container_name)} '
        f'{container_timeout_command}'
    )
    return build_server_timeout_command(
        container_command,
        timeout_seconds=timeout_seconds,
        sudo_prefix=sudo_prefix,
    )


def build_docker_exec_timeout_wrapper():
    return '''#!/usr/bin/env bash
set -u

real_docker="${OBD_REAL_DOCKER_BINARY:?}"
deadline="${OBD_OMS_UPGRADE_DEADLINE_EPOCH:?}"
grace="${OBD_OMS_COMMAND_TERMINATION_GRACE_SECONDS:-30}"

if [ "${1:-}" != "exec" ]; then
    exec "$real_docker" "$@"
fi

shift
docker_args=(exec)
while [ "$#" -gt 0 ]; do
    # The OMS helper scripts use `docker exec -it` even though OBD runs them
    # without an interactive terminal.  Keeping `-t` can leave the host-side
    # docker client blocked in TTY attach after the container command exits.
    # Neither stdin nor a pseudo-terminal is needed by DCDTC/DCDR.  Under
    # OBD's SSH PTY, keeping `-i` can make the host docker client read the
    # controlling terminal and stop with SIGTTIN even after the container
    # command exits.  Docker/pflag accepts combined short options and attached
    # values (`-itw/root`, `-ituroot`), so parse the whole bundle: remove i/t,
    # preserve d, and keep e/u/w with either their attached or following value.
    case "$1" in
        -i|--interactive|-i=*|--interactive=*|\
        -t|--tty|-t=*|--tty=*)
            shift
            ;;
        --detach|--detach=*|--privileged|--privileged=*)
            docker_args+=("$1")
            shift
            ;;
        -e|--env|--env-file|-u|--user|-w|--workdir|--detach-keys)
            [ "$#" -ge 2 ] || exit 125
            docker_args+=("$1" "$2")
            shift 2
            ;;
        --env=*|--env-file=*|--user=*|--workdir=*|--detach-keys=*)
            docker_args+=("$1")
            shift
            ;;
        --)
            docker_args+=(--)
            shift
            break
            ;;
        -?*)
            short_options="${1#-}"
            # A boolean bundle may use an explicit value (`-dit=true`).  pflag
            # applies that value only to the last shorthand; earlier boolean
            # flags use true.  i/t are deliberately disabled regardless, while
            # d keeps its original value.  Value suffixes on e/u/w are handled
            # below as ordinary attached values.
            boolean_value=""
            if [[ "$short_options" =~ ^([dit]+)=(.*)$ ]]; then
                boolean_flags="${BASH_REMATCH[1]}"
                case "${BASH_REMATCH[2]}" in
                    1|t|T|true|TRUE|True)
                        boolean_value="true"
                        ;;
                    0|f|F|false|FALSE|False)
                        boolean_value="false"
                        ;;
                    *)
                        exit 125
                        ;;
                esac
                short_options="$boolean_flags"
            fi
            rewritten_short_options=""
            consume_next=false
            detach_false=false
            while [ -n "$short_options" ]; do
                option="${short_options:0:1}"
                short_options="${short_options:1}"
                case "$option" in
                    i|t)
                        ;;
                    d)
                        if [ "$boolean_value" = "false" ] && \
                                [ -z "$short_options" ]; then
                            # Keep an explicit false value so it can override a
                            # preceding -d/--detach, including one in another
                            # argv token.
                            detach_false=true
                        else
                            rewritten_short_options+="d"
                        fi
                        ;;
                    e|u|w)
                        rewritten_short_options+="$option"
                        if [ -n "$short_options" ]; then
                            rewritten_short_options+="$short_options"
                            short_options=""
                        else
                            consume_next=true
                        fi
                        ;;
                    *)
                        exit 125
                        ;;
                esac
            done
            if [ -n "$rewritten_short_options" ]; then
                docker_args+=("-$rewritten_short_options")
            fi
            if $detach_false; then
                docker_args+=("-d=false")
            fi
            shift
            if $consume_next; then
                [ "$#" -gt 0 ] || exit 125
                docker_args+=("$1")
                shift
            fi
            ;;
        *)
            break
            ;;
    esac
done

[ "$#" -gt 0 ] || exit 125
container="$1"
shift
remaining=$((deadline - $(date +%s)))
[ "$remaining" -gt 0 ] || exit 124

exec "$real_docker" "${docker_args[@]}" "$container" \
    timeout --signal=TERM --kill-after="${grace}s" "${remaining}s" "$@"
'''


def build_timed_docker_script_inner_command(
        script_path,
        script_arguments,
        docker_wrapper_dir,
        real_docker_path,
        timeout_seconds=UPGRADE_COMMAND_TIMEOUT_SECONDS):
    # Finish the container TERM/KILL cycle before the host timeout can close
    # the docker exec attachment.
    container_deadline_seconds = container_command_timeout(timeout_seconds)
    arguments = ' '.join(
        shlex.quote(str(argument)) for argument in script_arguments)
    return (
        f'export OBD_OMS_UPGRADE_DEADLINE_EPOCH=$(( $(date +%s) + '
        f'{container_deadline_seconds} )); '
        f'export OBD_OMS_COMMAND_TERMINATION_GRACE_SECONDS='
        f'{COMMAND_TERMINATION_GRACE_SECONDS}; '
        f'export OBD_REAL_DOCKER_BINARY={shlex.quote(real_docker_path)}; '
        f'export PATH={shlex.quote(docker_wrapper_dir)}:$PATH; '
        f'sh {shlex.quote(script_path)} {arguments}'
    )


def online_upgrade(plugin_context, dest_repository, default_oms_files_path=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    global_config = cluster_config.get_global_conf()
    container_name = global_config.get('container_name')
    oms_script_paths = {}
    oms_files_paths = {}
    docker_wrapper_dirs = {}
    real_docker_paths = {}
    sudo_clients = {}

    def get_server_sudo_client(server):
        if server not in sudo_clients:
            sudo_clients[server] = get_root_permission_client(
                clients[server], server, stdio)
        return sudo_clients[server]

    def external_health_is_ready(server):
        nginx_server_port = cluster_config.get_server_conf(
            server).get('nginx_server_port', 8089)
        url = f'http://{server.ip}:{nginx_server_port}/oms/health'
        try:
            response = requests.get(url, timeout=4)
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('healthy') is True
        except (requests.RequestException, ValueError, AttributeError):
            return False

    def wait_servers_health(servers, deadline, check_external=False):
        pending_servers = list(servers)
        locally_healthy_servers = set()
        while pending_servers and time.monotonic() < deadline:
            for server in list(pending_servers):
                if server not in locally_healthy_servers:
                    check_client = get_server_sudo_client(server)
                    if not check_client:
                        continue
                    nginx_server_port = cluster_config.get_server_conf(
                        server).get('nginx_server_port', 8089)
                    check_cmd = (
                        f'curl --max-time 4 -fsS '
                        f'http://127.0.0.1:{nginx_server_port}/oms/health '
                        "| grep -q '\"healthy\":true'"
                    )
                    if not check_client.execute_command(check_cmd, timeout=10):
                        continue
                    locally_healthy_servers.add(server)
                if not check_external or external_health_is_ready(server):
                    pending_servers.remove(server)
            if pending_servers:
                time.sleep(min(1, max(0, deadline - time.monotonic())))
        return pending_servers

    def start_servers(servers):
        failed_servers = []
        for server in servers:
            start_client = get_server_sudo_client(server)
            if not start_client:
                failed_servers.append(server)
                continue
            start_prefix = get_sudo_prefix(start_client)
            start_cmd = (
                f'{start_prefix}docker exec {container_name} supervisorctl start '
                'nginx oms_console oms_drc_cm oms_drc_supervisor >/dev/null 2>&1 || true'
            )
            if not start_client.execute_command(start_cmd, timeout=60):
                failed_servers.append(server)
        return failed_servers

    def backup_is_complete(server, container_backup_path):
        backup_client = get_server_sudo_client(server)
        if not backup_client:
            return False
        backup_prefix = get_sudo_prefix(backup_client)
        marker_path = os.path.join(container_backup_path, BACKUP_COMPLETE_MARKER)
        marker_cmd = (
            f'{backup_prefix}docker exec {container_name} test -f '
            f'{shlex.quote(marker_path)}'
        )
        return bool(backup_client.execute_command(marker_cmd))

    def backup_runtime_state(server, container_backup_path):
        backup_client = get_server_sudo_client(server)
        if not backup_client:
            return False
        backup_prefix = get_sudo_prefix(backup_client)
        runtime_backup_path = os.path.join(
            container_backup_path, RUNTIME_BACKUP_DIR)
        runtime_backup_inner_command = (
            f"set -e; backup_dir={shlex.quote(runtime_backup_path)}; "
            'rm -rf "$backup_dir"; mkdir -p "$backup_dir"; '
            ': > "$backup_dir/existing_paths"; '
            ': > "$backup_dir/absent_dirs"; '
            'for path in /usr/bin/python3 /usr/bin/pip3 /usr/bin/mysql '
            '/etc/ld.so.conf.d/openssl11.conf; do '
            '[ -e "$path" ] || [ -L "$path" ] && echo "${path#/}" '
            '>> "$backup_dir/existing_paths"; done; '
            'for path in /usr/local/openssl11 /usr/local/python3.9 '
            '/usr/local/mariadb-10.6.25; do '
            '[ -e "$path" ] || echo "${path#/}" >> "$backup_dir/absent_dirs"; done; '
            'tar -cpf "$backup_dir/original_paths.tar" -C / '
            '-T "$backup_dir/existing_paths"; '
            'touch "$backup_dir/ready"'
        )
        backup_cmd = build_timed_container_command(
            container_name,
            runtime_backup_inner_command,
            sudo_prefix=backup_prefix,
            timeout_seconds=RUNTIME_STATE_TIMEOUT_SECONDS,
        )
        return bool(backup_client.execute_command(
            backup_cmd,
            timeout=command_transport_timeout(RUNTIME_STATE_TIMEOUT_SECONDS),
        ))

    def restore_runtime_state(server, container_backup_path):
        restore_client = get_server_sudo_client(server)
        if not restore_client:
            return False
        restore_prefix = get_sudo_prefix(restore_client)
        runtime_backup_path = os.path.join(
            container_backup_path, RUNTIME_BACKUP_DIR)
        restore_runtime_inner_command = (
            f"set -e; backup_dir={shlex.quote(runtime_backup_path)}; "
            'test -f "$backup_dir/ready"; '
            'if grep -qx usr/local/openssl11 "$backup_dir/absent_dirs"; then '
            'rm -rf /usr/local/openssl11; '
            'rm -f /etc/ld.so.conf.d/openssl11.conf; fi; '
            'if grep -qx usr/local/python3.9 "$backup_dir/absent_dirs"; then '
            'rm -rf /usr/local/python3.9; '
            'rm -f /usr/bin/python3 /usr/bin/pip3; fi; '
            'if grep -qx usr/local/mariadb-10.6.25 "$backup_dir/absent_dirs"; then '
            'rm -rf /usr/local/mariadb-10.6.25; rm -f /usr/bin/mysql; fi; '
            'tar -xpf "$backup_dir/original_paths.tar" -C /; '
            'ldconfig >/dev/null 2>&1 || true'
        )
        restore_cmd = build_timed_container_command(
            container_name,
            restore_runtime_inner_command,
            sudo_prefix=restore_prefix,
            timeout_seconds=RUNTIME_STATE_TIMEOUT_SECONDS,
        )
        return bool(restore_client.execute_command(
            restore_cmd,
            timeout=command_transport_timeout(RUNTIME_STATE_TIMEOUT_SECONDS),
        ))

    def rollback_servers(servers, container_backup_path, recover_only_servers=None):
        failed_servers = []
        recover_servers = list(servers)
        for recover_only_server in recover_only_servers or []:
            if recover_only_server not in recover_servers:
                recover_servers.append(recover_only_server)

        # Complete every file rollback before starting any node. This prevents a
        # slow first node from consuming another node's service recovery window.
        for rollback_server in servers:
            rollback_client = get_server_sudo_client(rollback_server)
            if not rollback_client:
                failed_servers.append(rollback_server)
                continue
            rollback_prefix = get_sudo_prefix(rollback_client)
            rollback_script_path = oms_script_paths[rollback_server]
            rollback_inner_command = build_timed_docker_script_inner_command(
                os.path.join(rollback_script_path, const.DCDR_SCRIPT),
                [container_name, container_backup_path],
                docker_wrapper_dirs[rollback_server],
                real_docker_paths[rollback_server],
            )
            rollback_cmd = build_server_timeout_command(
                rollback_inner_command,
                sudo_prefix=rollback_prefix,
            )
            rollback_succeeded = bool(rollback_client.execute_command(
                rollback_cmd,
                use_tty=True,
                timeout=command_transport_timeout(),
            ))
            runtime_restore_succeeded = restore_runtime_state(
                rollback_server, container_backup_path)
            if not rollback_succeeded or not runtime_restore_succeeded:
                failed_servers.append(rollback_server)

        start_failed_servers = start_servers(recover_servers)
        health_deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
        health_failed_servers = wait_servers_health(
            recover_servers, health_deadline, check_external=True)
        for failed_server in start_failed_servers + health_failed_servers:
            if failed_server not in failed_servers:
                failed_servers.append(failed_server)
        return failed_servers

    stdio.start_loading('Start get upgrade script')
    for server in cluster_config.servers:
        client = clients[server]
        if client.config.username == 'root':
            oms_script_path = '/root/oms_script'
        else:
            oms_script_path = f'/home/{client.config.username}/oms_script'
        oms_script_paths[server] = oms_script_path
        sudo_client = get_server_sudo_client(server)
        if not sudo_client:
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        prefix = get_sudo_prefix(sudo_client)
        dest_image_name = cluster_config.image_name + ':' + dest_repository.version
        tool_container_name = 'oms-config-tool'
        cleanup_tool_cmd = (
            f'{prefix}docker rm -f {tool_container_name} >/dev/null 2>&1 || true'
        )
        cp_script_cmd = (
            f'{prefix}mkdir -p {shlex.quote(oms_script_path)} || exit $?; '
            f'{cleanup_tool_cmd}; '
            f'{prefix}docker run -d --net host --name {tool_container_name} '
            f'{shlex.quote(dest_image_name)} bash && '
            f'{prefix}docker cp {tool_container_name}:/root/{const.DDFFI_SCRIPT} '
            f'{shlex.quote(oms_script_path)}/ && '
            f'{prefix}docker cp {tool_container_name}:/root/{const.DCDTC_SCRIPT} '
            f'{shlex.quote(oms_script_path)}/ && '
            f'{prefix}docker cp {tool_container_name}:/root/{const.DCDR_SCRIPT} '
            f'{shlex.quote(oms_script_path)}/; '
            f'ret=$?; {cleanup_tool_cmd}; exit $ret'
        )
        if not sudo_client.execute_command(cp_script_cmd):
            stdio.stop_loading('fail')
            stdio.error('copy upgrade script to %s failed.' % server)
            return plugin_context.return_false()
        real_docker_ret = sudo_client.execute_command('command -v docker')
        real_docker_path = real_docker_ret.stdout.strip() if real_docker_ret else ''
        if not real_docker_path:
            stdio.stop_loading('fail')
            stdio.error('%s: docker executable not found.' % server)
            return plugin_context.return_false()
        docker_wrapper_dir = os.path.join(
            oms_script_path, DOCKER_TIMEOUT_WRAPPER_DIR)
        docker_wrapper_path = os.path.join(
            docker_wrapper_dir, DOCKER_TIMEOUT_WRAPPER_NAME)
        wrapper_content = build_docker_exec_timeout_wrapper()
        install_wrapper_cmd = (
            f'{prefix}mkdir -p {shlex.quote(docker_wrapper_dir)} && '
            f'printf %s {shlex.quote(wrapper_content)} | '
            f'{prefix}tee {shlex.quote(docker_wrapper_path)} >/dev/null && '
            f'{prefix}chmod 700 {shlex.quote(docker_wrapper_path)}'
        )
        if not sudo_client.execute_command(install_wrapper_cmd):
            stdio.stop_loading('fail')
            stdio.error('%s: failed to install docker exec timeout wrapper.' % server)
            return plugin_context.return_false()
        docker_wrapper_dirs[server] = docker_wrapper_dir
        real_docker_paths[server] = real_docker_path
        dcdtc_script_path = os.path.join(oms_script_path, const.DCDTC_SCRIPT)
        marker_script_line = (
            'run_task $USESUDO docker exec -it ${OMS_CONTAINER_NAME} '
            f'touch $BACKUPPATH/{BACKUP_COMPLETE_MARKER}'
        )
        runtime_sync_marker_sed_expression = (
            r'/^sync_usr_local_runtime_from_dump$/i ' + marker_script_line
        )
        legacy_marker_sed_expression = (
            r'/^# update \/root$/i ' + marker_script_line
        )
        patch_marker_cmd = (
            f'if {prefix}grep -qxF {shlex.quote(marker_script_line)} '
            f'{shlex.quote(dcdtc_script_path)}; then :; '
            f'elif {prefix}grep -qxF sync_usr_local_runtime_from_dump '
            f'{shlex.quote(dcdtc_script_path)}; then '
            f'{prefix}sed -i {shlex.quote(runtime_sync_marker_sed_expression)} '
            f'{shlex.quote(dcdtc_script_path)}; else '
            f'{prefix}sed -i {shlex.quote(legacy_marker_sed_expression)} '
            f'{shlex.quote(dcdtc_script_path)}; fi; '
            f'{prefix}grep -qxF {shlex.quote(marker_script_line)} '
            f'{shlex.quote(dcdtc_script_path)}'
        )
        if not sudo_client.execute_command(patch_marker_cmd):
            stdio.stop_loading('fail')
            stdio.error('%s: failed to add the backup completion marker.' % server)
            return plugin_context.return_false()
    stdio.stop_loading('succeed')

    input_path = True
    if default_oms_files_path:
        input_path = False
    oms_files_path = default_oms_files_path
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        oms_script_path = oms_script_paths[server]
        if not default_oms_files_path:
            if not oms_files_path:
                mount_path = os.path.dirname(server_config.get('logs_mount_path')) if server_config.get('logs_mount_path') else server_config['mount_path']
                default_oms_files_path = oms_files_path or f'{mount_path}/upgrade_docker_files'
            else:
                default_oms_files_path = oms_files_path
        while True:
            if input_path:
                oms_files_path = stdio.read(f'{server.ip}:Please specify a local directory(minimum 20GB) for exporting files from the OMS image. (Default: {default_oms_files_path}): ',blocked=True).strip() or default_oms_files_path
            if not client.execute_command(f"ls {oms_files_path}"):
                client.execute_command(f"mkdir -p {oms_files_path}")
            else:
                stdio.print(f'{oms_files_path} is exist.')
                if input_path:
                    continue
                else:
                    return plugin_context.return_false()
            if Capacity(client.execute_command(f"df -BG {oms_files_path} | awk 'NR==2 {{print $4}}'").stdout.strip()).bytes > 20 << 30:
                break
            stdio.error('The specified directory is too small. Please specify a larger directory.')
        oms_files_paths[server] = oms_files_path
        image_name = cluster_config.image_name + ':' + dest_repository.version
        if not client.execute_command(f"ls {oms_script_path}/{const.DDFFI_SCRIPT}"):
            stdio.error('%s: missing script file %s' % (server, const.DDFFI_SCRIPT))
            return plugin_context.return_false()
        client.execute_command(f"rm -rf {oms_files_path}")
        stdio.start_loading('%s: wait dump oms files from image' % server.ip)
        sudo_client = get_server_sudo_client(server)
        if not sudo_client:
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        prefix = get_sudo_prefix(sudo_client)
        if not sudo_client.execute_command(f'{prefix}sh {oms_script_path}/{const.DDFFI_SCRIPT} {image_name} {oms_files_path}'):
            stdio.stop_loading('fail')
            stdio.error('copy oms files to %s failed.' % server.ip)
            return plugin_context.return_false()
        stdio.stop_loading('succeed')

    stdio.start_loading('Start upgrade oms file')
    container_backup_path = '/home/admin/logs/back' + datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    modified_servers = []
    for server in cluster_config.servers:
        client = clients[server]
        oms_script_path = oms_script_paths[server]
        oms_files_path = oms_files_paths[server]
        client.remote_client_get_tpy()
        if not client.execute_command(f"ls {oms_script_path}/{const.DCDTC_SCRIPT}"):
            stdio.stop_loading('fail')
            stdio.error('%s: missing script file %s' % (server, const.DCDTC_SCRIPT))
            rb_failed_servers = rollback_servers(modified_servers, container_backup_path)
            rb_failed_servers and stdio.error('Rollback failed servers: %s.' % rb_failed_servers)
            return plugin_context.return_false()
        sudo_client = get_server_sudo_client(server)
        if not sudo_client:
            stdio.stop_loading('fail')
            rb_failed_servers = rollback_servers(modified_servers, container_backup_path)
            rb_failed_servers and stdio.error('Rollback failed servers: %s.' % rb_failed_servers)
            return plugin_context.return_false()
        prefix = get_sudo_prefix(sudo_client)
        if not backup_runtime_state(server, container_backup_path):
            stdio.stop_loading('fail')
            rb_failed_servers = rollback_servers(modified_servers, container_backup_path)
            stdio.error('%s: backup runtime state failed.' % server)
            rb_failed_servers and stdio.error('Rollback failed servers: %s.' % rb_failed_servers)
            return plugin_context.return_false()
        copy_inner_command = build_timed_docker_script_inner_command(
            os.path.join(oms_script_path, const.DCDTC_SCRIPT),
            [container_name, oms_files_path, container_backup_path],
            docker_wrapper_dirs[server],
            real_docker_paths[server],
        )
        copy_cmd = build_server_timeout_command(
            copy_inner_command,
            sudo_prefix=prefix,
        )
        if not sudo_client.execute_command(
                copy_cmd,
                use_tty=True,
                timeout=command_transport_timeout()):
            stdio.stop_loading('fail')
            if backup_is_complete(server, container_backup_path):
                modified_servers.append(server)
                rb_failed_servers = rollback_servers(modified_servers, container_backup_path)
            else:
                rb_failed_servers = rollback_servers(
                    modified_servers,
                    container_backup_path,
                    recover_only_servers=[server],
                )
            stdio.error('%s: docker copy dumpfile to container failed. Please contact official technical support.' % server)
            rb_failed_servers and stdio.error('Rollback failed servers: %s.' % rb_failed_servers)
            return plugin_context.return_false()
        # Only a successful copy command proves that the backup is complete and
        # safe for the destructive rollback script.
        modified_servers.append(server)
    stdio.stop_loading('succeed')

    stdio.start_loading('Start upgrade oms')
    for server in cluster_config.servers:
        sudo_client = get_server_sudo_client(server)
        if not sudo_client:
            stdio.stop_loading('fail')
            rb_failed_servers = rollback_servers(modified_servers, container_backup_path)
            rb_failed_servers and stdio.error('Rollback failed servers: %s.' % rb_failed_servers)
            return plugin_context.return_false()
        prefix = get_sudo_prefix(sudo_client)
        # docker_hot_update_init.sh invokes docker_init.sh itself, but does not
        # propagate its exit status. Remove the old marker first and use the
        # marker recreated by a successful initialization as the authoritative
        # result. Calling docker_init.sh again is unsafe because initialization
        # is not idempotent.
        hot_upgrade_inner_command = build_hot_upgrade_inner_command()
        hot_upgrade_cmd = build_timed_container_command(
            container_name,
            hot_upgrade_inner_command,
            sudo_prefix=prefix,
        )
        ret = sudo_client.execute_command(
            hot_upgrade_cmd,
            timeout=command_transport_timeout(),
        )
        if not ret:
            stdio.stop_loading('fail')
            rb_failed_servers = rollback_servers(modified_servers, container_backup_path)
            error_output = ret.stderr.strip() or 'See the OMS container initialization log for details.'
            stdio.error('%s: Hot update oms failed. %s' % (server, error_output))
            rb_failed_servers and stdio.error('Rollback failed servers: %s.' % rb_failed_servers)
            return plugin_context.return_false()
    stdio.stop_loading('succeed')

    stdio.start_loading('Verify online upgraded OMS health')
    health_deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
    health_failed_servers = wait_servers_health(
        cluster_config.servers, health_deadline, check_external=True)
    if health_failed_servers:
        stdio.stop_loading('fail')
        rb_failed_servers = rollback_servers(modified_servers, container_backup_path)
        stdio.error('%s: health check failed after online upgrade.' % ','.join(
            server.ip for server in health_failed_servers))
        rb_failed_servers and stdio.error('Rollback failed servers: %s.' % rb_failed_servers)
        return plugin_context.return_false()
    stdio.stop_loading('succeed')

    return plugin_context.return_true()
