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
from _rpm import Version
from _mirror import MirrorRepositoryManager, PackageInfo
from _plugin import PluginManager, PluginType, InstallPlugin
from _repository import RepositoryManager, LocalPackage, Repository
from _deploy import (
    DeployManager, DeployStatus, 
    DeployConfig, DeployConfigStatus,
    ParserError, Deploy
)
from _errno import EC_SOME_SERVER_STOPED
from _lock import LockManager


class ObdHome(object):

    HOME_LOCK_RELATIVE_PATH = 'obd.conf'

    def __init__(self, home_path, dev_mode=False, stdio=None):
        self.home_path = home_path
        self.dev_mode = dev_mode
        self._lock = None
        self._home_conf = None
        self._mirror_manager = None
        self._repository_manager = None
        self._deploy_manager = None
        self._plugin_manager = None
        self._lock_manager = None
        self.stdio = None
        self._stdio_func = None
        self.set_stdio(stdio)
        self.lock_manager.global_sh_lock()

    @property
    def mirror_manager(self):
        if not self._mirror_manager:
            self._mirror_manager = MirrorRepositoryManager(self.home_path, self.lock_manager, self.stdio)
        return self._mirror_manager

    @property
    def repository_manager(self):
        if not self._repository_manager:
            self._repository_manager = RepositoryManager(self.home_path, self.lock_manager, self.stdio)
        return self._repository_manager

    @property
    def plugin_manager(self):
        if not self._plugin_manager:
            self._plugin_manager = PluginManager(self.home_path, self.dev_mode, self.stdio)
        return self._plugin_manager

    @property
    def deploy_manager(self):
        if not self._deploy_manager:
            self._deploy_manager = DeployManager(self.home_path, self.lock_manager, self.stdio)
        return self._deploy_manager

    @property
    def lock_manager(self):
        if not self._lock_manager:
            self._lock_manager = LockManager(self.home_path, self.stdio)
        return self._lock_manager

    def _obd_update_lock(self):
        self.lock_manager.global_ex_lock()

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
            errors += cluster_config.check_param()[1]
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
        self._call_stdio('verbose', 'Search %s plugin for %s' % (plugin_type.name.lower(), repository.name))
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

    def search_py_script_plugin(self, repositories, script_name, no_found_act='exit'):
        if no_found_act == 'exit':
            no_found_exit = True
        else:
            no_found_exit = False
            msg_lv = 'warn' if no_found_act == 'warn' else 'verbose'
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
                    self._call_stdio(msg_lv, 'No such %s plugin for %s-%s' % (script_name, repository.name, repository.version))
        return plugins

    def search_images(self, component_name, version, release=None, disable=[], usable=[], release_first=False, print_match=True):
        matchs = {}
        usable_matchs = []
        for pkg in self.mirror_manager.get_pkgs_info(component_name, version=version, release=release):
            if pkg.md5 in disable:
                self._call_stdio('verbose', 'Disable %s' % pkg.md5)
            else:
                matchs[pkg.md5] = pkg
        for repo in self.repository_manager.get_repositories(component_name, version):
            if release and release != repo.release:
                continue
            if repo.md5 in disable:
                self._call_stdio('verbose', 'Disable %s' % repo.md5)
            else:
                matchs[repo.md5] = repo
        if matchs:
            print_match and self._call_stdio(
                'print_list',
                matchs,
                ['name', 'version', 'release', 'arch', 'md5'], 
                lambda x: [matchs[x].name, matchs[x].version, matchs[x].release, matchs[x].arch, matchs[x].md5],
                title='Search %s %s Result' % (component_name, version) 
            )
            for md5 in usable:
                if md5 in matchs:
                    self._call_stdio('verbose', 'Usable %s' % md5)
                    usable_matchs.append(matchs[md5])
            if not usable_matchs:
                usable_matchs = [info[1] for info in sorted(matchs.items())]
                if release_first:
                    usable_matchs = usable_matchs[:1]
            
        return usable_matchs
    
    def search_components_from_mirrors(self, deploy_config, fuzzy_match=False, only_info=True, update_if_need=None):
        pkgs = []
        errors = []
        repositories = []
        self._call_stdio('verbose', 'Search package for components...')
        for component in deploy_config.components:
            config = deploy_config.components[component]
            # First, check if the component exists in the repository. If exists, check if the version is available. If so, use the repository directly.

            self._call_stdio('verbose', 'Get %s repository' % component)
            repository = self.repository_manager.get_repository(component, config.version, config.package_hash if config.package_hash else config.tag)
            if repository and not repository.hash:
                repository = None
            self._call_stdio('verbose', 'Search %s package from mirror' % component)
            pkg = self.mirror_manager.get_best_pkg(name=component, version=config.version, md5=config.package_hash, fuzzy_match=fuzzy_match, only_info=only_info)
            if repository or pkg:
                if pkg:
                    self._call_stdio('verbose', 'Found Package %s-%s-%s' % (pkg.name, pkg.version, pkg.md5))
                if repository:
                    if repository >= pkg or (
                        (
                            update_if_need is None and 
                            not self._call_stdio('confirm', 'Found a higher version\n%s\nDo you want to use it?' % pkg)
                        ) or update_if_need is False
                    ):
                        repositories.append(repository)
                        self._call_stdio('verbose', 'Use repository %s' % repository)
                        self._call_stdio('print', '%s-%s already installed.' % (repository.name, repository.version))
                        continue
                if config.version and pkg.version != config.version:
                    self._call_stdio('warn', 'No such package %s-%s. Use similar package %s-%s.' % (component, config.version, pkg.name, pkg.version))
                else:
                    self._call_stdio('print', 'Package %s-%s is available.' % (pkg.name, pkg.version))
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

    def load_local_repositories(self, deploy_info, allow_shadow=True):
        repositories = []
        if allow_shadow:
            get_repository = self.repository_manager.get_repository_allow_shadow
        else:
            get_repository = self.repository_manager.get_repository

        components = deploy_info.components
        for component_name in components:
            data = components[component_name]
            version = data.get('version')
            pkg_hash = data.get('hash')
            self._call_stdio('verbose', 'Get local repository %s-%s-%s' % (component_name, version, pkg_hash))
            repository = get_repository(component_name, version, pkg_hash)
            if repository:
                repositories.append(repository)
            else:
                self._call_stdio('critical', 'Local repository %s-%s-%s is empty.' % (component_name, version, pkg_hash))
        return repositories

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
        def is_server_list_change(deploy_config):
            for component_name in deploy_config.components:
                if deploy_config.components[component_name].servers != deploy.deploy_config.components[component_name].servers:
                    return True
            return False
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        param_plugins = {}
        repositories, pkgs = [], []
        is_deployed = deploy and deploy.deploy_info.status not in [DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_DESTROYED]
        is_started = deploy and deploy.deploy_info.status in [DeployStatus.STATUS_RUNNING, DeployStatus.STATUS_STOPPED]
        initial_config = ''
        if deploy:
            try:
                if deploy.deploy_info.config_status == DeployConfigStatus.UNCHNAGE:
                    path = deploy.deploy_config.yaml_path
                else:
                    path = Deploy.get_temp_deploy_yaml_path(deploy.config_dir)
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
        if is_deployed:
            repositories = self.load_local_repositories(deploy.deploy_info)
            self._call_stdio('start_loading', 'Search param plugin and load')
            for repository in repositories:
                self._call_stdio('verbose', 'Search param plugin for %s' % repository)
                plugin = self.plugin_manager.get_best_plugin(PluginType.PARAM, repository.name, repository.version)
                if plugin:
                    self._call_stdio('verbose', 'Applying %s for %s' % (plugin, repository))
                    cluster_config = deploy.deploy_config.components[repository.name]
                    cluster_config.update_temp_conf(plugin.params)
                    param_plugins[repository.name] = plugin
            self._call_stdio('stop_loading', 'succeed')

        EDITOR = os.environ.get('EDITOR','vi')
        self._call_stdio('verbose', 'Get environment variable EDITOR=%s' % EDITOR)
        self._call_stdio('verbose', 'Create tmp yaml file')
        tf = tempfile.NamedTemporaryFile(suffix=".yaml")
        tf.write(initial_config.encode())
        tf.flush()
        self.lock_manager.set_try_times(-1)
        config_status = DeployConfigStatus.UNCHNAGE
        while True:
            tf.seek(0)
            self._call_stdio('verbose', '%s %s' % (EDITOR, tf.name))
            subprocess_call([EDITOR, tf.name])
            self._call_stdio('verbose', 'Load %s' % tf.name)
            try:
                deploy_config = DeployConfig(tf.name, yaml_loader=YamlLoader(self.stdio), config_parser_manager=self.deploy_manager.config_parser_manager)
            except Exception as e:
                if confirm(e):
                    continue
                break

            self._call_stdio('verbose', 'Configure component change check')
            if not deploy_config.components:
                if self._call_stdio('confirm', 'Empty configuration. Continue editing?'):
                    continue
                return False
            self._call_stdio('verbose', 'Information check for the configuration component.')
            if not deploy:
                config_status = DeployConfigStatus.UNCHNAGE
            elif is_deployed:
                if deploy_config.components.keys() != deploy.deploy_config.components.keys() or is_server_list_change(deploy_config):
                    if not self._call_stdio('confirm', 'Modifications to the deployment architecture take effect after you redeploy the architecture. Are you sure that you want to start a redeployment? '):
                        continue
                    config_status = DeployConfigStatus.NEED_REDEPLOY
                else:
                    for component_name in deploy_config.components:
                        old_cluster_config = deploy.deploy_config.components[component_name]
                        new_cluster_config = deploy_config.components[component_name]
                        if new_cluster_config.version != old_cluster_config.origin_version \
                            or new_cluster_config.package_hash != old_cluster_config.origin_package_hash \
                            or new_cluster_config.tag != old_cluster_config.origin_tag:
                            config_status = DeployConfigStatus.NEED_REDEPLOY
                            break
                    
            # Loading the parameter plugins that are available to the application
            self._call_stdio('start_loading', 'Search param plugin and load')
            if not is_deployed or config_status == DeployConfigStatus.NEED_REDEPLOY:
                param_plugins = {}
                pkgs, repositories, errors = self.search_components_from_mirrors(deploy_config, update_if_need=False)
                for repository in repositories:
                    self._call_stdio('verbose', 'Search param plugin for %s' % repository)
                    plugin = self.plugin_manager.get_best_plugin(PluginType.PARAM, repository.name, repository.version)
                    if plugin:
                        param_plugins[repository.name] = plugin
                for pkg in pkgs:
                    self._call_stdio('verbose', 'Search param plugin for %s' % pkg)
                    plugin = self.plugin_manager.get_best_plugin(PluginType.PARAM, pkg.name, pkg.version)
                    if plugin:
                        param_plugins[pkg.name] = plugin

            for component_name in param_plugins:
                deploy_config.components[component_name].update_temp_conf(param_plugins[component_name].params)

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
                self._call_stdio('print', 'Deploy "%s" config %s%s' % (name, config_status.value, deploy.effect_tip() if deploy else ''))
                return True

            if is_deployed and config_status != DeployConfigStatus.NEED_REDEPLOY:
                if is_started:
                    if deploy.deploy_config.user.username != deploy_config.user.username:
                        config_status = DeployConfigStatus.NEED_RESTART
                    errors = []
                    for component_name in param_plugins:
                        old_cluster_config = deploy.deploy_config.components[component_name]
                        new_cluster_config = deploy_config.components[component_name]
                        modify_limit_params = param_plugins[component_name].modify_limit_params
                        for server in old_cluster_config.servers:
                            old_config = old_cluster_config.get_server_conf(server)
                            new_config = new_cluster_config.get_server_conf(server)
                            for item in modify_limit_params:
                                key = item.name
                                try:
                                    item.modify_limit(old_config.get(key), new_config.get(key))
                                except Exception as e:
                                    self._call_stdio('exceptione', '')
                                    errors.append('[%s] %s: %s' % (component_name, server, str(e)))
                    if errors:
                        self._call_stdio('print', '\n'.join(errors))
                        if self._call_stdio('confirm', 'Modifications take effect after a redeployment. Are you sure that you want to start a redeployment?'):
                            config_status = DeployConfigStatus.NEED_REDEPLOY
                        elif self._call_stdio('confirm', 'Continue to edit?'):
                            continue
                        else:
                            return False
                    
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
            target_src_path = Deploy.get_temp_deploy_yaml_path(deploy.config_dir)
            old_config_status = deploy.deploy_info.config_status
            try:
                if deploy.update_deploy_config_status(config_status):
                    FileUtil.copy(tf.name, target_src_path, self.stdio)
                ret = True
                if deploy:
                    if deploy.deploy_info.status == DeployStatus.STATUS_RUNNING or (
                        config_status == DeployConfigStatus.NEED_REDEPLOY and is_deployed
                    ):
                        msg += deploy.effect_tip()
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
            self._call_stdio('verbose', 'get head repository')
            head_repository = self.repository_manager.get_repository(pkg.name, pkg.version, pkg.name)
            self._call_stdio('verbose', 'head repository: %s' % head_repository)
            if repository > head_repository:
                self.repository_manager.create_tag_for_repository(repository, pkg.name, True)
            repositories.append(repository)
        return install_plugins

    def install_lib_for_repositories(self, repositories):
        all_data = []
        temp_repositories = repositories
        while temp_repositories:
            data = {}
            temp_map = {}
            repositories = temp_repositories
            temp_repositories = []
            for repository in repositories:
                lib_name = '%s-libs' % repository.name
                if lib_name in data:
                    temp_repositories.append(repository)
                    continue
                data[lib_name] = {'global': {
                    'version': repository.version
                }}
                temp_map[lib_name] = repository
            all_data.append((data, temp_map))
        try:
            repositories_lib_map = {}
            for data, temp_map in all_data:
                with tempfile.NamedTemporaryFile(suffix=".yaml", mode='w') as tf:
                    yaml_loader = YamlLoader(self.stdio)
                    yaml_loader.dump(data, tf)
                    deploy_config = DeployConfig(tf.name, yaml_loader=yaml_loader, config_parser_manager=self.deploy_manager.config_parser_manager)
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
            remote_home_path = client.execute_command('echo ${OBD_HOME:-"$HOME"}/.obd').stdout.strip()
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
                if not client.put_file(file_path, remote_file_path):
                    self._call_stdio('stop_loading', 'fail')
                    return False
            client.put_file(repository.data_file_path, remote_repository_data_path)
            self._call_stdio('verbose', '%s %s installed' % (server, repository.name))
        self._call_stdio('stop_loading', 'succeed')
        return True

    def servers_repository_lib_check(self, ssh_clients, servers, repository, install_plugin, msg_lv='error'):
        ret = True
        self._call_stdio('start_loading', 'Remote %s repository lib check' % repository)
        for server in servers:
            self._call_stdio('verbose', '%s %s repository lib check' % (server, repository))
            client = ssh_clients[server]
            need_libs = set()
            remote_home_path = client.execute_command('echo ${OBD_HOME:-"$HOME"}/.obd').stdout.strip()
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
                    servers_obd_home[server] = client.execute_command('echo ${OBD_HOME:-"$HOME"}/.obd').stdout.strip()
                remote_home_path = servers_obd_home[server]
                remote_lib_repository_data_path = lib_repository.repository_dir.replace(self.home_path, remote_home_path)
            # lib installation
            self._call_stdio('verbose', 'Remote %s repository integrity check' % repository)
            if not self.servers_repository_install(ssh_clients, cluster_config.servers, lib_repository, install_plugin):
                ret = False
                break
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
        self._call_stdio('start_loading', 'Cluster status check')
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
            self._call_stdio('stop_loading', 'succeed')
            return False
        status = None
        for repository in component_status:
            if status is None:
                status = component_status[repository]
                continue
            if status != component_status[repository]:
                self._call_stdio('verbose', 'Deploy status inconsistent')
                self._call_stdio('stop_loading', 'succeed')
                return False
        self._call_stdio('stop_loading', 'succeed')
        return status

    def search_components_from_mirrors_and_install(self, deploy_config):
        # Check the best suitable mirror for the components
        self._call_stdio('verbose', 'Search best suitable repository')
        pkgs, repositories, errors = self.search_components_from_mirrors(deploy_config, only_info=False)
        if errors:
            self._call_stdio('error', '\n'.join(errors))
            return repositories, None

        # Get the installation plugins. Install locally
        install_plugins = self.get_install_plugin_and_install(repositories, pkgs)
        return repositories, install_plugins

    def sort_repositories_by_depends(self, deploy_config, repositories):
        sort_repositories = []
        wait_repositories = repositories
        imported_depends = []
        available_depends = [repository.name for repository in repositories]
        while wait_repositories:
            repositories = wait_repositories
            wait_repositories = []
            for repository in repositories:
                cluster_config = deploy_config.components[repository.name]
                for component_name in cluster_config.depends:
                    if component_name not in available_depends:
                        continue
                    if component_name not in imported_depends:
                        wait_repositories.append(repository)
                        break
                else:
                    sort_repositories.append(repository)
                    imported_depends.append(repository.name)
        return sort_repositories

    def genconfig(self, name, opt=Values()):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if deploy:
            deploy_info = deploy.deploy_info
            if deploy_info.status not in [DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_DESTROYED]:
                self._call_stdio('error', 'Deploy "%s" is %s. You could not deploy an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
                return False
            # self._call_stdio('error', 'Deploy name `%s` have been occupied.' % name)
            # return False

        config_path = getattr(opt, 'config', '')
        if not config_path:
            self._call_stdio('error', "Configuration file is need.\nPlease use -c to set configuration file")
            return False

        self._call_stdio('verbose', 'Create deploy by configuration path')
        deploy = self.deploy_manager.create_deploy_config(name, config_path)
        if not deploy:
            return False

        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config
        if not deploy_config:
            self._call_stdio('error', 'Deploy configuration is empty.\nIt may be caused by a failure to resolve the configuration.\nPlease check your configuration file.')
            return False

        # Check the best suitable mirror for the components and installation plguins. Install locally
        repositories, install_plugins = self.search_components_from_mirrors_and_install(deploy_config)
        if not install_plugins or not repositories:
            return False

        for repository in repositories:
            real_servers = set()
            cluster_config = deploy_config.components[repository.name]
            for server in cluster_config.servers:
                if server.ip in real_servers:
                    self._call_stdio('error', 'Deploying multiple %s instances on the same server is not supported.' % repository.name)
                    return False
                real_servers.add(server.ip)
        
        self._call_stdio('start_loading', 'Cluster param config check')
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)

        # Parameter check
        errors = self.deploy_param_check(repositories, deploy_config)
        if errors:
            self._call_stdio('stop_loading', 'fail')
            self._call_stdio('error', '\n'.join(errors))
            return False
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        gen_config_plugins = self.search_py_script_plugin(repositories, 'generate_config')
        
        component_num = len(repositories)
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]

            self._call_stdio('verbose', 'Call %s for %s' % (gen_config_plugins[repository], repository))
            ret = gen_config_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], opt, self.stdio, deploy_config)
            if ret:
                component_num -= 1
                
        if component_num == 0 and deploy_config.dump():
            return True
        
        self.deploy_manager.remove_deploy_config(name)
        return False

    def check_for_ocp(self, name, options=Values()):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
            
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('error', 'Deploy "%s" not RUNNING' % (name))
            return False
            
        version = getattr(options, 'version', '')
        if not version:
            self._call_stdio('error', 'Use the --version option to specify the required OCP version.')
            return False

        deploy_config = deploy.deploy_config
        components = getattr(options, 'components', '')
        if components:
            components = components.split(',')
            for component in components:
                if component not in deploy_config.components:
                    self._call_stdio('error', 'No such component: %s' % component)
                    return False
        else:
            components = deploy_config.components.keys()

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)

        ocp_check = self.search_py_script_plugin(repositories, 'ocp_check', no_found_act='ignore')
        connect_plugins = self.search_py_script_plugin([repository for repository in ocp_check], 'connect')

        self._call_stdio('stop_loading', 'succeed')

        self._call_stdio('start_loading', 'Load cluster param plugin')
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        if deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
            new_deploy_config = deploy.temp_deploy_config
            change_user = deploy_config.user.username != new_deploy_config.user.username
            self.search_param_plugin_and_apply(repositories, new_deploy_config)
        else:
            new_deploy_config = None

        self._call_stdio('stop_loading', 'succeed')
        
        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
        if new_deploy_config and deploy_config.user.username != new_deploy_config.user.username:
            new_ssh_clients = self.get_clients(new_deploy_config, repositories)
        else:
            new_ssh_clients = None

        component_num = len(repositories)
        for repository in repositories:
            if repository.name not in components:
                continue
            if repository not in ocp_check:
                component_num -= 1
                self._call_stdio('print', '%s No check plugin available.' % repository.name)
                continue
                
            cluster_config = deploy_config.components[repository.name]
            new_cluster_config = new_deploy_config.components[repository.name] if new_deploy_config else None
            cluster_servers = cluster_config.servers
            
            self._call_stdio('verbose', 'Call %s for %s' % (connect_plugins[repository], repository))
            ret = connect_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, '', options, self.stdio)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            else:
                break
            
            self._call_stdio('verbose', 'Call %s for %s' % (ocp_check[repository], repository))
            if ocp_check[repository](deploy_config.components.keys(), ssh_clients, cluster_config, '', options, self.stdio, cursor=cursor, ocp_version=version, new_cluster_config=new_cluster_config, new_clients=new_ssh_clients):
                component_num -= 1
                self._call_stdio('print', '%s Check passed.' % repository.name)
        
        return component_num == 0

    def change_deploy_config_style(self, name, options=Values()):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
            
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy config status judge')
        if deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
            self._call_stdio('error', 'Deploy %s %s' % (name, deploy_info.config_status.value))
            return False
        deploy_config = deploy.deploy_config
        if not deploy_config:
            self._call_stdio('error', 'Deploy configuration is empty.\nIt may be caused by a failure to resolve the configuration.\nPlease check your configuration file.')
            return False

        style = getattr(options, 'style', '')
        if not style:
            self._call_stdio('error', 'Use the --style option to specify the preferred style.')
            return False

        components = getattr(options, 'components', '')
        if components:
            components = components.split(',')
            for component in components:
                if component not in deploy_config.components:
                    self._call_stdio('error', 'No such component: %s' % component)
                    return False
        else:
            components = deploy_config.components.keys()

        self._call_stdio('start_loading', 'Change style')
        try:
            parsers = {}
            for component_name in components:
                parsers[component_name] = self.deploy_manager.config_parser_manager.get_parser(component_name, style)
                self._call_stdio('verbose', 'get %s for %s' % (parsers[component_name], component_name))

            for component_name in deploy_config.components:
                if component_name in parsers:
                    deploy_config.change_component_config_style(component_name, style)
            if deploy_config.dump():
                self._call_stdio('stop_loading', 'succeed')
                return True
        except Exception as e:
            self._call_stdio('exception', e)
        
        self._call_stdio('stop_loading', 'fail')
        return False


    def deploy_cluster(self, name, opt=Values()):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if deploy:
            self._call_stdio('verbose', 'Get deploy info')
            deploy_info = deploy.deploy_info
            self._call_stdio('verbose', 'judge deploy status')
            if deploy_info.status not in [DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_DESTROYED]:
                self._call_stdio('error', 'Deploy "%s" is %s. You could not deploy an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
                return False
            if deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
                self._call_stdio('verbose', 'Apply temp deploy configuration')
                if not deploy.apply_temp_deploy_config():
                    self._call_stdio('error', 'Failed to apply new deploy configuration')
                    return False
        
        config_path = getattr(opt, 'config', '')
        unuse_lib_repo = getattr(opt, 'unuselibrepo', False)
        auto_create_tenant = getattr(opt, 'auto_create_tenant', False)
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

        # Check the best suitable mirror for the components and installation plguins. Install locally
        repositories, install_plugins = self.search_components_from_mirrors_and_install(deploy_config)
        if not install_plugins:
            return False

        self._call_stdio(
            'print_list', 
            repositories, 
            ['Repository', 'Version', 'Release', 'Md5'], 
            lambda repository: [repository.name, repository.version, repository.release, repository.hash], 
            title='Packages'
        )

        errors = []
        self._call_stdio('start_loading', 'Repository integrity check')
        for repository in repositories:
            if not repository.file_check(install_plugins[repository]):
                errors.append('%s intstall failed' % repository.name)
        if errors:
            self._call_stdio('stop_loading', 'fail')
            self._call_stdio('error', '\n'.join(errors))
            return False
        self._call_stdio('stop_loading', 'succeed')

        self._call_stdio('start_loading', 'Parameter check')
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)

        # Parameter check
        self._call_stdio('verbose', 'Cluster param configuration check')
        errors = self.deploy_param_check(repositories, deploy_config)
        if errors:
            self._call_stdio('stop_loading', 'fail')
            self._call_stdio('error', '\n'.join(errors))
            return False
        self._call_stdio('stop_loading', 'succeed')
        
        if unuse_lib_repo and not deploy_config.unuse_lib_repository:
            deploy_config.set_unuse_lib_repository(True)
        if auto_create_tenant and not deploy_config.auto_create_tenant:
            deploy_config.set_auto_create_tenant(True)
        
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
        init_plugins = self.search_py_script_plugin(repositories, 'init')
        component_num = len(repositories)
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            init_plugin = init_plugins[repository]
            self._call_stdio('verbose', 'Exec %s init plugin' % repository)
            self._call_stdio('verbose', 'Apply %s for %s-%s' % (init_plugin, repository.name, repository.version))
            if init_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], opt, self.stdio, self.home_path, repository.repository_dir):
                deploy.use_model(repository.name, repository, False)
                component_num -= 1
        
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
        if deploy_info.config_status != DeployConfigStatus.UNCHNAGE and not getattr(options, 'without_parameter', False):
            self._call_stdio('error', 'Deploy %s.%s\nIf you still need to start the cluster, use the `obd cluster start %s --wop` option to start the cluster without loading parameters. ' % (deploy_info.config_status.value, deploy.effect_tip(), name))
            return False

        self._call_stdio('verbose', 'Get deploy config')
        deploy_config = deploy.deploy_config

        update_deploy_status = True
        components = getattr(options, 'components', '')
        if components:
            components = components.split(',')
            for component in components:
                if component not in deploy_info.components:
                    self._call_stdio('error', 'No such component: %s' % component)
                    return False
            if len(components) != len(deploy_info.components):
                update_deploy_status = False
        else:
            components = deploy_info.components.keys()

        servers = getattr(options, 'servers', '')
        server_list = servers.split(',') if servers else []

        self._call_stdio('start_loading', 'Get local repositories and plugins')

        # Get the repository
        repositories = self.load_local_repositories(deploy_info, False)

        start_check_plugins = self.search_py_script_plugin(repositories, 'start_check', no_found_act='warn')
        create_tenant_plugins = self.search_py_script_plugin(repositories, 'create_tenant', no_found_act='ignore') if deploy_config.auto_create_tenant else {}
        start_plugins = self.search_py_script_plugin(repositories, 'start')
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        bootstrap_plugins = self.search_py_script_plugin(repositories, 'bootstrap')
        display_plugins = self.search_py_script_plugin(repositories, 'display')
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        self._call_stdio('start_loading', 'Load cluster param plugin')
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Check the status for the deployed cluster
        component_status = {}
        if DeployStatus.STATUS_RUNNING == deploy_info.status:
            cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
            if cluster_status == 1:
                self._call_stdio('print', 'Deploy "%s" is running' % name)
                return True

        strict_check = getattr(options, 'strict_check', False)
        success = True
        for repository in repositories:
            if repository.name not in components:
                continue
            if repository not in start_check_plugins:
                continue
            cluster_config = deploy_config.components[repository.name]
            self._call_stdio('verbose', 'Call %s for %s' % (start_check_plugins[repository], repository))
            ret = start_check_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, cmd, options, self.stdio, strict_check=strict_check)
            if not ret:
                success = False
        
        if success is False:
            # self._call_stdio('verbose', 'Starting check failed. Use --skip-check to skip the starting check. However, this may lead to a starting failure.')
            return False

        component_num = len(components)
        for repository in repositories:
            if repository.name not in components:
                continue
            cluster_config = deploy_config.components[repository.name]
            cluster_servers = cluster_config.servers
            if servers:
                cluster_config.servers = [srv for srv in cluster_servers if srv.ip in server_list or srv.name in server_list]
            if not cluster_config.servers:
                component_num -= 1
                continue
            start_all = cluster_servers == cluster_config.servers
            update_deploy_status = update_deploy_status and start_all

            self._call_stdio('verbose', 'Call %s for %s' % (start_plugins[repository], repository))
            ret = start_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, cmd, options, self.stdio, self.home_path, repository.repository_dir)
            if ret:
                need_bootstrap = ret.get_return('need_bootstrap')
            else:
                self._call_stdio('error', '%s start failed' % repository.name)
                break

            self._call_stdio('verbose', 'Call %s for %s' % (connect_plugins[repository], repository))
            ret = connect_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, cmd, options, self.stdio)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            else:
                break

            if need_bootstrap and start_all:
                self._call_stdio('print', 'Initialize cluster')
                self._call_stdio('verbose', 'Call %s for %s' % (bootstrap_plugins[repository], repository))
                if not bootstrap_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, cmd, options, self.stdio, cursor):
                    self._call_stdio('error', 'Cluster init failed')
                    break
                if repository in create_tenant_plugins:
                    create_tenant_options = Values({"variables": "ob_tcp_invited_nodes='%'"})
                    self._call_stdio('verbose', 'Call %s for %s' % (bootstrap_plugins[repository], repository))
                    create_tenant_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], create_tenant_options, self.stdio, cursor)

            if not start_all:
                component_num -= 1
                continue

            self._call_stdio('verbose', 'Call %s for %s' % (display_plugins[repository], repository))
            if display_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, cmd, options, self.stdio, cursor):
                component_num -= 1
        
        if component_num == 0:
            if update_deploy_status:
                self._call_stdio('verbose', 'Set %s deploy status to running' % name)
                if deploy.update_deploy_status(DeployStatus.STATUS_RUNNING):
                    self._call_stdio('print', '%s running' % name)
                    return True
            else:
                self._call_stdio('print', "succeed")
                return True
        return False

    def create_tenant(self, name, options=Values()):
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
        repositories = self.load_local_repositories(deploy_info)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
            
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        create_tenant_plugins = self.search_py_script_plugin(repositories, 'create_tenant', no_found_act='ignore')
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
            
        for repository in create_tenant_plugins:
            cluster_config = deploy_config.components[repository.name]
            db = None
            cursor = None
            self._call_stdio('verbose', 'Call %s for %s' % (connect_plugins[repository], repository))
            ret = connect_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            if not db:
                return False

            self._call_stdio('verbose', 'Call %s for %s' % (create_tenant_plugins[repository], repository))
            if not create_tenant_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], options, self.stdio, cursor):
                return False
        return True

    def drop_tenant(self, name, options=Values()):
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
        repositories = self.load_local_repositories(deploy_info)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
            
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        drop_tenant_plugins = self.search_py_script_plugin(repositories, 'drop_tenant', no_found_act='ignore')
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
            
        for repository in drop_tenant_plugins:
            cluster_config = deploy_config.components[repository.name]
            db = None
            cursor = None
            self._call_stdio('verbose', 'Call %s for %s' % (connect_plugins[repository], repository))
            ret = connect_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            if not db:
                return False

            self._call_stdio('verbose', 'Call %s for %s' % (drop_tenant_plugins[repository], repository))
            if not drop_tenant_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], options, self.stdio, cursor):
                return False
        return True

    def reload_cluster(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s. Input the configuration path to create a new deploy' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not reload an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
            return False

        if deploy_info.config_status == DeployConfigStatus.UNCHNAGE:
            self._call_stdio('print', 'Deploy config is UNCHNAGE')
            return True

        if deploy_info.config_status != DeployConfigStatus.NEED_RELOAD:
            self._call_stdio('error', 'Deploy `%s` %s%s' % (name, deploy_info.config_status.value, deploy.effect_tip()))
            return False

        return self._reload_cluster(deploy)

    def _reload_cluster(self, deploy):
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Get deploy config')
        deploy_config = deploy.deploy_config
        self._call_stdio('verbose', 'Get new deploy config')
        new_deploy_config = deploy.temp_deploy_config

        if deploy_config.components.keys() != new_deploy_config.components.keys():
            self._call_stdio('error', 'The deployment architecture is changed and cannot be reloaded.')
            return False

        for component_name in deploy_config.components:
            if deploy_config.components[component_name].servers != new_deploy_config.components[component_name].servers:
                self._call_stdio('error', 'The deployment architecture is changed and cannot be reloaded.')
                return False

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)

        reload_plugins = self.search_py_script_plugin(repositories, 'reload')
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')

        self._call_stdio('stop_loading', 'succeed')

        self._call_stdio('start_loading', 'Load cluster param plugin')
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self.search_param_plugin_and_apply(repositories, new_deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            if self.stdio:
                self._call_stdio('error', EC_SOME_SERVER_STOPED)
                for repository in component_status:
                    cluster_status = component_status[repository]
                    for server in cluster_status:
                        if cluster_status[server] == 0:
                            self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
            return False
            
        repositories = self.sort_repositories_by_depends(deploy_config, repositories)
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
                continue

            self._call_stdio('verbose', 'Call %s for %s' % (reload_plugins[repository], repository))
            if not reload_plugins[repository](
                deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, 
                cursor=cursor, new_cluster_config=new_cluster_config, repository_dir=repository.repository_dir):
                continue
            component_num -= 1
        if component_num == 0:
            if deploy.apply_temp_deploy_config():
                self._call_stdio('print', '%s reload' % deploy.name)
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
        repositories = self.load_local_repositories(deploy_info)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
            
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        display_plugins = self.search_py_script_plugin(repositories, 'display')
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            if self.stdio:
                self._call_stdio('error', EC_SOME_SERVER_STOPED)
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
                return False

            self._call_stdio('verbose', 'Call %s for %s' % (display_plugins[repository], repository))
            display_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, cursor)
        return True

    def stop_cluster(self, name, options=Values()):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Check the deploy status')
        status = [DeployStatus.STATUS_DEPLOYED, DeployStatus.STATUS_STOPPED, DeployStatus.STATUS_RUNNING]
        if getattr(options, 'force', False):
            status.append(DeployStatus.STATUS_UPRADEING)
        if deploy_info.status not in status:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not stop an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
            return False
        self._call_stdio('verbose', 'Get deploy config')
        deploy_config = deploy.deploy_config

        update_deploy_status = True
        components = getattr(options, 'components', '')
        if components:
            components = components.split(',')
            for component in components:
                if component not in deploy_info.components:
                    self._call_stdio('error', 'No such component: %s' % component)
                    return False
            if len(components) != len(deploy_info.components):
                update_deploy_status = False
        else:
            components = deploy_info.components.keys()

        servers = getattr(options, 'servers', '')
        server_list = servers.split(',') if servers else []

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)

        # Check whether the components have the parameter plugins and apply the plugins

        self.search_param_plugin_and_apply(repositories, deploy_config)

        stop_plugins = self.search_py_script_plugin(repositories, 'stop')
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        component_num = len(components)
        for repository in repositories:
            if repository.name not in components:
                continue
            cluster_config = deploy_config.components[repository.name]
            cluster_servers = cluster_config.servers
            if servers:
                cluster_config.servers = [srv for srv in cluster_servers if srv.ip in server_list or srv.name in server_list]
            if not cluster_config.servers:
                component_num -= 1
                continue

            start_all = cluster_servers == cluster_config.servers
            update_deploy_status = update_deploy_status and start_all

            self._call_stdio('verbose', 'Call %s for %s' % (stop_plugins[repository], repository))
            if stop_plugins[repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio):
                component_num -= 1
        
        if component_num == 0:
            if len(components) != len(repositories) or servers:
                self._call_stdio('print', "succeed")
                return True
            else:
                self._call_stdio('verbose', 'Set %s deploy status to stopped' % name)
                if deploy.update_deploy_status(DeployStatus.STATUS_STOPPED):
                    self._call_stdio('print', '%s stopped' % name)
                    return True
        return False

    def restart_cluster(self, name, options=Values()):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        if deploy_info.config_status == DeployConfigStatus.NEED_REDEPLOY:
            self._call_stdio('error', 'Deploy needs redeploy')
            return False

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        deploy_config = deploy.deploy_config
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)

        restart_plugins = self.search_py_script_plugin(repositories, 'restart')
        reload_plugins = self.search_py_script_plugin(repositories, 'reload')
        start_plugins = self.search_py_script_plugin(repositories, 'start')
        stop_plugins = self.search_py_script_plugin(repositories, 'stop')
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        display_plugins = self.search_py_script_plugin(repositories, 'display')
        bootstrap_plugins = self.search_py_script_plugin(repositories, 'bootstrap')

        self._call_stdio('stop_loading', 'succeed')

        self._call_stdio('start_loading', 'Load cluster param plugin')
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        if getattr(options, 'without_parameter', False) is False and deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
            apply_change = True
            new_deploy_config = deploy.temp_deploy_config
            change_user = deploy_config.user.username != new_deploy_config.user.username
            self.search_param_plugin_and_apply(repositories, new_deploy_config)
        else:
            new_deploy_config = None
            apply_change = change_user = False

        self._call_stdio('stop_loading', 'succeed')

        update_deploy_status = True 
        components = getattr(options, 'components', '')
        if components:
            components = components.split(',')
            for component in components:
                if component not in deploy_info.components:
                    self._call_stdio('error', 'No such component: %s' % component)
                    return False
            if len(components) != len(deploy_info.components):
                if apply_change:
                    self._call_stdio('error', 'Configurations are changed and must be applied to all components and servers.')
                    return False
                update_deploy_status = False
        else:
            components = deploy_info.components.keys()

        servers = getattr(options, 'servers', '')
        if servers:
            server_list = servers.split(',') 
            if apply_change:
                for repository in repositories:
                    cluster_config = deploy_config.components[repository.name]
                    for server in cluster_config.servers:
                        if server.name not in server_list:
                            self._call_stdio('error', 'Configurations are changed and must be applied to all components and servers.')
                            return False
        else:
            server_list = []

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
        if new_deploy_config and deploy_config.user.username != new_deploy_config.user.username:
            new_ssh_clients = self.get_clients(new_deploy_config, repositories)
            self._call_stdio('start_loading', 'Check sudo')
            for server in new_ssh_clients:
                client = new_ssh_clients[server]
                ret = client.execute_command('sudo whoami')
                if not ret:
                    self._call_stdio('error', ret.stderr)
                    self._call_stdio('stop_loading', 'fail')
                    return False
            self._call_stdio('stop_loading', 'succeed')
        else:
            new_ssh_clients = None

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            if self.stdio:
                self._call_stdio('error', EC_SOME_SERVER_STOPED)
                for repository in component_status:
                    cluster_status = component_status[repository]
                    for server in cluster_status:
                        if cluster_status[server] == 0:
                            self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
            return False

        done_repositories = []
        cluster_configs = {}
        component_num = len(components)
        repositories = self.sort_repositories_by_depends(deploy_config, repositories)
        for repository in repositories:
            if repository.name not in components:
                continue
            cluster_config = deploy_config.components[repository.name]
            new_cluster_config = new_deploy_config.components[repository.name] if new_deploy_config else None
            if apply_change is False:
                cluster_servers = cluster_config.servers
                if servers:
                    cluster_config.servers = [srv for srv in cluster_servers if srv.ip in server_list or srv.name in server_list]
                if not cluster_config.servers:
                    component_num -= 1
                    continue

                start_all = cluster_servers == cluster_config.servers
                update_deploy_status = update_deploy_status and start_all

            self._call_stdio('verbose', 'Call %s for %s' % (restart_plugins[repository], repository))
            if restart_plugins[repository](
                deploy_config.components.keys(), ssh_clients, cluster_config, [], options, self.stdio,
                local_home_path=self.home_path,
                start_plugin=start_plugins[repository], 
                reload_plugin=reload_plugins[repository],
                stop_plugin=stop_plugins[repository], 
                connect_plugin=connect_plugins[repository], 
                display_plugin=display_plugins[repository],
                repository=repository, 
                new_cluster_config=new_cluster_config, 
                new_clients=new_ssh_clients
            ):
                component_num -= 1
                done_repositories.append(repository)
                if new_cluster_config:
                    cluster_configs[repository.name] = cluster_config
                    deploy_config.update_component(new_cluster_config)
            else:
                break
        
        if component_num == 0:
            if len(components) != len(repositories) or servers:
                self._call_stdio('print', "succeed")
                return True
            else:
                if apply_change and not deploy.apply_temp_deploy_config():
                    self._call_stdio('error', 'Failed to apply new deploy configuration')
                    return False
                self._call_stdio('verbose', 'Set %s deploy status to running' % name)
                if deploy.update_deploy_status(DeployStatus.STATUS_RUNNING):
                    self._call_stdio('print', '%s restart' % name)
                    return True
        elif new_ssh_clients:
            self._call_stdio('start_loading', 'Rollback')
            component_num = len(done_repositories)
            for repository in done_repositories:
                new_cluster_config = new_deploy_config.components[repository.name]
                cluster_config = cluster_configs[repository.name]

                self._call_stdio('verbose', 'Call %s for %s' % (restart_plugins[repository], repository))
                if restart_plugins[repository](
                    deploy_config.components.keys(), ssh_clients, cluster_config, [], options, self.stdio,
                    local_home_path=self.home_path,
                    start_plugin=start_plugins[repository], 
                    reload_plugin=reload_plugins[repository],
                    stop_plugin=stop_plugins[repository], 
                    connect_plugin=connect_plugins[repository], 
                    display_plugin=display_plugins[repository],
                    repository=repository, 
                    new_cluster_config=new_cluster_config, 
                    new_clients=new_ssh_clients,
                    rollback=True,
                    bootstrap_plugin=bootstrap_plugins[repository],
                ):
                    deploy_config.update_component(cluster_config)

            self._call_stdio('stop_loading', 'succeed')
        return False

    def redeploy_cluster(self, name, opt=Values()):
        return self.destroy_cluster(name, opt) and self.deploy_cluster(name) and self.start_cluster(name)

    def destroy_cluster(self, name, opt=Values()):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Check deploy status')
        if deploy_info.status in [DeployStatus.STATUS_RUNNING, DeployStatus.STATUS_UPRADEING]:
            if not self.stop_cluster(name, Values({'force': True})):
                return False
        elif deploy_info.status not in [DeployStatus.STATUS_STOPPED, DeployStatus.STATUS_DEPLOYED]:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not destroy an undeployed cluster' % (name, deploy_info.status.value))
            return False
        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)

        plugins = self.search_py_script_plugin(repositories, 'destroy')
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 1:
            if getattr(opt, 'force_kill', False):
                self._call_stdio('verbose', 'Try to stop cluster')
                status = deploy.deploy_info.status
                deploy.update_deploy_status(DeployStatus.STATUS_RUNNING)
                if not self.stop_cluster(name):
                    deploy.update_deploy_status(status)
                    self._call_stdio('error', 'Fail to stop cluster')
                    return False
            else:
                self._call_stdio('error', 'Some of the servers in the cluster are running')
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

    def change_repository(self, name, options=Values()):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status in [DeployStatus.STATUS_DESTROYED, DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_UPRADEING]:
            self._call_stdio('error', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False

        component = getattr(options, 'component')
        usable = getattr(options, 'hash')
        if not component:
            self._call_stdio('error', 'Specify the components you want to change.')
            return False
        if not usable:
            self._call_stdio('error', 'Specify the hash you want to upgrade.')
            return False
        if component not in deploy_info.components:
            self._call_stdio('error', 'Not found %s in Deploy "%s" ' % (component, name))
            return False

        deploy_config = deploy.deploy_config

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        for current_repository in repositories:
            if current_repository.name == component:
                break

        stop_plugins = self.search_py_script_plugin([current_repository], 'stop')
        start_plugins = self.search_py_script_plugin([current_repository], 'start')
        change_repo_plugin = self.plugin_manager.get_best_py_script_plugin('change_repo', 'general', '0.1')
        self._call_stdio('stop_loading', 'succeed')

        self._call_stdio('verbose', 'search target repository')
        dest_repository = self.repository_manager.get_repository(current_repository.name, version=current_repository.version, tag=usable)
        if not dest_repository:
            pkg = self.mirror_manager.get_exact_pkg(name=current_repository.name, version=current_repository.version, md5=usable)
            if not pkg:
                self._call_stdio('error', 'No such package %s-%s-%s' % (component, current_repository.version, usable))
                return False
            repositories = []
            install_plugins = self.get_install_plugin_and_install(repositories, [pkg])
            if not install_plugins:
                return False
            dest_repository = repositories[0]
        else:
            install_plugins = self.search_plugins([dest_repository], PluginType.INSTALL)

        if dest_repository is None:
            self._call_stdio('error', 'Target version not found')
            return False

        if dest_repository == current_repository:
            self._call_stdio('print', 'The current version is already %s.\nNoting to do.' % current_repository)
            return False
            
        # Get the client
        ssh_clients = self.get_clients(deploy_config, [current_repository])
        cluster_config = deploy_config.components[current_repository.name]

        self._call_stdio('start_loading', 'Load cluster param plugin')
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        cluster_config = deploy_config.components[dest_repository.name]
        # cluster files check
        self.servers_repository_install(ssh_clients, cluster_config.servers, dest_repository, install_plugins[dest_repository])
        # lib check
        if not self.servers_repository_lib_check(ssh_clients, cluster_config.servers, dest_repository, install_plugins[dest_repository], 'warn'):
            self._call_stdio('print', 'Try to get lib-repository')
            repositories_lib_map = self.install_lib_for_repositories([dest_repository])
            if repositories_lib_map is False:
                self._call_stdio('error', 'Failed to install lib package for local')
                return False
            if self.servers_apply_lib_repository_and_check(ssh_clients, deploy_config, [dest_repository], repositories_lib_map):
                self._call_stdio('error', 'Failed to install lib package for cluster servers')
                return False


        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, [current_repository], component_status)
        if cluster_status is False or cluster_status == 1:
            self._call_stdio('verbose', 'Call %s for %s' % (stop_plugins[current_repository], current_repository))
            if not stop_plugins[current_repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], options, self.stdio):
                return False

        self._call_stdio('verbose', 'Call %s for %s' % (change_repo_plugin, dest_repository))
        if not change_repo_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], options, self.stdio, self.home_path, dest_repository):
            return False

        if deploy_info.status == DeployStatus.STATUS_RUNNING:
            self._call_stdio('verbose', 'Call %s for %s' % (start_plugins[current_repository], dest_repository))
            setattr(options, 'without_parameter', True)
            if not start_plugins[current_repository](deploy_config.components.keys(), ssh_clients, cluster_config, [], options, self.stdio, self.home_path, dest_repository.repository_dir) and getattr(options, 'force', False) is False:
                self._call_stdio('verbose', 'Call %s for %s' % (change_repo_plugin, current_repository))
                change_repo_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], options, self.stdio, self.home_path, current_repository)
                return False
        
        deploy.update_component_repository(dest_repository)
        return True

    def upgrade_cluster(self, name, options=Values()):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status not in [DeployStatus.STATUS_UPRADEING, DeployStatus.STATUS_RUNNING]:
            self._call_stdio('error', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False
        
        deploy_config = deploy.deploy_config

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)

        # Check whether the components have the parameter plugins and apply the plugins

        self.search_param_plugin_and_apply(repositories, deploy_config)

        self._call_stdio('stop_loading', 'succeed')

        if deploy_info.status == DeployStatus.STATUS_RUNNING:
            component = getattr(options, 'component')
            version = getattr(options, 'version')
            usable = getattr(options, 'usable', '')
            disable = getattr(options, 'disable', '')

            if component:
                if component not in deploy_info.components:
                    self._call_stdio('error', 'Not found %s in Deploy "%s" ' % (component, name))
                    return False
            else:
                for component in deploy_info.components:
                    break
                if not component:
                    self._call_stdio('error', 'Specify the components you want to upgrade.')
                    return False

            for current_repository in repositories:
                if current_repository.name == component:
                    break

            if not version:
                self._call_stdio('error', 'Specify the target version.')
                return False
            if Version(version) < current_repository.version:
                self._call_stdio('error', 'The target version %s is lower than the current version %s.' % (version, current_repository.version))
                return False

            usable = usable.split(',')
            disable = disable.split(',')

            self._call_stdio('verbose', 'search target version')
            images = self.search_images(component, version=version, disable=disable, usable=usable)
            if not images:
                self._call_stdio('error', 'No such package %s-%s' % (component, version))
                return False
            if len(images) > 1:
                self._call_stdio(
                    'print_list',
                    images,
                    ['name', 'version', 'release', 'arch', 'md5'], 
                    lambda x: [x.name, x.version, x.release, x.arch, x.md5],
                    title='%s %s Candidates' % (component, version) 
                )
                self._call_stdio('error', 'Too many match')
                return False

            if isinstance(images[0], Repository):
                pkg = self.mirror_manager.get_exact_pkg(name=images[0].name, md5=images[0].md5)
                if pkg:
                    repositories = []
                    pkgs = [pkg]
                else:
                    repositories = [images[0]]
                    pkgs = []
            else:
                repositories = []
                pkg = self.mirror_manager.get_exact_pkg(name=images[0].name, md5=images[0].md5)
                pkgs = [pkg]
                
            install_plugins = self.get_install_plugin_and_install(repositories, pkgs)
            if not install_plugins:
                return False
            
            dest_repository = repositories[0]
            if dest_repository is None:
                self._call_stdio('error', 'Target version not found')
                return False

            if dest_repository == current_repository:
                self._call_stdio('print', 'The current version is already %s.\nNoting to do.' % current_repository)
                return False
            # Get the client
            ssh_clients = self.get_clients(deploy_config, [current_repository])
            cluster_config = deploy_config.components[current_repository.name]

            route = []
            use_images = []
            upgrade_route_plugins = self.search_py_script_plugin([current_repository], 'upgrade_route', no_found_act='warn')
            if current_repository in upgrade_route_plugins:
                ret = upgrade_route_plugins[current_repository](deploy_config.components.keys(), ssh_clients, cluster_config, {}, options, self.stdio, current_repository, dest_repository)
                route = ret.get_return('route')
                if not route:
                    return False
                for node in route[1: -1]:
                    images = self.search_images(component, version=node.get('version'), release=node.get('release'), disable=disable, usable=usable, release_first=True)
                    if not images:
                        self._call_stdio('error', 'No such package %s-%s' % (component, version))
                        return False
                    if len(images) > 1:
                        self._call_stdio(
                            'print_list',
                            images,
                            ['name', 'version', 'release', 'arch', 'md5'], 
                            lambda x: [x.name, x.version, x.release, x.arch, x.md5],
                            title='%s %s Candidates' % (component, version) 
                        )
                        self._call_stdio('error', 'Too many match')
                        return False
                    use_images.append(images[0])
            else:
                use_images = []

            pkgs = []
            upgrade_repositories = [current_repository]
            for image in use_images:
                if isinstance(image, Repository):
                    upgrade_repositories.append(image)
                else:
                    repository = self.repository_manager.get_repository_by_version(name=image.name, version=image.version, tag=image.md5)
                    if repository:
                        upgrade_repositories.append(repository)
                    else:
                        pkg = self.mirror_manager.get_exact_pkg(name=image.name, version=image.version, md5=image.md5)
                        if not pkg:
                            return False
                        install_plugins = self.get_install_plugin_and_install(upgrade_repositories, [pkg])
                        if not install_plugins:
                            return False
            upgrade_repositories.append(dest_repository)

            upgrade_check_plugins = self.search_py_script_plugin(upgrade_repositories, 'upgrade_check', no_found_act='warn')
            if current_repository in upgrade_check_plugins:
                connect_plugin = self.search_py_script_plugin(upgrade_repositories, 'connect')[current_repository]
                db = None
                cursor = None
                self._call_stdio('verbose', 'Call %s for %s' % (connect_plugin, current_repository))
                ret = connect_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio)
                if ret:
                    db = ret.get_return('connect')
                    cursor = ret.get_return('cursor')
                if not db:
                    return False
                self._call_stdio('verbose', 'Call %s for %s' % (upgrade_check_plugins[current_repository], current_repository))
                if not upgrade_check_plugins[current_repository](
                    deploy_config.components.keys(), ssh_clients, cluster_config, {}, options, self.stdio, 
                    current_repository=current_repository,
                    repositories=upgrade_repositories,
                    route=route,
                    cursor=cursor
                    ):
                    return False
                cursor.close()
                db.close()

            self._call_stdio(
                'print_list',
                upgrade_repositories,
                ['name', 'version', 'release', 'arch', 'md5', 'mark'], 
                lambda x: [x.name, x.version, x.release, x.arch, x.md5, 'start' if x == current_repository else 'dest' if x == dest_repository else ''],
                title='Packages Will Be Used' 
            )
                    
            if not self._call_stdio('confirm', 'If you use a non-official release, we cannot guarantee a successful upgrade or technical support when you fail. Make sure that you want to use the above package to upgrade.'):
                return False

            index = 1
            upgrade_ctx = {
                'route': route, 
                'upgrade_repositories': [
                    {
                    'version': repository.version,
                    'hash': repository.md5
                    } for repository in upgrade_repositories
                ],
                'index': 1
            }
            deploy.start_upgrade(component, **upgrade_ctx)
        else:
            component = deploy.upgrading_component
            upgrade_ctx = deploy.upgrade_ctx
            upgrade_repositories = []
            for data in upgrade_ctx['upgrade_repositories']:
                repository = self.repository_manager.get_repository(component, data['version'], data['hash'])
                upgrade_repositories.append(repository)
            route = upgrade_ctx['route']
            current_repository = upgrade_repositories[0]
            dest_repository = upgrade_repositories[-1]
            # Get the client
            ssh_clients = self.get_clients(deploy_config, [current_repository])
            cluster_config = deploy_config.components[current_repository.name]
        
        install_plugins = self.get_install_plugin_and_install(upgrade_repositories, [])
        if not install_plugins:
            return False

        need_lib_repositories = []
        for repository in upgrade_repositories[1:]:
            cluster_config = deploy_config.components[repository.name]
            # cluster files check
            self.servers_repository_install(ssh_clients, cluster_config.servers, repository, install_plugins[repository])
            # lib check
            if not self.servers_repository_lib_check(ssh_clients, cluster_config.servers, repository, install_plugins[repository], 'warn'):
                need_lib_repositories.append(repository)

        if need_lib_repositories:
            self._call_stdio('print', 'Try to get lib-repository')
            repositories_lib_map = self.install_lib_for_repositories(need_lib_repositories)
            if repositories_lib_map is False:
                self._call_stdio('error', 'Failed to install lib package for local')
                return False
            if self.servers_apply_lib_repository_and_check(ssh_clients, deploy_config, need_lib_repositories, repositories_lib_map):
                self._call_stdio('error', 'Failed to install lib package for cluster servers')
                return False

        n = len(upgrade_repositories)
        while upgrade_ctx['index'] < n:
            repository = upgrade_repositories[upgrade_ctx['index'] - 1]
            repositories = [repository]
            upgrade_plugin = self.search_py_script_plugin(repositories, 'upgrade')[repository]

            ret = upgrade_plugin(
                    deploy_config.components.keys(), ssh_clients, cluster_config, [], options, self.stdio,
                    search_py_script_plugin=self.search_py_script_plugin,
                    local_home_path=self.home_path,
                    current_repository=current_repository,
                    upgrade_repositories=upgrade_repositories,
                    apply_param_plugin=lambda repository: self.search_param_plugin_and_apply([repository], deploy_config),
                    upgrade_ctx=upgrade_ctx
                )
            deploy.update_upgrade_ctx(**upgrade_ctx)
            if not ret:
                return False

        deploy.stop_upgrade(dest_repository)

        return True

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
        info = PackageInfo(name=attrs['name'], version=attrs['version'], release=None, arch=None, md5=None)
        for item in plugin.file_list(info):
            path = os.path.join(repo_path, item.src_path)
            path = os.path.normcase(path)
            if not os.path.exists(path):
                path = os.path.join(repo_path, item.target_path)
                path = os.path.normcase(path)
                if not os.path.exists(path):
                    self._call_stdio('error', 'need %s: %s ' % ('dir' if item.type == InstallPlugin.FileItemType.DIR else 'file', path))
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
            for component_name in ['obproxy', 'obproxy-ce', 'oceanbase', 'oceanbase-ce']:
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
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            if self.stdio:
                self._call_stdio('error', EC_SOME_SERVER_STOPED)
                for repository in component_status:
                    cluster_status = component_status[repository]
                    for server in cluster_status:
                        if cluster_status[server] == 0:
                            self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
            return False

        connect_plugin = self.search_py_script_plugin(repositories, 'connect')[repository]
        ret = connect_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, target_server=opts.test_server, sys_root=False)
        if not ret or not ret.get_return('connect'):
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
            self._call_stdio('verbose', 'Call %s for %s' % (mysqltest_run_test_plugin, repository))
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
                obd = ObdHome(self.home_path, self.dev_mode, stdio=stdio)
                obd.lock_manager.set_try_times(-1)
                if obd.redeploy_cluster(name):
                    self._call_stdio('stop_loading', 'succeed')
                else:
                    self._call_stdio('stop_loading', 'fail')
                    result.append(case_result)
                    break
                obd.lock_manager.set_try_times(6000)
                obd = None
                connect_plugin = self.search_py_script_plugin(repositories, 'connect')[repository]
                ret = connect_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, target_server=opts.test_server, sys_root=False)
                if not ret or not ret.get_return('connect'):
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

    def sysbench(self, name, opts):
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

        allow_components = ['obproxy', 'obproxy-ce', 'oceanbase', 'oceanbase-ce']
        if opts.component is None:
            for component_name in allow_components:
                if component_name in deploy_config.components:
                    if opts.test_server is not None:
                        cluster_config = deploy_config.components[component_name]
                        for server in cluster_config.servers:
                            if server.name == opts.test_server:
                                break
                        else:
                            continue
                    self._call_stdio('verbose', 'Select component %s' % component_name)
                    opts.component = component_name
                    break
        elif opts.component not in allow_components:
            self._call_stdio('error', '%s not support. %s is allowed' % (opts.component, allow_components))
            return False
        if opts.component not in deploy_config.components:
            self._call_stdio('error', 'Can not find the component for sysbench, use `--component` to select component')
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

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            if self.stdio:
                self._call_stdio('error', EC_SOME_SERVER_STOPED)
                for repository in component_status:
                    cluster_status = component_status[repository]
                    for server in cluster_status:
                        if cluster_status[server] == 0:
                            self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
            return False

        for repository in repositories:
            if repository.name == opts.component:
                break
        
        env = {'sys_root': False}
        db = None
        cursor = None
        odp_db = None
        odp_cursor = None
        ob_optimization = True

        connect_plugin = self.search_py_script_plugin(repositories, 'connect')[repository]

        
        if repository.name in ['obproxy', 'obproxy-ce']:
            ob_optimization = False
            allow_components = ['oceanbase', 'oceanbase-ce']
            for component_name in deploy_config.components:
                if component_name in allow_components:
                    config = deploy_config.components[component_name]
                    env['user'] = 'root'
                    env['password'] = config.get_global_conf().get('root_password', '')
                    ob_optimization = True
                    break
            ret = connect_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, target_server=opts.test_server)
            if not ret or not ret.get_return('connect'):
                return False
            odp_db = ret.get_return('connect')
            odp_cursor = ret.get_return('cursor')

        ret = connect_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, target_server=opts.test_server, **env)
        if not ret or not ret.get_return('connect'):
            return False
        db = ret.get_return('connect')
        cursor = ret.get_return('cursor')
    
        run_test_plugin = self.plugin_manager.get_best_py_script_plugin('run_test', 'sysbench', repository.version)

        setattr(opts, 'host', opts.test_server.ip)
        setattr(opts, 'port', db.port)
        setattr(opts, 'ob_optimization', ob_optimization)

        self._call_stdio('verbose', 'Call %s for %s' % (run_test_plugin, repository))
        if run_test_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], opts, self.stdio, db, cursor, odp_db, odp_cursor):
            return True
        return False

    def tpch(self, name, opts):
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

        allow_components = ['oceanbase', 'oceanbase-ce']
        if opts.component is None:
            for component_name in allow_components:
                if component_name in deploy_config.components:
                    opts.component = component_name
                    break
        elif opts.component not in allow_components:
            self._call_stdio('error', '%s not support. %s is allowed' % (opts.component, allow_components))
            return False
        if opts.component not in deploy_config.components:
            self._call_stdio('error', 'Can not find the component for tpch, use `--component` to select component')
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

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.get_local_repositories({opts.component: deploy_config.components[opts.component]})
        repository = repositories[0]

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            if self.stdio:
                self._call_stdio('error', EC_SOME_SERVER_STOPED)
                for repository in component_status:
                    cluster_status = component_status[repository]
                    for server in cluster_status:
                        if cluster_status[server] == 0:
                            self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
            return False

        connect_plugin = self.search_py_script_plugin(repositories, 'connect')[repository]
        ret = connect_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio, target_server=opts.test_server)
        if not ret or not ret.get_return('connect'):
            return False
        db = ret.get_return('connect')
        cursor = ret.get_return('cursor')

        pre_test_plugin = self.plugin_manager.get_best_py_script_plugin('pre_test', 'tpch', repository.version)
        run_test_plugin = self.plugin_manager.get_best_py_script_plugin('run_test', 'tpch', repository.version)

        setattr(opts, 'host', opts.test_server.ip)
        setattr(opts, 'port', db.port)


        self._call_stdio('verbose', 'Call %s for %s' % (pre_test_plugin, repository))
        if pre_test_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], opts, self.stdio):
            self._call_stdio('verbose', 'Call %s for %s' % (run_test_plugin, repository))
            if run_test_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], opts, self.stdio, db, cursor):
                return True
        return False

    def update_obd(self, version, install_prefix='/'):
        self._obd_update_lock()
        component_name = 'ob-deploy'
        plugin = self.plugin_manager.get_best_plugin(PluginType.INSTALL, component_name, '1.0.0')
        if not plugin:
            self._call_stdio('critical', 'OBD upgrade plugin not found')
            return False
        pkg = self.mirror_manager.get_best_pkg(name=component_name)
        if not (pkg and pkg > PackageInfo(component_name, version, pkg.release, pkg.arch, '')):
            self._call_stdio('print', 'No updates detected. OBD is already up to date.')
            return False
        
        self._call_stdio('print', 'Found a higher version package for OBD\n%s' % pkg)
        repository = self.repository_manager.create_instance_repository(pkg.name, pkg.version, pkg.md5)
        repository.load_pkg(pkg, plugin)
        if DirectoryUtil.copy(repository.repository_dir, install_prefix, self.stdio):
            self._call_stdio('print', 'Upgrade successful.\nCurrent version : %s' % pkg.version)
            return True
        return False

    def tpcc(self, name, opts):
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

        allow_components = ['obproxy', 'obproxy-ce', 'oceanbase', 'oceanbase-ce']
        if opts.component is None:
            for component_name in allow_components:
                if component_name in deploy_config.components:
                    opts.component = component_name
                    break
        elif opts.component not in allow_components:
            self._call_stdio('error', '%s not support. %s is allowed' % (opts.component, allow_components))
            return False
        if opts.component not in deploy_config.components:
            self._call_stdio('error', 'Can not find the component for tpcc, use `--component` to select component')
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

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.get_local_repositories({opts.component: deploy_config.components[opts.component]})
        repository = repositories[0]

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(ssh_clients, deploy_config, repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            if self.stdio:
                self._call_stdio('error', EC_SOME_SERVER_STOPED)
                for repository in component_status:
                    cluster_status = component_status[repository]
                    for server in cluster_status:
                        if cluster_status[server] == 0:
                            self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
            return False

        for repository in repositories:
            if repository.name == opts.component:
                break

        env = {'sys_root': False}
        odp_db = None
        odp_cursor = None
        ob_optimization = True
        ob_component = None
        odp_component = None
        # ob_cluster_config = None

        connect_plugin = self.search_py_script_plugin(repositories, 'connect')[repository]

        if repository.name in ['obproxy', 'obproxy-ce']:
            odp_component = repository.name
            ob_optimization = False
            allow_components = ['oceanbase', 'oceanbase-ce']
            for component in deploy_info.components:
                if component in allow_components:
                    ob_component = component
                    config = deploy_config.components[component]
                    env['user'] = 'root'
                    env['password'] = config.get_global_conf().get('root_password', '')
                    ob_optimization = True
                    break
            ret = connect_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio,
                                 target_server=opts.test_server)
            if not ret or not ret.get_return('connect'):
                return False
            odp_db = ret.get_return('connect')
            odp_cursor = ret.get_return('cursor')
            # ob_cluster_config = deploy_config.components[ob_component]
        else:
            ob_component = opts.component
            # ob_cluster_config = cluster_config

        ret = connect_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {}, self.stdio,
                             target_server=opts.test_server, **env)
        if not ret or not ret.get_return('connect'):
            return False
        db = ret.get_return('connect')
        cursor = ret.get_return('cursor')

        pre_test_plugin = self.plugin_manager.get_best_py_script_plugin('pre_test', 'tpcc', repository.version)
        optimize_plugin = self.plugin_manager.get_best_py_script_plugin('optimize', 'tpcc', repository.version)
        build_plugin = self.plugin_manager.get_best_py_script_plugin('build', 'tpcc', repository.version)
        run_test_plugin = self.plugin_manager.get_best_py_script_plugin('run_test', 'tpcc', repository.version)
        recover_plugin = self.plugin_manager.get_best_py_script_plugin('recover', 'tpcc', repository.version)

        setattr(opts, 'host', opts.test_server.ip)
        setattr(opts, 'port', db.port)
        setattr(opts, 'ob_optimization', ob_optimization)

        kwargs = {}

        optimized = False
        optimization = getattr(opts, 'optimization', 0)
        test_only = getattr(opts, 'test_only', False)
        components = []
        if getattr(self.stdio, 'sub_io'):
            stdio = self.stdio.sub_io()
        else:
            stdio = None
        obd = None
        try:
            self._call_stdio('verbose', 'Call %s for %s' % (pre_test_plugin, repository))
            ret = pre_test_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], opts, self.stdio,
                                  cursor, odp_cursor, **kwargs)
            if not ret:
                return False
            else:
                kwargs.update(ret.kwargs)
            if optimization:
                optimized = True
                kwargs['optimization_step'] = 'build'
                self._call_stdio('verbose', 'Call %s for %s' % (optimize_plugin, repository))
                ret = optimize_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], opts, self.stdio, cursor,
                             odp_cursor, **kwargs)
                if not ret:
                    return False
                else:
                    kwargs.update(ret.kwargs)
                if kwargs.get('odp_need_reboot') and odp_component:
                    components.append(odp_component)
                if kwargs.get('obs_need_reboot') and ob_component:
                    components.append(ob_component)
                if components:
                    db.close()
                    cursor.close()
                    if odp_db:
                        odp_db.close()
                    if odp_cursor:
                        odp_cursor.close()
                    self._call_stdio('start_loading', 'Restart cluster')
                    obd = ObdHome(self.home_path, self.dev_mode, stdio=stdio)
                    obd.lock_manager.set_try_times(-1)
                    option = Values({'components': ','.join(components), 'without_parameter': True})
                    if obd.stop_cluster(name=name, options=option) and obd.start_cluster(name=name, options=option) and obd.display_cluster(name=name):
                        self._call_stdio('stop_loading', 'succeed')
                    else:
                        self._call_stdio('stop_loading', 'fail')
                        return False
                    if repository.name in ['obproxy', 'obproxy-ce']:
                        ret = connect_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {},
                                             self.stdio,
                                             target_server=opts.test_server)
                        if not ret or not ret.get_return('connect'):
                            return False
                        odp_db = ret.get_return('connect')
                        odp_cursor = ret.get_return('cursor')
                    ret = connect_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], {},
                                         self.stdio,
                                         target_server=opts.test_server, **env)
                    if not ret or not ret.get_return('connect'):
                        return False
                    db = ret.get_return('connect')
                    cursor = ret.get_return('cursor')
            if not test_only:
                self._call_stdio('verbose', 'Call %s for %s' % (build_plugin, repository))
                ret = build_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], opts, self.stdio, cursor,
                             odp_cursor, **kwargs)
                if not ret:
                    return False
                else:
                    kwargs.update(ret.kwargs)
            if optimization:
                kwargs['optimization_step'] = 'test'
                self._call_stdio('verbose', 'Call %s for %s' % (optimize_plugin, repository))
                ret = optimize_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], opts, self.stdio, cursor,
                             odp_cursor, **kwargs)
                if not ret:
                    return False
                else:
                    kwargs.update(ret.kwargs)
            self._call_stdio('verbose', 'Call %s for %s' % (run_test_plugin, repository))
            ret = run_test_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], opts, self.stdio, cursor,
                         odp_cursor, **kwargs)
            if not ret:
                return False
            else:
                kwargs.update(ret.kwargs)
            return True
        except Exception as e:
            self._call_stdio('error', e)
            return False
        finally:
            if optimization and optimized:
                self._call_stdio('verbose', 'Call %s for %s' % (recover_plugin, repository))
                if not recover_plugin(deploy_config.components.keys(), ssh_clients, cluster_config, [], opts, self.stdio,
                                      cursor, odp_cursor, **kwargs):
                    return False
                if components and obd:
                    self._call_stdio('start_loading', 'Restart cluster')
                    option = Values({'components': ','.join(components), 'without_parameter': True})
                    if obd.stop_cluster(name=name, options=option) and obd.start_cluster(name=name, options=option):
                        self._call_stdio('stop_loading', 'succeed')
                    else:
                        self._call_stdio('stop_loading', 'fail')
            if db:
                db.close()
            if odp_db:
                odp_db.close()



