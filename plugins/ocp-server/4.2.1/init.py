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
from glob import glob

import _errno as err
from _arch import getArchList
from core import ObdHome
from const import CONST_OBD_HOME
from ssh import LocalClient
from _mirror import MirrorRepositoryManager


def _clean(server, client, path, stdio=None):
    ret = client.execute_command('rm -fr %s' % path, timeout=-1)
    if not ret:
        stdio.warn(err.EC_CLEAN_PATH_FAILED.format(server=server, path=path))
        return False
    else:
        stdio.verbose('%s:%s cleaned' % (server, path))
        return True


def _ocp_lib(client, home_path, soft_dir='', stdio=None):
    stdio.verbose('cp rpm & pos')
    if soft_dir:
        client.execute_command('mkdir -p -m 775  %s' % soft_dir, timeout=-1)
    else:
        client.execute_command('mkdir -p -m 775  %s/data/files/' % home_path, timeout=-1)
    client.execute_command('mkdir -p -m 775  %s/ocp-server/lib/' % home_path, timeout=-1)
    client.execute_command('mkdir -p -m 775  %s/logs/ocp/' % home_path, timeout=-1)

    OBD_HOME = os.path.join(os.environ.get(CONST_OBD_HOME, os.getenv('HOME')), '.obd')
    mirror_manager = MirrorRepositoryManager(OBD_HOME)
    pkgs = []
    for arch in ['x86_64', 'aarch64']:
        pkg = mirror_manager.get_exact_pkg(name="ocp-agent-ce", arch=arch, only_download=True)
        if pkg:
            pkgs.append(pkg)
    for comp in ['oceanbase-ce', 'oceanbase-ce-libs', 'oceanbase-ce-utils', 'obproxy-ce']:
        pkg = mirror_manager.get_exact_pkg(name=comp, only_download=True)
        if pkg:
            pkgs.append(pkg)
    for pkg in pkgs:
        client.put_file(pkg.path, os.path.join(home_path, 'ocp-server/lib/', pkg.file_name))
        if soft_dir:
            client.put_file(pkg.path, os.path.join(soft_dir, pkg.file_name))



def init(plugin_context, upgrade=False, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    deploy_name = plugin_context.deploy_name

    global_ret = True
    force = getattr(plugin_context.options, 'force', False)
    clean = getattr(plugin_context.options, 'clean', False)
    if upgrade:
        for server in cluster_config.servers:
            client = clients[server]
            server_config = cluster_config.get_server_conf(server)
            home_path = server_config['home_path']
            soft_dir = server_config.get('soft_dir', '')
            _ocp_lib(client, home_path, soft_dir, stdio)
        plugin_context.return_true()
        return

    stdio.start_loading('Initializes %s work home' % cluster_config.name)
    servers_dirs = {}
    cp_lib = 0
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        ip = server.ip
        if ip not in servers_dirs:
            servers_dirs[ip] = {}
        dirs = servers_dirs[ip]
        home_path = server_config['home_path']
        launch_user = server_config.get('launch_user', None)
        soft_dir = server_config.get('soft_dir', '')
        keys = ['home_path', 'log_dir', 'soft_dir']
        for key in keys:
            if key not in server_config:
                continue
            path = server_config[key]
            if path in dirs:
                global_ret = False
                stdio.error(err.EC_CONFIG_CONFLICT_DIR.format(server1=server, path=path, server2=dirs[path]['server'], key=dirs[path]['key']))
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
                stdio.error(err.EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err_msg))
                continue
            need_clean = True
        if need_clean:
            port = server_config['port']
            client.execute_command("pkill -9 -u `whoami` -f 'java -jar {home_path}/lib/ocp-server.jar --port {port}'".format(home_path=home_path, port=port))
            if not _clean(server, client, home_path, stdio=stdio):
                global_ret = False
                continue
        if client.execute_command('mkdir -p -m 775 %s' % home_path):
            ret = client.execute_command('ls %s' % (home_path))
            if not ret or ret.stdout.strip():
                global_ret = False
                stdio.error(err.EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err.InitDirFailedErrorMessage.NOT_EMPTY.format(path=home_path)))
                stdio.error(err.EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                continue
        else:
            global_ret = False
            stdio.error(err.EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err.InitDirFailedErrorMessage.CREATE_FAILED.format(path=home_path)))
            continue
        if not client.execute_command("bash -c 'mkdir -p -m 775 %s/{run,bin,lib}'" % home_path):
            global_ret = False
            stdio.error(err.EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err.InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=home_path)))
        if 'log_dir' in server_config:
            log_dir = server_config['log_dir']
            if client.execute_command('mkdir -p -m 775 %s' % log_dir):
                ret = client.execute_command('ls %s' % log_dir)
                if not ret or ret.stdout.strip():
                    global_ret = False
                    stdio.error(err.EC_FAIL_TO_INIT_PATH.format(server=server, key='log dir', msg=err.InitDirFailedErrorMessage.NOT_EMPTY.format(path=log_dir)))
                    stdio.error(err.EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                    continue
            else:
                global_ret = False
                stdio.error(err.EC_FAIL_TO_INIT_PATH.format(server=server, key='log dir', msg=err.InitDirFailedErrorMessage.CREATE_FAILED.format(path=log_dir)))
                continue
        else:
            log_dir = os.path.join(home_path, 'log')
            if not client.execute_command('mkdir -p -m 775  %s' % log_dir):
                global_ret = False
                stdio.error(err.EC_FAIL_TO_INIT_PATH.format(server=server, key='log dir', msg=err.InitDirFailedErrorMessage.NOT_EMPTY.format(path=log_dir)))
                stdio.error(err.EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                continue
        link_path = os.path.join(home_path, 'log')
        client.execute_command("if [ ! '%s' -ef '%s' ]; then ln -sf %s %s; fi" % (log_dir, link_path, log_dir, link_path))
        if cp_lib < 1:
            _ocp_lib(client, home_path, soft_dir, stdio)
        cp_lib += 1
        if launch_user:
            res_home = client.execute_command("sudo chown -R %s %s" % (launch_user, home_path))
            res_log = client.execute_command("sudo chown -R %s %s" % (launch_user, log_dir))
            res_soft = client.execute_command("sudo chown -R %s %s" % (launch_user, soft_dir))
            if not (res_home and res_log and res_soft):
                global_ret = False
    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        plugin_context.return_false()

