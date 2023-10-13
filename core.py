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
import time
from optparse import Values
from copy import deepcopy, copy
import requests

import tempfile
from subprocess import call as subprocess_call

from ssh import SshClient, SshConfig
from tool import FileUtil, DirectoryUtil, YamlLoader, timeout, COMMAND_ENV, OrderedDict
from _stdio import MsgLevel
from _rpm import Version
from _mirror import MirrorRepositoryManager, PackageInfo
from _plugin import PluginManager, PluginType, InstallPlugin, PluginContextNamespace
from _deploy import DeployManager, DeployStatus, DeployConfig, DeployConfigStatus, Deploy
from _repository import RepositoryManager, LocalPackage, Repository
import _errno as err
from _lock import LockManager, LockMode
from _optimize import OptimizeManager
from _environ import ENV_REPO_INSTALL_MODE, ENV_BASE_DIR
from const import OB_OFFICIAL_WEBSITE


class ObdHome(object):

    HOME_LOCK_RELATIVE_PATH = 'obd.conf'

    def __init__(self, home_path, dev_mode=False, lock_mode=None, stdio=None):
        self.home_path = home_path
        self.dev_mode = dev_mode
        self._lock = None
        self._home_conf = None
        self._mirror_manager = None
        self._repository_manager = None
        self._deploy_manager = None
        self._plugin_manager = None
        self._lock_manager = None
        self._optimize_manager = None
        self.stdio = None
        self._stdio_func = None
        self.ssh_clients = {}
        self.deploy = None
        self.cmds = []
        self.options = Values()
        self.repositories = None
        self.namespaces = {}
        self.set_stdio(stdio)
        if lock_mode is None:
            lock_mode = LockMode.DEPLOY_SHARED_LOCK if dev_mode else LockMode.DEFAULT
        self.lock_manager.set_lock_mode(lock_mode)
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

    @property
    def optimize_manager(self):
        if not self._optimize_manager:
            self._optimize_manager = OptimizeManager(self.home_path, stdio=self.stdio)
        return self._optimize_manager

    def _global_ex_lock(self):
        self.lock_manager.global_ex_lock()

    def fork(self, deploy=None, repositories=None, cmds=None, options=None, stdio=None):
        new_obd = copy(self)
        if deploy:
            new_obd.set_deploy(deploy)
        if repositories:
            new_obd.set_repositories(repositories)
        if cmds:
            new_obd.set_cmds(cmds)
        if options:
            new_obd.set_options(options)
        if stdio:
            new_obd.set_stdio(stdio)
        return new_obd

    def set_deploy(self, deploy):
        self.deploy = deploy

    def set_repositories(self, repositories):
        self.repositories = repositories

    def set_cmds(self, cmds):
        self.cmds = cmds

    def set_options(self, options):
        self.options = options

    def set_stdio(self, stdio):
        def _print(msg, *arg, **kwarg):
            sep = kwarg['sep'] if 'sep' in kwarg else None
            end = kwarg['end'] if 'end' in kwarg else None
            return print(msg, sep='' if sep is None else sep, end='\n' if end is None else end)
        self.stdio = stdio
        self._stdio_func = {}
        if not self.stdio:
            return
        for func in ['start_loading', 'stop_loading', 'print', 'confirm', 'verbose', 'warn', 'exception', 'error', 'critical', 'print_list', 'read']:
            self._stdio_func[func] = getattr(self.stdio, func, _print)

    def get_namespace(self, spacename):
        if spacename in self.namespaces:
            namespace = self.namespaces[spacename]
        else:
            namespace = PluginContextNamespace(spacename=spacename)
            self.namespaces[spacename] = namespace
        return namespace 

    def call_plugin(self, plugin, repository, spacename=None, **kwargs):
        args = {
            'namespace': self.get_namespace(repository.name if spacename == None else spacename),
            'namespaces': self.namespaces,
            'deploy_name': None,
            'cluster_config': None,
            'repositories': self.repositories,
            'repository': repository,
            'components': None,
            'cmd': self.cmds,
            'options': self.options,
            'stdio': self.stdio
        }
        if self.deploy:
            args['deploy_name'] = self.deploy.name
            args['components'] = self.deploy.deploy_info.components
            args['cluster_config'] = self.deploy.deploy_config.components[repository.name]
            if "clients" not in kwargs:
                args['clients'] = self.get_clients(self.deploy.deploy_config, self.repositories)
        args.update(kwargs)
        
        self._call_stdio('verbose', 'Call %s for %s' % (plugin, repository))
        return plugin(**args)

    def _call_stdio(self, func, msg, *arg, **kwarg):
        if func not in self._stdio_func:
            return None
        return self._stdio_func[func](msg, *arg, **kwarg)

    def add_mirror(self, src):
        if re.match('^https?://', src):
            return self.mirror_manager.add_remote_mirror(src)
        else:
            return self.mirror_manager.add_local_mirror(src, getattr(self.options, 'force', False))

    def deploy_param_check(self, repositories, deploy_config, gen_config_plugins={}):
        # parameter check
        errors = []
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            errors += cluster_config.check_param()[1]
            skip_keys = []
            if repository in gen_config_plugins:
                ret = self.call_plugin(gen_config_plugins[repository], repository, return_generate_keys=True, clients={})
                if ret:
                    skip_keys = ret.get_return('generate_keys', [])
            for server in cluster_config.servers:
                self._call_stdio('verbose', '%s %s param check' % (server, repository))
                need_items = cluster_config.get_unconfigured_require_item(server, skip_keys=skip_keys)
                if need_items:
                    errors.append(str(err.EC_NEED_CONFIG.format(server=server, component=repository.name, miss_keys=','.join(need_items))))
        return errors

    def deploy_param_check_return_check_status(self, repositories, deploy_config, gen_config_plugins={}):
        # parameter check
        param_check_status = {}
        check_pass = True
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            check_status = param_check_status[repository.name] = {}
            skip_keys = []
            if repository in gen_config_plugins:
                ret = self.call_plugin(gen_config_plugins[repository], repository, return_generate_keys=True, clients={})
                if ret:
                    skip_keys = ret.get_return('generate_keys', [])
            check_res = cluster_config.servers_check_param()
            for server in check_res:
                status = err.CheckStatus()
                errors = check_res[server].get('errors', [])
                self._call_stdio('verbose', '%s %s param check' % (server, repository))
                need_items = cluster_config.get_unconfigured_require_item(server, skip_keys=skip_keys)
                if need_items:
                    errors.append(err.EC_NEED_CONFIG.format(server=server, component=repository.name, miss_keys=','.join(need_items)))
                if errors:
                    status.status = err.CheckStatus.FAIL
                    check_pass = False
                    status.error = err.EC_PARAM_CHECK.format(errors=errors)
                    status.suggests.append(err.SUG_PARAM_CHECK.format())
                else:
                    status.status = err.CheckStatus.PASS
                check_status[server] = status
        return param_check_status, check_pass
    
    def get_clients(self, deploy_config, repositories):
        ssh_clients, _ = self.get_clients_with_connect_status(deploy_config, repositories, True)
        return ssh_clients

    def get_clients_with_connect_status(self, deploy_config, repositories, fail_exit=False):
        servers = set()
        user_config = deploy_config.user
        if user_config not in self.ssh_clients:
            self.ssh_clients[user_config] = {}
        ssh_clients = self.ssh_clients[user_config]
        connect_status = {}
    
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            for server in cluster_config.servers:
                if server not in ssh_clients:
                    servers.add(server)
                else:
                    connect_status[server] = err.CheckStatus(err.CheckStatus.PASS)
        if servers:
            connect_status.update(self.ssh_clients_connect(servers, ssh_clients, user_config, fail_exit))
        return ssh_clients, connect_status

    def ssh_clients_connect(self, servers, ssh_clients, user_config, fail_exit=False):
        self._call_stdio('start_loading', 'Open ssh connection')
        connect_io = self.stdio if fail_exit else self.stdio.sub_io()
        connect_status = {}
        success = True
        for server in servers:
            if server not in ssh_clients:
                client = SshClient(
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
                error = client.connect(stdio=connect_io)
                connect_status[server] = status = err.CheckStatus()
                if error is not True:
                    success = False
                    status.status = err.CheckStatus.FAIL
                    status.error = error
                    status.suggests.append(err.SUG_SSH_FAILED.format())
                else:
                    status.status = err.CheckStatus.PASS
                    ssh_clients[server] = client
        self._call_stdio('stop_loading', 'succeed' if success else 'fail')
        return connect_status

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
            repository = self.repository_manager.get_repository(name=component, version=config.version, tag=config.tag, release=config.release, package_hash=config.package_hash)
            if repository and not repository.hash:
                repository = None
            if not config.tag:
                self._call_stdio('verbose', 'Search %s package from mirror' % component)
                pkg = self.mirror_manager.get_best_pkg(
                    name=component, version=config.version, md5=config.package_hash, release=config.release, fuzzy_match=fuzzy_match, only_info=only_info)
            else:
                pkg = None
            if repository or pkg:
                if pkg:
                    self._call_stdio('verbose', 'Found Package %s-%s-%s-%s' % (pkg.name, pkg.version, pkg.release, pkg.md5))
                if repository:
                    if repository >= pkg or (
                        (
                            update_if_need is None and 
                            not self._call_stdio('confirm', 'Found a higher version\n%s\nDo you want to use it?' % pkg)
                        ) or update_if_need is False
                    ):
                        if pkg and repository.release == pkg.release:
                            pkgs.append(pkg)
                            self._call_stdio('verbose', '%s as same as %s, Use package %s' % (pkg, repository, pkg))
                        else:
                            repositories.append(repository)
                            self._call_stdio('verbose', 'Use repository %s' % repository)
                            self._call_stdio('print', '%s-%s already installed.' % (repository.name, repository.version))
                        continue
                if config.version and pkg.version != config.version:
                    self._call_stdio('warn', 'No such package %s-%s-%s. Use similar package %s-%s-%s.' % (component, config.version, config.release, pkg.name, pkg.version, pkg.release))
                else:
                    self._call_stdio('print', 'Package %s-%s-%s is available.' % (pkg.name, pkg.version, pkg.release))
                repository = self.repository_manager.get_repository(pkg.name, pkg.md5)
                if repository:
                    repositories.append(repository)
                else:
                    pkgs.append(pkg)
            else:
                pkg_name = [component]
                if config.version:
                    pkg_name.append("version: %s" % config.version)
                if config.release:
                    pkg_name.append("release: %s" % config.release)
                if config.package_hash:
                    pkg_name.append("package hash: %s" % config.package_hash)
                if config.tag:
                    pkg_name.append("tag: %s" % config.tag)
                errors.append('No such package name: %s.' % (', '.join(pkg_name)))
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
        if not self.stdio:
            raise IOError("IO Not Found")

        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        param_plugins = {}
        repositories, pkgs = [], []
        is_deployed = deploy and deploy.deploy_info.status not in [DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_DESTROYED]
        is_started = deploy and deploy.deploy_info.status in [DeployStatus.STATUS_RUNNING, DeployStatus.STATUS_STOPPED]
        user_input = self._call_stdio('read', '')
        if not user_input and not self.stdio.isatty():
            time.sleep(0.1)
            user_input = self._call_stdio('read', '')
            if not user_input:
                self._call_stdio('error', 'Input is empty')
                return False
        initial_config = ''
        if deploy:
            try:
                deploy.deploy_config.allow_include_error()
                if deploy.deploy_info.config_status == DeployConfigStatus.UNCHNAGE:
                    path = deploy.deploy_config.yaml_path
                else:
                    path = Deploy.get_temp_deploy_yaml_path(deploy.config_dir)
                if user_input:
                    initial_config = user_input
                else:
                    self._call_stdio('verbose', 'Load %s' % path)
                    with open(path, 'r') as f:
                        initial_config = f.read()
            except:
                self._call_stdio('exception', '')
            msg = 'Save deploy "%s" configuration' % name
        else:
            if user_input:
                initial_config = user_input
            else:
                if not self.stdio:
                    return False
                if not initial_config and not self._call_stdio('confirm', 'No such deploy: %s. Create?' % name):
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
            if not user_input:
                tf.seek(0)
                self._call_stdio('verbose', '%s %s' % (EDITOR, tf.name))
                subprocess_call([EDITOR, tf.name])
                self._call_stdio('verbose', 'Load %s' % tf.name)
            try:
                deploy_config = DeployConfig(
                    tf.name, yaml_loader=YamlLoader(self.stdio),
                    config_parser_manager=self.deploy_manager.config_parser_manager,
                    inner_config=deploy.deploy_config.inner_config if deploy else None
                    )
                deploy_config.allow_include_error()
                if not deploy_config.get_base_dir():
                    deploy_config.set_base_dir('/', save=False)
            except Exception as e:
                if not user_input and confirm(e):
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
                        if user_input:
                            return False
                        continue
                    config_status = DeployConfigStatus.NEED_REDEPLOY

                if config_status != DeployConfigStatus.NEED_REDEPLOY:
                    comp_attr_changed = False
                    for component_name in deploy_config.components:
                        old_cluster_config = deploy.deploy_config.components[component_name]
                        new_cluster_config = deploy_config.components[component_name]
                        if new_cluster_config.version != old_cluster_config.config_version \
                            or new_cluster_config.package_hash != old_cluster_config.config_package_hash \
                            or new_cluster_config.release != old_cluster_config.config_release \
                            or new_cluster_config.tag != old_cluster_config.tag:
                            comp_attr_changed = True
                            config_status = DeployConfigStatus.NEED_REDEPLOY
                            break
                    if comp_attr_changed:
                        if not self._call_stdio('confirm', 'Modifications to the version, release or hash of the component take effect after you redeploy the cluster. Are you sure that you want to start a redeployment? '):
                            if user_input:
                                return False
                            continue
                        config_status = DeployConfigStatus.NEED_REDEPLOY

                if config_status != DeployConfigStatus.NEED_REDEPLOY:
                    rsync_conf_changed = False
                    for component_name in deploy_config.components:
                        old_cluster_config = deploy.deploy_config.components[component_name]
                        new_cluster_config = deploy_config.components[component_name]
                        if new_cluster_config.get_rsync_list() != old_cluster_config.get_rsync_list():
                            rsync_conf_changed = True
                            break
                    if rsync_conf_changed:
                        if not self._call_stdio('confirm', 'Modifications to the rsync config of a deployed cluster take effect after you redeploy the cluster. Are you sure that you want to start a redeployment? '):
                            if user_input:
                                return False
                            continue
                        config_status = DeployConfigStatus.NEED_REDEPLOY

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
                        if user_input:
                            return False
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
                    if is_started or (config_status == DeployConfigStatus.NEED_REDEPLOY and is_deployed):
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
            self._call_stdio('verbose', 'create instance repository for %s-%s' % (pkg.name, pkg.version))
            repository = self.repository_manager.create_instance_repository(pkg.name, pkg.version, pkg.md5)
            if repository.need_load(pkg, install_plugins[repository]):
                self._call_stdio('start_loading', 'install %s-%s for local' % (pkg.name, pkg.version))
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
            else:
                self._call_stdio('verbose', '%s-%s is already install' % (pkg.name, pkg.version))
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

    # check cluster server status, running/stopped
    def cluster_server_status_check(self, status='running'):
        if status not in ['running', 'stopped']:
            self.stdio.error(err.EC_INVALID_PARAMETER.format('status', status))
            return False
        component_status = {}
        cluster_status = self.cluster_status_check(self.repositories, component_status)
        value = 0 if status == 'running' else 1
        if cluster_status is False or cluster_status == value:
            self.stdio.error(err.EC_SOME_SERVER_STOPED.format())
            for repository in component_status:
                cluster_status = component_status[repository]
                for server in cluster_status:
                    if cluster_status[server] == value:
                        self. stdio.error('server status error: %s %s is %s' % (server, repository.name, status))
            return False
        return True

    # If the cluster states are consistent, the status value is returned. Else False is returned.
    def cluster_status_check(self, repositories, ret_status={}):
        self._call_stdio('start_loading', 'Cluster status check')
        status_plugins = self.search_py_script_plugin(repositories, 'status')
        component_status = {}
        for repository in repositories:
            plugin_ret = self.call_plugin(status_plugins[repository], repository)
            cluster_status = plugin_ret.get_return('cluster_status')
            ret_status[repository] = cluster_status
            for server in cluster_status:
                if repository not in component_status:
                    component_status[repository] = cluster_status[server]
                    continue
                if component_status[repository] != cluster_status[server]:
                    self._call_stdio('verbose', '%s cluster status is inconsistent' % repository)
                    component_status[repository] = False
                    break
            else:
                continue

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

    def genconfig(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if deploy:
            deploy_info = deploy.deploy_info
            if deploy_info.status not in [DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_DESTROYED]:
                self._call_stdio('error', 'Deploy "%s" is %s. You could not deploy an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
                return False
            # self._call_stdio('error', 'Deploy name `%s` have been occupied.' % name)
            # return False

        config_path = getattr(self.options, 'config', '')
        if not config_path:
            self._call_stdio('error', "Configuration file is need.\nPlease use -c to set configuration file")
            return False

        self._call_stdio('verbose', 'Create deploy by configuration path')
        deploy = self.deploy_manager.create_deploy_config(name, config_path)
        self.set_deploy(deploy)
        if not deploy:
            return False

        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config
        if not deploy_config:
            self._call_stdio('error', 'Deploy configuration is empty.\nIt may be caused by a failure to resolve the configuration.\nPlease check your configuration file.\nSee https://github.com/oceanbase/obdeploy/blob/master/docs/zh-CN/4.configuration-file-description.md')
            return False

        # Check the best suitable mirror for the components and installation plugins. Install locally
        repositories, install_plugins = self.search_components_from_mirrors_and_install(deploy_config)
        if not install_plugins or not repositories:
            return False
        self.set_repositories(repositories)

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
        gen_config_plugins = self.search_py_script_plugin(repositories, 'generate_config')

        if not  getattr(self.options, 'skip_param_check', False):
            # Parameter check
            errors = self.deploy_param_check(repositories, deploy_config, gen_config_plugins=gen_config_plugins)
            if errors:
                self._call_stdio('stop_loading', 'fail')
                self._call_stdio('error', '\n'.join(errors))
                return False

        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        generate_consistent_config = getattr(self.options, 'generate_consistent_config', False)
        component_num = len(repositories)
        for repository in repositories:
            ret = self.call_plugin(gen_config_plugins[repository], repository, generate_consistent_config=generate_consistent_config)
            if ret:
                component_num -= 1
                
        if component_num == 0 and deploy_config.dump():
            return True
        
        self.deploy_manager.remove_deploy_config(name)
        return False

    def check_for_ocp(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False

        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('error', 'Deploy "%s" not RUNNING' % (name))
            return False

        version = getattr(self.options, 'version', '')
        if not version:
            self._call_stdio('error', 'Use the --version option to specify the required OCP version.')
            return False

        deploy_config = deploy.deploy_config
        components = getattr(self.options, 'components', '')
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
        self.set_repositories(repositories)

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

            ret = self.call_plugin(connect_plugins[repository], repository)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            else:
                break

            if self.call_plugin(ocp_check[repository], repository, cursor=cursor, ocp_version=version, new_cluster_config=new_cluster_config, new_clients=new_ssh_clients):
                component_num -= 1
                self._call_stdio('print', '%s Check passed.' % repository.name)

        return component_num == 0

    def sort_repository_by_depend(self, repositories, deploy_config):
        sorted_repositories = []
        sorted_componets = {}
        while repositories:
            temp_repositories = []
            for repository in repositories:
                cluster_config = deploy_config.components.get(repository.name)
                for componet_name in cluster_config.depends:
                    if componet_name not in sorted_componets:
                        temp_repositories.append(repository)
                        break
                else:
                    sorted_componets[repository.name] = 1
                    sorted_repositories.append(repository)
            if len(temp_repositories) == len(repositories):
                sorted_repositories += temp_repositories
                break
            repositories = temp_repositories
        return sorted_repositories

    def change_deploy_config_style(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
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
            self._call_stdio('error', 'Deploy configuration is empty.\nIt may be caused by a failure to resolve the configuration.\nPlease check your configuration file.\nSee https://github.com/oceanbase/obdeploy/blob/master/docs/zh-CN/4.configuration-file-description.md')
            return False

        style = getattr(self.options, 'style', '')
        if not style:
            self._call_stdio('error', 'Use the --style option to specify the preferred style.')
            return False

        components = getattr(self.options, 'components', '')
        if components:
            components = components.split(',')
            for component in components:
                if component not in deploy_config.components:
                    self._call_stdio('error', 'No such component: %s' % component)
                    return False
        else:
            components = deploy_config.components.keys()

        self._call_stdio('start_loading', 'Load param plugin')

        # Get the repository
        if deploy_info.status not in [DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_DESTROYED]:
            repositories = self.load_local_repositories(deploy_info)
        else:
            repositories = []
            for component_name in components:
                repositories.append(self.repository_manager.get_repository_allow_shadow(component_name, '100000.0'))
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

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

    def demo(self):
        name = 'demo'
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if deploy:
            self._call_stdio('verbose', 'Get deploy info')
            deploy_info = deploy.deploy_info
            self._call_stdio('verbose', 'judge deploy status')
            if deploy_info.status == DeployStatus.STATUS_DEPLOYED:
                if not self.destroy_cluster(name):
                    return False
            elif deploy_info.status not in [DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_DESTROYED]:
                self._call_stdio('error', 'Deploy "%s" is %s. You could not deploy an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
                return False

        components = set()
        for component_name in getattr(self.options, 'components', '').split(','):
            if component_name:
                components.add(component_name)
                self.get_namespace(component_name).set_variable('generate_config_mini', True)
                self.get_namespace(component_name).set_variable('generate_password', False)
                self.get_namespace(component_name).set_variable('auto_depend', True)

        if not components:
            self._call_stdio('error', 'Use `-c/--components` to set in the components to be deployed')
            return
        global_key = 'global'
        home_path_key = 'home_path'
        global_config = {home_path_key: os.getenv('HOME')}
        opt_config = {}
        for key in self.options.__dict__:
            tmp = key.split('.', 1)
            if len(tmp) == 1:
                if key == home_path_key:
                    global_config[key] = self.options.__dict__[key]
            else:
                component_name = tmp[0]
                if component_name not in components:
                    component_name = component_name.replace('_', '-')
                if component_name not in opt_config:
                    opt_config[component_name] = {global_key: {}}
                if tmp[1] in ['version', 'tag', 'package_hash', 'release']:
                    _config = opt_config[component_name]
                else:
                    _config = opt_config[component_name][global_key]
                _config[tmp[1]] = self.options.__dict__[key]

        configs = OrderedDict()
        for component_name in components:
            configs[component_name] = {
                'servers': ['127.0.0.1'],
                global_key: deepcopy(global_config)
            }
            configs[component_name][global_key][home_path_key] = os.path.join(configs[component_name][global_key][home_path_key], component_name)
            if component_name in opt_config:
                configs[component_name][global_key].update(opt_config[component_name][global_key])
                del opt_config[component_name][global_key]
                configs[component_name].update(opt_config[component_name])

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode='w') as tf:
            yaml_loader = YamlLoader(self.stdio)
            yaml_loader.dump(configs, tf)
            setattr(self.options, 'config', tf.name)
            setattr(self.options, 'skip_param_check', True)
            if not self.genconfig(name):
                return False
            setattr(self.options, 'config', '')
            return self.deploy_cluster(name) and self.start_cluster(name)

    def deploy_cluster(self, name):
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

        config_path = getattr(self.options, 'config', '')
        unuse_lib_repo = getattr(self.options, 'unuselibrepo', False)
        auto_create_tenant = getattr(self.options, 'auto_create_tenant', False)
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
        self.set_deploy(deploy)

        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config
        if not deploy_config:
            self._call_stdio('error', 'Deploy configuration is empty.\nIt may be caused by a failure to resolve the configuration.\nPlease check your configuration file.\nSee https://github.com/oceanbase/obdeploy/blob/master/docs/zh-CN/4.configuration-file-description.md')
            return False

        if not deploy_config.components:
            self._call_stdio('error', 'Components not detected.\nPlease check the syntax of your configuration file.\nSee https://github.com/oceanbase/obdeploy/blob/master/docs/zh-CN/4.configuration-file-description.md')
            return False

        for component_name in deploy_config.components:
            if not deploy_config.components[component_name].servers:
                self._call_stdio('error', '%s\'s servers list is empty.' % component_name)
                return False

        install_mode = COMMAND_ENV.get(ENV_REPO_INSTALL_MODE)
        if not install_mode:
            install_mode = 'cp' if self.dev_mode else 'ln'

        if install_mode == 'cp':
            deploy_config.enable_cp_install_mode(save=False)
        elif install_mode == 'ln':
            deploy_config.enable_ln_install_mode(save=False)
        else:
            self._call_stdio('error', 'Invalid repository install mode: {}'.format(install_mode))
            return False

        if self.dev_mode:
            base_dir = COMMAND_ENV.get(ENV_BASE_DIR, '')
            deploy_config.set_base_dir(base_dir, save=False)

        # Check the best suitable mirror for the components and installation plugins. Install locally
        repositories, install_plugins = self.search_components_from_mirrors_and_install(deploy_config)
        if not repositories or not install_plugins:
            return False
        self.set_repositories(repositories)

        if unuse_lib_repo and not deploy_config.unuse_lib_repository:
            deploy_config.set_unuse_lib_repository(True)
        if auto_create_tenant and not deploy_config.auto_create_tenant:
            deploy_config.set_auto_create_tenant(True)
        return self._deploy_cluster(deploy, repositories)

    def _deploy_cluster(self, deploy, repositories):
        deploy_config = deploy.deploy_config
        install_plugins = self.search_plugins(repositories, PluginType.INSTALL)
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
                errors.append('%s install failed' % repository.name)
        if errors:
            self._call_stdio('stop_loading', 'fail')
            self._call_stdio('error', '\n'.join(errors))
            return False
        self._call_stdio('stop_loading', 'succeed')

        self._call_stdio('start_loading', 'Parameter check')
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)

        # Generate password when password is None
        gen_config_plugins = self.search_py_script_plugin(repositories, 'generate_config')
        for repository in repositories:
            if repository in gen_config_plugins:
                self.call_plugin(gen_config_plugins[repository], repository, only_generate_password=True)

        # Parameter check
        self._call_stdio('verbose', 'Cluster param configuration check')
        errors = self.deploy_param_check(repositories, deploy_config)
        if errors:
            self._call_stdio('stop_loading', 'fail')
            self._call_stdio('error', '\n'.join(errors))
            return False
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        if not getattr(self.options, 'skip_cluster_status_check', False):
            component_status = {}
            cluster_status = self.cluster_status_check(repositories, component_status)
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
            init_plugin = init_plugins[repository]
            self._call_stdio('verbose', 'Exec %s init plugin' % repository)
            self._call_stdio('verbose', 'Apply %s for %s-%s' % (init_plugin, repository.name, repository.version))
            if self.call_plugin(init_plugin, repository):
                component_num -= 1
        if component_num != 0:
            return False

        # Install repository to servers
        if not self.install_repositories_to_servers(deploy_config, repositories, install_plugins, ssh_clients, self.options):
            return False

        # Sync runtime dependencies
        if not self.sync_runtime_dependencies(deploy_config, repositories, ssh_clients, self.options):
            return False

        for repository in repositories:
            deploy.use_model(repository.name, repository, False)

        if deploy.update_deploy_status(DeployStatus.STATUS_DEPLOYED) and deploy_config.dump():
            self._call_stdio('print', '%s deployed' % deploy.name)
            return True
        return False

    def install_repository_to_servers(self, components, cluster_config, repository, ssh_clients, unuse_lib_repository=False):
        install_repo_plugin = self.plugin_manager.get_best_py_script_plugin('install_repo', 'general', '0.1')
        install_plugins = self.search_plugins([repository], PluginType.INSTALL)
        if not install_plugins:
            return False
        install_plugin = install_plugins[repository]
        check_file_map = install_plugin.file_map(repository)
        ret = self.call_plugin(install_repo_plugin, repository, obd_home=self.home_path, install_repository=repository,
                               install_plugin=install_plugin, check_repository=repository,
                               check_file_map=check_file_map,
                               msg_lv='error' if unuse_lib_repository else 'warn')
        if not ret:
            return False
        elif ret.get_return('checked'):
            return True
        elif unuse_lib_repository:
            return False
        self._call_stdio('print', 'Try to get lib-repository')
        repositories_lib_map = self.install_lib_for_repositories([repository])
        if repositories_lib_map is False:
            self._call_stdio('error', 'Failed to install lib package for local')
            return False
        lib_repository = repositories_lib_map[repository]['repositories']
        install_plugin = repositories_lib_map[repository]['install_plugin']
        ret = self.call_plugin(install_repo_plugin, repository, obd_home=self.home_path, install_repository=lib_repository,
                               install_plugin=install_plugin, check_repository=repository,
                               check_file_map=check_file_map, msg_lv='error')
        if not ret or not ret.get_return('checked'):
            self._call_stdio('error', 'Failed to install lib package for cluster servers')
            return False

    def install_repositories_to_servers(self, deploy_config, repositories, install_plugins, ssh_clients, options):
        install_repo_plugin = self.plugin_manager.get_best_py_script_plugin('install_repo', 'general', '0.1')
        check_file_maps = {}
        need_lib_repositories = []
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            install_plugin = install_plugins[repository]
            check_file_map = check_file_maps[repository] = install_plugin.file_map(repository)
            ret = self.call_plugin(install_repo_plugin, repository, obd_home=self.home_path, install_repository=repository,
                                   install_plugin=install_plugin, check_repository=repository, check_file_map=check_file_map,
                                   msg_lv='error' if deploy_config.unuse_lib_repository else 'warn')
            if not ret:
                return False
            if not ret.get_return('checked'):
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
            for need_lib_repository in need_lib_repositories:
                cluster_config = deploy_config.components[need_lib_repository.name]
                check_file_map = check_file_maps[need_lib_repository]
                lib_repository = repositories_lib_map[need_lib_repository]['repositories']
                install_plugin = repositories_lib_map[need_lib_repository]['install_plugin']
                ret = self.call_plugin(install_repo_plugin, need_lib_repository, obd_home=self.home_path, install_repository=lib_repository,
                                       install_plugin=install_plugin, check_repository=need_lib_repository,
                                       check_file_map=check_file_map, msg_lv='error')
                if not ret or not ret.get_return('checked'):
                    self._call_stdio('error', 'Failed to install lib package for cluster servers')
                    return False
        return True

    def sync_runtime_dependencies(self, deploy_config, repositories, ssh_clients, option):
        rsync_plugin = self.plugin_manager.get_best_py_script_plugin('rsync', 'general', '0.1')
        ret = True
        for repository in repositories:
            ret = self.call_plugin(rsync_plugin, repository) and ret
        return ret

    def start_cluster(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
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
        if deploy_info.config_status != DeployConfigStatus.UNCHNAGE and not getattr(self.options, 'without_parameter', False):
            self._call_stdio('error', 'Deploy %s.%s\nIf you still need to start the cluster, use the `obd cluster start %s --wop` option to start the cluster without loading parameters. ' % (deploy_info.config_status.value, deploy.effect_tip(), name))
            return False

        self._call_stdio('start_loading', 'Get local repositories')

        # Get the repository
        repositories = self.load_local_repositories(deploy_info, False)
        self.set_repositories(repositories)
        self._call_stdio('stop_loading', 'succeed')
        return self._start_cluster(deploy, repositories)

    def _start_cluster(self, deploy, repositories):
        self._call_stdio('verbose', 'Get deploy config')
        deploy_config = deploy.deploy_config
        deploy_info = deploy.deploy_info
        name = deploy.name

        update_deploy_status = True
        components = getattr(self.options, 'components', '')
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

        servers = getattr(self.options, 'servers', '')
        server_list = servers.split(',') if servers else []

        self._call_stdio('start_loading', 'Search plugins')
        start_check_plugins = self.search_py_script_plugin(repositories, 'start_check', no_found_act='warn')
        create_tenant_plugins = self.search_py_script_plugin(repositories, 'create_tenant', no_found_act='ignore')
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
            cluster_status = self.cluster_status_check(repositories, component_status)
            if cluster_status == 1:
                self._call_stdio('print', 'Deploy "%s" is running' % name)
                return True

        repositories = self.sort_repository_by_depend(repositories, deploy_config)

        strict_check = getattr(self.options, 'strict_check', False)
        success = True
        repository_dir_map = {}
        repositories_start_all = {}
        start_repositories = []
        for repository in repositories:
            repository_dir_map[repository.name] = repository.repository_dir
            if repository.name not in components:
                continue
            if repository not in start_check_plugins:
                continue
            cluster_config = deploy_config.components[repository.name]
            cluster_servers = cluster_config.servers
            if servers:
                cluster_config.servers = [srv for srv in cluster_servers if srv.ip in server_list or srv.name in server_list]
            repositories_start_all[repository] = start_all = cluster_servers == cluster_config.servers
            update_deploy_status = update_deploy_status and start_all
            if not cluster_config.servers:
                continue
            ret = self.call_plugin(start_check_plugins[repository], repository, strict_check=strict_check)
            if not ret:
                self._call_stdio('verbose', '%s starting check failed.' % repository.name)
                success = False
            start_repositories.append(repository)
        
        if success is False:
            # self._call_stdio('verbose', 'Starting check failed. Use --skip-check to skip the starting check. However, this may lead to a starting failure.')
            return False

        component_num = len(start_repositories)
        display_repositories = []
        connect_ret = {}
        for repository in start_repositories:
            start_all = repositories_start_all[repository]
            ret = self.call_plugin(start_plugins[repository], repository, local_home_path=self.home_path, repository_dir_map=repository_dir_map)
            if ret:
                need_bootstrap = ret.get_return('need_bootstrap')
            else:
                self._call_stdio('error', '%s start failed' % repository.name)
                break

            ret = self.call_plugin(connect_plugins[repository], repository)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
                connect_ret[repository] = ret.kwargs
            else:
                break

            if need_bootstrap and start_all:
                self._call_stdio('start_loading', 'Initialize %s' % repository.name)
                if not self.call_plugin(bootstrap_plugins[repository], repository, cursor=cursor):
                    self._call_stdio('stop_loading', 'fail')
                    self._call_stdio('error', 'Cluster init failed')
                    break
                self._call_stdio('stop_loading', 'succeed')
                if repository in create_tenant_plugins:
                    if self.get_namespace(repository.name).get_variable("create_tenant_options"):
                        self.call_plugin(create_tenant_plugins[repository], repository, cursor=cursor)

                    if deploy_config.auto_create_tenant:
                        create_tenant_options = Values({"variables": "ob_tcp_invited_nodes='%'", "create_if_not_exists": True})
                        self.call_plugin(create_tenant_plugins[repository], repository, cursor=cursor, create_tenant_options=create_tenant_options)

            if not start_all:
                component_num -= 1
                continue
            display_repositories.append(repository)
        
        for repository in display_repositories:
            if self.call_plugin(display_plugins[repository], repository, **connect_ret[repository]):
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

    def create_tenant(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
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
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
            
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        create_tenant_plugins = self.search_py_script_plugin(repositories, 'create_tenant', no_found_act='ignore')
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
            
        for repository in create_tenant_plugins:
            db = None
            cursor = None
            ret = self.call_plugin(connect_plugins[repository], repository)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            if not db:
                return False

            if not self.call_plugin(create_tenant_plugins[repository], repository, cursor=cursor):
                return False
        return True

    def get_component_repositories(self, deploy_info, components):
        repositories = self.load_local_repositories(deploy_info)
        component_repositories = []
        for repository in repositories:
            if repository.name in components:
                component_repositories.append(repository)
        return component_repositories

    def create_standby_tenant(self, standby_deploy_name, primary_deploy_name, primary_tenant):
        standby_deploy = self.deploy_manager.get_deploy_config(standby_deploy_name)
        if not standby_deploy:
            self._call_stdio('error', 'No such deploy: %s.' % standby_deploy_name)
            return None
        self.set_deploy(standby_deploy)
        primary_deploy = self.deploy_manager.get_deploy_config(primary_deploy_name)
        if not primary_deploy:
            self._call_stdio('error', 'No such deploy: %s.' % primary_deploy_name)
            return None
        if standby_deploy.deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('error', 'Deploy "%s" is %s' % (standby_deploy_name, standby_deploy.deploy_info.status.value))
            return False
        if primary_deploy.deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('error', 'Deploy "%s" is %s' % (primary_deploy_name, primary_deploy.deploy_info.status.value))
            return False
        primary_repositories = self.load_local_repositories(primary_deploy.deploy_info)
        standby_repositories = self.get_component_repositories(standby_deploy.deploy_info, ['oceanbase-ce', 'oceanbase'])
        standby_version_check_plugins = self.search_py_script_plugin(standby_repositories, 'standby_version_check')
        self.set_repositories(standby_repositories)
        for repository in standby_version_check_plugins:
            if not self.call_plugin(standby_version_check_plugins[repository], repository, primary_repositories=primary_repositories):
                return
        # Check the status for standby cluster
        if not self.cluster_server_status_check():
            return
        create_standby_tenant_pre_plugins = self.search_py_script_plugin(standby_repositories, 'create_standby_tenant_pre')
        connect_plugins = self.search_py_script_plugin(standby_repositories, 'connect')
        get_relation_tenants_plugins = self.search_py_script_plugin(standby_repositories, 'get_relation_tenants')
        create_tenant_plugins = self.search_py_script_plugin(standby_repositories, 'create_tenant')
        get_deployment_connections_plugins = self.search_py_script_plugin(standby_repositories, 'get_deployment_connections')
        for repository in get_relation_tenants_plugins:
            if not self.call_plugin(get_relation_tenants_plugins[repository], repository, deployment_name=primary_deploy_name, get_deploy=self.deploy_manager.get_deploy_config, tenant_name=primary_tenant):
                return False
        for repository in get_deployment_connections_plugins:
            if not self.call_plugin(get_deployment_connections_plugins[repository], repository, connect_plugin=connect_plugins[repository], relation_deploy_names=[primary_deploy_name, standby_deploy_name]):
                return False

        for repository in create_standby_tenant_pre_plugins:
            if not self.call_plugin(create_standby_tenant_pre_plugins[repository], repository,
                    primary_deploy_name=primary_deploy_name,
                    primary_tenant=primary_tenant):
                return False

        for repository in create_tenant_plugins:
            if not self.call_plugin(create_tenant_plugins[repository], repository, cursor=None):
                return False
        return True

    def switchover_tenant(self, standby_deploy_name, tenant_name):
        # check oceanbase connect status
        deploy = self.deploy_manager.get_deploy_config(standby_deploy_name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % standby_deploy_name)
            return False
        self.set_deploy(deploy)
        if deploy.deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('error', 'Deploy "%s" is %s' % (standby_deploy_name, deploy.deploy_info.status.value))
            return False
        standby_repositories = self.get_component_repositories(deploy.deploy_info, ['oceanbase-ce', 'oceanbase'])
        self.set_repositories(standby_repositories)
        get_relation_tenants_plugins = self.search_py_script_plugin(standby_repositories, 'get_relation_tenants')
        get_deployment_connections_plugins = self.search_py_script_plugin(standby_repositories, 'get_deployment_connections')
        switchover_tenant_pre_plugins = self.search_py_script_plugin(standby_repositories, 'switchover_tenant_pre')
        switchover_tenant_plugins = self.search_py_script_plugin(standby_repositories, 'switchover_tenant')
        get_standbys_plugins = self.search_py_script_plugin(standby_repositories, 'get_standbys')
        connect_plugins = self.search_py_script_plugin(standby_repositories, 'connect')
        # Check the status for standby cluster
        if not self.cluster_server_status_check():
            return False
        setattr(self.options, 'tenant_name', tenant_name)
        for repository in get_relation_tenants_plugins:
            if not self.call_plugin(get_relation_tenants_plugins[repository], repository, get_deploy=self.deploy_manager.get_deploy_config):
                return False

        for repository in get_deployment_connections_plugins:
            if not self.call_plugin(get_deployment_connections_plugins[repository], repository, connect_plugin=connect_plugins[repository]):
                return False

        for repository in switchover_tenant_pre_plugins:
            if not self.call_plugin(switchover_tenant_pre_plugins[repository], repository):
                return False

        for repository in switchover_tenant_plugins:
            if not self.call_plugin(switchover_tenant_plugins[repository], repository, get_standbys_plugins=get_standbys_plugins):
                return False
        return True

    def failover_decouple_tenant(self, standby_deploy_name, tenant_name, option_type='failover'):
        deploy = self.deploy_manager.get_deploy_config(standby_deploy_name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % standby_deploy_name)
            return False
        self.set_deploy(deploy)
        if deploy.deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('error', 'Deploy "%s" is %s' % (standby_deploy_name, deploy.deploy_info.status.value))
            return False
        standby_repositories = self.get_component_repositories(deploy.deploy_info, ['oceanbase-ce', 'oceanbase'])
        self.set_repositories(standby_repositories)
        self.search_py_script_plugin(standby_repositories, 'standby_version_check')
        get_deployment_connections_plugins = self.search_py_script_plugin(standby_repositories, 'get_deployment_connections')
        failover_decouple_tenant_pre_plugins = self.search_py_script_plugin(standby_repositories, 'failover_decouple_tenant_pre')
        connect_plugins = self.search_py_script_plugin(standby_repositories, 'connect')
        get_relation_tenants_plugins = self.search_py_script_plugin(standby_repositories, 'get_relation_tenants')
        failover_decouple_tenant_plugins = self.search_py_script_plugin(standby_repositories, 'failover_decouple_tenant')
        # Check the status for standby cluster
        if not self.cluster_server_status_check():
            return
        setattr(self.options, 'tenant_name', tenant_name)
        for repository in get_relation_tenants_plugins:
            if not self.call_plugin(get_relation_tenants_plugins[repository], repository, get_deploy=self.deploy_manager.get_deploy_config):
                return False

        for repository in get_deployment_connections_plugins:
            if not self.call_plugin(get_deployment_connections_plugins[repository], repository, connect_plugin=connect_plugins[repository]):
                return False

        for repository in failover_decouple_tenant_pre_plugins:
            if not self.call_plugin(failover_decouple_tenant_pre_plugins[repository], repository, option_type=option_type):
                return False

        for repository in failover_decouple_tenant_plugins:
            if not self.call_plugin(failover_decouple_tenant_plugins[repository], repository, option_type=option_type):
                return False

        delete_standby_info_plugins = self.search_py_script_plugin(standby_repositories, 'delete_standby_info', no_found_act='ignore')
        for repository in delete_standby_info_plugins:
            if not self.call_plugin(delete_standby_info_plugins[repository], repository, delete_password=False):
                self._call_stdio('warn', 'Delete relation of standby tenant failed')
        return True

    def drop_tenant(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
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
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
            
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        drop_tenant_plugins = self.search_py_script_plugin(repositories, 'drop_tenant', no_found_act='ignore')
        get_standbys_plugins = self.search_py_script_plugin(repositories, 'get_standbys', no_found_act='ignore')
        get_relation_tenants_plugins = self.search_py_script_plugin(repositories, 'get_relation_tenants', no_found_act='ignore')
        get_deployment_connections_plugins = self.search_py_script_plugin(repositories, 'get_deployment_connections', no_found_act='ignore')
        check_exit_standby_plugins = self.search_py_script_plugin(repositories, 'check_exit_standby', no_found_act='ignore')
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
        for repository in drop_tenant_plugins:
            db = None
            cursor = None
            ret = self.call_plugin(connect_plugins[repository], repository)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            if not db:
                return False

            if repository in get_relation_tenants_plugins:
                if not self.call_plugin(get_relation_tenants_plugins[repository], repository, get_deploy=self.deploy_manager.get_deploy_config):
                    self._call_stdio('error', err.EC_UNEXPECTED_EXCEPTION)
                    return False
            if not getattr(self.options, 'ignore_standby', False):
                # check if the current tenant has a standby tenant in other cluster
                if repository in get_relation_tenants_plugins and repository in get_deployment_connections_plugins\
                        and repository in get_standbys_plugins and repository in check_exit_standby_plugins:

                    if not self.call_plugin(get_deployment_connections_plugins[repository], repository, connect_plugin=connect_plugins[repository]):
                        self._call_stdio('error', err.EC_CHECK_STANDBY)
                        return False

                    if not self.call_plugin(get_standbys_plugins[repository], repository, primary_deploy_name=name):
                        self._call_stdio('error', err.EC_CHECK_STANDBY)
                        return False

                    if not self.call_plugin(check_exit_standby_plugins[repository], repository):
                        self._call_stdio('error', err.EC_CHECK_STANDBY)
                        return False

            if not self.call_plugin(drop_tenant_plugins[repository], repository, cursor=cursor):
                return False
        delete_standby_info_plugins = self.search_py_script_plugin(repositories, 'delete_standby_info', no_found_act='ignore')
        for repository in delete_standby_info_plugins:
            ret = self.call_plugin(delete_standby_info_plugins[repository], repository)
            if not ret:
                self._call_stdio('warn', 'Delete relation of standby tenant failed')
        return True

    def list_tenant(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
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
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        list_tenant_plugins = self.search_py_script_plugin(repositories, 'list_tenant', no_found_act='ignore')
        print_standby_graph_plugins = self.search_py_script_plugin(repositories, 'print_standby_graph', no_found_act='ignore')
        get_deployment_connections_plugins = self.search_py_script_plugin(repositories, 'get_deployment_connections', no_found_act='ignore')
        get_relation_tenants_plugins = self.search_py_script_plugin(repositories, 'get_relation_tenants', no_found_act='ignore')
        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
        
        for repository in get_relation_tenants_plugins:
            if repository in get_deployment_connections_plugins:
                if not self.call_plugin(get_relation_tenants_plugins[repository], repository, get_deploy=self.deploy_manager.get_deploy_config):
                    return False
                if not self.call_plugin(get_deployment_connections_plugins[repository], repository, connect_plugin=connect_plugins[repository]):
                    return False

        self._call_stdio('stop_loading', 'succeed')
        
        for repository in list_tenant_plugins:
            cluster_config = deploy_config.components[repository.name]
            db = None
            cursor = None
            ret = self.call_plugin(connect_plugins[repository], repository)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            if not db:
                return False
            if not self.call_plugin(list_tenant_plugins[repository], repository, cursor=cursor, name=name):
                return False
            
        for repository in print_standby_graph_plugins:
            if not self.call_plugin(print_standby_graph_plugins[repository], repository):
                self._call_stdio('error', 'print standby tenant graph error.')
                return False
        return True

    def reload_cluster(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s. Input the configuration path to create a new deploy' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status not in [DeployStatus.STATUS_RUNNING, DeployStatus.STATUS_STOPPED]:
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
        self.set_repositories(repositories)

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
        cluster_status = self.cluster_status_check(repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            sub_io = None
            if getattr(self.stdio, 'sub_io'):
                sub_io = self.stdio.sub_io(msg_lv=MsgLevel.ERROR)
            obd = self.fork(options=Values({'without_parameter': True}), stdio=sub_io)
            if not obd._start_cluster(deploy, repositories):
                if self.stdio:
                    self._call_stdio('error', err.EC_SOME_SERVER_STOPED.format())
                return False
            
        repositories = self.sort_repositories_by_depends(deploy_config, repositories)
        component_num = len(repositories)
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            new_cluster_config = new_deploy_config.components[repository.name]

            ret = self.call_plugin(connect_plugins[repository], repository)
            if not ret:
                ret = self.call_plugin(connect_plugins[repository], repository, components=new_deploy_config.components.keys(), cluster_config=new_cluster_config)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            else:
                continue

            if not self.call_plugin(reload_plugins[repository], repository, cursor=cursor, new_cluster_config=new_cluster_config):
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
        self.set_deploy(deploy)
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
        repositories = self.sort_repository_by_depend(repositories, deploy_config)
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
            
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        display_plugins = self.search_py_script_plugin(repositories, 'display')
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        self.cluster_status_check(repositories, component_status)
            
        for repository in repositories:
            cluster_status = component_status[repository]
            servers = []
            for server in cluster_status:
                if cluster_status[server] == 0:
                    self._call_stdio('warn', '%s %s is stopped' % (server, repository.name))
                else:
                    servers.append(server)
            if not servers:
                continue

            db = None
            cursor = None
            ret = self.call_plugin(connect_plugins[repository], repository)
            if ret:
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
            if not db:
                continue

            self.call_plugin(display_plugins[repository], repository, cursor=cursor)
        return True

    def stop_cluster(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Check the deploy status')
        status = [DeployStatus.STATUS_DEPLOYED, DeployStatus.STATUS_STOPPED, DeployStatus.STATUS_RUNNING]
        if getattr(self.options, 'force', False):
            status.append(DeployStatus.STATUS_UPRADEING)
        if deploy_info.status not in status:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not stop an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
            return False

        self._call_stdio('start_loading', 'Get local repositories')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)
        self._call_stdio('stop_loading', 'succeed')
        return self._stop_cluster(deploy, repositories)

    def _stop_cluster(self, deploy, repositories):
        self._call_stdio('verbose', 'Get deploy config')
        deploy_config = deploy.deploy_config
        deploy_info = deploy.deploy_info
        name = deploy.name

        update_deploy_status = True
        components = getattr(self.options, 'components', '')
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

        servers = getattr(self.options, 'servers', '')
        server_list = servers.split(',') if servers else []

        self._call_stdio('start_loading', 'Search plugins')
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

            if self.call_plugin(stop_plugins[repository], repository):
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

    def restart_cluster(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        status = [DeployStatus.STATUS_DEPLOYED, DeployStatus.STATUS_STOPPED, DeployStatus.STATUS_RUNNING]
        if deploy_info.status not in status:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not restart an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
            return False
        
        if deploy_info.config_status == DeployConfigStatus.NEED_REDEPLOY:
            self._call_stdio('error', 'Deploy needs redeploy')
            return False

        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status not in [DeployStatus.STATUS_RUNNING, DeployStatus.STATUS_STOPPED]:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not restart an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
            return False

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        deploy_config = deploy.deploy_config
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)

        restart_plugins = self.search_py_script_plugin(repositories, 'restart')
        reload_plugins = self.search_py_script_plugin(repositories, 'reload')
        start_check_plugins = self.search_py_script_plugin(repositories, 'start_check')
        start_plugins = self.search_py_script_plugin(repositories, 'start')
        stop_plugins = self.search_py_script_plugin(repositories, 'stop')
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        display_plugins = self.search_py_script_plugin(repositories, 'display')
        bootstrap_plugins = self.search_py_script_plugin(repositories, 'bootstrap')

        self._call_stdio('stop_loading', 'succeed')

        self._call_stdio('start_loading', 'Load cluster param plugin')
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        if getattr(self.options, 'without_parameter', False) is False and deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
            apply_change = True
            new_deploy_config = deploy.temp_deploy_config
            change_user = deploy_config.user.username != new_deploy_config.user.username
            self.search_param_plugin_and_apply(repositories, new_deploy_config)
        else:
            new_deploy_config = None
            apply_change = change_user = False

        self._call_stdio('stop_loading', 'succeed')

        update_deploy_status = True
        components = getattr(self.options, 'components', '')
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

        servers = getattr(self.options, 'servers', '')
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
        cluster_status = self.cluster_status_check(repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            sub_io = None
            if getattr(self.stdio, 'sub_io'):
                sub_io = self.stdio.sub_io(msg_lv=MsgLevel.ERROR)
            obd = self.fork(options=Values({'without_parameter': True}), stdio=sub_io)
            if not obd._start_cluster(deploy, repositories):
                if self.stdio:
                    self._call_stdio('error', err.EC_SOME_SERVER_STOPED.format())
                return False

        done_repositories = []
        cluster_configs = {}
        component_num = len(components)
        repositories = self.sort_repositories_by_depends(deploy_config, repositories)
        self.set_repositories(repositories)
        repository_dir_map = {}
        for repository in repositories:
            repository_dir_map[repository.name] = repository.repository_dir
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

            if self.call_plugin(
                    restart_plugins[repository],
                    repository,
                    local_home_path=self.home_path,
                    start_check_plugin=start_check_plugins[repository],
                    start_plugin=start_plugins[repository],
                    reload_plugin=reload_plugins[repository],
                    stop_plugin=stop_plugins[repository],
                    connect_plugin=connect_plugins[repository],
                    bootstrap_plugin=bootstrap_plugins[repository],
                    display_plugin=display_plugins[repository],
                    new_cluster_config=new_cluster_config,
                    new_clients=new_ssh_clients,
                    repository_dir_map=repository_dir_map,
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

                if self.call_plugin(
                        restart_plugins[repository],
                        repository,
                        local_home_path=self.home_path,
                        start_plugin=start_plugins[repository],
                        reload_plugin=reload_plugins[repository],
                        stop_plugin=stop_plugins[repository],
                        connect_plugin=connect_plugins[repository],
                        display_plugin=display_plugins[repository],
                        new_cluster_config=new_cluster_config,
                        new_clients=new_ssh_clients,
                        rollback=True,
                        bootstrap_plugin=bootstrap_plugins[repository],
                        repository_dir_map=repository_dir_map,
                ):
                    deploy_config.update_component(cluster_config)

            self._call_stdio('stop_loading', 'succeed')
        return False

    def redeploy_cluster(self, name, search_repo=True, need_confirm=False):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False

        if need_confirm and not self._call_stdio('confirm', 'Are you sure to  destroy the "%s" cluster and rebuild it?' % name):
            return False
        deploy_info = deploy.deploy_info

        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config
        self._call_stdio('start_loading', 'Get local repositories')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)
        self._call_stdio('stop_loading', 'succeed')

        get_relation_tenants_plugins = self.search_py_script_plugin(repositories, 'get_relation_tenants', no_found_act='ignore')
        for repository in get_relation_tenants_plugins:
            if not self.call_plugin(get_relation_tenants_plugins[repository], repository, get_deploy=self.deploy_manager.get_deploy_config):
                self._call_stdio('error', err.EC_UNEXPECTED_EXCEPTION)
                return False
        if not getattr(self.options, 'ignore_standby', False):
            # check if the current cluster's tenant has a standby tenant in other cluster
            self._call_stdio('start_loading', 'Check for standby tenant')
            connect_plugins = self.search_py_script_plugin(repositories, 'connect')
            get_standbys_plugins = self.search_py_script_plugin(repositories, 'get_standbys', no_found_act='ignore')
            get_deployment_connections_plugins = self.search_py_script_plugin(repositories, 'get_deployment_connections', no_found_act='ignore')
            check_exit_standby_plugins = self.search_py_script_plugin(repositories, 'check_exit_standby', no_found_act='ignore')
            for repository in get_relation_tenants_plugins:
                if repository in get_deployment_connections_plugins and repository in get_standbys_plugins and repository in check_exit_standby_plugins:
                    if not self.call_plugin(get_deployment_connections_plugins[repository], repository, connect_plugin=connect_plugins[repository]):
                        self._call_stdio('error', err.EC_CHECK_STANDBY)
                        return False
                    if not self.call_plugin(get_standbys_plugins[repository], repository, primary_deploy_name=name, skip_no_primary_cursor=True):
                        self._call_stdio('error', err.EC_CHECK_STANDBY)
                        return False
                    if not self.call_plugin(check_exit_standby_plugins[repository], repository):
                        return False
            self._call_stdio('stop_loading', 'succeed')

        self._call_stdio('verbose', 'Check deploy status')
        if deploy_info.status in [DeployStatus.STATUS_RUNNING, DeployStatus.STATUS_UPRADEING]:
            obd = self.fork(options=Values({'force': True}))
            if not obd._stop_cluster(deploy, repositories):
                return False
        elif deploy_info.status not in [DeployStatus.STATUS_STOPPED, DeployStatus.STATUS_DEPLOYED]:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not destroy an undeployed cluster' % (
                name, deploy_info.status.value))
            return False

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        if not self._destroy_cluster(deploy, repositories):
            return False
        if search_repo:
            if deploy_info.config_status != DeployConfigStatus.UNCHNAGE and not deploy.apply_temp_deploy_config():
                self._call_stdio('error', 'Failed to apply new deploy configuration')
                return False
            self._call_stdio('verbose', 'Get deploy configuration')
            deploy_config = deploy.deploy_config
            repositories, install_plugins = self.search_components_from_mirrors_and_install(deploy_config)
            if not repositories or not install_plugins:
                return False
            self.set_repositories(repositories)
        return self._deploy_cluster(deploy, repositories) and self._start_cluster(deploy, repositories)

    def destroy_cluster(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False

        deploy_info = deploy.deploy_info

        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config
        # allow included file not exist
        deploy_config.allow_include_error()

        self._call_stdio('start_loading', 'Get local repositories')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)
        self._call_stdio('stop_loading', 'succeed')

        get_relation_tenants_plugins = self.search_py_script_plugin(repositories, 'get_relation_tenants', no_found_act='ignore')
        for repository in get_relation_tenants_plugins:
            if not self.call_plugin(get_relation_tenants_plugins[repository], repository, get_deploy=self.deploy_manager.get_deploy_config):
                self._call_stdio('error', err.EC_UNEXPECTED_EXCEPTION)
                return False
        if not getattr(self.options, 'ignore_standby', False):
            self._call_stdio('verbose', 'Check for standby tenant')
            # check if the current cluster's tenant has a standby tenant in other cluster
            self._call_stdio('start_loading', 'Check for standby tenant')
            connect_plugins = self.search_py_script_plugin(repositories, 'connect')
            get_standbys_plugins = self.search_py_script_plugin(repositories, 'get_standbys', no_found_act='ignore')
            get_deployment_connections_plugins = self.search_py_script_plugin(repositories, 'get_deployment_connections', no_found_act='ignore')
            check_exit_standby_plugins = self.search_py_script_plugin(repositories, 'check_exit_standby', no_found_act='ignore')
            for repository in get_relation_tenants_plugins:
                if repository in get_deployment_connections_plugins and repository in get_standbys_plugins and repository in check_exit_standby_plugins:
                    if not self.call_plugin(get_deployment_connections_plugins[repository], repository, connect_plugin=connect_plugins[repository]):
                        self._call_stdio('error', err.EC_CHECK_STANDBY)
                        return False
                    if not self.call_plugin(get_standbys_plugins[repository], repository, primary_deploy_name=name, skip_no_primary_cursor=True):
                        self._call_stdio('error', err.EC_CHECK_STANDBY)
                        return False
                    if not self.call_plugin(check_exit_standby_plugins[repository], repository):
                        return False
            self._call_stdio('stop_loading', 'succeed')

        self._call_stdio('verbose', 'Check deploy status')
        if deploy_info.status in [DeployStatus.STATUS_RUNNING, DeployStatus.STATUS_UPRADEING]:
            obd = self.fork(options=Values({'force': True}))
            if not obd._stop_cluster(deploy, repositories):
                return False
        elif deploy_info.status not in [DeployStatus.STATUS_STOPPED, DeployStatus.STATUS_DEPLOYED]:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not destroy an undeployed cluster' % (name, deploy_info.status.value))
            return False

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        return self._destroy_cluster(deploy, repositories)

    def _destroy_cluster(self, deploy, repositories):
        deploy_config = deploy.deploy_config
        self._call_stdio('start_loading', 'Search plugins')
        # Get the repository
        destroy_plugins = self.search_py_script_plugin(repositories, 'destroy')
        self._call_stdio('stop_loading', 'succeed')
        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(repositories, component_status)
        if cluster_status is False or cluster_status == 1:
            if getattr(self.options, 'force_kill', False):
                self._call_stdio('verbose', 'Try to stop cluster')
                status = deploy.deploy_info.status
                deploy.update_deploy_status(DeployStatus.STATUS_RUNNING)
                if not self._stop_cluster(deploy, repositories):
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
            self.call_plugin(destroy_plugins[repository], repository)

        delete_standby_info_plugins = self.search_py_script_plugin(repositories, 'delete_standby_info', no_found_act='ignore')
        for repository in delete_standby_info_plugins:
            ret = self.call_plugin(delete_standby_info_plugins[repository], repository, get_deploy=self.deploy_manager.get_deploy_config)
            if not ret:
                self._call_stdio('warn', 'Delete relation of standby tenant failed')

        self._call_stdio('verbose', 'Set %s deploy status to destroyed' % deploy.name)
        if deploy.update_deploy_status(DeployStatus.STATUS_DESTROYED):
            self._call_stdio('print', '%s destroyed' % deploy.name)
            return True
        return False

    def reinstall(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status in [DeployStatus.STATUS_DESTROYED, DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_UPRADEING]:
            self._call_stdio('error', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False

        component = getattr(self.options, 'component')
        usable = getattr(self.options, 'hash')
        if not component:
            self._call_stdio('error', 'Specify the components you want to reinstall.')
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
        self.set_repositories(repositories)

        stop_plugins = self.search_py_script_plugin([current_repository], 'stop')
        start_plugins = self.search_py_script_plugin([current_repository], 'start')

        self._call_stdio('stop_loading', 'succeed')
        # Get the client
        ssh_clients = self.get_clients(deploy_config, [current_repository])

        current_cluster_config = deploy_config.components[current_repository.name]
        need_sync = bool(current_cluster_config.get_rsync_list())
        need_change_repo = bool(usable)
        sync_repositories = [current_repository]
        repository = current_repository
        cluster_config = current_cluster_config

        # search repo and install
        if usable:
            self._call_stdio('verbose', 'search target repository')
            dest_repository = self.repository_manager.get_repository(current_repository.name, version=current_repository.version, tag=usable)
            if not dest_repository:
                pkg = self.mirror_manager.get_exact_pkg(name=current_repository.name, version=current_repository.version, md5=usable)
                if not pkg:
                    self._call_stdio('error', 'No such package %s-%s-%s' % (component, current_repository.version, usable))
                    return False
                repositories_temp = []
                install_plugins = self.get_install_plugin_and_install(repositories_temp, [pkg])
                if not install_plugins:
                    return False
                dest_repository = repositories_temp[0]
            else:
                install_plugins = self.search_plugins([dest_repository], PluginType.INSTALL)

            if dest_repository is None:
                self._call_stdio('error', 'Target version not found')
                return False

            if dest_repository == current_repository:
                self._call_stdio('print', 'The current version is already %s.\nNoting to do.' % current_repository)
                need_change_repo = False
            else:
                self._call_stdio('start_loading', 'Load cluster param plugin')
                # Check whether the components have the parameter plugins and apply the plugins
                self.search_param_plugin_and_apply(repositories, deploy_config)
                self._call_stdio('stop_loading', 'succeed')
                cluster_config = deploy_config.components[dest_repository.name]
        need_restart = need_sync or need_change_repo
        # stop cluster if needed
        if need_restart:
            # Check the status for the deployed cluster
            component_status = {}
            cluster_status = self.cluster_status_check([current_repository], component_status)
            if cluster_status is False or cluster_status == 1:
                if not self.call_plugin(stop_plugins[current_repository], current_repository):
                    return False

        # install repo to remote servers
        if need_change_repo:
            if not self.install_repositories_to_servers(deploy_config, [dest_repository, ], install_plugins, ssh_clients, self.options):
                return False
            sync_repositories = [dest_repository]
            repository = dest_repository

        # sync runtime dependencies
        if not self.sync_runtime_dependencies(deploy_config, sync_repositories, ssh_clients, self.options):
            return False

        # start cluster if needed
        if need_restart and deploy_info.status == DeployStatus.STATUS_RUNNING:
            setattr(self.options, 'without_parameter', True)
            obd = self.fork(options=self.options)
            if not obd.call_plugin(start_plugins[current_repository], current_repository, home_path=self.home_path) and getattr(self.options, 'force', False) is False:
                self.install_repositories_to_servers(deploy_config, [current_repository, ], install_plugins, ssh_clients, self.options)
                return False

        # update deploy info
        if need_change_repo:
            deploy.use_model(dest_repository.name, dest_repository)
        return True

    def upgrade_cluster(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
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
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins

        self.search_param_plugin_and_apply(repositories, deploy_config)

        self._call_stdio('stop_loading', 'succeed')

        get_standbys_plugins = self.search_py_script_plugin(repositories, 'get_standbys', no_found_act='ignore')
        get_relation_tenants_plugins = self.search_py_script_plugin(repositories, 'get_relation_tenants', no_found_act='ignore')
        get_deployment_connections_plugins = self.search_py_script_plugin(repositories, 'get_deployment_connections', no_found_act='ignore')
        connect_plugins = self.search_py_script_plugin(repositories, 'connect', no_found_act='ignore')
        if not getattr(self.options, 'ignore_standby', False):
            for repository in get_relation_tenants_plugins:
                if repository in get_deployment_connections_plugins and repository in get_standbys_plugins:
                    if not self.call_plugin(get_relation_tenants_plugins[repository], repository, get_deploy=self.deploy_manager.get_deploy_config):
                        self._call_stdio('error', err.EC_CHECK_STANDBY)
                        return False
                    if not self.call_plugin(get_deployment_connections_plugins[repository], repository, connect_plugin=connect_plugins[repository]):
                        self._call_stdio('error', err.EC_CHECK_STANDBY)
                        return False
                    if not self.call_plugin(get_standbys_plugins[repository], repository, primary_deploy_name=name):
                        self._call_stdio('error', err.EC_CHECK_STANDBY)
                        return False

        if deploy_info.status == DeployStatus.STATUS_RUNNING:
            component = getattr(self.options, 'component')
            version = getattr(self.options, 'version')
            usable = getattr(self.options, 'usable', '')
            disable = getattr(self.options, 'disable', '')

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

            # Check the status for the deployed cluster
            component_status = {}
            cluster_status = self.cluster_status_check(repositories, component_status)
            if cluster_status is False or cluster_status == 0:
                if self.stdio:
                    self._call_stdio('error', err.EC_SOME_SERVER_STOPED)
                    for repository in component_status:
                        cluster_status = component_status[repository]
                        for server in cluster_status:
                            if cluster_status[server] == 0:
                                self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
                return False

            route = []
            use_images = []
            upgrade_route_plugins = self.search_py_script_plugin([dest_repository], 'upgrade_route', no_found_act='warn')
            if dest_repository in upgrade_route_plugins:
                ret = self.call_plugin(upgrade_route_plugins[dest_repository], current_repository , current_repository=current_repository, dest_repository=dest_repository)
                route = ret.get_return('route')
                if not route:
                    return False
                for node in route[1: -1]:
                    _version = node.get('version')
                    _release = node.get('release')
                    images = self.search_images(component, version=_version, release=_release, disable=disable, usable=usable, release_first=True)
                    if not images:
                        pkg_name = component
                        if _version:
                            pkg_name = pkg_name + '-' + str(_version)
                        if _release:
                            pkg_name = pkg_name + '-' + str(_release)
                        self._call_stdio('error', 'No such package %s' % pkg_name)
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
                    repository = self.repository_manager.get_repository(name=image.name, version=image.version, package_hash=image.md5)
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
                ret = self.call_plugin(connect_plugin, current_repository)
                if ret:
                    db = ret.get_return('connect')
                    cursor = ret.get_return('cursor')
                if not db:
                    return False
                if not self.call_plugin(
                    upgrade_check_plugins[current_repository], current_repository,
                    current_repository=current_repository,
                    upgrade_repositories=upgrade_repositories,
                    route=route,
                    cursor=cursor
                ):
                    return False
                cursor.close()

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

        script_query_timeout = getattr(self.options, 'script_query_timeout', '')
        n = len(upgrade_repositories)
        while upgrade_ctx['index'] < n:
            repository = upgrade_repositories[upgrade_ctx['index']]
            repositories = [repository]
            upgrade_plugin = self.search_py_script_plugin(repositories, 'upgrade')[repository]
            self.set_repositories(repositories)
            ret = self.call_plugin(
                upgrade_plugin, repository,
                search_py_script_plugin=self.search_py_script_plugin,
                local_home_path=self.home_path,
                current_repository=current_repository,
                upgrade_repositories=upgrade_repositories,
                apply_param_plugin=lambda repository: self.search_param_plugin_and_apply([repository], deploy_config),
                upgrade_ctx=upgrade_ctx,
                install_repository_to_servers=self.install_repository_to_servers,
                unuse_lib_repository=deploy_config.unuse_lib_repository,
                script_query_timeout=script_query_timeout
            )
            deploy.update_upgrade_ctx(**upgrade_ctx)
            if not ret:
                return False

        deploy.stop_upgrade(dest_repository)

        return True

    def create_repository(self):
        force = getattr(self.options, 'force', False)
        necessary = ['name', 'version', 'path']
        attrs = self.options.__dict__
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
            if not os.path.exists(path) or os.path.isdir(path) != (item.type == InstallPlugin.FileItemType.DIR):
                path = os.path.join(repo_path, item.target_path)
                path = os.path.normcase(path)
                if not os.path.exists(path):
                    self._call_stdio('error', 'need %s: %s ' % ('dir' if item.type == InstallPlugin.FileItemType.DIR else 'file', path))
                    success = False
                    continue
                if os.path.isdir(path) != (item.type == InstallPlugin.FileItemType.DIR):
                    self._call_stdio('error', 'need %s, but %s is %s' % (item.type, path, 'file' if item.type == InstallPlugin.FileItemType.DIR else 'dir'))
                    success = False
                    continue
            files[item.src_path] = path
        if success is False:
            return False

        self._call_stdio('start_loading', 'Package')
        try:
            pkg = LocalPackage(repo_path, attrs['name'], attrs['version'], files, getattr(self.options, 'release', None), getattr(self.options, 'arch', None))
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

    def _test_optimize_init(self, test_name, repository):
        opts = self.options
        deploy_config = self.deploy.deploy_config
        optimize_config_path = getattr(opts, 'optimize_config', None)
        if optimize_config_path:
            self._call_stdio('verbose', 'load optimize config {}'.format(optimize_config_path))
            self.optimize_manager.load_config(optimize_config_path, stdio=self.stdio)
        else:
            for component, cluster_config in deploy_config.components.items():
                self.optimize_manager.register_component(component, cluster_config.version)
            self._call_stdio('verbose', 'load default optimize config for {}'.format(test_name))
            self.optimize_manager.load_default_config(test_name=test_name, stdio=self.stdio)
        self._call_stdio('verbose', 'Get optimize config')
        optimize_config = self.optimize_manager.optimize_config
        check_options_plugin = self.plugin_manager.get_best_py_script_plugin('check_options', 'optimize', '0.1')
        return self.call_plugin(check_options_plugin, repository, optimize_config=optimize_config)

    @staticmethod
    def _get_first_db_and_cursor_from_connect(namespace):
        if not namespace:
            return None, None
        connect_ret = namespace.get_return('connect')
        dbs = connect_ret.get_return('connect')
        cursors = connect_ret.get_return('cursor')
        if not dbs or not cursors:
            return None, None
        if isinstance(dbs, dict) and isinstance(cursors, dict):
            tmp_server = list(dbs.keys())[0]
            db = dbs[tmp_server]
            cursor = cursors[tmp_server]
            return db, cursor
        else:
            return dbs, cursors

    def _test_optimize_operation(self, repository, ob_repository, optimize_envs, connect_namespaces, connect_plugin, stage=None, operation='optimize'):
        """
        :param stage: optimize stage
        :param optimize_envs: envs for optimize plugin
        :param operation: "optimize" or "recover"
        :return:
        """
        if operation == 'optimize':
            self._call_stdio('verbose', 'Optimize for stage {}'.format(stage))
        elif operation == 'recover':
            self._call_stdio('verbose', 'Recover the optimizes')
        else:
            raise Exception("Invalid optimize operation!")
        ob_cursor = None
        odp_cursor = None
        for namespace in connect_namespaces:
            db, cursor = self._get_first_db_and_cursor_from_connect(namespace)
            if not db or not cursor:
                if not self.call_plugin(connect_plugin, repository, spacename=namespace.spacename):
                    raise Exception('call connect plugin for {} failed'.format(namespace.spacename))
            if namespace.spacename in ['oceanbase', 'oceanbase-ce']:
                ob_db, ob_cursor = db, cursor
            elif namespace.spacename in ['obproxy', 'obproxy-ce']:
                odp_db, odp_cursor = db, cursor
        operation_plugin = self.plugin_manager.get_best_py_script_plugin(operation, 'optimize', '0.1')
        optimize_config = self.optimize_manager.optimize_config
        ret = self.call_plugin(operation_plugin, repository,
                               optimize_config=optimize_config, stage=stage,
                               ob_cursor=ob_cursor, odp_cursor=odp_cursor, optimize_envs=optimize_envs)
        if ret:
            restart_components = ret.get_return('restart_components')
        else:
            return False
        if restart_components:
            self._call_stdio('verbose', 'Components {} need restart.'.format(','.join(restart_components)))
            for namespace in connect_namespaces:
                db, cursor = self._get_first_db_and_cursor_from_connect(namespace)
                if cursor:
                    cursor.close()
            ret = self._restart_cluster_for_optimize(self.deploy.name, restart_components)
            if not ret:
                return False
            if operation == 'optimize':
                for namespace in connect_namespaces:
                    if not self.call_plugin(connect_plugin, repository, spacename=namespace.spacename):
                        raise Exception('call connect plugin for {} failed'.format(namespace.spacename))
                    if namespace.spacename == ob_repository.name and ob_repository.name in restart_components:
                        self._call_stdio('verbose', '{}: major freeze for component ready'.format(ob_repository.name))
                        self._call_stdio('start_loading', 'Waiting for {} ready'.format(ob_repository.name))
                        db, cursor = self._get_first_db_and_cursor_from_connect(namespace)
                        if not self._major_freeze(repository=ob_repository, cursor=cursor, tenant=optimize_envs.get('tenant')):
                            self._call_stdio('stop_loading', 'fail')
                            return False
                    self._call_stdio('stop_loading', 'succeed')
        return True

    def _major_freeze(self, repository, **kwargs):
        major_freeze_plugin = self.plugin_manager.get_best_py_script_plugin('major_freeze', repository.name, repository.version)
        if not major_freeze_plugin:
            self._call_stdio('verbose', 'no major freeze plugin for component {}, skip.'.format(repository.name))
            return True
        return self.call_plugin(major_freeze_plugin, repository, **kwargs)

    def _restart_cluster_for_optimize(self, deploy_name, components):
        self._call_stdio('start_loading', 'Restart cluster')
        if getattr(self.stdio, 'sub_io'):
            stdio = self.stdio.sub_io(msg_lv=MsgLevel.ERROR)
        else:
            stdio = None
        obd = ObdHome(self.home_path, self.dev_mode, stdio=stdio)
        obd.lock_manager.set_try_times(-1)
        obd.set_options(Values({'components': ','.join(components), 'without_parameter': True}))
        if obd.stop_cluster(name=deploy_name) and \
                obd.start_cluster(name=deploy_name) and obd.display_cluster(name=deploy_name):
            self._call_stdio('stop_loading', 'succeed')
            return True
        else:
            self._call_stdio('stop_loading', 'fail')
            return False

    def create_mysqltest_snap(self, repositories, create_snap_plugin, start_plugins, stop_plugins, snap_configs, env={}):
        for repository in repositories:
            if repository in snap_configs:
                if not self.call_plugin(stop_plugins[repository], repository):
                    return False
                if not self.call_plugin(create_snap_plugin, repository, env=env, snap_config=snap_configs[repository]):
                    return False
                if not self.call_plugin(start_plugins[repository], repository, home_path=self.home_path):
                    return False
        return True

    def mysqltest(self, name, opts):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        
        fast_reboot = getattr(opts, 'fast_reboot', False)
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Check deploy status')
        if fast_reboot:
            setattr(opts, 'without_parameter', True)
            status = [DeployStatus.STATUS_DEPLOYED, DeployStatus.STATUS_RUNNING]
        else:
            status = [DeployStatus.STATUS_RUNNING]
        if deploy_info.status not in status:
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
        # repositories = self.get_local_repositories({opts.component: deploy_config.components[opts.component]})
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)
        target_repository = None
        ob_repository = None
        for repository in repositories:
            if repository.name == opts.component:
                target_repository = repository
            if repository.name in ['oceanbase', 'oceanbase-ce']:
                ob_repository = repository

        if not target_repository:
            self._call_stdio('error', 'Can not find the component for mysqltest, use `--component` to select component')
            return False
        if not ob_repository:
            self._call_stdio('error', 'Deploy {} must contain the component oceanbase or oceanbase-ce.'.format(deploy.name))
            return False
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        if deploy_info.status == DeployStatus.STATUS_DEPLOYED and not self._start_cluster(deploy, repositories):
            return False

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            if self.stdio:
                self._call_stdio('error', err.EC_SOME_SERVER_STOPED.format())
                for repository in component_status:
                    cluster_status = component_status[repository]
                    for server in cluster_status:
                        if cluster_status[server] == 0:
                            self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
            return False
        namespace = self.get_namespace(target_repository.name)
        namespace.set_variable('target_server', opts.test_server)
        namespace.set_variable('connect_proxysys', False)

        connect_plugin = self.search_py_script_plugin(repositories, 'connect')[target_repository]
        ret = self.call_plugin(connect_plugin, target_repository)
        if not ret or not ret.get_return('connect'):
            return False
        db = ret.get_return('connect')
        cursor = ret.get_return('cursor')
        env = opts.__dict__
        env['cursor'] = cursor
        env['host'] = opts.test_server.ip
        env['port'] = db.port

        namespace.set_variable('env', env)
        mysqltest_init_plugin = self.plugin_manager.get_best_py_script_plugin('init', 'mysqltest', ob_repository.version)
        mysqltest_check_opt_plugin = self.plugin_manager.get_best_py_script_plugin('check_opt', 'mysqltest', ob_repository.version)
        mysqltest_check_test_plugin = self.plugin_manager.get_best_py_script_plugin('check_test', 'mysqltest', ob_repository.version)
        mysqltest_run_test_plugin = self.plugin_manager.get_best_py_script_plugin('run_test', 'mysqltest', ob_repository.version)
        mysqltest_collect_log_plugin = self.plugin_manager.get_best_py_script_plugin('collect_log', 'mysqltest', ob_repository.version)

        start_plugins = self.search_py_script_plugin(repositories, 'start')
        stop_plugins = self.search_py_script_plugin(repositories, 'stop')
        # display_plugin = self.search_py_script_plugin(repositories, 'display')[repository]

        if fast_reboot:
            create_snap_plugin = self.plugin_manager.get_best_py_script_plugin('create_snap', 'general', '0.1')
            load_snap_plugin = self.plugin_manager.get_best_py_script_plugin('load_snap', 'general', '0.1')
            snap_check_plugin = self.plugin_manager.get_best_py_script_plugin('snap_check', 'general', '0.1')
            snap_configs = self.search_plugins(repositories, PluginType.SNAP_CONFIG, no_found_exit=False)

        ret = self.call_plugin(mysqltest_check_opt_plugin, target_repository)
        if not ret:
            return False
        if not env['init_only']:
            ret = self.call_plugin(mysqltest_check_test_plugin, target_repository)
            if not ret:
                self._call_stdio('error', 'Failed to get test set')
                return False
            if env['test_set'] is None:
                self._call_stdio('error', 'Test set is empty')
                return False

        use_snap = False
        if env['need_init'] or env['init_only']:
            if not self.call_plugin(mysqltest_init_plugin, target_repository, env=env):
                self._call_stdio('error', 'Failed to init for mysqltest')
                return False
            if fast_reboot:
                if not self.create_mysqltest_snap(repositories, create_snap_plugin, start_plugins, stop_plugins, snap_configs, env):
                    return False
                ret = self.call_plugin(connect_plugin, target_repository)
                if not ret or not ret.get_return('connect'):
                    return False
                db = ret.get_return('connect')
                cursor = ret.get_return('cursor')
                env['cursor'] = cursor
                env['host'] = opts.test_server.ip
                env['port'] = db.port
                self._call_stdio('start_loading', 'Check init')
                env['load_snap'] = True
                self.call_plugin(mysqltest_init_plugin, target_repository)
                env['load_snap'] = False
                self._call_stdio('stop_loading', 'succeed')
                use_snap = True

            if env['init_only']:
                return True

        if fast_reboot and use_snap is False:
            self._call_stdio('start_loading', 'Check init')
            env['load_snap'] = True
            self.call_plugin(mysqltest_init_plugin, target_repository)
            env['load_snap'] = False
            self._call_stdio('stop_loading', 'succeed')
            snap_num = 0
            for repository in repositories:
                if repository in snap_configs:
                    if not self.call_plugin(snap_check_plugin, repository, env=env, snap_config=snap_configs[repository]):
                        break
                    snap_num += 1
            use_snap = len(snap_configs) == snap_num
        env['load_snap'] = use_snap

        self._call_stdio('verbose', 'test set: {}'.format(env['test_set']))
        self._call_stdio('verbose', 'total: {}'.format(len(env['test_set'])))
        reboot_success = True
        while True:
            ret = self.call_plugin(mysqltest_run_test_plugin, target_repository)
            if not ret:
                break
            self.call_plugin(mysqltest_collect_log_plugin, target_repository)
            if ret.get_return('finished'):
                break
            if ret.get_return('reboot') and not env['disable_reboot']:
                cursor.close()
                if getattr(self.stdio, 'sub_io'):
                    stdio = self.stdio.sub_io(msg_lv=MsgLevel.ERROR)
                else:
                    stdio = None
                reboot_timeout = getattr(opts, 'reboot_timeout', 0)
                reboot_retries = getattr(opts, 'reboot_retries', 5)
                reboot_success = False
                while reboot_retries and not reboot_success:
                    reboot_retries -= 1
                    with timeout(reboot_timeout):
                        if use_snap:
                            self._call_stdio('start_loading', 'Snap Reboot')
                            for repository in repositories:
                                if repository in snap_configs:
                                    cluster_config = deploy_config.components[repository.name]
                                    if not self.call_plugin(stop_plugins[repository]):
                                        self._call_stdio('stop_loading', 'fail')
                                        continue
                                    if not self.call_plugin(load_snap_plugin, repository,  env=env, snap_config=snap_configs[repository]):
                                        self._call_stdio('stop_loading', 'fail')
                                        continue
                                    if not self.call_plugin(start_plugins[repository], repository, home_path=self.home_path):
                                        self._call_stdio('stop_loading', 'fail')
                                        continue
                        else:
                            self._call_stdio('start_loading', 'Reboot')
                            obd = ObdHome(self.home_path, self.dev_mode, stdio=stdio)
                            obd.lock_manager.set_try_times(-1)
                            obd.set_options(Values({'force_kill': True, 'force': True, 'force_delete': True}))
                            if not obd.redeploy_cluster(name, search_repo=False):
                                self._call_stdio('stop_loading', 'fail')
                                continue
                            obd.lock_manager.set_try_times(6000)
                            obd = None

                        self._call_stdio('stop_loading', 'succeed')
                        ret = self.call_plugin(connect_plugin, target_repository)
                        if not ret or not ret.get_return('connect'):
                            self._call_stdio('error', 'Failed to connect server')
                            continue
                        db = ret.get_return('connect')
                        cursor = ret.get_return('cursor')
                        env['cursor'] = cursor

                        if self.call_plugin(mysqltest_init_plugin, target_repository):
                            if fast_reboot and use_snap is False:
                                if not self.create_mysqltest_snap(repositories, create_snap_plugin, start_plugins, stop_plugins, snap_configs, env):
                                    return False
                                use_snap = True
                                ret = self.call_plugin(connect_plugin, target_repository)
                                if not ret or not ret.get_return('connect'):
                                    self._call_stdio('error', 'Failed to connect server')
                                    continue
                                db = ret.get_return('connect')
                                cursor = ret.get_return('cursor')
                                env['cursor'] = cursor
                                self.call_plugin(mysqltest_init_plugin, target_repository)
                            reboot_success = True
                        else:
                            self._call_stdio('error', 'Failed to prepare for mysqltest')
                if not reboot_success:
                    env['collect_log'] = True
                    self.call_plugin(mysqltest_collect_log_plugin, target_repository, test_name='reboot_failed')
                    break
        result = env.get('case_results', [])
        passcnt = len(list(filter(lambda x: x["ret"] == 0, result)))
        totalcnt = len(env.get('run_test_cases', []))
        failcnt = totalcnt - passcnt
        if result:
            self._call_stdio(
                'print_list', result, ['Case', 'Cost (s)', 'Status'], 
                lambda x: [x['name'], '%.2f' % x['cost'], '\033[31mFAILED\033[0m' if x['ret'] else '\033[32mPASSED\033[0m'], 
                title='Result (Total %d, Passed %d, Failed %s)' % (totalcnt, passcnt, failcnt), 
                align={'Cost (s)': 'r'}
            )
        if failcnt or not reboot_success:
            if not reboot_success:
                self._call_stdio('error', 'reboot cluster failed')
            self._call_stdio('print', 'Mysqltest failed')
        else:
            self._call_stdio('print', 'Mysqltest passed')
            return True
        return False

    def sysbench(self, name, opts):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
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
        self.set_repositories(repositories)
        self.get_clients(deploy_config, repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Check the status for the deployed cluster
        if not getattr(opts, 'skip_cluster_status_check', False):
            component_status = {}
            cluster_status = self.cluster_status_check(repositories, component_status)
            if cluster_status is False or cluster_status == 0:
                if self.stdio:
                    self._call_stdio('error', err.EC_SOME_SERVER_STOPED.format())
                    for repository in component_status:
                        cluster_status = component_status[repository]
                        for server in cluster_status:
                            if cluster_status[server] == 0:
                                self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
                return False

        ob_repository = None
        repository = None
        connect_namespaces = []
        for tmp_repository in repositories:
            if tmp_repository.name in ["oceanbase", "oceanbase-ce"]:
                ob_repository = tmp_repository
            if tmp_repository.name == opts.component:
                repository = tmp_repository
        if not ob_repository:
            self._call_stdio('error', 'Deploy {} must contain the component oceanbase or oceanbase-ce.'.format(deploy.name))
            return False
        sys_namespace = self.get_namespace(ob_repository.name)
        connect_plugin = self.plugin_manager.get_best_py_script_plugin('connect', repository.name, repository.version)
        if repository.name in ['obproxy', 'obproxy-ce']:
            for component_name in deploy_config.components:
                if component_name in ['oceanbase', 'oceanbase-ce']:
                    ob_cluster_config = deploy_config.components[component_name]
                    sys_namespace.set_variable("connect_proxysys", False)
                    sys_namespace.set_variable("user", "root")
                    sys_namespace.set_variable("password", ob_cluster_config.get_global_conf().get('root_password', ''))
                    sys_namespace.set_variable("target_server",  opts.test_server)
                    break
            proxysys_namespace = self.get_namespace(repository.name)
            proxysys_namespace.set_variable("component_name", repository)
            proxysys_namespace.set_variable("target_server", opts.test_server)
            ret = self.call_plugin(connect_plugin, repository, spacename=proxysys_namespace.spacename)
            if not ret or not ret.get_return('connect'):
                return False
            connect_namespaces.append(proxysys_namespace)
        plugin_version = ob_repository.version if ob_repository else repository.version
        ret = self.call_plugin(connect_plugin, repository, spacename=sys_namespace.spacename)
        if not ret or not ret.get_return('connect'):
            return False
        connect_namespaces.append(sys_namespace)
        db, cursor = self._get_first_db_and_cursor_from_connect(namespace=sys_namespace)
        pre_test_plugin = self.plugin_manager.get_best_py_script_plugin('pre_test', 'sysbench', plugin_version)
        run_test_plugin = self.plugin_manager.get_best_py_script_plugin('run_test', 'sysbench', plugin_version)

        setattr(opts, 'host', opts.test_server.ip)
        setattr(opts, 'port', db.port)

        optimization = getattr(opts, 'optimization', 0)

        ret = self.call_plugin(pre_test_plugin, repository, cursor=cursor)
        if not ret:
            return False
        kwargs = ret.kwargs
        optimization_init = False
        try:
            if optimization:
                if not self._test_optimize_init(test_name='sysbench', repository=repository):
                    return False
                optimization_init = True
                if not self._test_optimize_operation(repository=repository, ob_repository=ob_repository, stage='test', connect_namespaces=connect_namespaces, connect_plugin=connect_plugin, optimize_envs=kwargs):
                    return False
            if self.call_plugin(run_test_plugin, repository):
                return True
            return False
        finally:
            if optimization and optimization_init:
                self._test_optimize_operation(repository=repository,  ob_repository=ob_repository, connect_namespaces=connect_namespaces, connect_plugin=connect_plugin, optimize_envs=kwargs, operation='recover')

    def tpch(self, name, opts):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
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
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        if not getattr(opts, 'skip_cluster_status_check', False):
            # Check the status for the deployed cluster
            component_status = {}
            cluster_status = self.cluster_status_check(repositories, component_status)
            if cluster_status is False or cluster_status == 0:
                if self.stdio:
                    self._call_stdio('error', err.EC_SOME_SERVER_STOPED.format())
                    for repository in component_status:
                        cluster_status = component_status[repository]
                        for server in cluster_status:
                            if cluster_status[server] == 0:
                                self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
                return False
        repository = repositories[0]
        namespace = self.get_namespace(repository.name)
        namespace.set_variable('target_server', opts.test_server)
        connect_plugin = self.plugin_manager.get_best_py_script_plugin('connect', repository.name, repository.version)
        ret = self.call_plugin(connect_plugin, repository)
        if not ret or not ret.get_return('connect'):
            return False
        db = ret.get_return('connect')
        cursor = ret.get_return('cursor')

        pre_test_plugin = self.plugin_manager.get_best_py_script_plugin('pre_test', 'tpch', repository.version)
        run_test_plugin = self.plugin_manager.get_best_py_script_plugin('run_test', 'tpch', repository.version)

        setattr(opts, 'host', opts.test_server.ip)
        setattr(opts, 'port', db.port)

        optimization = getattr(opts, 'optimization', 0)

        ret = self.call_plugin(pre_test_plugin,repository, cursor=cursor)
        if not ret:
            return False
        kwargs = ret.kwargs
        optimization_init = False
        try:
            if optimization:
                if not self._test_optimize_init(test_name='tpch', repository=repository):
                    return False
                optimization_init = True
                if not self._test_optimize_operation(
                        repository=repository, ob_repository=repository, stage='test',
                        connect_namespaces=[namespace], connect_plugin=connect_plugin, optimize_envs=kwargs):
                    return False
            if self.call_plugin(run_test_plugin, repository, db=db, cursor=cursor, **kwargs):
                return True
            return False
        except Exception as e:
            self._call_stdio('error', e)
            return False
        finally:
            if optimization and optimization_init:
                self._test_optimize_operation(
                    repository=repository, ob_repository=repository, connect_namespaces=[namespace],
                    connect_plugin=connect_plugin, optimize_envs=kwargs, operation='recover')

    def update_obd(self, version, install_prefix='/'):
        self._global_ex_lock()
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

    def tpcds(self, name, opts):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
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

        db_component = None
        db_components = ['oceanbase', 'oceanbase-ce']
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
            self._call_stdio('error', 'Can not find the component for tpcds, use `--component` to select component')
            return False

        for component_name in db_components:
            if component_name in deploy_config.components:
                db_component = component_name
        if db_component is None:
            self._call_stdio('error', 'Missing database component (%s) in deploy' % ','.join(db_components))
            return False

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        # repositories = self.get_local_repositories({opts.component: deploy_config.components[opts.component]})
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        component_status = {}
        cluster_status = self.cluster_status_check(repositories, component_status)
        if cluster_status is False or cluster_status == 0:
            if self.stdio:
                self._call_stdio('error', err.EC_SOME_SERVER_STOPED.format())
                for repository in component_status:
                    cluster_status = component_status[repository]
                    for server in cluster_status:
                        if cluster_status[server] == 0:
                            self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
            return False

        db_cluster_config =  deploy_config.components[db_component]
        cluster_config =  deploy_config.components[opts.component]

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

        check_opt_plugin = self.plugin_manager.get_best_py_script_plugin('check_opt', 'tpcds', db_cluster_config.version)
        load_data_plugin = self.plugin_manager.get_best_py_script_plugin('load_data', 'tpcds', cluster_config.version)
        run_test_plugin = self.plugin_manager.get_best_py_script_plugin('run_test', 'tpcds', cluster_config.version)
        repository = None
        for tmp_repository in repositories:
            if tmp_repository.name == opts.component:
                repository = tmp_repository

        if not self.call_plugin(check_opt_plugin, repository, db_cluster_config=db_cluster_config):
            return False
        if not self.call_plugin(load_data_plugin, repository):
            return False
        return self.call_plugin(run_test_plugin)

    def tpcc(self, name, opts):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
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
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        if not getattr(opts, 'skip_cluster_status_check', False):
            component_status = {}
            cluster_status = self.cluster_status_check(repositories, component_status)
            if cluster_status is False or cluster_status == 0:
                if self.stdio:
                    self._call_stdio('error', err.EC_SOME_SERVER_STOPED.format())
                    for repository in component_status:
                        cluster_status = component_status[repository]
                        for server in cluster_status:
                            if cluster_status[server] == 0:
                                self._call_stdio('print', '%s %s is stopped' % (server, repository.name))
                return False

        ob_repository = None
        repository = None
        odp_cursor = None
        proxysys_namespace = None
        connect_namespaces = []
        for tmp_repository in repositories:
            if tmp_repository.name in ["oceanbase", "oceanbase-ce"]:
                ob_repository = tmp_repository
            if tmp_repository.name == opts.component:
                repository = tmp_repository
        if not ob_repository:
            self._call_stdio('error', 'Deploy {} must contain the component oceanbase or oceanbase-ce.'.format(deploy.name))
            return False
        sys_namespace = self.get_namespace(ob_repository.name)
        connect_plugin = self.plugin_manager.get_best_py_script_plugin('connect', repository.name, repository.version)
        if repository.name in ['obproxy', 'obproxy-ce']:
            for component_name in deploy_config.components:
                if component_name in ['oceanbase', 'oceanbase-ce']:
                    ob_cluster_config = deploy_config.components[component_name]
                    sys_namespace.set_variable("connect_proxysys", False)
                    sys_namespace.set_variable("user", "root")
                    sys_namespace.set_variable("password", ob_cluster_config.get_global_conf().get('root_password', ''))
                    sys_namespace.set_variable("target_server", opts.test_server)
                    break
            proxysys_namespace = self.get_namespace(repository.name)
            proxysys_namespace.set_variable("component_name", repository)
            proxysys_namespace.set_variable("target_server", opts.test_server)
            ret = self.call_plugin(connect_plugin, repository, spacename=proxysys_namespace.spacename)
            if not ret or not ret.get_return('connect'):
                return False
            odp_db, odp_cursor = self._get_first_db_and_cursor_from_connect(proxysys_namespace)
            connect_namespaces.append(proxysys_namespace)
        plugin_version = ob_repository.version if ob_repository else repository.version
        ret = self.call_plugin(connect_plugin, repository, spacename=sys_namespace.spacename)
        if not ret or not ret.get_return('connect'):
            return False
        connect_namespaces.append(sys_namespace)
        db, cursor = self._get_first_db_and_cursor_from_connect(namespace=sys_namespace)
        pre_test_plugin = self.plugin_manager.get_best_py_script_plugin('pre_test', 'tpcc', plugin_version)
        build_plugin = self.plugin_manager.get_best_py_script_plugin('build', 'tpcc', plugin_version)
        run_test_plugin = self.plugin_manager.get_best_py_script_plugin('run_test', 'tpcc', plugin_version)

        setattr(opts, 'host', opts.test_server.ip)
        setattr(opts, 'port', db.port)

        kwargs = {}

        optimization = getattr(opts, 'optimization', 0)
        test_only = getattr(opts, 'test_only', False)
        optimization_inited = False
        try:
            ret = self.call_plugin(pre_test_plugin, repository, cursor=cursor, odp_cursor=odp_cursor, **kwargs)
            if not ret:
                return False
            else:
                kwargs.update(ret.kwargs)
            if optimization:
                if not self._test_optimize_init(test_name='tpcc', repository=repository):
                    return False
                optimization_inited = True
                if not self._test_optimize_operation(repository=repository, ob_repository=ob_repository, stage='build',
                                                     connect_namespaces=connect_namespaces,
                                                     connect_plugin=connect_plugin, optimize_envs=kwargs):
                    return False
            if not test_only:
                db, cursor = self._get_first_db_and_cursor_from_connect(sys_namespace)
                odp_db, odp_cursor = self._get_first_db_and_cursor_from_connect(proxysys_namespace)
                ret = self.call_plugin(build_plugin, repository,  cursor=cursor, odp_cursor=odp_cursor, **kwargs)
                if not ret:
                    return False
                else:
                    kwargs.update(ret.kwargs)
            if optimization:
                if not self._test_optimize_operation(repository=repository, ob_repository=ob_repository, stage='test',
                                                     connect_namespaces=connect_namespaces,
                                                     connect_plugin=connect_plugin, optimize_envs=kwargs):
                    return False
            db, cursor = self._get_first_db_and_cursor_from_connect(sys_namespace)
            ret = self.call_plugin(run_test_plugin, repository, cursor=cursor, **kwargs)
            if not ret:
                return False
            else:
                kwargs.update(ret.kwargs)
            return True
        except Exception as e:
            self._call_stdio('exception', e)
            return False
        finally:
            if optimization and optimization_inited:
                self._test_optimize_operation(repository=repository, ob_repository=ob_repository,
                                              connect_namespaces=connect_namespaces,
                                              connect_plugin=connect_plugin, optimize_envs=kwargs, operation='recover')

    def db_connect(self, name, opts):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name, read_only=True)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        self.set_deploy(deploy)
        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config
        deploy_info = deploy.deploy_info

        if deploy_info.status in (DeployStatus.STATUS_DESTROYED, DeployStatus.STATUS_CONFIGURED):
            self._call_stdio('print', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False

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
            self._call_stdio('error', 'Can not find the component for db connect, use `--component` to select component')
            return False

        cluster_config = deploy_config.components[opts.component]
        if not cluster_config.servers:
            self._call_stdio('error', '%s server list is empty' % opts.component)
            return False
        if opts.server is None:
            opts.server = cluster_config.servers[0]
        else:
            for server in cluster_config.servers:
                if server.name == opts.server:
                    opts.server = server
                    break
            else:
                self._call_stdio('error', '%s is not a server in %s' % (opts.server, opts.component))
                return False
        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)
        repository = None
        for tmp_repository in repositories:
            if tmp_repository.name == opts.component:
                repository = tmp_repository

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        sync_config_plugin = self.plugin_manager.get_best_py_script_plugin('sync_cluster_config', 'general', '0.1')
        self.call_plugin(sync_config_plugin, repository)
        db_connect_plugin = self.plugin_manager.get_best_py_script_plugin('db_connect', 'general', '0.1')
        return self.call_plugin(db_connect_plugin, repository)

    def commands(self, name, cmd_name, opts):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name, read_only=True)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        self.set_deploy(deploy)
        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config
        deploy_info = deploy.deploy_info

        if deploy_info.status in (DeployStatus.STATUS_DESTROYED, DeployStatus.STATUS_CONFIGURED):
            self._call_stdio('print', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        repositories = self.sort_repositories_by_depends(deploy_config, repositories)
        self.set_repositories(repositories)
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        check_opt_plugin = self.plugin_manager.get_best_py_script_plugin('check_opt', 'commands', '0.1')
        prepare_variables_plugin = self.plugin_manager.get_best_py_script_plugin('prepare_variables', 'commands', '0.1')
        commands_plugin = self.plugin_manager.get_best_py_script_plugin('commands', 'commands', '0.1')
        sync_config_plugin = self.plugin_manager.get_best_py_script_plugin('sync_cluster_config', 'general', '0.1')

        repository = repositories[0]
        context = {}
        self.call_plugin(sync_config_plugin, repository)
        ret = self.call_plugin(check_opt_plugin, repository, name=cmd_name, context=context)
        if not ret:
            return
        for component in context['components']:
            for repository in repositories:
                if repository.name == component:
                    break
            for server in context['servers']:
                ret = self.call_plugin(prepare_variables_plugin, repository, name=cmd_name, component=component, server=server, context=context)
                if not ret:
                    return
                if not ret.get_return("skip"):
                    ret = self.call_plugin(commands_plugin, repository, context=context)
        if context.get('interactive'):
            return bool(ret)
        results = context.get('results', [])
        self._call_stdio("print_list", results, ["Component", "Server", cmd_name.title()], title=cmd_name.title())
        return not context.get('failed')

    def dooba(self, name, opts):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name, read_only=True)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        self.set_deploy(deploy)
        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config
        deploy_info = deploy.deploy_info

        if deploy_info.status in (DeployStatus.STATUS_DESTROYED, DeployStatus.STATUS_CONFIGURED):
            self._call_stdio('print', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False

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
            self._call_stdio('error',
                             'Can not find the component for dooba, use `--component` to select component')
            return False

        for component in deploy_config.components:
            if component in ['oceanbase', 'oceanbase-ce']:
                break
        else:
            self._call_stdio('error', 'Dooba must contain the component oceanbase or oceanbase-ce.')
            return False

        cluster_config = deploy_config.components[opts.component]
        if not cluster_config.servers:
            self._call_stdio('error', '%s server list is empty' % opts.component)
            return False
        if opts.server is None:
            opts.server = cluster_config.servers[0]
        else:
            for server in cluster_config.servers:
                if server.name == opts.server:
                    opts.server = server
                    break
            else:
                self._call_stdio('error', '%s is not a server in %s' % (opts.server, opts.component))
                return False
        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)
        plugin_version = None
        target_repository = None
        for repository in repositories:
            if repository.name in ['oceanbase', 'oceanbase-ce']:
                plugin_version = repository.version
            if repository.name == opts.component:
                target_repository = repository
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        sync_config_plugin = self.plugin_manager.get_best_py_script_plugin('sync_cluster_config', 'general', '0.1')
        self.call_plugin(sync_config_plugin, target_repository)
        dooba_plugin = self.plugin_manager.get_best_py_script_plugin('run', 'dooba', plugin_version)
        return self.call_plugin(dooba_plugin, target_repository)

    def telemetry_post(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False

        deploy_info = deploy.deploy_info
        if deploy_info.status in (DeployStatus.STATUS_DESTROYED, DeployStatus.STATUS_CONFIGURED):
            self._call_stdio('print', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False

        repositories = self.load_local_repositories(deploy_info)
        if repositories == []:
            return
        self.set_repositories(repositories)

        telemetry_info_collect_plugin = self.plugin_manager.get_best_py_script_plugin('telemetry_info_collect', 'general', '0.1')
        for repository in repositories:
            if not self.call_plugin(telemetry_info_collect_plugin, repository, spacename='telemetry'):
                return False
            
        telemetry_post_plugin = self.plugin_manager.get_best_py_script_plugin('telemetry_post', 'general', '0.1')
        return self.call_plugin(telemetry_post_plugin, repository, spacename='telemetry')


    def obdiag_gather(self, name, gather_type, opts):
        self._global_ex_lock()
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name, read_only=True)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        self.set_deploy(deploy)
        self._call_stdio('verbose', 'Get deploy configuration')
        deploy_config = deploy.deploy_config
        deploy_info = deploy.deploy_info

        if deploy_info.status in (DeployStatus.STATUS_DESTROYED, DeployStatus.STATUS_CONFIGURED):
            self._call_stdio('print', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False

        allow_components = []
        if gather_type.startswith("gather_obproxy"):
            allow_components = ['obproxy-ce', 'obproxy']
        else:
            allow_components = ['oceanbase-ce', 'oceanbase']

        component_name = ""
        for component in deploy_config.components:
            if component in allow_components:
                component_name = component
                break
        if component_name == "":
            self._call_stdio('error', err.EC_OBDIAG_NOT_CONTAIN_DEPEND_COMPONENT.format(components=allow_components))
            return False

        cluster_config = deploy_config.components[component_name]
        if not cluster_config.servers:
            self._call_stdio('error', '%s server list is empty' % allow_components)
            return False
        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)
        self._call_stdio('stop_loading', 'succeed')
        target_repository = None
        for repository in repositories:
            if repository.name == component_name:
                target_repository = repository
                break
        if gather_type in ['gather_plan_monitor']:
            setattr(opts, 'connect_cluster', True)          
        obdiag_path = getattr(opts, 'obdiag_dir', None) 

        diagnostic_component_name = 'oceanbase-diagnostic-tool'
        obdiag_version = '1.0'
        pre_check_plugin = self.plugin_manager.get_best_py_script_plugin('pre_check', diagnostic_component_name, obdiag_version)    
        check_pass = self.call_plugin(pre_check_plugin,
            target_repository,
            gather_type = gather_type,
            obdiag_path = obdiag_path, 
            version_check = True,
            utils_work_dir_check = True)
        if not check_pass:
            # obdiag checker return False
            if not check_pass.get_return('obdiag_found'):
                if not self._call_stdio('confirm', 'Could not find the obdiag, please confirm whether to install it' ):
                    return False
                self.obdiag_deploy(auto_deploy=True, install_prefix=obdiag_path)
            # utils checker return False
            if not check_pass.get_return('utils_status'):
                repositories_utils_map = self.get_repositories_utils(repositories)
                if repositories_utils_map is False:
                    self._call_stdio('error', 'Failed to get utils package')
                else:
                    if not self._call_stdio('confirm', 'obdiag gather clog/slog need to install ob_admin\nDo you want to install ob_admin?'):
                        if not check_pass.get_return('skip'):
                            return False
                        else:
                            self._call_stdio('warn', 'Just skip gather clog/slog')
                    else:
                        if not self.install_utils_to_servers(repositories, repositories_utils_map):
                            self._call_stdio('error', 'Failed to install utils to servers')
        obdiag_version = check_pass.get_return('obdiag_version')
        generate_config_plugin = self.plugin_manager.get_best_py_script_plugin('generate_config', diagnostic_component_name, obdiag_version)
        self.call_plugin(generate_config_plugin, target_repository, deploy_config=deploy_config)
        self._call_stdio('generate_config', 'succeed')
        obdiag_plugin = self.plugin_manager.get_best_py_script_plugin(gather_type, diagnostic_component_name, obdiag_version)
        return self.call_plugin(obdiag_plugin, target_repository)


    def obdiag_deploy(self, auto_deploy=False, install_prefix=None):
        self._global_ex_lock()
        component_name = 'oceanbase-diagnostic-tool'
        if install_prefix is None:
            install_prefix = os.path.join(os.getenv('HOME'), component_name)
        pkg = self.mirror_manager.get_best_pkg(name=component_name)
        if not pkg:
            self._call_stdio('critical', '%s package not found' % component_name)
            return False
        plugin = self.plugin_manager.get_best_plugin(PluginType.INSTALL, component_name, pkg.version)
        self._call_stdio('print', 'obdiag plugin : %s' % plugin)

        repository = self.repository_manager.create_instance_repository(pkg.name, pkg.version, pkg.md5)
        check_plugin = self.plugin_manager.get_best_py_script_plugin('pre_check', component_name, pkg.version)
        if not auto_deploy:
            ret = self.call_plugin(check_plugin,
                repository,
                clients={},
                obdiag_path = install_prefix,
                obdiag_new_version = pkg.version, 
                version_check = True)
            if not ret and ret.get_return('obdiag_found'):
                self._call_stdio('print', 'No updates detected. obdiag is already up to date.')
                return False
            if not self._call_stdio('confirm', 'Found a higher version\n%s\nDo you want to use it?' % pkg):
                return False
        self._call_stdio('start_loading', 'Get local repositories and plugins')
        repository.load_pkg(pkg, plugin)
        src_path = os.path.join(repository.repository_dir, component_name)
        if FileUtil.symlink(src_path, install_prefix, self.stdio):
            self._call_stdio('stop_loading', 'succeed')
            self._call_stdio('print', 'Deploy obdiag successful.\nCurrent version : %s. \nPath of obdiag : %s' % (pkg.version, install_prefix))
        return True


    def get_repositories_utils(self, repositories):
        all_data = []
        data = {}
        temp_map = {}
        need_install_repositories = ['oceanbase-ce']
        for repository in repositories:
            utils_name = '%s-utils' % repository.name
            if (utils_name in data) or (repository.name not in need_install_repositories):
                continue
            data[utils_name] = {'version': repository.version}
            temp_map[utils_name] = repository
        all_data.append((data, temp_map))
        try:
            repositories_utils_map = {}
            for data, temp_map in all_data:
                with tempfile.NamedTemporaryFile(suffix=".yaml", mode='w') as tf:
                    yaml_loader = YamlLoader(self.stdio)
                    yaml_loader.dump(data, tf)
                    deploy_config = DeployConfig(tf.name, yaml_loader=yaml_loader, config_parser_manager=self.deploy_manager.config_parser_manager)
                    self._call_stdio('verbose', 'Search best suitable repository utils')
                    pkgs, utils_repositories, errors = self.search_components_from_mirrors(deploy_config, only_info=False)
                    if errors:
                        self._call_stdio('error', '\n'.join(errors))
                        return False

                    # Get the installation plugin and install
                    install_plugins = self.get_install_plugin_and_install(utils_repositories, pkgs)
                    if not install_plugins:
                        return False
                    for utils_repository in utils_repositories:
                        repository = temp_map[utils_repository.name]
                        install_plugin = install_plugins[utils_repository]
                        repositories_utils_map[repository] = {
                            'repositories': utils_repository,
                            'install_plugin': install_plugin
                        }
            return repositories_utils_map
        except:
            self._call_stdio('exception', 'Failed to create utils-repo config file')
            pass
        return False


    def install_utils_to_servers(self, repositories, repositories_utils_map, unuse_utils_repository=True):
        install_repo_plugin = self.plugin_manager.get_best_py_script_plugin('install_repo', 'general', '0.1')
        check_file_maps = {}
        need_install_repositories = ['oceanbase-ce']
        for repository in repositories:
            if (repository.name not in need_install_repositories):
                continue
            temp_repository = deepcopy(repository)
            temp_repository.name = '%s-utils' % repository.name
            utils_repository = repositories_utils_map[temp_repository]['repositories']
            install_plugin = repositories_utils_map[temp_repository]['install_plugin']
            check_file_map = check_file_maps[repository] = install_plugin.file_map(repository)
            ret = self.call_plugin(install_repo_plugin, repository, obd_home=self.home_path, install_repository=utils_repository,
                        install_plugin=install_plugin, check_repository=repository, check_file_map=check_file_map,
                        msg_lv='error' if unuse_utils_repository else 'warn')
            if not ret:
                return False
        return True