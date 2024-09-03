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
import os

from _errno import EC_CONFIG_CONFLICT_DIR, EC_FAIL_TO_INIT_PATH, InitDirFailedErrorMessage, EC_COMPONENT_DIR_NOT_EMPTY

stdio = None
force = False
global_ret = True


def critical(*arg, **kwargs):
    global global_ret
    global_ret = False
    stdio.error(*arg, **kwargs)


def init_dir(server, client, key, path, deploy_name, link_path=None):
    if force:
        ret = client.execute_command('rm -fr %s' % path, timeout=-1)
        if not ret:
            critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='%s path' % key, msg=ret.stderr))
            return False
    else:
        if client.execute_command('mkdir -p %s' % path):
            ret = client.execute_command('ls %s' % (path))
            if not ret or ret.stdout.strip():
                critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='%s path' % key, msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=path)))
                critical(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                return False
        else:
            critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='%s path' % key, msg=InitDirFailedErrorMessage.CREATE_FAILED.format(path=path)))
            return False
    ret = client.execute_command('mkdir -p %s' % path)
    if ret:
        if link_path:
            client.execute_command("if [ ! '%s' -ef '%s' ]; then ln -sf %s %s; fi" % (path, link_path, path, link_path))
        return True
    else:
        critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='%s path' % key, msg=ret.stderr))
        return False


def init(plugin_context, *args, **kwargs):
    global stdio, force
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    deploy_name = plugin_context.deploy_name
    servers_dirs = {}
    force = getattr(plugin_context.options, 'force', False)
    clean = getattr(plugin_context.options, 'clean', False)
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
        if not server_config.get('slog_dir'):
            server_config['slog_dir'] = '%s/slog' % server_config['data_dir']
        if not server_config.get('clog_dir'):
            server_config['clog_dir'] = '%s/clog' % server_config['redo_dir']

        if server_config['redo_dir'] == server_config['data_dir']:
            keys = ['home_path', 'data_dir', 'clog_dir', 'slog_dir']
        else:
            keys = ['home_path', 'data_dir', 'redo_dir', 'clog_dir', 'slog_dir']
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
            client.execute_command(
                "pkill -9 -u `whoami` -f '^%s/bin/observer -p %s'" % (home_path, server_config['mysql_port']))
            ret = client.execute_command('rm -fr %s/*' % home_path, timeout=-1)
            if not ret:
                critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=ret.stderr))
                continue
        else:
            if client.execute_command('mkdir -p %s' % home_path):
                ret = client.execute_command('ls %s' % (home_path))
                if not ret or ret.stdout.strip():
                    critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=home_path)))
                    critical(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                    continue
            else:
                critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=InitDirFailedErrorMessage.CREATE_FAILED.format(path=home_path)))
        ret = client.execute_command('bash -c "mkdir -p %s/{etc,admin,.conf,log,bin,lib}"' % home_path)
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
                        critical(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                        continue
                else:
                    critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='data dir', msg=InitDirFailedErrorMessage.CREATE_FAILED.format(path=data_path)))
            ret = client.execute_command('bash -c "mkdir -p %s/sstable"' % data_path)
            if ret:
                link_path = '%s/store' % home_path
                client.execute_command("if [ ! '%s' -ef '%s' ]; then ln -sf %s %s; fi" % (data_path, link_path, data_path, link_path))
                for key in ['clog', 'slog']:
                    # init_dir(server, client, key, server_config['%s_dir' % key], deploy_name, os.path.join(data_path, key))
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
                                critical(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
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
            stdio.verbose("check slog dir in the same disk with data dir")
            slog_disk = data_disk = None
            ret = client.execute_command("df --block-size=1024 %s | awk 'NR == 2 { print $1 }'" % server_config['slog_dir'])
            if ret:
                slog_disk = ret.stdout.strip()
                stdio.verbose('slog disk is {}'.format(slog_disk))
            ret = client.execute_command("df --block-size=1024 %s | awk 'NR == 2 { print $1 }'" % server_config['data_dir'])
            if ret:
                data_disk = ret.stdout.strip()
                stdio.verbose('data disk is {}'.format(data_disk))
            if slog_disk != data_disk:
                critical(EC_FAIL_TO_INIT_PATH.format(
                    server=server, key='slog dir',
                    msg=': slog and data should be on the same disk. Now the slog disk is {slog_disk}, and the data disk is {data_disk}.'.format(slog_disk=slog_disk, data_disk=data_disk)))

    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')