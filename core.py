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

import re
import os
import sys
import time
import fcntl
from optparse import Values

import tempfile
from subprocess import call as subprocess_call
from prettytable import PrettyTable
from halo import Halo

from ssh import SshClient, SshConfig
from tool import ConfigUtil, FileUtil, DirectoryUtil, YamlLoader
from _stdio import MsgLevel
from _mirror import MirrorRepositoryManager
from _plugin import PluginManager, PluginType
from _repository import RepositoryManager, LocalPackage
from _deploy import DeployManager, DeployStatus, DeployConfig, DeployConfigStatus


class ObdHome(object):

    HOME_LOCK_RELATIVE_PATH = 'obd.conf'

    def __init__(self, home_path, stdio=None, lock=True):
        self.home_path = home_path
        self._lock = None
        self._home_conf = None
        self._mirror_manager = None
        self._repository_manager = None
        self._deploy_manager = None
        self._plugin_manager = None
        self.stdio = None
        self._stdio_func = None
        lock and self.lock()
        self.set_stdio(stdio)

    def lock(self):
        if self._lock is None:
            self._lock = FileUtil.open(os.path.join(self.home_path, self.HOME_LOCK_RELATIVE_PATH), 'w')
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def unlock(self):
        try:
            if self._lock is None:
                fcntl.flock(self._lock, fcntl.LOCK_UN)
        except:
            pass

    def __del__(self):
        self.unlock()

    @property
    def mirror_manager(self):
        if not self._mirror_manager:
            self._mirror_manager = MirrorRepositoryManager(self.home_path, self.stdio)
        return self._mirror_manager

    @property
    def repository_manager(self):
        if not self._repository_manager:
            self._repository_manager = RepositoryManager(self.home_path, self.stdio)
        return self._repository_manager

    @property
    def plugin_manager(self):
        if not self._plugin_manager:
            self._plugin_manager = PluginManager(self.home_path, self.stdio)
        return self._plugin_manager

    @property
    def deploy_manager(self):
        if not self._deploy_manager:
            self._deploy_manager = DeployManager(self.home_path, self.stdio)
        return self._deploy_manager

    def set_stdio(self, stdio):
        def _print(msg, *arg, **kwarg):
            sep = kwarg['sep'] if 'sep' in kwarg else None
            end = kwarg['end'] if 'end' in kwarg else None
            return print(msg, sep='' if sep is None else sep, end='\n' if end is None else end)
        self.stdio = stdio
        self._stdio_func = {}
        if not self.stdio:
            return
        for func in ['start_loading', 'stop_loading', 'print', 'confirm', 'verbose', 'warn', 'exception', 'error', 'critical', 'print_list']:
            self._stdio_func[func] = getattr(self.stdio, func, _print)

    def _call_stdio(self, func, msg, *arg, **kwarg):
        if func not in self._stdio_func:
            return None
        return self._stdio_func[func](msg, *arg, **kwarg)

    def add_mirror(self, src, opts):
        if re.match('^https?://', src):
            return self.mirror_manager.add_remote_mirror(src)
        else:
            return self.mirror_manager.add_local_mirror(src, getattr(opts, 'force', False))

    def deploy_param_check(self, repositories, deploy_config):
        # parameter check
        errors = []
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            for server in cluster_config.servers:
                self._call_stdio('verbose', '%s %s param check' % (server, repository))
                need_items = cluster_config.get_unconfigured_require_item(server)
                if need_items:
                    errors.append('%s %s need config: %s' % (server, repository.name, ','.join(need_items)))
        return errors

    def get_clients(self, deploy_config, repositories):
        ssh_clients = {}
        self._call_stdio('start_loading', 'Open ssh connection')
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            # ssh check
            self.ssh_clients_connect(ssh_clients, cluster_config.servers, deploy_config.user)
        self._call_stdio('stop_loading', 'succeed')
        return ssh_clients

    def ssh_clients_connect(self, ssh_clients, servers, user_config):
        for server in servers:
            if server.ip not in ssh_clients:
                ssh_clients[server] = SshClient(
                    SshConfig(
                        server.ip,
                        user_config.username, 
                        user_config.password, 
                        user_config.key_file, 
                        user_config.port, 
                        user_config.timeout
                    ),
                    self.stdio
                )
                ssh_clients[server].connect()

    def search_plugin(self, repository, plugin_type, no_found_exit=True):
        self._call_stdio('verbose', 'Search %s plugin for %s' % (plugin_type.name.lower(), repository))
        plugin = self.plugin_manager.get_best_plugin(plugin_type, repository.name, repository.version)
        if plugin:
            self._call_stdio('verbose', 'Found for %s for %s-%s' % (plugin, repository.name, repository.version))
        else:
            if no_found_exit:
                self._call_stdio('critical', 'No such %s plugin for %s-%s' % (plugin_type.name.lower(), repository.name, repository.version))
            else:
                self._call_stdio('warn', 'No such %s plugin for %s-%s' % (plugin_type.name.lower(), repository.name, repository.version))
        return plugin

    def search_plugins(self, repositories, plugin_type, no_found_exit=True):
        plugins = {}
        self._call_stdio('verbose', 'Searching %s plugin for components ...', plugin_type.name.lower())
        for repository in repositories:
            plugin = self.search_plugin(repository, plugin_type, no_found_exit)
            if plugin:
                plugins[repository] = plugin
            elif no_found_exit:
                return None
        return plugins

    def search_py_script_plugin(self, repositories, script_name, no_found_exit=True):
        plugins = {}
        self._call_stdio('verbose', 'Searching %s plugin for components ...', script_name)
        for repository in repositories:
            self._call_stdio('verbose', 'Searching %s plugin for %s' % (script_name, repository))
            plugin = self.plugin_manager.get_best_py_script_plugin(script_name, repository.name, repository.version)
            if plugin:
                plugins[repository] = plugin
                self._call_stdio('verbose', 'Found for %s for %s-%s' % (plugin, repository.name, repository.version))
            else:
                if no_found_exit:
                    self._call_stdio('critical', 'No such %s plugin for %s-%s' % (script_name, repository.name, repository.version))
                    break
                else:
                    self._call_stdio('warn', 'No such %s plugin for %s-%s' % (script_name, repository.name, repository.version))
        return plugins
    
    def search_components_from_mirrors(self, deploy_config, fuzzy_match=False, only_info=True):
        pkgs = []
        errors = []
        repositories = []
        self._call_stdio('verbose', 'Search package for components...')
        for component in deploy_config.components:
            config = deploy_config.components[component]
            # First, check if the component exists in the repository. If exists, check if the version is available. If so, use the repository directly.

            self._call_stdio('verbose', 'Get %s repository' % component)
            repository = self.repository_manager.get_repository(component, config.version, config.package_hash if config.package_hash else config.tag)
            self._call_stdio('verbose', 'Check %s version for the repository' % repository)
            if repository and repository.hash:
                repositories.append(repository)
                self._call_stdio('verbose', 'Use repository %s' % repository)
                self._call_stdio('print', '%s-%s already installed' % (repository.name, repository.version))
                continue
            self._call_stdio('verbose', 'Search %s package from mirror' % component)
            pkg = self.mirror_manager.get_best_pkg(name=component, version=config.version, md5=config.package_hash, fuzzy_match=fuzzy_match, only_info=only_info)
            if pkg:
                self._call_stdio('verbose', 'Package %s-%s is available.' % (pkg.name, pkg.version))
                if config.version and pkg.version != config.version:
                   self._call_stdio('warn', 'No such package %s-%s. Use similar package %s-%s.' % (component, config.version, pkg.name, pkg.version))
                else:
                    self._call_stdio('print', 'Package %s-%s is available' % (pkg.name, pkg.version))
                repository = self.repository_manager.get_repository(pkg.name, pkg.md5)
                if repository:
                    repositories.append(repository)
                else:
                    pkgs.append(pkg)
            else:
                pkg_name = [component]
                if config.version:
                    pkg_name.append(config.version)
                if config.package_hash:
                    pkg_name.append(config.package_hash)
                elif config.tag:
                    pkg_name.append(config.tag)
                errors.append('No such package %s.' % ('-'.join(pkg_name)))
        return pkgs, repositories, errors

    def load_local_repositories(self, deploy_config, allow_shadow=True):
        return self.get_local_repositories(deploy_config.components, allow_shadow)

    def get_local_repositories(self, components, allow_shadow=True):
        repositories = []
        if allow_shadow:
            get_repository = self.repository_manager.get_repository_allow_shadow
        else:
            get_repository = self.repository_manager.get_repository

        for component_name in components:
            cluster_config = components[component_name]
            self._call_stdio('verbose', 'Get local repository %s-%s-%s' % (component_name, cluster_config.version, cluster_config.tag))
            repository = get_repository(component_name, cluster_config.version, cluster_config.package_hash if cluster_config.package_hash else cluster_config.tag)
            if repository:
                repositories.append(repository)
            else:
                self._call_stdio('critical', 'Local repository %s-%s-%s is empty.' % (component_name, cluster_config.version, cluster_config.tag))
        return repositories

    def search_param_plugin_and_apply(self, repositories, deploy_config):
        self._call_stdio('verbose', 'Searching param plugin for components ...')
        for repository in repositories:
            plugin = self.search_plugin(repository, PluginType.PARAM, False)
            if plugin:
                self._call_stdio('verbose', 'Applying %s for %s' % (plugin, repository))
                cluster_config = deploy_config.components[repository.name]
                cluster_config.update_temp_conf(plugin.params)

    def edit_deploy_config(self, name):
        def confirm(msg):
            if self.stdio:
                self._call_stdio('print', msg)
                if self._call_stdio('confirm', 'edit?'):
                    return True
            return False
        def is_deployed():
            return deploy and deploy.deploy_info.status not in [DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_DESTROYED]
        def is_server_list_change(deploy_config):
            for component_name in deploy_config.components:
                if deploy_config.components[component_name].servers != deploy.deploy_config.components[component_name].servers:
                    return True
            return False
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        initial_config = ''
        if deploy:
            try:
                if deploy.deploy_info.config_status == DeployConfigStatus.UNCHNAGE:
                    path = deploy.deploy_config.yaml_path
                else:
                    path = deploy.get_temp_deploy_yaml_path(deploy.config_dir)
                self._call_stdio('verbose', 'Load %s' % path)
                with open(path, 'r') as f:
                    initial_config = f.read()
            except:
                self._call_stdio('exception', '')
            msg = 'Save deploy "%s" configuration' % name
        else:
            if not self.stdio:
                return False
            if not self._call_stdio('confirm', 'No such deploy: %s. Create?' % name):
                return False
            msg = 'Create deploy "%s" configuration' % name
        EDITOR = os.environ.get('EDITOR','vi')
        self._call_stdio('verbose', 'Get environment variable EDITOR=%s' % EDITOR)
        self._call_stdio('verbose', 'Create tmp yaml file')
        tf = tempfile.NamedTemporaryFile(suffix=".yaml")
        tf.write(initial_config.encode())
        tf.flush()
        while True:
            tf.seek(0)
            self._call_stdio('verbose', '%s %s' % (EDITOR, tf.name))
            subprocess_call([EDITOR, tf.name])
            self._call_stdio('verbose', 'Load %s' % tf.name)
            deploy_config = DeployConfig(tf.name, YamlLoader(self.stdio))
            self._call_stdio('verbose', 'Configure component change check')
            if not deploy_config.components:
                if self._call_stdio('confirm', 'Empty configuration'):
                    continue
                return False
            self._call_stdio('verbose', 'Information check for the configuration component.')
            if not deploy:
                config_status = DeployConfigStatus.NEED_REDEPLOY
            elif is_deployed():
                if deploy_config.components.keys() != deploy.deploy_config.components.keys():
                    if confirm('Modifying the component list of a deployed cluster is not permitted.'):
                        continue
                    return False
                if is_server_list_change(deploy_config):
                    if confirm('Modifying the server list of a deployed cluster is not permitted.'):
                        continue
                    return False
                success = True
                for component_name in deploy_config.components:
                    old_cluster_config = deploy.deploy_config.components[component_name]
                    new_cluster_config = deploy_config.components[component_name]
                    if new_cluster_config.version and new_cluster_config.version != old_cluster_config.version:
                        success = False
                        break
                    if new_cluster_config.package_hash and new_cluster_config.package_hash != old_cluster_config.package_hash:
                        success = False
                        break
                if not success:
                    if confirm('Modifying the version and hash of the component is not permitted.'):
                        continue
                    return False
            pkgs, repositories, errors = self.search_components_from_mirrors(deploy_config)
            # Loading the parameter plugins that are available to the application
            self._call_stdio('start_loading', 'Search param plugin and load')
            for repository in repositories:
                self._call_stdio('verbose', 'Search param plugin for %s' % repository)
                plugin = self.plugin_manager.get_best_plugin(PluginType.PARAM, repository.name, repository.version)
                if plugin:
                    self._call_stdio('verbose', 'Load param plugin for %s' % repository)
                    deploy_config.components[repository.name].update_temp_conf(plugin.params)
                    if deploy and repository.name in deploy.deploy_config.components:
                        deploy.deploy_config.components[repository.name].update_temp_conf(plugin.params)
            for pkg in pkgs:
                self._call_stdio('verbose', 'Search param plugin for %s' % pkg)
                plugin = self.plugin_manager.get_best_plugin(PluginType.PARAM, pkg.name, pkg.version)
                if plugin:
                    self._call_stdio('verbose', 'load param plugin for %s' % pkg)
                    deploy_config.components[pkg.name].update_temp_conf(plugin.params)
                    if deploy and pkg.name in deploy.deploy_config.components:
                        deploy.deploy_config.components[pkg.name].update_temp_conf(plugin.params)
            self._call_stdio('stop_loading', 'succeed')
            # Parameter check
            self._call_stdio('start_loading', 'Parameter check')
            errors = self.deploy_param_check(repositories, deploy_config) + self.deploy_param_check(pkgs, deploy_config)
            self._call_stdio('stop_loading', 'fail' if errors else 'succeed')
            if errors:
                if confirm('\n'.join(errors)):
                    continue
                return False
            self._call_stdio('verbose', 'configure change check')
            if initial_config and initial_config == tf.read().decode(errors='replace'):
                config_status = deploy.deploy_info.config_status if deploy else DeployConfigStatus.UNCHNAGE
                self._call_stdio('print', 'Deploy "%s" config %s' % (name, config_status.value))
                return True
            config_status = DeployConfigStatus.UNCHNAGE
            if is_deployed():
                for component_name in deploy_config.components:
                    if config_status == DeployConfigStatus.NEED_REDEPLOY:
                        break
                    old_cluster_config = deploy.deploy_config.components[component_name]
                    new_cluster_config = deploy_config.components[component_name]
                    if old_cluster_config == new_cluster_config:
                        continue
                    if config_status == DeployConfigStatus.UNCHNAGE:
                        config_status = DeployConfigStatus.NEED_RELOAD
                    for server in old_cluster_config.servers:
                        if old_cluster_config.get_need_redeploy_items(server) != new_cluster_config.get_need_redeploy_items(server):
                            config_status = DeployConfigStatus.NEED_REDEPLOY
                            break
                        if old_cluster_config.get_need_restart_items(server) != new_cluster_config.get_need_restart_items(server):
                            config_status = DeployConfigStatus.NEED_RESTART
                if deploy.deploy_info.status == DeployStatus.STATUS_DEPLOYED and config_status != DeployConfigStatus.NEED_REDEPLOY:
                    config_status = DeployConfigStatus.UNCHNAGE
            break
        self._call_stdio('verbose', 'Set deploy configuration status to %s' % config_status)
        self._call_stdio('verbose', 'Save new configuration yaml file')
        if config_status == DeployConfigStatus.UNCHNAGE:
            ret = self.deploy_manager.create_deploy_config(name, tf.name).update_deploy_config_status(config_status)
        else:
            target_src_path = deploy.get_temp_deploy_yaml_path(deploy.config_dir)
            old_config_status = deploy.deploy_info.config_status
            try:
                if deploy.update_deploy_config_status(config_status):
                    FileUtil.copy(tf.name, target_src_path, self.stdio)
                ret = True
                if deploy:
                    if deploy.deploy_info.status == DeployStatus.STATUS_RUNNING or (
                        config_status == DeployConfigStatus.NEED_REDEPLOY and is_deployed()
                    ):
                        msg += '\ndeploy "%s"' % config_status.value
            except Exception as e:
                deploy.update_deploy_config_status(old_config_status)
                self._call_stdio('exception', 'Copy %s to %s failed, error: \n%s' % (tf.name, target_src_path, e))
                msg += ' failed'
                ret = False
        self._call_stdio('print', msg)
        tf.close()
        return ret

    def list_deploy(self):
        self._call_stdio('verbose', 'Get deploy list')
        deploys = self.deploy_manager.get_deploy_configs()
        if deploys:
            self._call_stdio('print_list', deploys, 
                ['Name', 'Configuration Path', 'Status (Cached)'], 
                lambda x: [x.name, x.config_dir, x.deploy_info.status.value], 
                title='Cluster List',
            )
        else:
            self._call_stdio('print', 'Local deploy is empty')
        return True

    def get_install_plugin_and_install(self, repositories, pkgs):
        # Check if the component contains the installation plugins
        install_plugins = self.search_plugins(repositories, PluginType.INSTALL)
        if install_plugins is None:
            return None
        temp = self.search_plugins(pkgs, PluginType.INSTALL)
        if temp is None:
            return None
        for pkg in temp:
            repository = self.repository_manager.create_instance_repository(pkg.name, pkg.version, pkg.md5)
            install_plugins[repository] = temp[pkg]

        # Install for local
        # self._call_stdio('print', 'install package for local ...')
        for pkg in pkgs:
            self._call_stdio('start_loading', 'install %s-%s for local' % (pkg.name, pkg.version))
            # self._call_stdio('verbose', 'install %s-%s for local' % (pkg.name, pkg.version))
            repository = self.repository_manager.create_instance_repository(pkg.name, pkg.version, pkg.md5)
            if not repository.load_pkg(pkg, install_plugins[repository]):
                self._call_stdio('stop_loading', 'fail')
                self._call_stdio('error', 'Failed to extract file from %s' % pkg.path)
                return None
            self._call_stdio('stop_loading', 'succeed')
            self.repository_manager.create_tag_for_repository(repository, pkg.name)
            repositories.append(repository)
        return install_plugins

    def install_lib_for_repositories(self, repositories):
        data = {}
        temp_map = {}
        for repository in repositories:
            lib_name = '%s-libs' % repository.name
            data[lib_name] = {'global': {
                'version': repository.version
            }}
            temp_map[lib_name] = repository
        try:
            with tempfile.NamedTemporaryFile(suffix=".yaml", mode='w') as tf:
                yaml_loader = YamlLoader(self.stdio)
                yaml_loader.dump(data, tf)
                deploy_config = DeployConfig(tf.name, yaml_loader)
                # Look for the best suitable mirrors for the components
                self._call_stdio('verbose', 'Search best suitable repository libs')
                pkgs, lib_repositories, errors = self.search_components_from_mirrors(deploy_config, only_info=False)
                if errors:
                    self._call_stdio('error', '\n'.join(errors))
                    return False

                # Get the installation plugin and install locally
                install_plugins = self.get_install_plugin_and_install(lib_repositories, pkgs)
                if not install_plugins:
                    return False
                repositories_lib_map = {}
                for lib_repository in lib_repositories:
                    repository = temp_map[lib_repository.name]
                    install_plugin = install_plugins[lib_repository]
                    repositories_lib_map[repository] = {
                        'repositories': lib_repository,
                        'install_plugin': install_plugin
                    }
                return repositories_lib_map
        except:
            self._call_stdio('exception', 'Failed to create lib-repo config file')
            pass
        return False

    def servers_repository_install(self, ssh_clients, servers, repository, install_plugin):
        self._call_stdio('start_loading', 'Remote %s repository install' % repository)
        self._call_stdio('verbose', 'Remote %s repository integrity check' % repository)
        for server in servers:
            self._call_stdio('verbose', '%s %s repository integrity check' % (server, repository))
            client = ssh_clients[server]
            remote_home_path = client.execute_command('echo $HOME/.obd').stdout.strip()
            remote_repository_data_path = repository.data_file_path.replace(self.home_path, remote_home_path)
            remote_repository_data = client.execute_command('cat %s' % remote_repository_data_path).stdout
            self._call_stdio('verbose', '%s %s install check' % (server, repository))
            try:
                yaml_loader = YamlLoader(self.stdio)
                data = yaml_loader.load(remote_repository_data)
                if not data:
                    self._call_stdio('verbose', '%s %s need to be installed ' % (server, repository))
                elif data == repository:
                    # Version sync. Check for damages (TODO)
                    self._call_stdio('verbose', '%s %s has installed ' % (server, repository))
                    continue
                else:
                    self._call_stdio('verbose', '%s %s need to be updated' % (server, repository))
            except:
                self._call_stdio('verbose', '%s %s need to be installed ' % (server, repository))
            for file_path in repository.file_list(install_plugin):
                remote_file_path = file_path.replace(self.home_path, remote_home_path)
                self._call_stdio('verbose', '%s %s installing' % (server, repository))
                client.put_file(file_path, remote_file_path)
                client.execute_command('chmod %s %s' % (oct(os.stat(file_path).st_mode)[-3: ], remote_file_path))
            client.put_file(repository.data_file_path, remote_repository_data_path)
            self._call_stdio('verbose', '%s %s installed' % (server, repository.name))
        self._call_stdio('stop_loading', 'succeed')

    def servers_repository_lib_check(self, ssh_clients, servers, repository, install_plugin, msg_lv='error'):
        ret = True
        self._call_stdio('start_loading', 'Remote %s repository lib check' % repository)
        for server in servers:
            self._call_stdio('verbose', '%s %s repository lib check' % (server, repository))
            client = ssh_clients[server]
            need_libs = set()
            remote_home_path = client.execute_command('echo $HOME/.obd').stdout.strip()
            remote_repository_path = repository.repository_dir.replace(self.home_path, remote_home_path)
            remote_repository_data_path = repository.data_file_path.replace(self.home_path, remote_home_path)
            client.add_env('LD_LIBRARY_PATH', '%s/lib:' % remote_repository_path, True)
            
            for file_path in repository.bin_list(install_plugin):
                remote_file_path = file_path.replace(self.home_path, remote_home_path)
                libs = client.execute_command('ldd %s' % remote_file_path).stdout
                need_libs.update(re.findall('(/?[\w+\-/]+\.\w+[\.\w]+)[\s\\n]*\=\>[\s\\n]*not found', libs))
            if need_libs:
                for lib in need_libs:
                    self._call_stdio(msg_lv, '%s %s require: %s' % (server, repository, lib))
                ret = False
            client.add_env('LD_LIBRARY_PATH', '', True)

        self._call_stdio('stop_loading', 'succeed' if ret else msg_lv)
        return ret

    def servers_apply_lib_repository_and_check(self, ssh_clients, deploy_config, repositories, repositories_lib_map):
        ret = True
        servers_obd_home = {}
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            lib_repository = repositories_lib_map[repository]['repositories']
            install_plugin = repositories_lib_map[repository]['install_plugin']
            self._call_stdio('print', 'Use %s for %s' % (lib_repository, repository))
            
            for server in cluster_config.servers:
                client = ssh_clients[server]
                if server not in servers_obd_home:
                    servers_obd_home[server] = client.execute_command('echo $HOME/.obd').stdout.strip()
                remote_home_path = servers_obd_home[server]
                remote_lib_repository_data_path = lib_repository.repository_dir.replace(self.home_path, remote_home_path)
            # lib installation
            self._call_stdio('verbose', 'Remote %s repository integrity check' % repository)
            self.servers_repository_install(ssh_clients, cluster_config.servers, lib_repository, install_plugin)
            for server in cluster_config.servers:
                client = ssh_clients[server]
                remote_home_path = servers_obd_home[server]
                remote_repository_data_path = repository.repository_dir.replace(self.home_path, remote_home_path)
                remote_lib_repository_data_path = lib_repository.repository_dir.replace(self.home_path, remote_home_path)
                client.execute_command('ln -sf %s %s/lib' % (remote_lib_repository_data_path, remote_repository_data_path))

            if self.servers_repository_lib_check(ssh_clients, cluster_config.servers, repository, install_plugin):
                ret = False
            for server in cluster_config.servers:
                client = ssh_clients[server]
        return ret

    # If the cluster states are consistent, the status value is returned. Else False is returned.
    def cluster_status_check(self, ssh_clients, deploy_config, repositories, ret_status={}):
        status_plugins = self.search_py_script_plugin(repositories, 'status')
        component_status = {}
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            self._call_stdio('verbose', 'Call %s for %s' % (status_plugins[repository], repository))
            plugin_ret = status_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio)
            cluster_status = plugin_ret.get_return('cluster_status')
            ret_status[repository] = cluster_status
            for server in cluster_status:
                if repository not in component_status:
                    component_status[repository] = cluster_status[server]
                    continue
                if component_status[repository] != cluster_status[server]:
                    self._call_stdio('verbose', '%s cluster status is inconsistent' % repository)
                    break
            else:
                continue
            return False
        status = None
        for repository in component_status:
            if status is None:
                status = component_status[repository]
                continue
            if status != component_status[repository]:
                self._call_stdio('verbose', 'Deploy status inconsistent')
                return False
        return status

    def deploy_cluster(self, name, opt=Values()):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if deploy:
            self._call_stdio('verbose', 'Get deploy info')
            deploy_info = deploy.deploy_info
            self._call_stdio('verbose', 'judge deploy status')
            if deploy_info.status not in [DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_DESTROYED]:
                self._call_stdio('error', 'Deploy "%s" is %s. You could not realod an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
                return False
            if deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
                self._call_stdio('verbose', 'Apply temp deploy configuration')
                if not deploy.apply_temp_deploy_config():
                    self._call_stdio('error', 'Failed to apply new deploy configuration')
                    return False
        
        config_path = getattr(opt, 'config', '')
        unuse_lib_repo = getattr(opt, 'unuselibrepo', False)
        self._call_stdio('verbose', 'config path is None or not')
        if config_path:
            self._call_stdio('verbose', 'Create deploy by configuration path')
            deploy = self.deploy_manager.create_deploy_config(name, config_path)
            if not deploy:
                self._call_stdio('error', 'Failed to create deploy: %s. please check you configuration file' % name)
                return False
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s. you can input configuration path to create a new deploy' % name)
            return False

        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config
        if not deploy_config:
            self._call_stdio('error', 'Deploy configuration is empty.\nIt may be caused by a failure to resolve the configuration.\nPlease check your configuration file.')
            return False

        if not deploy_config.components:
            self._call_stdio('error', 'Components not detected.\nPlease check the syntax of your configuration file.')
            return False

        for component_name in deploy_config.components:
            if not deploy_config.components[component_name].servers:
                self._call_stdio('error', '%s\'s servers list is empty.' % component_name)
                return False

        # Check the best suitable mirror for the components
        self._call_stdio('verbose', 'Search best suitable repository')
        pkgs, repositories, errors = self.search_components_from_mirrors(deploy_config, only_info=False)
        if errors:
            self._call_stdio('error', '\n'.join(errors))
            return False

        # Get the installation plugins. Install locally
        install_plugins = self.get_install_plugin_and_install(repositories, pkgs)
        if not install_plugins:
            self._call_stdio('print', 'You could try using -f to force remove directory')
            return False

        self._call_stdio('print_list', repositories, ['Repository', 'Version', 'Md5'], lambda repository: [repository.name, repository.version, repository.hash], title='Packages')

        errors = []
        self._call_stdio('verbose', 'Repository integrity check')
        for repository in repositories:
            if not repository.file_check(install_plugins[repository]):
                errors.append('%s intstall failed' % repository.name)
        if errors:
            self._call_stdio('error', '\n'.join(errors))
            return False

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)

        # Parameter check
        self._call_stdio('verbose', 'Cluster param configuration check')
        errors = self.deploy_param_check(repositories, deploy_config)
        if errors:
            self._call_stdio('error', '\n'.join(errors))
            return False
        
        if unuse_lib_repo and not deploy_config.unuse_lib_repository:
            deploy_config.set_unuse_lib_repository(True)
        lib_not_found_msg_func = 'error' if deploy_config.unuse_lib_repository else 'print'
        
        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        need_lib_repositories = []
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            # cluster files check
            self.servers_repository_install(ssh_clients, cluster_config.servers, repository, install_plugins[repository])
            # lib check
            msg_lv = 'error' if deploy_config.unuse_lib_repository else 'warn'
            if not self.servers_repository_lib_check(ssh_clients, cluster_config.servers, repository, install_plugins[repository], msg_lv):
                need_lib_repositories.append(repository)

        if need_lib_repositories:
            if deploy_config.unuse_lib_repository:
                # self._call_stdio('print', 'You could try using -U to work around the problem')
                return False
            self._call_stdio('print', 'Try to get lib-repository')
            repositories_lib_map = self.install_lib_for_repositories(need_lib_repositories)
            if repositories_lib_map is False:
                self._call_stdio('error', 'Failed to install lib package for local')
                return False
            if self.servers_apply_lib_repository_and_check(ssh_clients, deploy_config, need_lib_repositories, repositories_lib_map):
                self._call_stdio('error', 'Failed to install lib package for cluster servers')
                return False

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 1:
            if self.stdio:
                self._call_stdio('error', 'Some of the servers in the cluster have been started')
                for repository in component_status:
                    cluster_status = component_status[repository]
                    for server in cluster_status:
                        if cluster_status[server] == 1:
                            self._call_stdio('print', '%s %s is started' % (server, repository.name))
            return False
            
        self._call_stdio('verbose', 'Search init plugin')
        init_plugins = self.search_py_script_plugin(repositories, 'init', False)
        component_num = len(repositories)
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            init_plugin = self.plugin_manager.get_best_py_script_plugin('init', repository.name, repository.version)
            if repository in init_plugins:
                init_plugin = init_plugins[repository]
                self._call_stdio('verbose', 'Exec %s init plugin' % repository)
                self._call_stdio('verbose', 'Apply %s for %s-%s' % (init_plugin, repository.name, repository.version))
                if init_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], opt, self.stdio):
                    deploy.use_model(repository.name, repository, False)
                    component_num -= 1
            else:
                self._call_stdio('print', 'No such init plugin for %s' % repository.name)
        
        if component_num == 0 and deploy.update_deploy_status(DeployStatus.STATUS_DEPLOYED):
            self._call_stdio('print', '%s deployed' % name)
            return True
        return False

    def start_cluster(self, name, cmd=[], options=Values()):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status not in [DeployStatus.STATUS_DEPLOYED, DeployStatus.STATUS_STOPPED, DeployStatus.STATUS_RUNNING]:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not start an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
            return False

        if deploy_info.config_status == DeployConfigStatus.NEED_REDEPLOY:
            self._call_stdio('error', 'Deploy needs redeploy')
            return False
        if deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
            self._call_stdio('verbose', 'Apply temp deploy configuration')
            if not deploy.apply_temp_deploy_config():
                self._call_stdio('error', 'Failed to apply new deploy configuration')
                return False

        self._call_stdio('verbose', 'Get deploy config')
        deploy_config = deploy.deploy_config

        self._call_stdio('start_loading', 'Get local repositories and plugins')

        # Get the repository
        repositories = self.load_local_repositories(deploy_config, False)

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        if DeployStatus.STATUS_RUNNING == deploy_info.status:
            cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
            if cluster_status == 1:
                self._call_stdio('print', 'Deploy "%s" is running' % name)
                return True

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)

        # Parameter check
        self._call_stdio('verbose', 'Cluster param config check')
        errors = self.deploy_param_check(repositories, deploy_config)
        if errors:
            self._call_stdio('error', '\n'.join(errors))
            return False

        start_check_plugins = self.search_py_script_plugin(repositories, 'start_check', False)
        start_plugins = self.search_py_script_plugin(repositories, 'start')
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        bootstrap_plugins = self.search_py_script_plugin(repositories, 'bootstrap')
        display_plugins = self.search_py_script_plugin(repositories, 'display')
        self._call_stdio('stop_loading', 'succeed')
        
        strict_check = getattr(options, 'strict_check', False)
        success = True
        for repository in repositories:
            if repository not in start_check_plugins:
                continue
            cluster_config = deploy_config.components[repository.name]
            self._call_stdio('verbose', 'Call %s for %s' % (start_check_plugins[repository], repository))
            ret = start_check_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, cmd, options, self.stdio, alert_lv='error' if strict_check else 'warn')
            if not ret:
                success = False
        
        if strict_check and success is False:
            # self._call_stdio('verbose', 'Starting check failed. Use --skip-check to skip the starting check. However, this may lead to a starting failure.')
            return False

        component_num = len(repositories)
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            if not deploy_config.unuse_lib_repository:
                for server in cluster_config.servers:
                    client = ssh_clients[server]
                    remote_home_path = client.execute_command('echo $HOME/.obd').stdout.strip()
                    remote_repository_path = repository.repository_dir.replace(self.home_path, remote_home_path)
                    client.add_env('LD_LIBRARY_PATH', '%s/lib:' % remote_repository_path, True)

            self._call_stdio('verbose', 'Call %s for %s' % (start_plugins[repository], repository))
            ret = start_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, cmd, options, self.stdio, self.home_path, repository.repository_dir)
            if ret:
                need_bootstrap = ret.get_return('need_bootstrap')
            else:
                self._call_stdio('error', '%s start failed' % repository.name)
                break

            if not deploy_config.unuse_lib_repository:
                for server in cluster_config.servers:
                    client = ssh_clients[server]
                    client.add_env('LD_LIBRARY_PATH', '', True)

            self._call_stdio('verbose', 'Call %s for %s' % (connect_plugins[repository], repository))
            ret = connect_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, cmd, options, self.stdio)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            else:
                self._call_stdio('error', 'Failed to connect %s' % repository.name)
                break

            if need_bootstrap:
                self._call_stdio('print', 'Initialize cluster')
                self._call_stdio('verbose', 'Call %s for %s' % (bootstrap_plugins[repository], repository))
                if not bootstrap_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, cmd, options, self.stdio, cursor):
                    self._call_stdio('print', 'Cluster init failed')
                    break
            self._call_stdio('verbose', 'Call %s for %s' % (display_plugins[repository], repository))
            if display_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, cmd, options, self.stdio, cursor):
                component_num -= 1
        
        if component_num == 0:
            self._call_stdio('verbose', 'Set %s deploy status to running' % name)
            if deploy.update_deploy_status(DeployStatus.STATUS_RUNNING):
                self._call_stdio('print', '%s running' % name)
                return True
        return False

    def reload_cluster(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s. Input the configuration path to create a new deploy' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not realod an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
            return False

        if deploy_info.config_status != DeployConfigStatus.NEED_RELOAD:
            self._call_stdio('error', 'Deploy config %s' % deploy_info.config_status.value)
            return False

        self._call_stdio('verbose', 'Get deploy config')
        deploy_config = deploy.deploy_config
        self._call_stdio('verbose', 'Apply new deploy config')
        new_deploy_config = DeployConfig(deploy.get_temp_deploy_yaml_path(deploy.config_dir), YamlLoader(self.stdio))

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_config)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self.search_param_plugin_and_apply(repositories, new_deploy_config)

        reload_plugins = self.search_py_script_plugin(repositories, 'reload')
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')

        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            if self.stdio:
                self._call_stdio('error', 'Some of the servers in the cluster have been stopped')
                for repository in component_status:
                    cluster_status = component_status[repository]
                    for server in cluster_status:
                        if cluster_status[server] == 0:
                            self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
            return False
            
        component_num = len(repositories)
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            new_cluster_config = new_deploy_config.components[repository.name]

            self._call_stdio('verbose', 'Call %s for %s' % (connect_plugins[repository], repository))
            ret = connect_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            else:
                self._call_stdio('error', 'Failed to connect %s' % repository.name)
                continue

            self._call_stdio('verbose', 'Call %s for %s' % (reload_plugins[repository], repository))
            if not reload_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, cursor, new_cluster_config):
                continue
            component_num -= 1
        if component_num == 0:
            if deploy.apply_temp_deploy_config():
                self._call_stdio('print', '%s reload' % name)
                return True
        else:
            deploy_config.dump()
            self._call_stdio('warn', 'Some configuration items reload failed')
        return False

    def display_cluster(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('print', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False
        self._call_stdio('verbose', 'Get deploy config')
        deploy_config = deploy.deploy_config

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_config)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
            
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        display_plugins = self.search_py_script_plugin(repositories, 'display')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
        self._call_stdio('stop_loading', 'succeed')

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            if self.stdio:
                self._call_stdio('error', 'Some of the servers in the cluster have been stopped')
                for repository in component_status:
                    cluster_status = component_status[repository]
                    for server in cluster_status:
                        if cluster_status[server] == 0:
                            self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
            return False
            
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]

            db = None
            cursor = None
            self._call_stdio('verbose', 'Call %s for %s' % (connect_plugins[repository], repository))
            ret = connect_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            if not db:
                self._call_stdio('error', 'Failed to connect %s' % repository.name)
                return False

            self._call_stdio('verbose', 'Call %s for %s' % (display_plugins[repository], repository))
            display_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, cursor)
        return True

    def stop_cluster(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Check the deploy status')
        if deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not stop an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
            return False
        self._call_stdio('verbose', 'Get deploy config')
        deploy_config = deploy.deploy_config

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_config)

        # Check whether the components have the parameter plugins and apply the plugins

        self.search_param_plugin_and_apply(repositories, deploy_config)

        stop_plugins = self.search_py_script_plugin(repositories, 'stop')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
        self._call_stdio('stop_loading', 'succeed')

        component_num = len(repositories)
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            self._call_stdio('verbose', 'Call %s for %s' % (stop_plugins[repository], repository))
            if stop_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio):
                component_num -= 1
        
        self._call_stdio('verbose', 'Set %s deploy status to stopped' % name)
        if component_num == 0 and deploy.update_deploy_status(DeployStatus.STATUS_STOPPED):
            self._call_stdio('print', '%s stopped' % name)
            return True
        return False

    def restart_cluster(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Check the deploy status')
        if deploy_info.status == DeployStatus.STATUS_RUNNING and not self.stop_cluster(name):
            return False
        return self.start_cluster(name)

    def redeploy_cluster(self, name):
        return self.destroy_cluster(name) and self.deploy_cluster(name) and self.start_cluster(name)

    def destroy_cluster(self, name, opt=Values()):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Check deploy status')
        if deploy_info.status == DeployStatus.STATUS_RUNNING:
            if not self.stop_cluster(name):
                return False
        elif deploy_info.status not in [DeployStatus.STATUS_STOPPED, DeployStatus.STATUS_DEPLOYED]:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not destroy an undeployed cluster' % (name, deploy_info.status.value))
            return False
        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_config)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)

        plugins = self.search_py_script_plugin(repositories, 'destroy')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
        self._call_stdio('stop_loading', 'succeed')

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 1:
            force_kill = getattr(opt, 'force_kill', False)
            msg_lv = 'warn' if force_kill else 'error'
            self._call_stdio(msg_lv, 'Some of the servers in the cluster are running')
            if force_kill:
                self._call_stdio('verbose', 'Try to stop cluster')
                status = deploy.deploy_info.status
                deploy.update_deploy_status(DeployStatus.STATUS_RUNNING)
                if not self.stop_cluster(name):
                    deploy.update_deploy_status(status)
                    self._call_stdio('error', 'Fail to stop cluster')
                    return False
            else:
                if self.stdio:
                    for repository in component_status:
                        cluster_status = component_status[repository]
                        for server in cluster_status:
                            if cluster_status[server] == 1:
                                self._call_stdio('print', '%s %s is running' % (server, repository.name))
                    self._call_stdio('print', 'You could try using -f to force kill process')
                return False

        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]

            self._call_stdio('verbose', 'Call %s for %s' % (plugins[repository], repository))
            plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio)
        
        self._call_stdio('verbose', 'Set %s deploy status to destroyed' % name)
        if deploy.update_deploy_status(DeployStatus.STATUS_DESTROYED):
            self._call_stdio('print', '%s destroyed' % name)
            return True
        return False

    def create_repository(self, options):
        force = getattr(options, 'force', False)
        necessary = ['name', 'version', 'path']
        attrs = options.__dict__
        success = True
        for key in necessary:
            if key not in attrs or not attrs[key]:
                success = False
                self._call_stdio('error', 'option: %s is necessary' % key)
        if success is False:
            return False
        plugin = self.plugin_manager.get_best_plugin(PluginType.INSTALL, attrs['name'], attrs['version'])
        if plugin:
            self._call_stdio('verbose', 'Found %s for %s-%s' % (plugin, attrs['name'], attrs['version']))
        else:
            self._call_stdio('error', 'No such %s plugin for %s-%s' % (PluginType.INSTALL.name.lower(), attrs['name'], attrs['version']))
            return False

        files = {}
        success = True
        repo_path = attrs['path']
        for item in plugin.file_list():
            path = os.path.join(repo_path, item.src_path)
            path = os.path.normcase(path)
            if not os.path.exists(path):
                path = os.path.join(repo_path, item.target_path)
                path = os.path.normcase(path)
                if not os.path.exists(path):
                    self._call_stdio('error', 'need file: %s ' % path)
                    success = False
                    continue
            files[item.src_path] = path
        if success is False:
            return False

        self._call_stdio('start_loading', 'Package')
        try:
            pkg = LocalPackage(repo_path, attrs['name'], attrs['version'], files, getattr(options, 'release', None), getattr(options, 'arch', None))
            self._call_stdio('stop_loading', 'succeed')
        except:
            self._call_stdio('exception', 'Package failed')
            self._call_stdio('stop_loading', 'fail')
            return False
        self._call_stdio('print', pkg)
        repository = self.repository_manager.get_repository_allow_shadow(attrs['name'], attrs['version'], pkg.md5)
        if os.path.exists(repository.repository_dir):
            if not force or not DirectoryUtil.rm(repository.repository_dir):
                self._call_stdio('error', 'Repository(%s) exists' % repository.repository_dir)
                return False
        repository = self.repository_manager.create_instance_repository(attrs['name'], attrs['version'], pkg.md5)
        if not repository.load_pkg(pkg, plugin):
            self._call_stdio('error', 'Failed to extract file from %s' % pkg.path)
            return False
        if 'tag' in attrs and attrs['tag']:
            for tag in attrs['tag'].split(','):
                tag_repository = self.repository_manager.get_repository_allow_shadow(tag, attrs['version'])
                self._call_stdio('verbose', 'Create tag(%s) for %s' % (tag, attrs['name']))
                if not self.repository_manager.create_tag_for_repository(repository, tag, force):
                    self._call_stdio('error', 'Repository(%s) existed' % tag_repository.repository_dir)
        return True

    def mysqltest(self, name, opts):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Check deploy status')
        if deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('print', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False
        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config

        if opts.component is None:
            for component_name in ['obproxy', 'oceanbase', 'oceanbase-ce']:
                if component_name in deploy_config.components:
                    opts.component = component_name
                    break
        if opts.component not in deploy_config.components:
            self._call_stdio('error', 'Can not find the component for mysqltest, use `--component` to select component')
            return False
        
        cluster_config = deploy_config.components[opts.component]
        if not cluster_config.servers:
            self._call_stdio('error', '%s server list is empty' % opts.component)
            return False
        if opts.test_server is None:
            opts.test_server = cluster_config.servers[0]
        else:
            for server in cluster_config.servers:
                if server.name == opts.test_server:
                    opts.test_server = server
                    break
            else:
                self._call_stdio('error', '%s is not a server in %s' % (opts.test_server, opts.component))
                return False

        if opts.auto_retry:
            for component_name in ['oceanbase', 'oceanbase-ce']:
                if component_name in deploy_config.components:
                    break
            else:
                opts.auto_retry = False
                self._call_stdio('warn', 'Set auto-retry to false because of %s does not contain the configuration of oceanbase database' % name)

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.get_local_repositories({opts.component: deploy_config.components[opts.component]})
        repository = repositories[0]

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
        self._call_stdio('stop_loading', 'succeed')

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            if self.stdio:
                self._call_stdio('error', 'Some of the servers in the cluster have been stopped')
                for repository in component_status:
                    cluster_status = component_status[repository]
                    for server in cluster_status:
                        if cluster_status[server] == 0:
                            self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
            return False

        connect_plugin = self.search_py_script_plugin(repositories, 'connect')[repository]
        ret = connect_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, target_server=opts.test_server, sys_root=False)
        if not ret or not ret.get_return('connect'):
            self._call_stdio('error', 'Failed to connect to the server')
            return False
        db = ret.get_return('connect')
        cursor = ret.get_return('cursor')

        mysqltest_init_plugin = self.plugin_manager.get_best_py_script_plugin('init', 'mysqltest', repository.version)
        mysqltest_check_opt_plugin = self.plugin_manager.get_best_py_script_plugin('check_opt', 'mysqltest', repository.version)
        mysqltest_check_test_plugin = self.plugin_manager.get_best_py_script_plugin('check_test', 'mysqltest', repository.version)
        mysqltest_run_test_plugin = self.plugin_manager.get_best_py_script_plugin('run_test', 'mysqltest', repository.version)

        env = opts.__dict__
        env['cursor'] = cursor
        env['host'] = opts.test_server.ip
        env['port'] = db.port
        self._call_stdio('verbose', 'Call %s for %s' % (mysqltest_check_opt_plugin, repository))
        ret = mysqltest_check_opt_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, env)
        if not ret:
            return False
        self._call_stdio('verbose', 'Call %s for %s' % (mysqltest_check_test_plugin, repository))
        ret = mysqltest_check_test_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, env)
        if not ret:
            self._call_stdio('error', 'Failed to get test set')
            return False
        if not env['test_set']:
            self._call_stdio('error', 'Test set is empty')
            return False

        if env['need_init']:
            self._call_stdio('verbose', 'Call %s for %s' % (mysqltest_init_plugin, repository))
            if not mysqltest_init_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, env):
                self._call_stdio('error', 'Failed to init for mysqltest')
                return False
        
        result = []
        for test in env['test_set']:
            ret = mysqltest_run_test_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, test, env)
            if not ret:
                break
            case_result = ret.get_return('result')
            if case_result['ret'] != 0 and opts.auto_retry:
                cursor.close()
                db.close()
                if getattr(self.stdio, 'sub_io'):
                    stdio = self.stdio.sub_io(msg_lv=MsgLevel.ERROR)
                else:
                    stdio = None
                self._call_stdio('start_loading', 'Reboot')
                obd = ObdHome(self.home_path, stdio=stdio, lock=False)
                if obd.redeploy_cluster(name):
                    self._call_stdio('stop_loading', 'succeed')
                else:
                    self._call_stdio('stop_loading', 'fail')
                    result.append(case_result)
                    break
                connect_plugin = self.search_py_script_plugin(repositories, 'connect')[repository]
                ret = connect_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, target_server=opts.test_server, sys_root=False)
                if not ret or not ret.get_return('connect'):
                    self._call_stdio('error', 'Failed to connect server')
                    break
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
                env['cursor'] = cursor
                self._call_stdio('verbose', 'Call %s for %s' % (mysqltest_init_plugin, repository))
                if not mysqltest_init_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, env):
                    self._call_stdio('error', 'Failed to prepare for mysqltest')
                    break
                ret = mysqltest_run_test_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, test, env)
                if not ret:
                    break
                case_result = ret.get_return('result')

            result.append(case_result)

        passcnt = len(list(filter(lambda x: x["ret"] == 0, result)))
        totalcnt = len(env['test_set'])
        failcnt = totalcnt - passcnt
        if result:
            self._call_stdio(
                'print_list', result, ['Case', 'Cost (s)', 'Status'], 
                lambda x: [x['name'], '%.2f' % x['cost'], '\033[31mFAILED\033[0m' if x['ret'] else '\033[32mPASSED\033[0m'], 
                title='Result (Total %d, Passed %d, Failed %s)' % (totalcnt, passcnt, failcnt), 
                align={'Cost (s)': 'r'}
            )
        if failcnt:
            self._call_stdio('print', 'Mysqltest failed')
        else:
            self._call_stdio('print', 'Mysqltest passed')
            return True
        return False
