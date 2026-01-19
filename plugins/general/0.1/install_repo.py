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
import re

from _plugin import InstallPlugin
from _deploy import InnerConfigKeywords
from tool import YamlLoader
from _rpm import Version

version_compatibility = {
    "1.8": ("1.8.0_161", "1.8.1"),
    "17": ("17", "18")
}


def install_repo(plugin_context, obd_home, install_repository, install_plugin, check_repository, check_file_map,
                 requirement_map, msg_lv, *args, **kwargs):
    cluster_config = plugin_context.cluster_config

    def install_to_home_path():
        repo_dir = install_repository.repository_dir.replace(obd_home, remote_obd_home, 1)
        if is_lib_repo:
            home_path = os.path.join(remote_home_path, 'lib')
        elif is_jre_repo:
            home_path = os.path.join(remote_home_path, 'jre')
            client.execute_command(f"rm -rf {home_path}")
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
                launch_user = cluster_config.get_global_conf().get("launch_user")
                if launch_user:
                    success = client.execute_command("sudo chown -R %s ${target}" % launch_user) and success

        return success
    
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    servers = cluster_config.servers
    is_lib_repo = install_repository.name.endswith("-libs")
    is_utils_repo = install_repository.name.endswith("-utils")
    is_jre_repo = install_repository.name.endswith("-jre")
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
            elif is_utils_repo:
                install_path = os.path.join(remote_home_path, 'bin')
            else:
                install_path = remote_home_path
            client.execute_command('mkdir -p {}'.format(install_path))
        remote_repository_data_path = os.path.join(install_path, '.data')
        remote_repository_data = client.execute_command('cat %s' % remote_repository_data_path).stdout
        stdio.verbose('%s %s install check' % (server, install_repository))
        try:
            yaml_loader = YamlLoader(stdio=stdio)
            data = yaml_loader.loads(remote_repository_data)
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
    def check_lib():
        lib_check = True
        stdio.start_loading('Remote %s repository lib check' % check_repository)
        need_libs = set()
        for server in servers:
            stdio.verbose('%s %s repository lib check' % (server, check_repository))
            client = clients[server]
            remote_home_path = home_path_map[server]
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
                    if requirement_map and libs and file_item.require in requirement_map:
                        need_libs.add(requirement_map[file_item.require])
                elif file_item.type == InstallPlugin.FileItemType.JAR:
                    client.add_env('PATH', '%s/jre/bin:' % remote_home_path)
                    ret = client.execute_command('java -version')
                    if not ret:
                        need_libs.add(requirement_map[file_item.require])
                    else:
                        pattern = r'version\s+\"(\d+\.\d+\.\d+_?\d*)'
                        match = re.search(pattern, ret.stderr)
                        if not match:
                            need_libs.add(requirement_map[file_item.require])
                        else:              
                            if requirement_map[file_item.require].version:
                                for version_key, (special_min, special_max) in version_compatibility.items():
                                    if version_key in requirement_map[file_item.require].version:
                                        min_version = special_min
                                        max_version = special_max
                                        break
                            else:
                                min_version = requirement_map[file_item.require].min_version
                                max_version = requirement_map[file_item.require].max_version
                            if Version(match.group(1)) < Version(min_version) or Version(match.group(1)) > Version(max_version):
                                    need_libs.add(requirement_map[file_item.require])
        if need_libs:
            for lib in need_libs:
                getattr(stdio, msg_lv, '%s %s require: %s' % (server, check_repository, lib.name))
            lib_check = False
        client.add_env('LD_LIBRARY_PATH', '', True)

        if msg_lv == 'error':
            stdio.stop_loading('succeed' if lib_check else 'fail')
        elif msg_lv == 'warn':
            stdio.stop_loading('succeed' if lib_check else 'warn')
        return plugin_context.return_true(checked=lib_check, requirements=need_libs)

    # check utils
    def check_utils():
        utils_check = True
        for server in servers:
            client = clients[server]
            remote_home_path = home_path_map[server]
            need_utils = set()

            for file_item in check_file_map.values():
                if file_item.type == InstallPlugin.FileItemType.BIN:
                    utils_file_path = os.path.join(remote_home_path, 'bin')
                    remote_file_path = os.path.join(utils_file_path, file_item.target_path)
                    ret = client.execute_command('ls -1 %s' % remote_file_path)
                    utils = file_item.target_path
                    if not ret:
                        stdio.error('Failed to execute repository utils check.')
                        return
                    need_utils.update(utils)
            if need_utils:
                for util in need_utils:
                    getattr(stdio, '%s %s require: %s' % (server, check_repository, util))
                utils_check = False
        return plugin_context.return_true(checked=utils_check)

    if is_utils_repo:
        return check_utils()
    else:
        return check_lib()
