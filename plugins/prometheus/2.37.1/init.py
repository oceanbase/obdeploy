# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.


from __future__ import absolute_import, division, print_function

import os.path

from _errno import EC_FAIL_TO_INIT_PATH, EC_CLEAN_PATH_FAILED, InitDirFailedErrorMessage, EC_CONFIG_CONFLICT_DIR, \
    EC_COMPONENT_DIR_NOT_EMPTY


def _clean(server, client, path, stdio=None):
    ret = client.execute_command('rm -fr %s' % path, timeout=-1)
    if not ret:
        stdio.warn(EC_CLEAN_PATH_FAILED.format(server=server, path=path))
        return False
    else:
        stdio.verbose('%s:%s cleaned' % (server, path))
        return True


def init(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    deploy_name = plugin_context.deploy_name
    global_ret = True
    force = getattr(plugin_context.options, 'force', False)
    clean = getattr(plugin_context.options, 'clean', False)
    stdio.start_loading('Initializes prometheus work home')
    servers_dirs = {}
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        ip = server.ip
        if ip not in servers_dirs:
            servers_dirs[ip] = {}
        dirs = servers_dirs[ip]
        home_path = server_config['home_path']
        data_dir = server_config.get('data_dir')
        if not data_dir:
            server_config['data_dir'] = os.path.join(home_path, 'data')
        keys = ['home_path', 'data_dir']
        for key in keys:
            path = server_config[key]
            if path in dirs:
                global_ret = False
                stdio.error(EC_CONFIG_CONFLICT_DIR.format(server1=server, path=path, server2=dirs[path]['server'], key=dirs[path]['key']))
                continue
            dirs[path] = {
                'server': server,
                'key': key,
            }
        need_clean = force
        if clean and not force:
            if client.execute_command(
                    'bash -c \'if [[ "$(ls -d {0} 2>/dev/null)" != "" && ! -O {0} ]]; then exit 0; else exit 1; fi\''.format(
                        home_path)):
                owner = client.execute_command("ls -ld %s | awk '{print $3}'" % home_path).stdout.strip()
                global_ret = False
                err_msg = ' {} is not empty, and the owner is {}'.format(home_path, owner)
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err_msg))
                continue
            need_clean = True
        if need_clean:
            port = server_config['port']
            address = server_config['address']
            client.execute_command(
                "pkill -9 -u `whoami` -f '^bash prometheusd.sh --config.file={home_path}/prometheus.yaml --web.listen-address={address}:{port}'".format(
                    home_path=home_path, address=address, port=port))
            client.execute_command(
                "pkill -9 -u `whoami` -f '^{home_path}/prometheus --config.file={home_path}/prometheus.yaml --web.listen-address={address}:{port}'".format(
                    home_path=home_path, address=address, port=port))
            if not _clean(server, client, home_path, stdio=stdio):
                global_ret = False
                continue
            if data_dir and not _clean(server, client, data_dir, stdio=stdio):
                global_ret = False
                continue
        if client.execute_command('mkdir -p %s' % home_path):
            ret = client.execute_command('ls %s' % (home_path))
            if not ret or ret.stdout.strip():
                global_ret = False
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path',
                                                        msg=InitDirFailedErrorMessage.NOT_EMPTY.format(
                                                            path=home_path)))
                stdio.error(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                continue
        else:
            global_ret = False
            stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path',
                                                    msg=InitDirFailedErrorMessage.CREATE_FAILED.format(
                                                        path=home_path)))
            continue
        if data_dir:
            if client.execute_command('mkdir -p %s' % data_dir):
                ret = client.execute_command('ls %s' % (data_dir))
                if not ret or ret.stdout.strip():
                    global_ret = False
                    stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='data_dir',
                                                            msg=InitDirFailedErrorMessage.NOT_EMPTY.format(
                                                                path=data_dir)))
                    stdio.error(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                    continue
            else:
                global_ret = False
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='data_dir',
                                                        msg=InitDirFailedErrorMessage.CREATE_FAILED.format(
                                                            path=data_dir)))
                continue
            link_path = '%s/data' % home_path
            client.execute_command(
                "if [ ! '%s' -ef '%s' ]; then ln -sf %s %s; fi" % (data_dir, link_path, data_dir, link_path))
        else:
            data_dir = os.path.join(home_path, 'data')
            if client.execute_command('mkdir -p %s' % data_dir):
                ret = client.execute_command('ls %s' % (data_dir))
                if not ret or ret.stdout.strip():
                    global_ret = False
                    stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='data_dir',
                                                            msg=InitDirFailedErrorMessage.NOT_EMPTY.format(
                                                                path=data_dir)))
                    stdio.error(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                    continue
            else:
                global_ret = False
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='data_dir',
                                                        msg=InitDirFailedErrorMessage.CREATE_FAILED.format(
                                                            path=data_dir)))
                continue

    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
