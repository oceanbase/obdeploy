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
import re

from _plugin import InstallPlugin
from _deploy import InnerConfigKeywords
from tool import YamlLoader


def install_repo(plugin_context, obd_home, install_repository, install_plugin, check_repository, check_file_map,
                 msg_lv, *args, **kwargs):
    cluster_config = plugin_context.cluster_config

    def install_to_home_path():
        repo_dir = install_repository.repository_dir.replace(obd_home, remote_obd_home, 1)
        if is_lib_repo:
            home_path = os.path.join(remote_home_path, 'lib')
        else:
            home_path = remote_home_path
        client.add_env("_repo_dir", repo_dir, True)
        client.add_env("_home_path", home_path, True)
        mkdir_bash = "mkdir -p ${_home_path} && cd ${_repo_dir} && find -type d | xargs -i mkdir -p ${_home_path}/{}"
        if not client.execute_command(mkdir_bash):
            return False
        success = True
        for install_file_item in install_file_items:
            source = os.path.join(repo_dir, install_file_item.target_path)
            target = os.path.join(home_path, install_file_item.target_path)
            client.add_env("source", source, True)
            client.add_env("target", target, True)
            if install_file_item.install_method == InstallPlugin.InstallMethod.CP:
                install_cmd = "cp -f"
            else:
                install_cmd = "ln -fs"
            if install_file_item.type == InstallPlugin.FileItemType.DIR:
                if client.execute_command("ls -1 ${source}"):
                    success = client.execute_command("cd ${source} && find -type f | xargs -i %(install_cmd)s ${source}/{} ${target}/{}" % {"install_cmd": install_cmd}) and success
                    success = client.execute_command("cd ${source} && find -type l | xargs -i %(install_cmd)s ${source}/{} ${target}/{}" % {"install_cmd": install_cmd}) and success
            else:
                success = client.execute_command("%(install_cmd)s ${source} ${target}" % {"install_cmd": install_cmd}) and success
        return success
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    servers = cluster_config.servers
    is_lib_repo = install_repository.name.endswith("-libs")
    home_path_map = {}
    for server in servers:
        server_config = cluster_config.get_server_conf(server)
        home_path_map[server] = server_config.get("home_path")

    is_ln_install_mode = cluster_config.is_ln_install_mode()

    # remote install repository
    stdio.start_loading('Remote %s repository install' % install_repository)
    stdio.verbose('Remote %s repository integrity check' % install_repository)
    for server in servers:
        client = clients[server]
        remote_home_path = home_path_map[server]
        install_file_items = install_plugin.file_map(install_repository).values()
        stdio.verbose('%s %s repository integrity check' % (server, install_repository))
        if is_ln_install_mode:
            remote_obd_home = client.execute_command('echo ${OBD_HOME:-"$HOME"}/.obd').stdout.strip()
            install_path = install_repository.repository_dir.replace(obd_home, remote_obd_home, 1)
        else:
            if is_lib_repo:
                install_path = os.path.join(remote_home_path, 'lib')
            else:
                install_path = remote_home_path
            client.execute_command('mkdir -p {}'.format(install_path))
        remote_repository_data_path = os.path.join(install_path, '.data')
        remote_repository_data = client.execute_command('cat %s' % remote_repository_data_path).stdout
        stdio.verbose('%s %s install check' % (server, install_repository))
        try:
            yaml_loader = YamlLoader(stdio=stdio)
            data = yaml_loader.load(remote_repository_data)
            if not data:
                stdio.verbose('%s %s need to be installed ' % (server, install_repository))
            elif data == install_repository:
                # Version sync. Check for damages (TODO)
                stdio.verbose('%s %s has installed ' % (server, install_repository))
                if not install_to_home_path():
                    stdio.error("Failed to install repository {} to {}".format(install_repository, remote_home_path))
                    return False
                continue
            else:
                stdio.verbose('%s %s need to be updated' % (server, install_repository))
        except:
            stdio.exception('')
            stdio.verbose('%s %s need to be installed ' % (server, install_repository))

        stdio.verbose('%s %s installing' % (server, install_repository))
        sub_io = stdio.sub_io()
        for file_item in install_file_items:
            file_path = os.path.join(install_repository.repository_dir, file_item.target_path)
            remote_file_path = os.path.join(install_path, file_item.target_path)
            if file_item.type == InstallPlugin.FileItemType.DIR:
                if os.path.isdir(file_path) and not client.put_dir(file_path, remote_file_path, stdio=sub_io):
                    stdio.stop_loading('fail')
                    return False
            else:
                if not client.put_file(file_path, remote_file_path, stdio=sub_io):
                    stdio.stop_loading('fail')
                    return False
        if is_ln_install_mode:
            # save data file for later comparing
            client.put_file(install_repository.data_file_path, remote_repository_data_path, stdio=sub_io)
            # link files to home_path
            install_to_home_path()
        stdio.verbose('%s %s installed' % (server, install_repository.name))
    stdio.stop_loading('succeed')

    # check lib
    lib_check = True
    stdio.start_loading('Remote %s repository lib check' % check_repository)
    for server in servers:
        stdio.verbose('%s %s repository lib check' % (server, check_repository))
        client = clients[server]
        remote_home_path = home_path_map[server]
        need_libs = set()
        client.add_env('LD_LIBRARY_PATH', '%s/lib:' % remote_home_path, True)

        for file_item in check_file_map.values():
            if file_item.type == InstallPlugin.FileItemType.BIN:
                remote_file_path = os.path.join(remote_home_path, file_item.target_path)
                ret = client.execute_command('ldd %s' % remote_file_path)
                libs = re.findall('(/?[\w+\-/]+\.\w+[\.\w]+)[\s\\n]*\=\>[\s\\n]*not found', ret.stdout)
                if not libs:
                    libs = re.findall('(/?[\w+\-/]+\.\w+[\.\w]+)[\s\\n]*\=\>[\s\\n]*not found', ret.stderr)
                if not libs and not ret:
                    stdio.error('Failed to execute repository lib check.')
                    return
                need_libs.update(libs)
        if need_libs:
            for lib in need_libs:
                getattr(stdio, msg_lv, '%s %s require: %s' % (server, check_repository, lib))
            lib_check = False
        client.add_env('LD_LIBRARY_PATH', '', True)

    if msg_lv == 'error':
        stdio.stop_loading('succeed' if lib_check else 'fail')
    elif msg_lv == 'warn':
        stdio.stop_loading('succeed' if lib_check else 'warn')
    return plugin_context.return_true(checked=lib_check)
