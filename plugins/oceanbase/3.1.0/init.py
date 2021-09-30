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


stdio = None
force = False
global_ret = True


def critical(*arg, **kwargs):
    global global_ret
    global_ret = False
    stdio.error(*arg, **kwargs)

def init_dir(server, client, key, path, link_path=None):
    if force:
        ret = client.execute_command('rm -fr %s/*' % path)
        if not ret:
            critical('fail to initialize %s %s path: %s permission denied' % (server, key, ret.stderr))
            return False
    else:
        if client.execute_command('mkdir -p %s' % path):
            ret = client.execute_command('ls %s' % (path))
            if not ret or ret.stdout.strip():
                critical('fail to initialize %s %s path: %s is not empty' % (server, key, path))
                return False
        else:
            critical('fail to initialize %s %s path: create %s failed' % (server, key, path))
            return False
    ret = client.execute_command('mkdir -p %s' % path)
    if ret:
        if link_path:
            client.execute_command("if [ ! '%s' -ef '%s' ]; then ln -sf %s %s; fi" % (path, link_path, path, link_path))
        return True
    else:
        critical('fail to initialize %s %s path: %s permission denied' % (server, key, ret.stderr))
        return False


def init(plugin_context, local_home_path, repository_dir, *args, **kwargs):
    global stdio, force
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers_dirs = {}
    force = getattr(plugin_context.options, 'force', False)
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
        remote_home_path = client.execute_command('echo $HOME/.obd').stdout.strip()
        remote_repository_dir = repository_dir.replace(local_home_path, remote_home_path)

        if not server_config.get('data_dir'):
            server_config['data_dir'] = '%s/store' % home_path
        if not server_config.get('redo_dir'):
            server_config['redo_dir'] = server_config['data_dir']
        if not server_config.get('clog_dir'):
            server_config['clog_dir'] = '%s/clog' % server_config['redo_dir']
        if not server_config.get('ilog_dir'):
            server_config['ilog_dir'] = '%s/ilog' % server_config['redo_dir']
        if not server_config.get('slog_dir'):
            server_config['slog_dir'] = '%s/slog' % server_config['redo_dir']
        if server_config['redo_dir'] == server_config['data_dir']:
            keys = ['home_path', 'data_dir', 'clog_dir', 'ilog_dir', 'slog_dir']
        else:
            keys = ['home_path', 'data_dir', 'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir']
        for key in keys:
            path = server_config[key]
            if path in dirs:
                critical('Configuration conflict %s: %s is used for %s\'s %s' % (server, path, dirs[path]['server'], dirs[path]['key']))
                continue
            dirs[path] = {
                'server': server,
                'key': key,
            }
            
        stdio.verbose('%s initializes observer work home' % server)
        if force:
            ret = client.execute_command('rm -fr %s/*' % home_path)
            if not ret:
                critical('failed to initialize %s home path: %s' % (server, ret.stderr))
                continue
        else:
            if client.execute_command('mkdir -p %s' % home_path):
                ret = client.execute_command('ls %s' % (home_path))
                if not ret or ret.stdout.strip():
                    critical('fail to init %s home path: %s is not empty' % (server, home_path))
                    continue
            else:
                critical('fail to init %s home path: create %s failed' % (server, home_path))
        ret = client.execute_command('bash -c "mkdir -p %s/{etc,admin,.conf,log,bin,lib}"' % home_path) \
         and client.execute_command("if [ -d %s/bin ]; then ln -s %s/bin/* %s/bin; fi" % (remote_repository_dir, remote_repository_dir, home_path)) \
         and client.execute_command("if [ -d %s/lib ]; then ln -s %s/lib/* %s/lib; fi" % (remote_repository_dir, remote_repository_dir, home_path))
        if ret:
            data_path = server_config['data_dir']
            if force:
                ret = client.execute_command('rm -fr %s/*' % data_path)
                if not ret:
                    critical('fail to init %s data path: %s permission denied' % (server, ret.stderr))
                    continue
            else:
                if client.execute_command('mkdir -p %s' % data_path):
                    ret = client.execute_command('ls %s' % (data_path))
                    if not ret or ret.stdout.strip():
                        critical('fail to init %s data path: %s is not empty' % (server, data_path))
                        continue
                else:
                    critical('fail to init %s data path: create %s failed' % (server, data_path))
            ret = client.execute_command('bash -c "mkdir -p %s/sstable"' % data_path)
            if ret:
                link_path = '%s/store' % home_path
                client.execute_command("if [ ! '%s' -ef '%s' ]; then ln -sf %s %s; fi" % (data_path, link_path, data_path, link_path))
                for key in ['clog', 'ilog', 'slog']:
                    # init_dir(server, client, key, server_config['%s_dir' % key], os.path.join(data_path, key))
                    log_dir = server_config['%s_dir' % key]
                    if force:
                        ret = client.execute_command('rm -fr %s/*' % log_dir)
                        if not ret:
                            critical('fail to init %s %s dir: %s permission denied' % (server, key, ret.stderr))
                            continue
                    else:
                        if client.execute_command('mkdir -p %s' % log_dir):
                            ret = client.execute_command('ls %s' % (log_dir))
                            if not ret or ret.stdout.strip():
                                critical('fail to init %s %s dir: %s is not empty' % (server, key, log_dir))
                                continue
                        else:
                            critical('fail to init %s %s dir: create %s failed' % (server, key, log_dir))
                    ret = client.execute_command('mkdir -p %s' % log_dir)
                    if ret:
                        link_path = '%s/%s' % (data_path, key)
                        client.execute_command("if [ ! '%s' -ef '%s' ]; then ln -sf %s %s; fi" % (log_dir, link_path, log_dir, link_path))
                    else:
                        critical('failed to initialize %s %s dir' % (server, key))
            else:
                critical('failed to initialize %s date path' % (server))
        else:
            critical('fail to init %s home path: %s permission denied' % (server, ret.stderr))
    
    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')