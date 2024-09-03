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
import signal
from optparse import Values
from copy import deepcopy, copy
from collections import defaultdict

import tempfile
from subprocess import call as subprocess_call

from ssh import SshClient, SshConfig
from tool import FileUtil, DirectoryUtil, YamlLoader, timeout, COMMAND_ENV, OrderedDict
from _stdio import MsgLevel, FormatText
from _rpm import Version
from _mirror import MirrorRepositoryManager, PackageInfo, RemotePackageInfo
from _plugin import PluginManager, PluginType, InstallPlugin, PluginContextNamespace
from _deploy import DeployManager, DeployStatus, DeployConfig, DeployConfigStatus, Deploy, ClusterStatus
from _tool import Tool, ToolManager
from _repository import RepositoryManager, LocalPackage, Repository, RepositoryVO
import _errno as err
from _lock import LockManager, LockMode
from _optimize import OptimizeManager
from _environ import ENV_REPO_INSTALL_MODE, ENV_BASE_DIR
from _types import Capacity
from const import COMP_OCEANBASE_DIAGNOSTIC_TOOL, COMP_OBCLIENT, PKG_RPM_FILE, TEST_TOOLS, COMPS_OB, PKG_REPO_FILE, TOOL_TPCC, TOOL_TPCH, TOOL_SYSBENCH
from ssh import LocalClient


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
        self._tool_manager = None
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
    
    @property
    def tool_manager(self):
        if not self._tool_manager:
            self._tool_manager = ToolManager(self.home_path, self.repository_manager, self.lock_manager, self.stdio)
        return self._tool_manager

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

    def call_plugin(self, plugin, repository, spacename=None, target_servers=None, **kwargs):
        args = {
            'namespace': self.get_namespace(repository.name if spacename == None else spacename),
            'namespaces': self.namespaces,
            'deploy_name': None,
            'deploy_status': None,
            'cluster_config': None,
            'repositories': self.repositories,
            'repository': repository,
            'components': None,
            'cmd': self.cmds,
            'options': self.options,
            'stdio': self.stdio,
            'target_servers': target_servers
        }
        if self.deploy:
            args['deploy_name'] = self.deploy.name
            args['deploy_status'] = self.deploy.deploy_info.status
            args['components'] = self.deploy.deploy_config.components.keys()
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

    def get_clients_with_connect_servers(self, deploy_config, repositories, fail_exit=False):
        ssh_clients, connect_status = self.get_clients_with_connect_status(deploy_config, repositories, fail_exit)

        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            cluster_config.servers = [server for server in cluster_config.servers if server in ssh_clients]

        failed_servers = []
        for k, v in connect_status.items():
            if v.status == v.FAIL:
                failed_servers.append(k.ip)
        for server in failed_servers:
            self._call_stdio('warn', '%s connect failed' % server)
        return ssh_clients

    def ssh_clients_connect(self, servers, ssh_clients, user_config, fail_exit=False):
        self._call_stdio('start_loading', 'Open ssh connection')
        connect_io = self.stdio if fail_exit else self.stdio.sub_io(msg_lv=MsgLevel.CRITICAL)
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
                error = client.connect(stdio=connect_io, exit=fail_exit)
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

    def search_images(self, component_name, version=None, min_version=None, max_version=None, release=None, disable=[],
                      usable=[], release_first=False, print_match=True):
        matchs = {}
        usable_matchs = []
        for pkg in self.mirror_manager.get_pkgs_info(component_name, version=version, min_version=min_version,
                                                     max_version=max_version, release=release):
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

    def search_components_from_mirrors(self, deploy_config, fuzzy_match=False, only_info=True, update_if_need=None, components=None):
        pkgs = []
        errors = []
        repositories = []
        self._call_stdio('verbose', 'Search package for components...')
        if components is None:
            components = deploy_config.components.keys()
        for component in components:
            if component not in deploy_config.components:
                errors.append('No such component name: {}'.format(component))
                continue
            config = deploy_config.components[component]

            # First, check if the component exists in the repository. If exists, check if the version is available. If so, use the repository directly.
            self._call_stdio('verbose', 'Get %s repository' % component)
            repository = self.repository_manager.get_repository(name=component, version=config.version, tag=config.tag, release=config.release, package_hash=config.package_hash)
            if repository and not repository.hash:
                repository = None
            if not config.tag:
                self._call_stdio('verbose', 'Search %s package from mirror' % component)
                pkg = self.mirror_manager.get_best_pkg(
                    name=component, version=config.version, md5=config.package_hash, release=config.release, fuzzy=fuzzy_match, only_info=only_info)
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

        if deploy and deploy.deploy_info.status == DeployStatus.STATUS_UPRADEING:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not edit an upgrading cluster' % (name, deploy.deploy_info.status.value))
            return False

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
        diff_need_redeploy_keys = []
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
                    inner_config=deploy.deploy_config.inner_config if deploy else None,
                    stdio=self.stdio
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
                    if not self._call_stdio('confirm', FormatText.warning('Modifications to the deployment architecture take effect after you redeploy the architecture. Are you sure that you want to start a redeployment? ')):
                        if user_input:
                            return False
                        continue
                    config_status = DeployConfigStatus.NEED_REDEPLOY

                if config_status != DeployConfigStatus.NEED_REDEPLOY:
                    comp_attr_changed = False
                    for component_name in deploy_config.components:
                        old_cluster_config = deploy.deploy_config.components[component_name]
                        new_cluster_config = deploy_config.components[component_name]
                        comp_attr_map = {'version': 'config_version', 'package_hash': 'config_package_hash', 'release': 'config_release', 'tag': 'tag'}
                        for key, value in comp_attr_map.items():
                            if getattr(new_cluster_config, key) != getattr(old_cluster_config, value):
                                comp_attr_changed = True
                                diff_need_redeploy_keys.append(key)
                                config_status = DeployConfigStatus.NEED_REDEPLOY
                    if comp_attr_changed:
                        if not self._call_stdio('confirm', FormatText.warning('Modifications to the version, release or hash of the component take effect after you redeploy the cluster. Are you sure that you want to start a redeployment? ')):
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
                        if not self._call_stdio('confirm', FormatText.warning('Modifications to the rsync config of a deployed cluster take effect after you redeploy the cluster. Are you sure that you want to start a redeployment? ')):
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
                        if self._call_stdio('confirm', FormatText.warning('Modifications take effect after a redeployment. Are you sure that you want to start a redeployment?')):
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
                        new_redeploy_items = new_cluster_config.get_need_redeploy_items(server)
                        old_redeploy_items = old_cluster_config.get_need_redeploy_items(server)
                        if new_redeploy_items != old_redeploy_items:
                            diff_need_redeploy_keys = [key for key in list(set(old_redeploy_items) | set(new_redeploy_items)) if new_redeploy_items.get(key, '') != old_redeploy_items.get(key, '')]
                            config_status = DeployConfigStatus.NEED_REDEPLOY
                            break
                        if old_cluster_config.get_need_restart_items(server) != new_cluster_config.get_need_restart_items(server):
                            config_status = DeployConfigStatus.NEED_RESTART
                if deploy.deploy_info.status == DeployStatus.STATUS_DEPLOYED and config_status != DeployConfigStatus.NEED_REDEPLOY:
                    config_status = DeployConfigStatus.UNCHNAGE
            break

        if config_status == DeployConfigStatus.NEED_REDEPLOY:
            for comp in set(COMPS_OB) & set(list(deploy.deploy_config.components.keys())):
                cluster_config = deploy.deploy_config.components[comp]
                default_config = cluster_config.get_global_conf_with_default()
                if default_config.get('production_mode', True):
                    diff_need_redeploy_keys = [f'`{key}`' for key in diff_need_redeploy_keys]
                    diff_need_redeploy_keys = list(set(diff_need_redeploy_keys))
                    self._call_stdio('error', err.EC_RUNNING_CLUSTER_NO_REDEPLOYED.format(key=', '.join(diff_need_redeploy_keys)))
                    return False

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

    def install_lib_for_repositories(self, need_libs):
        all_data = []
        temp_libs = need_libs
        while temp_libs:
            data = {}
            temp_map = {}
            libs = temp_libs
            temp_libs = []
            for lib in libs:
                repository = lib['repository']
                for requirement in lib['requirement']:
                    lib_name = requirement.name
                    if lib_name in data:
                        # To avoid remove one when require different version of same lib
                        temp_libs.append(lib)
                        continue
                    data[lib_name] = {
                        'version': requirement.version,
                        'min_version': requirement.min_version,
                        'max_version': requirement.max_version,
                    }
                    temp_map[lib_name] = repository
            all_data.append((data, temp_map))
        try:
            repositories_lib_map = {}
            for data, temp_map in all_data:
                with tempfile.NamedTemporaryFile(suffix=".yaml", mode='w') as tf:
                    yaml_loader = YamlLoader(self.stdio)
                    yaml_loader.dump(data, tf)
                    deploy_config = DeployConfig(tf.name, yaml_loader=yaml_loader, config_parser_manager=self.deploy_manager.config_parser_manager, stdio=self.stdio)
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
    def cluster_server_status_check(self, status=ClusterStatus.STATUS_RUNNING):
        if status not in [ClusterStatus.STATUS_RUNNING, ClusterStatus.STATUS_STOPPED]:
            self.stdio.error(err.EC_INVALID_PARAMETER.format('status', status))
            return False
        component_status = {}
        cluster_status = self.cluster_status_check(self.repositories, component_status)
        if cluster_status is False or cluster_status != status.value:
            self.stdio.error(err.EC_SOME_SERVER_STOPED.format())
            for repository in component_status:
                cluster_status = component_status[repository]
                for server in cluster_status:
                    if cluster_status[server] != status.value:
                        self. stdio.error('server status error: %s %s is not %s' % (server, repository.name, status.name))
            return False
        return True

    # If the cluster states are consistent, the status value is returned. Else False is returned.
    def cluster_status_check(self, repositories, ret_status=None):
        self._call_stdio('start_loading', 'Cluster status check')
        status_plugins = self.search_py_script_plugin(repositories, 'status')
        component_status = {}
        if ret_status is None:
            ret_status = {}
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

    def search_components_from_mirrors_and_install(self, deploy_config, components=None, raise_exception=True):
        # Check the best suitable mirror for the components
        errors = []
        self._call_stdio('verbose', 'Search best suitable repository')
        if components is None:
            components = deploy_config.components.keys()
        else:
            for component in components:
                if component not in deploy_config.components:
                    errors.append('No such component name: {} in cluster'.format(component))
        if not errors:
            pkgs, repositories, errors = self.search_components_from_mirrors(deploy_config, only_info=False, components=components)
        if errors:
            raise_exception and self._call_stdio('error', '\n'.join(errors))
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
        # reverse sort repositories by dependency, so that oceanbase will be the last one to proceed
        repositories = self.sort_repository_by_depend(repositories, deploy_config)
        repositories.reverse()

        for repository in repositories:
            ret = self.call_plugin(gen_config_plugins[repository], repository, generate_consistent_config=generate_consistent_config)
            if ret:
                component_num -= 1
        if component_num == 0 and deploy_config.dump():
            return True

        self.deploy_manager.remove_deploy_config(name)
        return False

    def export_to_ocp(self, name):
        # extract ocp info from options
        ocp_address = getattr(self.options, 'address', '')
        ocp_user = getattr(self.options, 'user', '')
        ocp_password = getattr(self.options, 'password', '')
        if ocp_address is None or ocp_address == '':
            self._call_stdio('error', 'address is required, pass it using -a or --address')
            return False
        if ocp_user is None or ocp_user == '':
            self._call_stdio('error', 'user is required, pass it using -u or --user')
            return False
        if ocp_password is None or ocp_password == '':
            self._call_stdio('error', 'password is required, pass it using -p or --password')
            return False
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

        deploy_config = deploy.deploy_config
        if "oceanbase-ce" not in deploy_config.components:
            self._call_stdio("error", "no oceanbase-ce in deployment %s" % name)
        cluster_config = deploy_config.components["oceanbase-ce"]
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)
        ssh_clients = self.get_clients(deploy_config, repositories)

        self._call_stdio('verbose', 'get plugins by mocking an ocp repository.')
        # search and get all related plugins using a mock ocp repository
        mock_ocp_repository = Repository("ocp-server-ce", "/")
        mock_ocp_repository.version = "4.2.1"
        repositories = [mock_ocp_repository]
        connect_plugin = self.plugin_manager.get_best_py_script_plugin('connect', mock_ocp_repository.name, mock_ocp_repository.version)
        takeover_precheck_plugins = self.search_py_script_plugin(repositories, "takeover_precheck")
        self._call_stdio('verbose', 'successfully get takeover precheck plugin.')
        takeover_plugins = self.search_py_script_plugin(repositories, "takeover")
        self._call_stdio('verbose', 'successfully get takeover plugin.')

        ret = self.call_plugin(connect_plugin, mock_ocp_repository, cluster_config=cluster_config,  clients=ssh_clients)
        if not ret or not ret.get_return('connect'):
            return False

        # do take over cluster by  call takeover precheck plugins
        self._call_stdio('print', 'precheck for export obcluster to ocp.')
        precheck_ret = self.call_plugin(takeover_precheck_plugins[mock_ocp_repository], mock_ocp_repository, cluster_config=cluster_config,  clients=ssh_clients)
        if not precheck_ret:
            return False
        else:
            # set version and component option
            ocp_version = precheck_ret.get_return("ocp_version")
            self.options._update_loose({"version": ocp_version, "components": "oceanbase-ce"})
        self._call_stdio('verbose', 'do takeover precheck by calling ocp finished')
        # check obcluster can be takeover by ocp
        check_ocp_result = self.check_for_ocp(name)
        if not check_ocp_result:
            self._call_stdio("error", "check obcluster to ocp takeover failed")
            return False
        self.set_deploy(None)
        self.set_repositories(None)
        takeover_ret = self.call_plugin(takeover_plugins[mock_ocp_repository], mock_ocp_repository, cluster_config=cluster_config, deploy_config=deploy_config, clients=ssh_clients)
        if not takeover_ret:
            return False
        else:
            task_id = takeover_ret.get_return("task_id")
            self._call_stdio("print", "takeover task successfully submitted to ocp, you can check task at %s/task/%d" % (ocp_address, task_id))
            return True

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
                component_num -= 1
                continue
            if repository not in ocp_check:
                component_num -= 1
                self._call_stdio('print', '%s No check plugin available.' % repository.name)
                continue

            cluster_config = deploy_config.components[repository.name]
            new_cluster_config = new_deploy_config.components[repository.name] if new_deploy_config else None
            if not self.call_plugin(connect_plugins[repository], repository):
                break

            if self.call_plugin(ocp_check[repository], repository, ocp_version=version, new_cluster_config=new_cluster_config, new_clients=new_ssh_clients):
                component_num -= 1
                self._call_stdio('print', '%s Check passed.' % repository.name)
        # search and install oceanbase-ce-utils, just log warning when failed since it can be installed after takeover
        repositories_utils_map = self.get_repositories_utils(repositories)
        if not repositories_utils_map:
            self._call_stdio('warn', 'Failed to get utils package')
        else:
            if not self.install_utils_to_servers(repositories, repositories_utils_map):
                self._call_stdio('warn', 'Failed to install utils to servers')
        return component_num == 0

    def sort_repository_by_depend(self, repositories, deploy_config):
        sorted_repositories = []
        sorted_components = {}
        while repositories:
            temp_repositories = []
            for repository in repositories:
                cluster_config = deploy_config.components.get(repository.name)
                for component_name in cluster_config.depends:
                    if component_name not in sorted_components:
                        temp_repositories.append(repository)
                        break
                else:
                    sorted_components[repository.name] = 1
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

    def _deploy_cluster(self, deploy, repositories, scale_out=False, dump=True):
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

        self._call_stdio('start_loading', 'Load param plugin')
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Generate password when password is None
        gen_config_plugins = self.search_py_script_plugin(repositories, 'generate_config')
        for repository in repositories:
            if repository in gen_config_plugins:
                self.call_plugin(gen_config_plugins[repository], repository, only_generate_password=True)

        # Parameter check
        self._call_stdio('start_loading', 'Parameter check')
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
            target_servers = deploy_config.get_added_servers(repository.name) if scale_out else None
            self._call_stdio('verbose', 'Exec %s init plugin' % repository)
            self._call_stdio('verbose', 'Apply %s for %s-%s' % (init_plugin, repository.name, repository.version))
            if self.call_plugin(init_plugin, repository, target_servers=target_servers):
                component_num -= 1
        if component_num != 0:
            return False

        # Install repository to servers
        if not self.install_repositories_to_servers(deploy_config, repositories, install_plugins):
            return False

        # Sync runtime dependencies
        if not self.sync_runtime_dependencies(deploy_config, repositories):
            return False

        if not dump:
            return True

        for repository in repositories:
            deploy.use_model(repository.name, repository, False)

        if deploy.update_deploy_status(DeployStatus.STATUS_DEPLOYED) and deploy_config.dump():
            self._call_stdio('print', '%s deployed' % deploy.name)
            return True
        return False

    def install_repository_to_servers(self, components, cluster_config, repository, ssh_clients, unuse_lib_repository=False):
        install_repo_plugin = self.plugin_manager.get_best_py_script_plugin('install_repo', 'general', '0.1')
        install_plugins = self.search_plugins([repository], PluginType.INSTALL)
        need_libs = []
        if not install_plugins:
            return False
        install_plugin = install_plugins[repository]
        check_file_map = install_plugin.file_map(repository)
        requirement_map = install_plugin.requirement_map(repository)
        ret = self.call_plugin(install_repo_plugin, repository, obd_home=self.home_path, install_repository=repository,
                               install_plugin=install_plugin, check_repository=repository,
                               check_file_map=check_file_map, requirement_map=requirement_map,
                               msg_lv='error' if unuse_lib_repository else 'warn')
        if not ret:
            return False
        elif ret.get_return('checked'):
            return True
        elif unuse_lib_repository:
            return False
        self._call_stdio('print', 'Try to get lib-repository')
        need_libs.append({
            'repository': repository,
            'requirement': ret.get_return('requirements')
        })
        repositories_lib_map = self.install_lib_for_repositories(need_libs)
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

    def install_repositories_to_servers(self, deploy_config, repositories, install_plugins):
        install_repo_plugin = self.plugin_manager.get_best_py_script_plugin('install_repo', 'general', '0.1')
        check_file_maps = {}
        need_lib_repositories = []
        need_libs = []
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            install_plugin = install_plugins[repository]
            check_file_map = check_file_maps[repository] = install_plugin.file_map(repository)

            requirement_map = install_plugin.requirement_map(repository)
            target_servers = cluster_config.added_servers if cluster_config.added_servers else None
            ret = self.call_plugin(install_repo_plugin, repository, obd_home=self.home_path, install_repository=repository,
                                   install_plugin=install_plugin, check_repository=repository, check_file_map=check_file_map,
                                   requirement_map = requirement_map,
                                   target_servers=target_servers,
                                   msg_lv='error' if deploy_config.unuse_lib_repository else 'warn')
            if not ret:
                return False
            if not ret.get_return('checked'):
                need_lib_repositories.append(repository)
                need_libs.append({
                    'repository': repository,
                    'requirement': ret.get_return('requirements')
                })

        if need_lib_repositories:
            if deploy_config.unuse_lib_repository:
                # self._call_stdio('print', 'You could try using -U to work around the problem')
                return False
            self._call_stdio('print', 'Try to get lib-repository')
            repositories_lib_map = self.install_lib_for_repositories(need_libs)
            if repositories_lib_map is False:
                self._call_stdio('error', 'Failed to install lib package for local')
                return False
            for need_lib_repository in need_lib_repositories:
                cluster_config = deploy_config.components[need_lib_repository.name]
                check_file_map = check_file_maps[need_lib_repository]
                lib_repository = repositories_lib_map[need_lib_repository]['repositories']
                install_plugin = repositories_lib_map[need_lib_repository]['install_plugin']
                requirement_map = install_plugins[need_lib_repository].requirement_map(need_lib_repository)
                target_servers = cluster_config.added_servers if cluster_config.added_servers else None
                ret = self.call_plugin(install_repo_plugin, need_lib_repository, obd_home=self.home_path, install_repository=lib_repository,
                                       install_plugin=install_plugin, check_repository=need_lib_repository, target_servers=target_servers,
                                       check_file_map=check_file_map, requirement_map=requirement_map, msg_lv='error')

                if not ret or not ret.get_return('checked'):
                    self._call_stdio('error', 'Failed to install lib package for cluster servers')
                    return False
        return True

    def sync_runtime_dependencies(self, deploy_config, repositories):
        rsync_plugin = self.plugin_manager.get_best_py_script_plugin('rsync', 'general', '0.1')
        ret = True
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            target_servers = cluster_config.added_servers if cluster_config.added_servers else None
            ret = self.call_plugin(rsync_plugin, repository, target_servers=target_servers) and ret
        return ret

    def scale_out(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        config_path = getattr(self.options, 'config', '')
        if not config_path:
            self._call_stdio('error', 'Additional config is required.')
            return False
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False

        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status not in [DeployStatus.STATUS_RUNNING]:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not scale out a %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
            return False

        if deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
            self._call_stdio('error', 'Deploy %s.%s' % (deploy_info.config_status.value, deploy.effect_tip()))
            return False

        all_repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(all_repositories)
        self.search_param_plugin_and_apply(all_repositories, deploy.deploy_config)
        if not self.cluster_server_status_check():
            self._call_stdio('error', 'Some of the servers in the cluster is not running')
            return False
        setattr(self.options, 'skip_cluster_status_check', True)

        deploy_config = deploy.deploy_config
        deploy_config.set_undumpable()
        if not deploy_config.scale_out(config_path):
            self._call_stdio('error', 'Failed to scale out %s' % name)
            return False

        components = deploy_config.changed_components
        self._call_stdio('start_loading', 'Get local repositories and plugins')
        repositories = self.get_component_repositories(deploy_info, components)
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # scale out check
        scale_out_check_plugins = self.search_py_script_plugin(all_repositories, 'scale_out_check', no_found_act='ignore')
        scale_out_plugins = self.search_py_script_plugin(repositories, 'scale_out', no_found_act='ignore')
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')

        check_pass = True
        for repository in all_repositories:
            if repository not in scale_out_check_plugins:
                continue
            if not self.call_plugin(scale_out_check_plugins[repository], repository):
                self._call_stdio('verbose', '%s scale out check failed.' % repository.name)
                check_pass = False
        if not check_pass:
            return False

        self._call_stdio('verbose', 'Start to deploy additional servers')
        if not self._deploy_cluster(deploy, repositories, scale_out=True, dump=False):
            return False
        deploy_config.enable_mem_mode()
        self._call_stdio('verbose', 'Start to start additional servers')
        if not self._start_cluster(deploy, repositories, scale_out=True):
            return False

        for repository in repositories:
            if repository not in scale_out_plugins:
                continue
            # get original servers
            pre_exist_server = list(filter(lambda x: x not in deploy_config.components[repository.name].added_servers, deploy_config.components[repository.name].servers))
            if not self.call_plugin(connect_plugins[repository], repository, target_servers=pre_exist_server):
                return False
            if not self.call_plugin(scale_out_plugins[repository], repository):
                return False

        succeed = True
        # prepare for added components
        for repository in all_repositories:
            if repository in scale_out_check_plugins:
                plugin_return = self.get_namespace(repository.name).get_return(scale_out_check_plugins[repository].name)
                plugins_list = plugin_return.get_return('plugins', [])
                self._call_stdio('verbose', '%s custom plugins: %s' % (repository.name, plugins_list))
                for plugin_name in plugins_list:
                    plugin =  self.search_py_script_plugin([repository], plugin_name)
                    if repository in plugin:
                        succeed = succeed and self.call_plugin(plugin[repository], repository)
        if not succeed:
            return False

        deploy_config.set_dumpable()
        if not deploy_config.dump():
            self._call_stdio('error', 'Failed to dump new deploy config')
            return False

        errors = []
        need_start = []
        need_reload = []
        for repository in all_repositories:
            namespace = self.get_namespace(repository.name)
            if repository not in scale_out_check_plugins:
                continue
            plugin_return = namespace.get_return(scale_out_check_plugins[repository].name)
            setattr(self.options, 'components', repository.name)
            if plugin_return.get_return('need_restart'):
                need_start.append(repository)
            if plugin_return.get_return('need_reload'):
                need_reload.append(repository)

        # todo: need_reload use need_start tips，supoort later
        if need_start or need_reload:
            self._call_stdio('print', 'Use `obd cluster restart %s --wp` to make changes take effect.' % name)

        if errors:
            self._call_stdio('warn', err.WC_FAIL_TO_RESTART_OR_RELOAD_AFTER_SCALE_OUT.format(detail='\n -'.join(errors)))
            return False

        self._call_stdio('print', FormatText.success('Execute ` obd cluster display %s ` to view the cluster status' % name))
        return True

    def add_components(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        config_path = getattr(self.options, 'config', '')
        if not config_path:
            self._call_stdio('error', 'Additional config is required.')
            return False
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status not in [DeployStatus.STATUS_RUNNING]:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not add components for a %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
            return False
        if deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
            self._call_stdio('error', 'Deploy %s.%s' % (deploy_info.config_status.value, deploy.effect_tip()))
            return False

        deploy_config = deploy.deploy_config
        self._call_stdio('start_loading', 'Get local repositories and plugins')
        current_repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(current_repositories)
        self.search_param_plugin_and_apply(current_repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        if not self.cluster_server_status_check():
            self._call_stdio('error', 'Some of the servers in the cluster is not running')
            return False
        setattr(self.options, 'skip_cluster_status_check', True)

        deploy_config.set_undumpable()
        if not deploy_config.add_components(config_path):
            self._call_stdio('error', 'Failed to add components for %s' % name)
            return False

        # search repositories for components to be added
        repositories, install_plugins = self.search_components_from_mirrors_and_install(deploy_config, components=deploy_config.added_components)
        if not repositories or not install_plugins:
            return False
        all_repositories = current_repositories + repositories
        self.set_repositories(all_repositories)
        self._call_stdio('start_loading', 'Get added repositories and plugins')
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # scale out check
        scale_out_check_plugins = self.search_py_script_plugin(all_repositories, 'scale_out_check', no_found_act='ignore')
        reload_plugins = self.search_py_script_plugin(all_repositories, 'reload')
        restart_plugins = self.search_py_script_plugin(all_repositories, 'restart')
        connect_plugins = self.search_py_script_plugin(all_repositories, 'connect')
        check_pass = True
        for repository in all_repositories:
            if repository not in scale_out_check_plugins:
                continue
            ret = self.call_plugin(scale_out_check_plugins[repository], repository)
            if not ret:
                self._call_stdio('verbose', '%s scale out check failed.' % repository.name)
                check_pass = False
        if not check_pass:
            return False

        succeed = True
        # prepare for added components
        for repository in all_repositories:
            if repository in scale_out_check_plugins:
                plugin_return = self.get_namespace(repository.name).get_return(scale_out_check_plugins[repository].name)
                plugins_list = plugin_return.get_return('plugins', [])
                for plugin_name in plugins_list:
                    plugin = self.search_py_script_plugin([repository], plugin_name)
                    if repository in plugin:
                        succeed = succeed and self.call_plugin(plugin[repository], repository)
        if not succeed:
            return False

        self._call_stdio('verbose', 'Start to deploy additional servers')
        if not self._deploy_cluster(deploy, repositories, dump=False):
            return False
        deploy_config.enable_mem_mode()
        self._call_stdio('verbose', 'Start to start additional servers')
        if not self._start_cluster(deploy, repositories):
            return False

        deploy_config.set_dumpable()
        for repository in repositories:
            deploy.use_model(repository.name, repository, False)
        if not deploy_config.dump():
            self._call_stdio('error', 'Failed to dump new deploy config')
            return False
        deploy.dump_deploy_info()

        errors = []
        need_start = []
        need_reload = []
        for repository in all_repositories:
            namespace = self.get_namespace(repository.name)
            if repository not in scale_out_check_plugins:
                continue
            plugin_return = namespace.get_return(scale_out_check_plugins[repository].name)
            setattr(self.options, 'components', repository.name)
            if plugin_return.get_return('need_restart'):
                need_start.append(repository)
            if plugin_return.get_return('need_reload'):
                need_reload.append(repository)

        # todo: need_reload use need_start tips，supoort later
        if need_start or need_reload:
            self._call_stdio('print', 'Use `obd cluster restart %s --wp` to make changes take effect.' % name)

        if errors:
            self._call_stdio('warn', err.WC_FAIL_TO_RESTART_OR_RELOAD.format(action='added', detail='\n -'.join(errors)))
            return False
        return True

    def delete_components(self, name, components):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False

        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status not in [DeployStatus.STATUS_RUNNING]:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not delete components for a %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
            return False

        if deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
            self._call_stdio('error', 'Deploy %s.%s' % (deploy_info.config_status.value, deploy.effect_tip()))
            return False

        if not components:
            self._call_stdio('error', 'Components is required.')
            return False

        deploy_config = deploy.deploy_config
        for component in components:
            if component not in deploy_config.components:
                self._call_stdio('error', 'Component {} is not in cluster'.format(component))
                return False
        deploy_config.set_undumpable()
        self._call_stdio('start_loading', 'Get local repositories and plugins')
        all_repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(all_repositories)
        repositories = self.get_component_repositories(deploy_info, components)
        self.search_param_plugin_and_apply(all_repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')
        force = getattr(self.options, 'force', False)

        if not self.cluster_server_status_check():
            if not force:
                self._call_stdio('error', 'Some of the servers in the cluster is not running; You can use `obd cluster component del %s %s -f`' % (name, ','.join(components)))
                return False

        self.get_clients_with_connect_servers(deploy_config, repositories, fail_exit=not force)
        self._call_stdio('start_loading', f"force del components({','.join(components)})")

        self.set_deploy(deploy)
        scale_in_check_plugins = self.search_py_script_plugin(all_repositories, 'scale_in_check', no_found_act='ignore')
        reload_plugins = self.search_py_script_plugin(all_repositories, 'reload')
        restart_plugins = self.search_py_script_plugin(all_repositories, 'restart')
        check_pass = True
        for repository in all_repositories:
            if repository not in scale_in_check_plugins:
                continue
            ret = self.call_plugin(scale_in_check_plugins[repository], repository)
            if not ret:
                self._call_stdio('verbose', '%s scale in check failed.' % repository.name)
                check_pass = False
        if not check_pass:
            return False

        if not deploy_config.del_components(components, dryrun=True):
            self._call_stdio('error', 'Failed to delete components for %s' % name)
            return False

        self._call_stdio('verbose', 'Start to stop target components')
        if not self._stop_cluster(deploy, repositories, dump=False):
            self._call_stdio('warn', 'failed to stop component {}'.format(','.join([r.name for r in repositories])))
            return False

        self._call_stdio('verbose', 'Start to destroy target components')
        if not self._destroy_cluster(deploy, repositories, dump=False):
            return False

        if not deploy_config.del_components(components):
            self._call_stdio('error', 'Failed to delete components for %s' % name)
            return False

        deploy_config.set_dumpable()
        for repository in repositories:
            deploy.unuse_model(repository.name, False)
        deploy.dump_deploy_info()

        if not deploy_config.dump():
            self._call_stdio('error', 'Failed to dump new deploy config')
            return False

        errors = []
        for repository in all_repositories:
            namespace = self.get_namespace(repository.name)
            if repository not in scale_in_check_plugins:
                continue
            plugin_return = namespace.get_return(scale_in_check_plugins[repository].name)
            setattr(self.options, 'components', repository.name)
            if plugin_return.get_return('need_restart'):
                setattr(self.options, 'display', None)
                if not self._restart_cluster(deploy, [repository]):
                    errors.append('failed to restart {}'.format(repository.name))
            elif plugin_return.get_return('need_reload'):
                if not self._reload_cluster(deploy, [repository]):
                    errors.append('failed to reload {}'.format(repository.name))
    
        if errors:
            self._call_stdio('warn', err.WC_FAIL_TO_RESTART_OR_RELOAD.format(action='removed', detail='\n -'.join(errors)))
            return False
        return True

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
        if deploy_info.config_status != DeployConfigStatus.UNCHNAGE and deploy_info.status != DeployStatus.STATUS_STOPPED and not getattr(self.options, 'without_parameter', False):
            self._call_stdio('error', 'Deploy %s.%s\nIf you still need to start the cluster, use the `obd cluster start %s --wop` option to start the cluster without loading parameters. ' % (deploy_info.config_status.value, deploy.effect_tip(), name))
            return False

        self._call_stdio('start_loading', 'Get local repositories')

        # Get the repository
        repositories = self.load_local_repositories(deploy_info, False)
        self.set_repositories(repositories)
        self._call_stdio('stop_loading', 'succeed')
        return self._start_cluster(deploy, repositories)

    def _start_cluster(self, deploy, repositories, scale_out=False):
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
            components = [repository.name for repository in repositories]

        servers = getattr(self.options, 'servers', '')
        server_list = servers.split(',') if servers else []

        self._call_stdio('start_loading', 'Search plugins')
        start_check_plugins = self.search_py_script_plugin(repositories, 'start_check', no_found_act='warn')
        create_tenant_plugins = self.search_py_script_plugin(repositories, 'create_tenant', no_found_act='ignore')
        tenant_optimize_plugins = self.search_py_script_plugin(repositories, 'tenant_optimize', no_found_act='ignore')
        start_plugins = self.search_py_script_plugin(repositories, 'start')
        connect_plugins = self.search_py_script_plugin(repositories, 'connect')
        bootstrap_plugins = self.search_py_script_plugin(repositories, 'bootstrap')
        display_plugins = self.search_py_script_plugin(repositories, 'display')
        self._call_stdio('stop_loading', 'succeed')

        self._call_stdio('start_loading', 'Load cluster param plugin')
        # Check whether the components have the parameter plugins and apply the plugins
        all_repositories = self.load_local_repositories(deploy_info)
        self.search_param_plugin_and_apply(all_repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Check the status for the deployed cluster
        if not getattr(self.options, 'skip_cluster_status_check', False):
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
        repositories_target_servers = {}
        start_repositories = []
        for repository in repositories:
            repository_dir_map[repository.name] = repository.repository_dir
            if repository.name not in components:
                continue
            if repository not in start_check_plugins:
                continue
            cluster_config = deploy_config.components[repository.name]
            cluster_servers = cluster_config.servers
            target_servers = None
            start_all = True
            if scale_out: 
                target_servers = cluster_config.added_servers
                start_all = False
            elif servers:
                target_servers = [srv for srv in cluster_servers if srv.ip in server_list or srv.name in server_list]
                start_all = len(target_servers) == len(cluster_servers)
                
            repositories_start_all[repository] = start_all
            repositories_target_servers[repository] = target_servers
            update_deploy_status = update_deploy_status and start_all
            if not cluster_config.servers:
                continue
            ret = self.call_plugin(start_check_plugins[repository], repository, strict_check=strict_check, target_servers=target_servers)
            if not ret:
                self._call_stdio('verbose', '%s starting check failed.' % repository.name)
                success = False
            start_repositories.append(repository)
        
        if success is False:
            # self._call_stdio('verbose', 'Starting check failed. Use --skip-check to skip the starting check. However, this may lead to a starting failure.')
            return False

        component_num = len(start_repositories)
        display_repositories = []
        for repository in start_repositories:
            start_all = repositories_start_all[repository]
            target_servers = repositories_target_servers[repository]
            ret = self.call_plugin(start_plugins[repository], repository, local_home_path=self.home_path, repository_dir_map=repository_dir_map, target_servers=target_servers)
            if ret:
                need_bootstrap = ret.get_return('need_bootstrap')
            else:
                self._call_stdio('error', '%s start failed' % repository.name)
                break
            if not self.call_plugin(connect_plugins[repository], repository, connect_all=scale_out, target_servers=target_servers):
                break

            if need_bootstrap and (start_all or scale_out):
                self._call_stdio('start_loading', 'Initialize %s' % repository.name)
                if not self.call_plugin(bootstrap_plugins[repository], repository, target_servers=target_servers):
                    self._call_stdio('stop_loading', 'fail')
                    self._call_stdio('error', 'Cluster init failed')
                    break
                self._call_stdio('stop_loading', 'succeed')
                if repository in create_tenant_plugins:
                    if self.get_namespace(repository.name).get_variable("create_tenant_options"):
                        if not self.call_plugin(create_tenant_plugins[repository], repository):
                            return False
                        if repository in tenant_optimize_plugins:
                            if not self.call_plugin(tenant_optimize_plugins[repository], repository):
                                return False
                    if deploy_config.auto_create_tenant:
                        create_tenant_options = [Values({"variables": "ob_tcp_invited_nodes='%'", "create_if_not_exists": True})]
                        if not self.call_plugin(create_tenant_plugins[repository], repository, create_tenant_options=create_tenant_options):
                            return False
                        if repository in tenant_optimize_plugins:
                            if not self.call_plugin(tenant_optimize_plugins[repository], repository):
                                return False

            if not start_all:
                component_num -= 1
                continue
            display_repositories.append(repository)
        
        for repository in display_repositories:
            if self.call_plugin(display_plugins[repository], repository):
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
        scenario_check_plugins = self.search_py_script_plugin(repositories, 'scenario_check', no_found_act='ignore')
        tenant_optimize_plugins = self.search_py_script_plugin(repositories, 'tenant_optimize', no_found_act='ignore')
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
            
        for repository in create_tenant_plugins:
            if repository in scenario_check_plugins:
                if not self.call_plugin(scenario_check_plugins[repository], repository):
                    return False

            if not self.call_plugin(connect_plugins[repository], repository):
                return False

            if not self.call_plugin(create_tenant_plugins[repository], repository):
                return False

            if repository in tenant_optimize_plugins:
                self.call_plugin(tenant_optimize_plugins[repository], repository)
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
            if not self.call_plugin(connect_plugins[repository], repository):
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

            if not self.call_plugin(drop_tenant_plugins[repository], repository):
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
            if not self.call_plugin(connect_plugins[repository], repository):
                return False
            if not self.call_plugin(list_tenant_plugins[repository], repository, name=name):
                return False
            
        for repository in print_standby_graph_plugins:
            if not self.call_plugin(print_standby_graph_plugins[repository], repository):
                self._call_stdio('error', 'print standby tenant graph error.')
                return False
        return True

    def tenant_optimize(self, deploy_name, tenant_name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(deploy_name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % deploy_name)
            return False

        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('print', 'Deploy "%s" is %s' % (deploy_name, deploy_info.status.value))
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
        scenario_check_plugins = self.search_py_script_plugin(repositories, 'scenario_check', no_found_act='ignore')
        tenant_optimize_plugins = self.search_py_script_plugin(repositories, 'tenant_optimize', no_found_act='ignore')
        if not tenant_optimize_plugins:
            self._call_stdio('error', 'The %s %s does not support tenant optimize' % (repositories[0].name, repositories[0].version))
            return False
        self._call_stdio('stop_loading', 'succeed')

        for repository in tenant_optimize_plugins:
            if repository in scenario_check_plugins:
                if not self.call_plugin(scenario_check_plugins[repository], repository):
                    return False

            if not self.call_plugin(connect_plugins[repository], repository):
                return False

            if not self.call_plugin(tenant_optimize_plugins[repository], repository, tenant_name=tenant_name):
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

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)

        return self._reload_cluster(deploy, repositories)

    def _reload_cluster(self, deploy, repositories):
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

            if not self.call_plugin(connect_plugins[repository], repository):
                if not self.call_plugin(connect_plugins[repository], repository, components=new_deploy_config.components.keys(), cluster_config=new_cluster_config):
                    continue

            if not self.call_plugin(reload_plugins[repository], repository, new_cluster_config=new_cluster_config):
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

            if not self.call_plugin(connect_plugins[repository], repository):
                continue
            self.call_plugin(display_plugins[repository], repository)

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

    def _stop_cluster(self, deploy, repositories, dump=True):
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
            components = [repository.name for repository in repositories]

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

            stop_all = cluster_servers == cluster_config.servers
            update_deploy_status = update_deploy_status and stop_all

            if self.call_plugin(stop_plugins[repository], repository):
                component_num -= 1
        
        if component_num == 0:
            if len(components) != len(repositories) or servers:
                self._call_stdio('print', "succeed")
                return True
            else:
                if not dump:
                    return True
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
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)
        return self._restart_cluster(deploy, repositories)

    def _restart_cluster(self, deploy, repositories):
        name = deploy.name
        deploy_info = deploy.deploy_info
        deploy_config = deploy.deploy_config
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

            ret = self.call_plugin(start_check_plugins[repository], repository, source_option='restart')
            if not ret:
                return False

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
                    display_plugin=display_plugins[repository] if getattr(self.options, 'display', True) else None,
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

        if need_confirm and not self._call_stdio('confirm', FormatText.warning('Are you sure to  destroy the "%s" cluster and rebuild it?' % name)):
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

    def destroy_cluster(self, name, need_confirm=False):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False
        if need_confirm and not self._call_stdio('confirm', FormatText.warning('Are you sure to destroy the "%s" cluster ?' % name)):
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

    def _destroy_cluster(self, deploy, repositories, dump=True):
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
        if not dump:
            return True
        self._call_stdio('verbose', 'Set %s deploy status to destroyed' % deploy.name)
        if deploy.update_deploy_status(DeployStatus.STATUS_DESTROYED):
            if deploy.deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
                deploy.apply_temp_deploy_config()
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
            if not self.install_repositories_to_servers(deploy_config, [dest_repository, ], install_plugins):
                return False
            sync_repositories = [dest_repository]
            repository = dest_repository

        # sync runtime dependencies
        if not self.sync_runtime_dependencies(deploy_config, sync_repositories):
            return False

        # start cluster if needed
        if need_restart and deploy_info.status == DeployStatus.STATUS_RUNNING:
            setattr(self.options, 'without_parameter', True)
            obd = self.fork(options=self.options)
            if not obd.call_plugin(start_plugins[current_repository], current_repository, home_path=self.home_path, is_reinstall=True) and getattr(self.options, 'force', False) is False:
                self.install_repositories_to_servers(deploy_config, [current_repository, ], install_plugins)
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

        if deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
            self._call_stdio('error', 'The current is config is modified. Deploy "%s" %s.' % (name, deploy_info.config_status.value))
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


            # do something before upgrade
            pre_deploy_config = deepcopy(deploy_config)
            cluster_config = pre_deploy_config.components[current_repository.name]
            upgrade_pre_plugins = self.search_py_script_plugin([dest_repository], 'upgrade_pre', no_found_act='ignore')
            if upgrade_pre_plugins and not self.call_plugin(upgrade_pre_plugins[dest_repository], dest_repository, cluster_config=cluster_config):
                return False

            self.search_param_plugin_and_apply([dest_repository], pre_deploy_config)
            start_check_plugins = self.search_py_script_plugin([dest_repository], 'start_check', no_found_act='ignore')
            if start_check_plugins and not self.call_plugin(start_check_plugins[dest_repository], dest_repository, cluster_config=cluster_config, source_option="upgrade"):
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
                if not self.call_plugin(connect_plugin, current_repository):
                    return False
                if not self.call_plugin(
                    upgrade_check_plugins[current_repository], current_repository,
                    current_repository=current_repository,
                    upgrade_repositories=upgrade_repositories,
                    route=route,
                ):
                    return False

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

        def signal_handler(sig, frame):
            deploy.update_upgrade_ctx(**upgrade_ctx)
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            raise KeyboardInterrupt

        signal.signal(signal.SIGINT, signal_handler)

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

    def create_repository(self, options=None):
        force = getattr(self.options, 'force', False)
        necessary = ['name', 'version', 'path']
        attrs = self.options.__dict__ if options is None else options
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
        info = PackageInfo(name=attrs['name'], version=attrs['version'], release=None, arch=None, md5=None, size=None)
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
            release = getattr(self.options, 'release', None)
            arch = getattr(self.options, 'arch', None)
            size = getattr(self.options, 'size', None)
            pkg = LocalPackage(repo_path, attrs['name'], attrs['version'], files, release, arch, size)
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
            self._call_stdio('print', '`{name}` deployment is not running. Please execute the command `obd cluster start {name}` to start the deployment first'.format(name=name))
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
            if deploy_info.status.value == DeployStatus.STATUS_DEPLOYED.value:
                self._call_stdio('print', '`{name}` deployment is not running. Please execute the command `obd cluster start {name}` to start the deployment first'.format(name=name))
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

        if not self.install_tool(TOOL_SYSBENCH):
            return False

        if not self.install_tool(COMP_OBCLIENT):
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
            if deploy_info.status.value == DeployStatus.STATUS_DEPLOYED.value:
                self._call_stdio('print', '`{name}` deployment is not running. Please execute the command `obd cluster start {name}` to start the deployment first'.format(name=name))
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

        if not self.install_tool(TOOL_TPCH):
            return False

        if not self.install_tool(COMP_OBCLIENT):
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
        if not (pkg and pkg > PackageInfo(component_name, version, pkg.release, pkg.arch, '', 0)):
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
            if deploy_info.status.value == DeployStatus.STATUS_DEPLOYED.value:
                self._call_stdio('print', '`{name}` deployment is not running. Please execute the command `obd cluster start {name}` to start the deployment first'.format(name=name))
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
            if deploy_info.status.value == DeployStatus.STATUS_DEPLOYED.value:
                self._call_stdio('print', '`{name}` deployment is not running. Please execute the command `obd cluster start {name}` to start the deployment first'.format(name=name))
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

        if not self.install_tool(TOOL_TPCC):
            return False

        if not self.install_tool(COMP_OBCLIENT):
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
        
        # Check whether obclient is avaliable
        ret = LocalClient.execute_command('%s --help' % opts.obclient_bin)
        if not ret:
            # install obclient
            tool_name = COMP_OBCLIENT
            if not self.tool_manager.is_tool_install(tool_name):
                if not self.install_tool(tool_name):
                    self._call_stdio('error', '%s is not an executable file. Please use `--obclient-bin` to set.\nYou may not have obclient installed' % opts.obclient_bin)
                    return
            tool = self.tool_manager.get_tool_config_by_name(tool_name)
            opts.obclient_bin = os.path.join(tool.config.path, 'bin/obclient')
            
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
        added_components = []
        config_path = getattr(opts, 'config', '')
        if config_path:
            deploy_config.set_undumpable()
            if not deploy_config.add_components(config_path, ignore_exist=True):
                self._call_stdio('error', 'Failed to add components configuration for %s' % name)
                return False
            added_components = deploy_config.added_components
        deploy_info = deploy.deploy_info

        if deploy_info.status in (DeployStatus.STATUS_DESTROYED, DeployStatus.STATUS_CONFIGURED):
            self._call_stdio('print', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        if added_components:
            repositories += self.get_local_repositories({key: value for key, value in deploy_config.components.items() if key in added_components})
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


    def obdiag_online_func(self, name, fuction_type, opts):
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
        if fuction_type.startswith("gather_obproxy") or fuction_type.startswith("analyze_obproxy"):
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
        if fuction_type in ['gather_plan_monitor']:
            setattr(opts, 'connect_cluster', True)

        diagnostic_component_name = COMP_OCEANBASE_DIAGNOSTIC_TOOL
        deployed = self.obdiag_deploy(fuction_type)
        tool = self.tool_manager.get_tool_config_by_name(diagnostic_component_name)
        if deployed and tool:
            generate_config_plugin = self.plugin_manager.get_best_py_script_plugin('generate_config', diagnostic_component_name, tool.config.version)
            self.call_plugin(generate_config_plugin, target_repository, deploy_config=deploy_config)
            self._call_stdio('generate_config', 'succeed')
            scene_config_plugin = self.plugin_manager.get_best_py_script_plugin('scene_config', diagnostic_component_name, tool.config.version)
            self.call_plugin(scene_config_plugin, target_repository)
            obdiag_plugin = self.plugin_manager.get_best_py_script_plugin(fuction_type, diagnostic_component_name, tool.config.version)
            return self.call_plugin(obdiag_plugin, target_repository)
        else:
            self._call_stdio('error', err.EC_OBDIAG_FUCYION_FAILED.format(fuction=fuction_type))
            return False


    def obdiag_offline_func(self, fuction_type, opts):
        tool_name = COMP_OCEANBASE_DIAGNOSTIC_TOOL
        pkg = self.mirror_manager.get_best_pkg(name=tool_name)
        if not pkg:
            self._call_stdio('critical', '%s package not found' % tool_name)
            return False
        repository = self.repository_manager.create_instance_repository(pkg.name, pkg.version, pkg.md5)
        deployed = self.obdiag_deploy(fuction_type)
        tool = self.tool_manager.get_tool_config_by_name(tool_name)
        if deployed and tool:
            scene_config_plugin = self.plugin_manager.get_best_py_script_plugin('scene_config', tool_name, repository.version)
            self.call_plugin(scene_config_plugin, repository, clients={})
            obdiag_plugin = self.plugin_manager.get_best_py_script_plugin(fuction_type, tool_name, repository.version)
            return self.call_plugin(obdiag_plugin, repository, clients={})
        else:
            self._call_stdio('error', err.EC_OBDIAG_FUCYION_FAILED.format(fuction=fuction_type))
            return False
        
    def obdiag_deploy(self, fuction_type):
        component_name = COMP_OCEANBASE_DIAGNOSTIC_TOOL
        # obdiag pre check
        pkg = self.mirror_manager.get_best_pkg(name=component_name)
        if not pkg:
            self._call_stdio('critical', '%s package not found' % component_name)
            return False
        repository = self.repository_manager.create_instance_repository(pkg.name, pkg.version, pkg.md5)
        pre_check_plugin = self.plugin_manager.get_best_py_script_plugin('pre_check', component_name, pkg.version)
        if not pre_check_plugin:
            self._call_stdio('info', '%s pre_check plugin not found' % component_name)
            return True
        obd = self.fork()
        obd.set_deploy(deploy=None)
        ret = obd.call_plugin(pre_check_plugin, repository, clients={})
        if not ret.get_return('checked'):
            self._call_stdio('error', 'Get the pre check return of the tool %s failed' % component_name)
            return False
        # obdiag install
        if not self.tool_manager.is_tool_install(component_name):
            return self.install_tool(component_name, force=True)
        else:
            # try to update obdiag to latest version
            tool = self.tool_manager.get_tool_config_by_name(component_name)
            obdiag_plugin = self.plugin_manager.get_best_py_script_plugin(fuction_type, component_name, tool.config.version)
            if not obdiag_plugin:
                self._call_stdio('warn', 'The obdiag version %s is not support command "obd obdiag %s", please update it' % (tool.config.version, fuction_type))
            if not self.update_tool(component_name):
                if not obdiag_plugin:
                    self._call_stdio('error', 'Update the obdiag version %s failed, please update it' % (tool.config.version))
                    return False
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
                    deploy_config = DeployConfig(tf.name, yaml_loader=yaml_loader, config_parser_manager=self.deploy_manager.config_parser_manager, stdio=self.stdio)
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
            requirement_map = install_plugin.requirement_map(repository)
            ret = self.call_plugin(install_repo_plugin, repository, obd_home=self.home_path, install_repository=utils_repository,
                        install_plugin=install_plugin, check_repository=repository, check_file_map=check_file_map,
                        requirement_map=requirement_map, msg_lv='error' if unuse_utils_repository else 'warn')
            if not ret:
                return False
        return True

    def clean_pkg(self, opts):
        filter_pkgs, filter_repositories = {}, {}
        if opts.type != PKG_REPO_FILE:
            downloaded_pkgs = self.mirror_manager.get_all_rpm_pkgs()
            if not downloaded_pkgs:
                self._call_stdio('print', 'There are no RPM files in the remote and local.')
            else:
                filter_pkgs = self.filter_pkgs(downloaded_pkgs, 'DELETE', hash=opts.hash, components=opts.components, max_version=True)
        if opts.type != PKG_RPM_FILE:
            repositories = self.repository_manager.get_repositories_view()
            if not repositories:
                self._call_stdio('print', 'There are no repositories.')
            else:
                filter_repositories = self.filter_pkgs(repositories, 'DELETE', hash=opts.hash, components=opts.components)
        delete_pkgs, cant_delete_pkgs = filter_pkgs.get('delete', []), filter_pkgs.get('cant_delete', [])
        delete_repositories, cant_delete_repositories = filter_repositories.get('delete', []), filter_repositories.get('cant_delete', [])
        if delete_pkgs + delete_repositories:
            self._call_stdio('print_list', delete_pkgs + delete_repositories, ['name', 'version', 'release', 'arch', 'md5', 'type'],
                lambda x: [x.name, x.version, x.release, x.arch, x.md5, PKG_REPO_FILE if isinstance(x, RepositoryVO) else PKG_RPM_FILE],
                title='Delete PKG Files List'
            )
        if cant_delete_pkgs + cant_delete_repositories:
            self._call_stdio('print_list', cant_delete_pkgs + cant_delete_repositories, ['name', 'version', 'release', 'arch', 'md5', 'type', 'reason'],
                lambda x: [x.name, x.version, x.release, x.arch, x.md5, PKG_REPO_FILE if isinstance(x, RepositoryVO) else PKG_RPM_FILE, x.reason],
                title='Can`t Delete PKG Files List'
            )
        if not delete_pkgs + delete_repositories:
            self._call_stdio('print', 'No Package need deleted')
            return False
        if not opts.confirm and not self._call_stdio('confirm', FormatText.warning('Are you sure to delete the files listed above ?')):
            return False
        if not self.mirror_manager.delete_pkgs(delete_pkgs) or not self.repository_manager.delete_repositories(delete_repositories):
            return False

        self.stdio.print("Delete the files listed above successful!")
        return True


    def print_tools(self, tools, title):
        if tools:
            self._call_stdio('print_list', tools, 
                ['Name', 'Arch', 'Version', 'Install Path', 'Install Size'], 
                lambda x: [x.name, x.config.arch, x.config.version, x.config.path, Capacity(x.config.size, 2).value], 
                title=title,
            )
        else:
            self._call_stdio('print', 'No tools have been installed')
    
    def list_tools(self):
        self._call_stdio('verbose', 'Get tool list')
        tools = self.tool_manager.get_tool_list()
        self.print_tools(tools, 'Tool List')
        return True
    
    def check_requirement(self, tool_name, repository, package, file_map, requirement_map, install_path):
        obd = self.fork()
        obd.set_deploy(deploy=None)
        if tool_name in TEST_TOOLS:
            check_requirement_plugin = self.plugin_manager.get_best_py_script_plugin('check_requirement', TEST_TOOLS[tool_name], package.version)
        else:
            check_requirement_plugin = self.plugin_manager.get_best_py_script_plugin('check_requirement', tool_name, package.version)
        if not check_requirement_plugin:
            self._call_stdio('verbose', '%s check_requirement plugin not found' % tool_name)
            return True
        ret = obd.call_plugin(check_requirement_plugin,
                repository,
                clients={},
                file_map = file_map,
                requirement_map = requirement_map)
        if not ret.get_return('checked'):
            for requirement in ret.get_return('requirements'):
                if not self.install_requirement(requirement.name, requirement.version, os.path.join(install_path, 'lib')):
                    self._call_stdio('error', 'Install the requirement %s failed' % requirement.name)
                    return False
        return True
    
    def install_requirement(self, tool_name, version, install_path):
        pkg = self.mirror_manager.get_best_pkg(name=tool_name, version=version)
        if not pkg:
            package_info = '%s-%s' % (tool_name, version) if version else tool_name
            self._call_stdio('critical', 'No such package: %s' % package_info)
            return False
        
        plugin = self.plugin_manager.get_best_plugin(PluginType.INSTALL, tool_name, pkg.version)
        if not plugin:
            self._call_stdio('critical', 'Not support requirement %s of version %s' % (tool_name, pkg.version))
            return False
        
        repository = self.repository_manager.create_instance_repository(pkg.name, pkg.version, pkg.md5)
        
        self._call_stdio('start_loading', 'Get local repositories and plugins')
        if not repository.load_pkg(pkg, plugin):
            self._call_stdio('error', 'Failed to extract file from %s' % pkg.path)
            return False
        self._call_stdio('stop_loading', 'succeed')
        
        self._call_stdio('start_loading', 'install requirement')
        if not self.tool_manager.install_requirement(repository, install_path):
            return False
        self._call_stdio('stop_loading', 'succeed')
        
        file_map = plugin.file_map(pkg)
        requirement_map = plugin.requirement_map(pkg)
        if file_map and requirement_map:
            if not self.check_requirement(tool_name, repository, pkg, file_map, requirement_map, install_path):
                self._call_stdio('critical', 'Check the requirement of tool %s failed' % tool_name)
                return False
        return True
        
    def _install_tool(self, tool_name, version, force, install_path):
        pkg = self.mirror_manager.get_best_pkg(name=tool_name, version=version, only_info=True)
        if not pkg:
            package_info = '%s-%s' % (tool_name, version) if version else tool_name
            self._call_stdio('critical', 'No such package: %s' % package_info)
            return False
        if tool_name in TEST_TOOLS:
            plugin = self.plugin_manager.get_best_plugin(PluginType.INSTALL, TEST_TOOLS[tool_name], pkg.version)
        else:
            plugin = self.plugin_manager.get_best_plugin(PluginType.INSTALL, tool_name, pkg.version)
        if not plugin:
            self._call_stdio('critical', 'Not support tool %s of version %s' % (tool_name, pkg.version))
            return False
        
        pkg = self.mirror_manager.get_best_pkg(name=tool_name, version=version)
        if not pkg:
            package_info = '%s-%s' % (tool_name, version) if version else tool_name
            self._call_stdio('critical', 'No such package: %s' % package_info)
            return False
        
        if not self._call_stdio('confirm', 'Found a avaiable version\n%s\nDo you want to use it?' % pkg):
            return False
            
        repository = self.repository_manager.create_instance_repository(pkg.name, pkg.version, pkg.md5)
        
        tool = self.tool_manager.create_tool_config(tool_name)
        
        self._call_stdio('start_loading', 'Get local repositories and plugins')
        if not repository.load_pkg(pkg, plugin):
            self._call_stdio('error', 'Failed to extract file from %s' % pkg.path)
            self.tool_manager.remove_tool_config(tool_name)
            return False
        self._call_stdio('stop_loading', 'succeed')
        
        self._call_stdio('start_loading', 'install tool')
        if not self.tool_manager.install_tool(tool, repository, install_path):
            self.tool_manager.remove_tool_config(tool_name)
            return False
        self._call_stdio('stop_loading', 'succeed')
        
        file_map = plugin.file_map(pkg)
        requirement_map = plugin.requirement_map(pkg)
        if file_map and requirement_map:
            if not self.check_requirement(tool_name, repository, pkg, file_map, requirement_map, install_path):
                self._call_stdio('critical', 'Check the requirement of tool %s failed' % tool_name)
                self.tool_manager.remove_tool_config(tool_name)
                return False
        if not tool.save_config(pkg.version, repository.hash, install_path):
            self._call_stdio('error', 'Failed to save tool config to %s' % tool.config_path)
            self.tool_manager.remove_tool_config(tool_name)
            return False
        return True
    
    def install_tool(self, tool_name, force=None, version=None, install_prefix=None):
        self._call_stdio('verbose', 'Try to install %s', tool_name)
        self._global_ex_lock()
        if not self.tool_manager.is_belong_tool(tool_name):
            self._call_stdio('error', 'The tool %s is not supported' % tool_name)
            self._call_stdio('print', 'The tool install only support %s' % self.tool_manager.get_support_tool_list())
            return False
        tool_name = self.tool_manager.get_tool_offical_name(tool_name)
        if not tool_name:
            return False
        
        if self.tool_manager.is_tool_install(tool_name):
            self._call_stdio('print', 'The tool %s is already installed' % tool_name)
            return True
        
        if not version:
            version = getattr(self.options, 'version', None)
        if not install_prefix:
            install_prefix = self.options.prefix \
                if getattr(self.options, 'prefix', None) is not None else os.getenv('HOME')
        force = self.options.force if getattr(self.options, 'force', None) is not None else force

        install_path = os.path.abspath(os.path.join(install_prefix, tool_name))
        
        if not self._install_tool(tool_name, version, force, install_path):
            self.tool_manager.remove_tool_config(tool_name)
            return False
        
        tool = self.tool_manager.get_tool_config_by_name(tool_name)
        self.print_tools([tool], 'Installed Tool')
        self._call_stdio('print', 'Install tool %s completely.', tool_name)
        
        return True
    
    def uninstall_tool(self, tool_name):
        self._call_stdio('verbose', 'Try to uninstall %s', tool_name)
        self._global_ex_lock()
        force = self.options.force if getattr(self.options, 'force', None) is not None else False
        
        if not self.tool_manager.is_belong_tool(tool_name):
            self._call_stdio('error', 'The tool %s is not supported' % tool_name)
            return False
        tool_name = self.tool_manager.get_tool_offical_name(tool_name)
        if not tool_name:
            return False
        tool = self.tool_manager.get_tool_config_by_name(tool_name)
        if not tool:
            self._call_stdio('error', 'The tool %s is not installed' % tool_name)
            return False
        
        self.print_tools([tool], 'Uninstall Tool')
        if not self._call_stdio('confirm', 'Uninstall tool %s\nIs this ok ' % tool_name):
            return False
        if not self.tool_manager.uninstall_tool(tool):
            self._call_stdio('error', 'Uninstall the tool %s failed' % tool_name)
            return False
        self.tool_manager.remove_tool_config(tool_name)
        self._call_stdio('print', 'Uninstall tool %s completely' % tool_name)
        return True

    def _update_tool(self, tool, version, force, install_path):
        pkg = self.mirror_manager.get_best_pkg(name=tool.name, version=version)
        if not pkg:
            package_info = '%s-%s' % (tool.name, version) if version else tool.name
            self._call_stdio('critical', 'No such package: %s' % package_info)
            return False
        
        plugin = self.plugin_manager.get_best_plugin(PluginType.INSTALL, tool.name, pkg.version)
        if not plugin:
            self._call_stdio('critical', 'Not support tool %s of version %s' % (tool.name, pkg.version))
            return False
        
        if self.tool_manager.check_if_avaliable_update(tool, pkg):
            if not self._call_stdio('confirm', 'Found a avaiable version\n%s\nDo you want to use it?' % pkg):
                return False
        else:
            self._call_stdio('print', 'The tool %s is already installed the latest version %s' % (tool.name, tool.config.version))
            return True
            
        repository = self.repository_manager.create_instance_repository(pkg.name, pkg.version, pkg.md5)
        
        self._call_stdio('start_loading', 'Get local repositories and plugins')
        if not repository.load_pkg(pkg, plugin):
            self._call_stdio('error', 'Failed to extract file from %s' % pkg.path)
            return False
        self._call_stdio('stop_loading', 'succeed')
        
        self._call_stdio('start_loading', 'install tool')
        if not self.tool_manager.update_tool(tool, repository, install_path):
            self.tool_manager.remove_tool_config(tool.name)
            return False
        self._call_stdio('stop_loading', 'succeed')
        
        file_map = plugin.file_map(pkg)
        requirement_map = plugin.requirement_map(pkg)
        if file_map and requirement_map:
            if not self.check_requirement(tool.name, repository, pkg, file_map, requirement_map, install_path):
                self._call_stdio('critical', 'Check the requirement of tool %s failed' % tool.name)
                return False
        if not tool.save_config(pkg.version, repository.hash, install_path):
            self._call_stdio('error', 'Failed to save tool config to %s' % tool.config_path)
            return False
        
        self.print_tools([tool], 'Updated tool')
        self._call_stdio('print', 'Update tool %s completely.', tool.name)
        return True

    def update_tool(self, tool_name, force=False, version=None, install_prefix=None):
        self._call_stdio('verbose', 'Try to update %s', tool_name)
        self._global_ex_lock()
        if not self.tool_manager.is_belong_tool(tool_name):
            self._call_stdio('error', 'The tool %s is not supported' % tool_name)
            self._call_stdio('print', 'The tool update only support %s' % self.tool_manager.get_support_tool_list())
            return False
        tool_name = self.tool_manager.get_tool_offical_name(tool_name)
        if not tool_name:
            return False
        tool = self.tool_manager.get_tool_config_by_name(tool_name)
        if not tool:
            self._call_stdio('error', 'The tool %s is not installed' % tool_name)
            return False
        if not version:
            version = getattr(self.options, 'version', None)
        if not install_prefix:
            previous_parent_path = os.path.dirname(tool.config.path) if tool.config.path else os.getenv('HOME')
            install_prefix = self.options.prefix \
                if getattr(self.options, 'prefix', None) is not None else previous_parent_path
        force = self.options.force if getattr(self.options, 'force', None) is not None else force
        
        install_path = os.path.abspath(os.path.join(install_prefix, tool_name))
        if not self._update_tool(tool, version, force, install_path):
            return False
        return True

    def takeover(self, name):
        host = getattr(self.options, 'host')
        mysql_port = getattr(self.options, 'mysql_port')
        root_password = getattr(self.options, 'root_password')
        ssh_user = getattr(self.options, 'ssh_user')
        ssh_password = getattr(self.options, 'ssh_password')
        ssh_key_file = getattr(self.options, 'ssh_key_file')
        ssh_port = getattr(self.options, 'ssh_port')
        ssh_timeout = getattr(self.options, 'ssh_timeout')

        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        if deploy:
            deploy_info = deploy.deploy_info
            if deploy_info.status not in [DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_DESTROYED]:
                self._call_stdio('error', 'The deployment {} has exited. Please modify the deploy name and take over again.'.format(name))
                return False

        self._call_stdio('verbose', 'get plugins by mocking an oceanbase repository.')
        # search and get all related plugins using a mock ocp repository
        mock_oceanbase_ce_repository = Repository("oceanbase-ce", "/")
        mock_oceanbase_ce_repository.version = "3.1.0"
        configs = OrderedDict()
        component_name = 'oceanbase-ce'
        global_config = {}
        configs[component_name] = {
            'servers': [host],
            'global': global_config
        }

        user = dict()
        if ssh_user:
            user['username'] = ssh_user
        if ssh_password:
            user['password'] = ssh_password
        if ssh_key_file:
            user['key_file'] = ssh_key_file
        if ssh_port:
            user['port'] = ssh_port
        if ssh_timeout:
            user['timeout'] = ssh_timeout
        if user:
            configs['user'] = user

        global_config['mysql_port'] = mysql_port
        global_config['root_password'] = root_password
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode='w') as tf:
            yaml_loader = YamlLoader()
            yaml_loader.dump(configs, tf)
            deploy_config = DeployConfig(
                tf.name, yaml_loader=YamlLoader(self.stdio),
                config_parser_manager=self.deploy_manager.config_parser_manager,
                inner_config=None,
                stdio=self.stdio
            )
            deploy_config.allow_include_error()
            connect_plugin = self.plugin_manager.get_best_py_script_plugin('connect', mock_oceanbase_ce_repository.name, mock_oceanbase_ce_repository.version)
            ssh_clients = self.get_clients(deploy_config, [mock_oceanbase_ce_repository])
            ret = self.call_plugin(connect_plugin, mock_oceanbase_ce_repository, cluster_config=deploy_config.components[component_name], clients=ssh_clients, stdio=self.stdio)
            if not ret or not ret.get_return('connect'):
                self._call_stdio('error', 'Failed to connect to OceanBase, Please check the database connection information.')
                return False
            cursor = ret.get_return('cursor')
            ret = cursor.fetchone('select version() as version', raise_exception=True)
            if ret is False:
                return False
            version = ret.get("version").split("-v")[-1]
            mock_oceanbase_ce_repository.version = version
            takeover_plugins = self.search_py_script_plugin([mock_oceanbase_ce_repository], "takeover")
            if not takeover_plugins:
                self._call_stdio('error', 'The current OceanBase version:%s does not support takeover, takeover plugin not found.' % version)
                return False
            # do take over cluster by call takeover precheck plugins
            prepare_ret = self.call_plugin(takeover_plugins[mock_oceanbase_ce_repository], mock_oceanbase_ce_repository,
                cursor=cursor,
                user_config=configs.get('user', None),
                name=name,
                clients=ssh_clients,
                obd_home=self.home_path,
                stdio=self.stdio)
            if not prepare_ret:
                return False
        try:
            self.deploy = self.deploy_manager.get_deploy_config(name)
            deploy_config = self.deploy.deploy_config
            cluster_config = deploy_config.components[component_name]
            version = cluster_config.version
            release = cluster_config.release
            repositories, _ = self.search_components_from_mirrors_and_install(deploy_config, raise_exception=False)
            repository = repositories[0] if repositories else None
            if not repository:
                self._call_stdio('verbose', 'Cannot find the image of oceanbase-ce version: %s, release: %s" ' % (version, release))
                ssh_clients = self.get_clients(deploy_config, [mock_oceanbase_ce_repository])
                tmp_dir = '{}/tmp_takeover'.format(self.deploy.config_dir)
                for server in cluster_config.servers:
                    ssh_client = ssh_clients[server]
                    server_config = cluster_config.get_server_conf(server)
                    home_path = server_config['home_path']
                    plugin = self.plugin_manager.get_best_plugin(PluginType.INSTALL, component_name, version)
                    if not plugin:
                        self._call_stdio('error', 'Cannot find the plugin for {}'.format(component_name))
                        return False
                    LocalClient.execute_command('rm -rf {}'.format(tmp_dir))
                    for file_map in plugin.file_map_data:
                        if file_map['type'] == 'bin':
                            self._call_stdio('start_loading', 'Get %s from %s' % (home_path, file_map['target_path']))
                            ret = ssh_client.get_file('{}/{}'.format(tmp_dir, file_map['target_path']), '{}/{}'.format(home_path, file_map['target_path']), stdio=self.stdio)
                            self._call_stdio('stop_loading', 'succeed')
                        elif file_map['type'] == 'dir':
                            ret = ssh_client.get_dir('{}/{}'.format(tmp_dir, file_map['target_path']), '{}/{}'.format(home_path, file_map['target_path']), stdio=self.stdio)
                        if not ret:
                            self._call_stdio('error', 'Cannot get the bin file from server: %s' % server)
                    break

                # create mirror by bin file
                self._call_stdio('start_loading', 'Create mirror')
                options = dict()
                options['name'] = component_name
                options['version'] = version
                options['path'] = tmp_dir
                options['force'] = True
                setattr(self.options, 'release', release)
                setattr(self.options, 'force', True)
                if not self.create_repository(options):
                    self._call_stdio('error', 'Failed to create mirror')
                    return False
                LocalClient.execute_command('rm -rf {}'.format(tmp_dir))
                self._call_stdio('stop_loading', 'succeed')
                repository = self.repository_manager.get_repository(component_name, version, release=release)

            self.repositories = [repository]
            self.deploy.deploy_info.components['oceanbase-ce']['md5'] = repository.md5
            self.deploy.deploy_info.status = DeployStatus.STATUS_RUNNING
            self.deploy.dump_deploy_info()
            display_plugins = self.search_py_script_plugin([repository], 'display')
            if not self.call_plugin(display_plugins[repository], repository):
                return False
            return True
        except:
            self.deploy_manager.remove_deploy_config(name)
            self._call_stdio('stop_loading', 'failed')
            self._call_stdio('error', 'Failed to takeover OceanBase cluster' )
            return False

    def filter_pkgs(self, pkgs, basic_condition, **pattern):
        ret_pkgs = {}
        if not pkgs:
            self.stdio.verbose("filter pkgs failed, pkgs is empty.")
            return ret_pkgs

        used_pkgs = []
        max_version_pkgs = []
        hash_hit_pkgs = []
        component_hit_pkgs = []
        # no pattern,default hit
        hit_pkgs = []

        # filter pkgs by DeployStatus
        for deploy in self.deploy_manager.get_deploy_configs():
            if deploy.deploy_info.status != DeployStatus.STATUS_DESTROYED:
                for component in deploy.deploy_config.components.values():
                    for pkg in pkgs:
                        if pkg.md5 == component.package_hash:
                            used_pkgs.append(pkg)
                            break

        # filter pkgs by pattern.hash
        if pattern.get('hash'):
            md5s = list(set(pattern['hash'].split(',')))
            for md5 in md5s:
                check_hash = False
                for pkg in pkgs:
                    if pkg.md5 == md5:
                        check_hash = True
                        hash_hit_pkgs.append(pkg)
                if not check_hash:
                    self.stdio.print("There is no RPM file with the hash value of %s." % md5)

        # filter pkgs by pattern.components
        if pattern.get("components"):
            components = list(set(pattern['components'].split(',')))
            for component in components:
                check_component_name = False
                for pkg in pkgs:
                    if pkg.name == component:
                        check_component_name = True
                        component_hit_pkgs.append(pkg)
                if not check_component_name:
                    self.stdio.print("There are no RPM files for the %s component." % check_component_name)

        # filter pkgs by pattern.max_version
        if pattern.get("max_version"):
            version_sorted_components_map = {}
            max_version_components_map = {}
            for pkg in pkgs:
                if pkg.name in version_sorted_components_map:
                    version_sorted_components_map[pkg.name].append(str(pkg.version))
                else:
                    version_sorted_components_map[pkg.name] = [str(pkg.version)]
            for component, versions in version_sorted_components_map.items():
                max_version_components_map[component] = sorted(versions).pop()
            for pkg in pkgs:
                if max_version_components_map.get(pkg.name) and pkg.version == max_version_components_map.get(pkg.name):
                    del max_version_components_map[pkg.name]
                    max_version_pkgs.append(pkg)

        # get all hit pkgs
        if not pattern.get('hash') and not pattern.get('components'):
            for pkg in pkgs:
                hit_pkgs.append(pkg)

        # filter libds pkgs and utils pkgs
        for pkg in pkgs:
            if pkg.name in ['oceanbase', 'oceanbase-ce'] and (pkg in hit_pkgs or pkg in hash_hit_pkgs or pkg in component_hit_pkgs):
                for sub_pkg in pkgs:
                    if (sub_pkg.name == '%s-libs' % pkg.name or sub_pkg.name == '%s-utils' % pkg.name) and sub_pkg.release == pkg.release:
                        if pkg in hit_pkgs:
                            hit_pkgs.append(sub_pkg)
                        if pkg in hash_hit_pkgs:
                            hash_hit_pkgs.append(sub_pkg)
                        if pkg in component_hit_pkgs:
                            component_hit_pkgs.append(sub_pkg)
                        if pkg in used_pkgs:
                            used_pkgs.append(sub_pkg)
                        if pkg in max_version_pkgs:
                            max_version_pkgs.append(sub_pkg)

        # filter the pkg that meets the deletion criteria.
        if basic_condition == 'DELETE':
            delete_pkgs = []
            cant_delete_pkgs = []
            for pkg in pkgs:
                if pkg in hit_pkgs or pkg in hash_hit_pkgs or pkg in component_hit_pkgs:
                    if pkg not in used_pkgs:
                        if pkg in hash_hit_pkgs or ((pkg in hit_pkgs or pkg in component_hit_pkgs) and pkg not in max_version_pkgs):
                            delete_pkgs.append(pkg)
                        elif pkg in max_version_pkgs and (pkg in hit_pkgs or pkg in component_hit_pkgs):
                            cant_delete_pkgs.append(pkg)
                    else:
                        if pkg in hash_hit_pkgs or pkg in hit_pkgs or pkg in component_hit_pkgs:
                            cant_delete_pkgs.append(pkg)

            for pkg in cant_delete_pkgs:
                if pkg in used_pkgs:
                    setattr(pkg, "reason", "in use")
                elif pkg in max_version_pkgs:
                    setattr(pkg, "reason", "the latest version")
                else:
                    setattr(pkg, "reason", "other reason")

            ret_pkgs = {'delete': delete_pkgs, 'cant_delete': cant_delete_pkgs}

        return ret_pkgs
