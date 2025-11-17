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
import os

from _errno import EC_CONFIG_CONFLICT_DIR, EC_FAIL_TO_INIT_PATH, InitDirFailedErrorMessage, EC_COMPONENT_DIR_NOT_EMPTY

stdio = None
force = False
global_ret = True


def critical(*arg, **kwargs):
    global global_ret
    global_ret = False
    stdio.error(*arg, **kwargs)


def init(plugin_context, source_option=None, *args, **kwargs):
    global stdio, force
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    deploy_name = plugin_context.deploy_name
    stdio = plugin_context.stdio
    servers_dirs = {}
    force = getattr(plugin_context.options, 'force', False)
    clean = getattr(plugin_context.options, 'clean', False)
    same_disk_check = plugin_context.get_variable('same_disk_check')
    ob_clean = plugin_context.get_variable('ob_clean')
    dir_mapping = plugin_context.get_variable('dir_mapping')
    mkdir_keys = plugin_context.get_variable('mkdir_keys')
    rm_meta = plugin_context.get_variable('rm_meta')
    clean_dir_keys = plugin_context.get_variable('clean_dir_keys')
    data_dir_not_same_redo_dir_keys = plugin_context.get_variable('data_dir_not_same_redo_dir_keys')
    data_dir_same_redo_dir_keys = plugin_context.get_variable('data_dir_same_redo_dir_keys')
    stop_ob_or_obshell = plugin_context.get_variable('stop_ob_or_obshell')
    stdio.verbose('option `force` is %s' % force)
    stdio.start_loading('Initializes observer work home')
    for server in cluster_config.servers:
        ip = server.ip
        if ip not in servers_dirs:
            servers_dirs[ip] = {}
        dirs = servers_dirs[ip]
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']

        if not server_config.get('data_dir'):
            server_config['data_dir'] = '%s/store' % home_path
        if not server_config.get('redo_dir'):
            server_config['redo_dir'] = server_config['data_dir']
        for key, value in dir_mapping.items():
            if not server_config.get('%s_dir' % key):
                server_config['%s_dir' % key] = '%s/%s' % (server_config[value], key)
        if server_config['redo_dir'] == server_config['data_dir']:
            keys = data_dir_same_redo_dir_keys
        else:
            keys = data_dir_not_same_redo_dir_keys
        for key in keys:
            path = server_config[key]
            if path in dirs:
                critical(EC_CONFIG_CONFLICT_DIR.format(server1=server, path=path, server2=dirs[path]['server'], key=dirs[path]['key']))
                continue
            dirs[path] = {
                'server': server,
                'key': key,
            }

        stdio.verbose('%s initializes observer work home' % server)
        need_clean = force
        if clean and not force:
            if client.execute_command('bash -c \'if [[ "$(ls -d {0} 2>/dev/null)" != "" && ! -O {0} ]]; then exit 0; else exit 1; fi\''.format(home_path)):
                owner = client.execute_command("ls -ld %s | awk '{print $3}'" % home_path).stdout.strip()
                err_msg = ' {} is not empty, and the owner is {}'.format(home_path, owner)
                critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err_msg))
                continue
            need_clean = True

        if need_clean:
            ob_clean(client=client, home_path=home_path, server_config=server_config, server=server, critical=critical, EC_FAIL_TO_INIT_PATH=EC_FAIL_TO_INIT_PATH)

        if need_clean:
            if stop_ob_or_obshell(client=client, home_path=home_path, server_config=server_config, server=server, critical=critical, EC_FAIL_TO_INIT_PATH=EC_FAIL_TO_INIT_PATH):
                continue
        else:
            if client.execute_command('mkdir -p %s' % home_path):
                ret = client.execute_command('ls %s' % (home_path))
                if not ret or ret.stdout.strip():
                    critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=home_path)))
                    source_option == "deploy" and critical(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                    continue
            else:
                critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=InitDirFailedErrorMessage.CREATE_FAILED.format(path=home_path)))
        rm_meta(client, home_path, critical, EC_FAIL_TO_INIT_PATH, server, InitDirFailedErrorMessage)
        ret = client.execute_command('bash -c "mkdir -p %s/%s"' % (home_path, mkdir_keys))
        if ret:
            data_path = server_config['data_dir']
            if need_clean:
                ret = client.execute_command('rm -fr %s/*' % data_path, timeout=-1)
                if not ret:
                    critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='data dir', msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=data_path)))
                    continue
            else:
                if client.execute_command('mkdir -p %s' % data_path):
                    ret = client.execute_command('ls %s' % (data_path))
                    if not ret or ret.stdout.strip():
                        critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='data dir', msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=data_path)))
                        source_option == "deploy" and critical(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                        continue
                else:
                    critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='data dir', msg=InitDirFailedErrorMessage.CREATE_FAILED.format(path=data_path)))
            ret = client.execute_command('bash -c "mkdir -p %s/sstable"' % data_path)
            if ret:
                link_path = '%s/store' % home_path
                client.execute_command("if [ ! '%s' -ef '%s' ]; then ln -sf %s %s; fi" % (data_path, link_path, data_path, link_path))
                for key in clean_dir_keys:
                    log_dir = server_config['%s_dir' % key]
                    if force:
                        ret = client.execute_command('rm -fr %s/*' % log_dir, timeout=-1)
                        if not ret:
                            critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='%s dir' % key, msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=log_dir)))
                            continue
                    else:
                        if client.execute_command('mkdir -p %s' % log_dir):
                            ret = client.execute_command('ls %s' % (log_dir))
                            if not ret or ret.stdout.strip():
                                critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='%s dir' % key, msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=log_dir)))
                                source_option == "deploy" and critical(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                                continue
                        else:
                            critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='%s dir' % key, msg=InitDirFailedErrorMessage.CREATE_FAILED.format(path=log_dir)))
                    ret = client.execute_command('mkdir -p %s' % log_dir)
                    if ret:
                        link_path = '%s/%s' % (data_path, key)
                        client.execute_command("if [ ! '%s' -ef '%s' ]; then ln -sf %s %s; fi" % (log_dir, link_path, log_dir, link_path))
                    else:
                        critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='%s dir' % key, msg=ret.stderr))
            else:
                critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='data dir', msg=InitDirFailedErrorMessage.PATH_ONLY.format(path=data_path)))
        else:
            critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=home_path)))
        if global_ret:
            same_disk_check(stdio, client, server_config, critical, EC_FAIL_TO_INIT_PATH, server)
    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')