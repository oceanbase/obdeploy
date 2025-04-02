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

import getpass
import re
import os
import sys
import time
import signal
from optparse import Values
from copy import deepcopy, copy
from collections import defaultdict

import tempfile
from subprocess import call as subprocess_call

import const
import tool
from ssh import SshClient, SshConfig
from tool import FileUtil, DirectoryUtil, YamlLoader, timeout, COMMAND_ENV, OrderedDict
from _stdio import MsgLevel, FormatText
from _rpm import Version
from _mirror import MirrorRepositoryManager, PackageInfo, RemotePackageInfo
from _plugin import PluginManager, PluginType, InstallPlugin, PluginContextNamespace
from _deploy import DeployManager, DeployStatus, DeployConfig, DeployConfigStatus, Deploy, ClusterStatus
from _workflow import WorkflowManager, Workflows, SubWorkflowTemplate, SubWorkflows
from _tool import Tool, ToolManager
from _repository import RepositoryManager, LocalPackage, Repository, RepositoryVO
import _errno as err
from _lock import LockManager, LockMode
from _optimize import OptimizeManager
from _environ import ENV_REPO_INSTALL_MODE, ENV_BASE_DIR
from _types import Capacity
from const import COMP_OCEANBASE_DIAGNOSTIC_TOOL, COMP_OBCLIENT, PKG_RPM_FILE, TEST_TOOLS, COMPS_OB, COMPS_ODP, PKG_REPO_FILE, TOOL_TPCC, TOOL_TPCH, TOOL_SYSBENCH, COMP_OB_STANDALONE
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
        self._workflow_manager = None
        self._lock_manager = None
        self._optimize_manager = None
        self._tool_manager = None
        self._enable_encrypt = False
        self._encrypted_passkey = None
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
    def workflow_manager(self):
        if not self._workflow_manager:
            self._workflow_manager = WorkflowManager(self.home_path, self.dev_mode, self.stdio)
        return self._workflow_manager

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

    @property
    def enable_encrypt(self):
        if not self._enable_encrypt:
            self._enable_encrypt = COMMAND_ENV.get(const.ENCRYPT_PASSWORD) == '1'
        return self._enable_encrypt

    @property
    def encrypted_passkey(self):
        if not self._encrypted_passkey:
            self._encrypted_passkey = COMMAND_ENV.get(const.ENCRYPT_PASSKEY)
        return self._encrypted_passkey


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

    def get_workflows(self, workflow_name, repositories=None, no_found_act='exit', **component_kwargs):
        if not repositories:
            repositories = self.repositories
        workflows = Workflows(workflow_name)
        for repository in repositories:
            template = self.get_workflow(repository, workflow_name, repository.name, repository.version, no_found_act=no_found_act, component_kwargs=component_kwargs)
            if template:
                workflows[repository.name] = template
        return workflows

    def get_workflow(self, repository, workflow_name, component_name, version='0.1', no_found_act='exit', **component_kwargs):
        if no_found_act == 'exit':
            no_found_exit = True
        else:
            no_found_exit = False
            msg_lv = 'warn' if no_found_act == 'warn' else 'verbose'
        self._call_stdio('verbose', 'Searching %s template for components ...', workflow_name)
        template = self.workflow_manager.get_workflow_template(workflow_name, component_name, version)
        if template:
            ret = self.call_workflow_template(template, repository, **component_kwargs)
            if ret:
                self._call_stdio('verbose', 'Found for %s for %s-%s' % (template, template.component_name, template.version))
                return ret
        if no_found_exit:
            self._call_stdio('critical', 'No such %s template for %s-%s' % (workflow_name, component_name, version))
            exit(1)
        else:
            self._call_stdio(msg_lv, 'No such %s template for %s-%s' % (workflow_name, component_name, version))

    def run_workflow(self, workflows, sorted_components=[], repositories=[], repositories_map={}, no_found_act='exit', error_exit=True, **kwargs):
        if not sorted_components and self.deploy:
            sorted_components = self.deploy.deploy_config.sorted_components
        if not repositories_map:
            if self.repositories:
                repositories_map = {repository.name: repository for repository in self.repositories}
            for repository in repositories:
                repositories_map[repository.name] = repository
        if not repositories:
            repositories = self.repositories if self.repositories else []
        if not sorted_components:
            sorted_components = [repository.name for repository in repositories]

        for stages in workflows(sorted_components):
            if not self.hanlde_sub_workflows(stages, sorted_components, repositories, no_found_act=no_found_act, **kwargs):
                return False
            for component_name in stages:
                for template in stages[component_name]:
                    if isinstance(template, SubWorkflowTemplate):
                        continue
                    if component_name in kwargs:
                        template.kwargs.update(kwargs[component_name])
                    if not self.run_plugin_template(template, component_name, repositories_map, no_found_act=no_found_act) and error_exit:
                        return False
        return True

    def hanlde_sub_workflows(self, stages, sorted_components, repositories, no_found_act='exit', **kwargs):
        sub_workflows = SubWorkflows()
        for repository in repositories:
            component_name = repository.name
            if component_name not in stages:
                continue
            for template in stages[component_name]:
                if not isinstance(template, SubWorkflowTemplate):
                    continue
                if component_name in kwargs:
                    template.kwargs.update(kwargs[component_name])
                version = template.version if template.version else repository.version
                workflow = self.get_workflow(repository, template.name, template.component_name, version, no_found_act=no_found_act, **template.kwargs)
                if workflow:
                    workflow.set_global_kwargs(**template.kwargs)
                    sub_workflows.add(workflow)

        for workflows in sub_workflows:
            if not self.run_workflow(workflows, sorted_components, repositories, no_found_act=no_found_act, **kwargs):
                return False
        return True

    def run_plugin_template(self, plugin_template, component_name, repositories=None, no_found_act='exit', **kwargs):
        if 'repository' in plugin_template.kwargs:
            repository = plugin_template.kwargs['repository']
            del plugin_template.kwargs['repository']
        else:
            if plugin_template.component_name in repositories:
                repository = repositories[plugin_template.component_name]
            else:
                repository = repositories[component_name]
        if not plugin_template.version:
            if plugin_template.component_name in repositories:
                plugin_template.version = repositories[plugin_template.component_name].version
            else:
                plugin_template.version = repository.version
        plugin = self.search_py_script_plugin_by_template(plugin_template, no_found_act=no_found_act)
        plugin_template.kwargs.update(kwargs)
        if plugin and not self.call_plugin(plugin, repository, **plugin_template.kwargs):
            return False
        return True

    def _init_call_args(self, repository, spacename=None, target_servers=None, **kwargs):
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
            'target_servers': target_servers,
            'mirror_manager': self.mirror_manager,
            'repository_manager': self.repository_manager,
            'plugin_manager': self.plugin_manager,
            'deploy_manager': self.deploy_manager,
            'lock_manager': self.lock_manager,
            'optimize_manager': self.optimize_manager,
            'tool_manager': self.tool_manager,
            'config_encrypted': None
        }
        if self.deploy:
            args['deploy_name'] = self.deploy.name
            args['deploy_status'] = self.deploy.deploy_info.status
            args['components'] = self.deploy.deploy_config.components.keys()
            args['cluster_config'] = self.deploy.deploy_config.components[repository.name]
            if "clients" not in kwargs:
                args['clients'] = self.get_clients(self.deploy.deploy_config, self.repositories)
            if self.deploy.deploy_config.inner_config:
                args['config_encrypted'] = self.deploy.deploy_config.inner_config.get_global_config(const.ENCRYPT_PASSWORD) or False
        args['clients'] = args.get('clients', {})
        args.update(kwargs)
        return args

    def call_workflow_template(self, workflow_template, repository, spacename=None, target_servers=None, **kwargs):
        self._call_stdio('verbose', 'Call workflow %s for %s' % (workflow_template, repository))
        args = self._init_call_args(repository, spacename, target_servers, clients=None, **kwargs)
        return workflow_template(**args)

    def call_plugin(self, plugin, repository, spacename=None, target_servers=None, **kwargs):
        self._call_stdio('verbose', 'Call plugin %s for %s' % (plugin, repository))
        args = self._init_call_args(repository, spacename, target_servers, **kwargs)
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
        if not repositories:
            return errors
        workflows = self.get_workflows('get_generate_keys', repositories)
        if not self.run_workflow(workflows, repositories):
            return False
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            errors += cluster_config.check_param()[1]
            skip_keys = []
            if repository.name in COMPS_OB:
                ret = self.get_namespace(repository.name).get_return("generate_password")
            else:
                ret = self.get_namespace(repository.name).get_return("generate_config")
            if ret:
                skip_keys = ret.kwargs.get('generate_keys', [])
            for server in cluster_config.servers:
                self._call_stdio('verbose', '%s %s param check' % (server, repository))
                need_items = cluster_config.get_unconfigured_require_item(server, skip_keys=skip_keys)
                if need_items:
                    errors.append(str(err.EC_NEED_CONFIG.format(server=server, component=repository.name, miss_keys=','.join(need_items))))
        return errors

    def deploy_param_check_return_check_status(self, repositories, deploy_config):
        # parameter check
        param_check_status = {}
        check_pass = True
        workflows = self.get_workflows('get_generate_keys', repositories=repositories)
        component_kwargs = {repository.name: {"return_generate_keys": True, "clients": {}} for repository in repositories}
        self.run_workflow(workflows, repositories=repositories, **component_kwargs)
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            check_status = param_check_status[repository.name] = {}
            skip_keys = []
            ret = self.get_namespace(repository.name).get_return('get_generate_keys')
            if ret:
                if const.COMP_OB == repository.name:
                    skip_keys = self.get_namespace(repository.name).get_return('generate_password').kwargs.get('generate_keys', [])
                else:
                    skip_keys = self.get_namespace(repository.name).get_return('generate_config').kwargs.get('generate_keys', [])
            check_res = cluster_config.servers_check_param()
            for server in check_res:
                status = err.CheckStatus()
                errors = check_res[server].get('errors', [])
                self._call_stdio('verbose', '%s %s param check' % (server, repository))
                need_items = cluster_config.get_unconfigured_require_item(server, skip_keys=skip_keys)
                if need_items:
                    errors.append(err.EC_NEED_CONFIG.format(server=server, component=repository.name, miss_keys=','.join(need_items)).msg)
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

    def search_py_script_plugin_by_template(self, template, no_found_act='exit'):
        repository = self.repository_manager.get_repository_allow_shadow(template.component_name, template.version)
        plugins = self.search_py_script_plugin([repository], template.name, no_found_act=no_found_act)
        return plugins.get(repository)

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
        self._call_stdio('info', 'Search package for components...')
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
                if component_name in deploy.deploy_config.components and deploy_config.components[component_name].servers != deploy.deploy_config.components[component_name].servers:
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
            if self.enable_encrypt:
                try_time = 2
                while try_time > 0:
                    epk = self.input_encryption_passkey(double_check=False, print_error=True)
                    if epk:
                        if not self.check_encryption_passkey(epk):
                            self._call_stdio('error', 'Encryption passkey is not correct')
                            try_time -= 1
                            if try_time == 0:
                                return False
                        else:
                            break
                    else:
                        return False
            try:
                deploy.deploy_config.allow_include_error()
                if deploy.deploy_info.config_status == DeployConfigStatus.UNCHNAGE:
                    need_decrypt_deploy_config = deploy.deploy_config
                    path = deploy.deploy_config.yaml_path
                else:
                    path = Deploy.get_temp_deploy_yaml_path(deploy.config_dir)
                    need_decrypt_deploy_config = DeployConfig(path, yaml_loader=YamlLoader(self.stdio),
                                                              config_parser_manager=self.deploy_manager.config_parser_manager,
                                                              inner_config=deploy.deploy_config.inner_config if deploy else None,
                                                              stdio=self.stdio)
                if user_input:
                    initial_config = user_input
                else:
                    self._call_stdio('verbose', 'Load %s' % path)
                    if self.enable_encrypt:
                        need_decrypt_deploy_config.change_deploy_config_password(False)
                        need_decrypt_deploy_config.dump()
                    with open(path, 'r') as f:
                        initial_config = f.read()
                    if self.enable_encrypt:
                        need_decrypt_deploy_config.change_deploy_config_password(True)
                        need_decrypt_deploy_config.dump()
                        need_decrypt_deploy_config.change_deploy_config_password(False, False)
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

        EDITOR = os.environ.get('EDITOR', 'vi')
        self._call_stdio('verbose', 'Get environment variable EDITOR=%s' % EDITOR)
        self._call_stdio('verbose', 'Create tmp yaml file')
        tf = tempfile.NamedTemporaryFile(suffix=".yaml")
        tf.write(initial_config.encode())
        tf.flush()
        self.lock_manager.set_try_times(-1)
        config_status = DeployConfigStatus.UNCHNAGE
        diff_need_redeploy_keys = []
        add_component_names = []
        del_component_names = []
        chang_component_names = []
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
                    config_encrypted=False, stdio=self.stdio
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
                if is_server_list_change(deploy_config):
                    if not self._call_stdio('confirm', FormatText.warning('Modifications to the deployment architecture take effect after you redeploy the architecture. Are you sure that you want to start a redeployment? ')):
                        if user_input:
                            return False
                        continue
                    config_status = DeployConfigStatus.NEED_REDEPLOY
                if deploy_config.components.keys() != deploy.deploy_config.components.keys():
                    add_component_names = list(set(deploy_config.components.keys()) - set(deploy.deploy_config.components.keys()))
                    del_component_names = list(set(deploy.deploy_config.components.keys()) - set(deploy_config.components.keys()))
                    chang_component_names = add_component_names + del_component_names
                    if (add_component_names and del_component_names) or not deploy.deploy_config.del_components(del_component_names, dryrun=True):
                        if not self._call_stdio('confirm', FormatText.warning('Modifications to the deployment architecture take effect after you redeploy the architecture. Are you sure that you want to start a redeployment? ')):
                            if user_input:
                                return False
                            continue
                        config_status = DeployConfigStatus.NEED_REDEPLOY

                if config_status != DeployConfigStatus.NEED_REDEPLOY:
                    comp_attr_changed = False
                    for component_name in deploy_config.components:
                        if component_name in chang_component_names:
                            continue
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
                        if component_name in chang_component_names:
                            continue
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
                if component_name in chang_component_names:
                    continue
                deploy_config.components[component_name].update_temp_conf(param_plugins[component_name].params)

            self._call_stdio('stop_loading', 'succeed')

            # Parameter check
            self._call_stdio('start_loading', 'Parameter check')
            if del_component_names:
                for repository in repositories:
                    if repository.name in del_component_names:
                        repositories.remove(repository)
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
                        if component_name in chang_component_names:
                            continue
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
                    if component_name in chang_component_names:
                        continue
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

        if chang_component_names and config_status != DeployConfigStatus.UNCHNAGE:
            self._call_stdio('error', "While component updates are in progress, cluster configuration changes are not permitted.")
            return False

        self._call_stdio('verbose', 'Set deploy configuration status to %s' % config_status)
        self._call_stdio('verbose', 'Save new configuration yaml file')
        if config_status == DeployConfigStatus.UNCHNAGE:
            if not chang_component_names:
                new_deploy = self.deploy_manager.create_deploy_config(name, tf.name)
                ret = new_deploy.update_deploy_config_status(config_status)
                new_deploy.set_config_decrypted()
                new_deploy.deploy_config.enable_encrypt_dump()
                new_deploy.deploy_config.dump()
            else:
                if del_component_names:
                    if self._call_stdio('confirm', FormatText.warning('Detected component changes in the configuration file. Do you want to add or remove these components: %s ?' % ', '.join(del_component_names))):
                        self._call_stdio('print', FormatText.success('Please execute the command `obd cluster component del %s %s` to delete components' % (name, ' '.join(del_component_names))))
                        return True
                    else:
                        return False
                elif add_component_names:
                    if self._call_stdio('confirm', FormatText.warning('Detected component changes in the configuration file. Do you want to add or remove these components: %s ?' % ', '.join(add_component_names))):
                        add_deploy_config = {}
                        for comp in add_component_names:
                            add_deploy_config[comp] = deploy_config._src_data[comp]
                        add_tf = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False)
                        yaml = YamlLoader()
                        add_tf.write(yaml.dumps(add_deploy_config).encode())
                        add_tf.flush()
                        self._call_stdio('print', FormatText.success('Please execute the command `obd cluster component add %s -c %s` to add components' % (name, add_tf.name)))
                        return True
                    else:
                        return False
        else:
            target_src_path = Deploy.get_temp_deploy_yaml_path(deploy.config_dir)
            old_config_status = deploy.deploy_info.config_status
            try:
                if deploy.update_deploy_config_status(config_status):
                    FileUtil.copy(tf.name, target_src_path, self.stdio)
                    if self.enable_encrypt:
                        need_encrypt_deploy_config = DeployConfig(target_src_path, yaml_loader=YamlLoader(self.stdio),
                                                                  config_parser_manager=self.deploy_manager.config_parser_manager,
                                                                  inner_config=deploy.deploy_config.inner_config if deploy else None,
                                                                  config_encrypted=False, stdio=self.stdio)
                        need_encrypt_deploy_config.change_deploy_config_password(True, False)
                        need_encrypt_deploy_config.dump()
                ret = True
                if deploy:
                    if is_started or (config_status == DeployConfigStatus.NEED_REDEPLOY and is_deployed):
                        msg += str(FormatText.success(deploy.effect_tip()))
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
        status_workflows = self.get_workflows('status', repositories=repositories)
        self.run_workflow(status_workflows, repositories=repositories)
        component_status = {}
        if ret_status is None:
            ret_status = {}
        for repository in repositories:
            plugin_ret = self.get_namespace(repository.name).get_return('status')
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
        deploy.set_config_decrypted()

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

        if not  getattr(self.options, 'skip_param_check', False):
            # Parameter check
            errors = self.deploy_param_check(repositories, deploy_config)
            if errors:
                self._call_stdio('stop_loading', 'fail')
                self._call_stdio('error', '\n'.join(errors))
                return False

        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        generate_consistent_config = getattr(self.options, 'generate_consistent_config', False)
        # reverse sort repositories by dependency, so that oceanbase will be the last one to proceed
        repositories = self.sort_repository_by_depend(repositories, deploy_config)
        repositories.reverse()

        deploy_config.disable_encrypt_dump()
        kwargs = {}
        for repository in repositories:
            kwargs[repository.name] = {"generate_consistent_config": generate_consistent_config}
        workflows = self.get_workflows("generate_config")
        if not self.run_workflow(workflows, **kwargs):
            return False

        deploy_config.enable_encrypt_dump()
        deploy_config.set_config_unencrypted()
        if deploy_config.dump():
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
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False

        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('error', 'Deploy "%s" not RUNNING' % (name))
            return False

        deploy_config = deploy.deploy_config
        if const.COMP_OB_CE not in deploy_config.components and const.COMP_OB not in deploy_config.components and const.COMP_OB_STANDALONE not in deploy_config.components:
            self._call_stdio("error", "no oceanbase-ce in deployment %s" % name)

        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)
        ssh_clients = self.get_clients(deploy_config, repositories)

        # search and get all related plugins using a mock ocp repository
        self._call_stdio('verbose', 'get plugins by mocking an ocp repository.')
        if const.COMP_OCP_SERVER in deploy_config.components:
            mock_ocp_repository = Repository(const.COMP_OCP_SERVER, "/")
            if const.COMP_OB in deploy_config.components:
                cluster_config = deploy_config.components[const.COMP_OB]
            elif const.COMP_OB_STANDALONE in deploy_config.components:
                cluster_config = deploy_config.components[const.COMP_OB_STANDALONE]

        else:
            mock_ocp_repository = Repository(const.COMP_OCP_SERVER_CE, "/")
            cluster_config = deploy_config.components[const.COMP_OB_CE]
            # search and install oceanbase-ce-utils, just log warning when failed since it can be installed after takeover
            repositories_utils_map = self.get_repositories_utils(repositories)
            if not repositories_utils_map:
                self._call_stdio('warn', 'Failed to get utils package')
            else:
                if not self.install_utils_to_servers(repositories, repositories_utils_map):
                    self._call_stdio('warn', 'Failed to install utils to servers')

        mock_ocp_repository.version = "4.2.1"
        repositories.extend([mock_ocp_repository])
        self.set_deploy(None)
        workflow = self.get_workflows('take_over', repositories=[mock_ocp_repository] + self.repositories, no_found_act='ignore')
        if not self.run_workflow(workflow, deploy_config=deploy_config, repositories=[mock_ocp_repository] + self.repositories, no_found_act='ignore', **{mock_ocp_repository.name: {'cluster_config': cluster_config, 'clients': ssh_clients}}):
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

        self._call_stdio('start_loading', 'Get local repositories')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)
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
        component_name = ''
        for repository in repositories:
            if repository.name in const.COMPS_OB:
                component_name = repository.name

        workflow = self.get_workflows('ocp_check', no_found_act='ignore')
        if not self.run_workflow(workflow, no_found_act='ignore', **{component_name: {'ocp_version': version, 'new_deploy_config': new_deploy_config, 'new_clients': new_ssh_clients}}):
            return False
        self._call_stdio('print', '%s Check passed.' % component_name)

        # search and install oceanbase-ce-utils, just log warning when failed since it can be installed after takeover
        repositories_utils_map = self.get_repositories_utils(repositories)
        if not repositories_utils_map:
            self._call_stdio('warn', 'Failed to get utils package')
        else:
            if not self.install_utils_to_servers(repositories, repositories_utils_map):
                self._call_stdio('warn', 'Failed to install utils to servers')
        return True

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
        if self.enable_encrypt:
            deploy_config.change_deploy_config_password(True, False)
            deploy_config.disable_encrypt_dump()
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

    def demo(self, name='demo'):
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
        config_path = getattr(self.options, 'config', '')
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
            if config_path:
                deploy.set_config_decrypted()
                deploy.deploy_config.inner_config.update_global_config(const.ENCRYPT_PASSWORD, False)

        unuse_lib_repo = getattr(self.options, 'unuselibrepo', False)
        auto_create_tenant = getattr(self.options, 'auto_create_tenant', False)
        self._call_stdio('verbose', 'config path is None or not')
        if config_path:
            self._call_stdio('verbose', 'Create deploy by configuration path')
            deploy = self.deploy_manager.create_deploy_config(name, config_path)
            if not deploy:
                self._call_stdio('error', 'Failed to create deploy: %s. please check you configuration file' % name)
                return False
            deploy.set_config_decrypted()

        deploy.deploy_config.enable_encrypt_dump()
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

    def _deploy_cluster(self, deploy, repositories, dump=True):
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

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        deploy_config.disable_encrypt_dump()
        workflows = self.get_workflows('init')
        if not self.run_workflow(workflows):
            return False
        deploy_config.enable_encrypt_dump()

        # Parameter check
        self._call_stdio('start_loading', 'Parameter check')
        errors = self.deploy_param_check(repositories, deploy_config)
        if errors:
            self._call_stdio('stop_loading', 'fail')
            self._call_stdio('error', '\n'.join(errors))
            return False
        self._call_stdio('stop_loading', 'succeed')

        # Install repository to servers
        if not self.install_repositories_to_servers(deploy_config, repositories, install_plugins):
            return False

        # Sync runtime dependencies
        if not self.sync_runtime_dependencies(repositories):
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

    def sync_runtime_dependencies(self, repositories):
        workflows = self.get_workflows('rsync', repositories=repositories)
        return self.run_workflow(workflows, repositories=repositories)

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
        workflows = self.get_workflows('status_check')
        if not self.run_workflow(workflows):
            return False
        setattr(self.options, 'skip_cluster_status_check', True)

        deploy_config = deploy.deploy_config
        deploy_config.set_undumpable()
        if not deploy_config.scale_out(config_path):
            self._call_stdio('error', 'Failed to scale out %s' % name)
            return False

        components = deploy_config.changed_components
        self._call_stdio('start_loading', 'Get local repositories and plugins')
        repositories, install_plugins = self.search_components_from_mirrors_and_install(deploy_config, components=components)
        if not install_plugins:
            return False
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

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

        # Parameter check
        self._call_stdio('start_loading', 'Parameter check')
        errors = self.deploy_param_check(repositories, deploy_config)
        if errors:
            self._call_stdio('stop_loading', 'fail')
            self._call_stdio('error', '\n'.join(errors))
            return False
        self._call_stdio('stop_loading', 'succeed')

        workflows = self.get_workflows('scale_out_pre', no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
            return False

        # Install repository to servers
        if not self.install_repositories_to_servers(deploy_config, repositories, install_plugins):
            return False

        # Sync runtime dependencies
        if not self.sync_runtime_dependencies(repositories):
            return False

        setattr(self.options, 'force', True)
        deploy_config.enable_mem_mode()
        workflows = self.get_workflows('scale_out', repositories=repositories, no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
            return False

        deploy_config.set_dumpable()
        if not deploy_config.dump():
            self._call_stdio('error', 'Failed to dump new deploy config')
            return False

        self._call_stdio('print', FormatText.success('Execute ` obd cluster display %s ` to view the cluster status' % name))
        return True

    def add_components(self, name, need_confirm=False):
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

        workflows = self.get_workflows('status_check')
        if not self.run_workflow(workflows):
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

        oceanbase_repo = None
        current_obproxy_repo = None
        for repository in current_repositories:
            if repository.name in const.COMPS_OB:
                oceanbase_repo = repository
            elif repository.name in const.COMPS_ODP:
                current_obproxy_repo = repository

        need_restart_obproxy = False
        add_component_pre_repositories = deepcopy(repositories)
        if oceanbase_repo:
            add_component_pre_repositories.append(oceanbase_repo)
        if const.COMP_OB_CONFIGSERVER in [repo.name for repo in repositories] and current_obproxy_repo:
            add_component_pre_repositories.append(current_obproxy_repo)
            need_restart_obproxy = True

        workflows = self.get_workflows('add_component_pre', repositories=add_component_pre_repositories, no_found_act='ignore')
        if not self.run_workflow(workflows, repositories=add_component_pre_repositories):
            return False

        # Install repository to servers
        if not self.install_repositories_to_servers(deploy_config, repositories, install_plugins):
            return False

        # Sync runtime dependencies
        if not self.sync_runtime_dependencies(repositories):
            return False

        deploy_config.enable_mem_mode()

        workflows = self.get_workflows('add_component', repositories=repositories + [oceanbase_repo] if oceanbase_repo else repositories, no_found_act='ignore')
        if not self.run_workflow(workflows, repositories=repositories + [oceanbase_repo] if oceanbase_repo else repositories):
            return False

        deploy_config.set_dumpable()
        for repository in repositories:
            deploy.use_model(repository.name, repository, False)
        if not deploy_config.dump():
            self._call_stdio('error', 'Failed to dump new deploy config')
            return False
        deploy.dump_deploy_info()
        restart_components_str = ''
        if need_restart_obproxy:
            restart_components_str = current_obproxy_repo.name
            if oceanbase_repo:
                restart_components_str += ',' + oceanbase_repo.name
        if not need_confirm or (need_restart_obproxy and self._call_stdio('read', FormatText.warning('Restart `%s` for %s to take effect. You can do it manually later or enter `restart` now: ' % (restart_components_str, name)), blocked=True).strip() == 'restart'):
            self._call_stdio('print', '\nRestart %s' % name)
            setattr(self.options, 'components', '%s' % restart_components_str)
            if not self.restart_cluster(name):
                self._call_stdio('warn', '%s restart failed. Please execute `obd cluster restart %s` to retry.' % (name, name))
        self._call_stdio('print', FormatText.success('Execute ` obd cluster display %s ` to view the cluster status' % name))
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
        workflows = self.get_workflows('delete_component_pre', repositories=repositories, no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
            return False

        if not deploy_config.del_components(components, dryrun=True):
            self._call_stdio('error', 'Failed to delete components for %s' % name)
            return False

        workflows = self.get_workflows('delete_component', repositories=repositories, no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
            return False

        if not deploy_config.del_components(components):
            self._call_stdio('error', 'Failed to delete components for %s' % name)
            return False

        self._call_stdio('stop_loading', 'succeed')

        deploy_config.set_dumpable()
        for repository in repositories:
            deploy.unuse_model(repository.name, False)
        deploy.dump_deploy_info()

        if not deploy_config.dump():
            self._call_stdio('error', 'Failed to dump new deploy config')
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
        sort_components = deploy.deploy_config.sorted_components
        if components:
            components = components.split(',')
            for component in components:
                if component not in deploy_info.components:
                    self._call_stdio('error', 'No such component: %s' % component)
                    return False
            if len(components) != len(deploy_info.components):
                update_deploy_status = False
            sort_components_map = {value: index for index, value in enumerate(sort_components)}
            components = sorted(components, key=lambda x: sort_components_map[x])
        else:
            components = sort_components

        servers = getattr(self.options, 'servers', '')
        server_list = servers.split(',') if servers else []

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

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        start_check_workflows = self.get_workflows('start_check')
        if not self.run_workflow(start_check_workflows, sorted_components=components):
            ob_repository = None
            for repository in all_repositories:
                if repository.name in const.COMPS_OB:
                    ob_repository = repository
                    break
            if ob_repository:
                finally_check_plugin_name = [value for value in start_check_workflows.workflows.get(ob_repository.name).stage.values()][-1][-1].name
                if self.get_namespace(ob_repository.name).get_return(finally_check_plugin_name).get_return('system_env_error'):
                    self._call_stdio('print', FormatText.success('You can use the `obd cluster init4env {name}` command to automatically configure system parameters'.format(name=name)))
            return False

        start_args = {}
        for repo in repositories:
            if repo.name in COMPS_OB:
                start_args[repo.name] = {}
                start_args[repo.name]["install_utils_to_servers"] = self.install_utils_to_servers
                start_args[repo.name]["get_repositories_utils"] = self.get_repositories_utils
        start_workflows = self.get_workflows('start', **{'new_clients': ssh_clients})
        if not self.run_workflow(start_workflows, sorted_components=components, **start_args):
            return False
        display_encrypt_password = None
        if self.enable_encrypt:
            display_encrypt_password = '******'
        components_kwargs = {}
        for repository in repositories:
            components_kwargs[repository.name] = {"display_encrypt_password": display_encrypt_password}
        display_workflows = self.get_workflows('display')
        if not self.run_workflow(display_workflows, sorted_components=components, **components_kwargs):
            return False

        if update_deploy_status:
            self._call_stdio('verbose', 'Set %s deploy status to running' % name)
            if deploy.update_deploy_status(DeployStatus.STATUS_RUNNING) and deploy.deploy_config.dump():
                self._call_stdio('print', '%s running' % name)
                return True
        else:
            self._call_stdio('print', "succeed")
            return True
        return True

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

        self._call_stdio('start_loading', 'Get local repositories')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        workflows = self.get_workflows('create_tenant', no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
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

        # version check
        primary_repositories = self.get_component_repositories(primary_deploy.deploy_info, const.COMPS_OB)
        standby_repositories = self.get_component_repositories(standby_deploy.deploy_info, const.COMPS_OB)
        for repo in primary_repositories + standby_repositories:
            if repo.version < Version('4.2.0.0'):
                self._call_stdio('error', 'Oceanbase must be version 4.2.0.0 or higher.')
                return False
        primary_repositories_name_list = [str(repository.version) for repository in primary_repositories]
        standby_repositories_name_list = [str(repository.version) for repository in standby_repositories]
        if list(set(primary_repositories_name_list)) != list(set(standby_repositories_name_list)):
            self._call_stdio('error', 'Version not match. standby version: {} , primary version: {}.'.format(standby_repositories_name_list[0], primary_repositories_name_list[0]))
            return False
        self.set_repositories(standby_repositories)

        workflows = self.get_workflows('create_standby_tenant', no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
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
        standby_repositories = self.get_component_repositories(deploy.deploy_info, const.COMPS_OB)
        self.set_repositories(standby_repositories)
        setattr(self.options, 'tenant_name', tenant_name)

        workflows = self.get_workflows('switchover_tenant', no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
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
        standby_repositories = self.get_component_repositories(deploy.deploy_info, const.COMPS_OB)
        self.set_repositories(standby_repositories)
        setattr(self.options, 'tenant_name', tenant_name)
        workflows = self.get_workflows('failover_decouple_tenant', no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
            return False
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

        self._call_stdio('start_loading', 'Get local repositories')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
        workflows = self.get_workflows('drop_tenant', no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
            return False
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

        self._call_stdio('start_loading', 'Get local repositories')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        workflows = self.get_workflows('list_tenant', no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
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

        tenant_optimize_plugins = self.search_py_script_plugin(repositories, 'tenant_optimize', no_found_act='ignore')
        if not tenant_optimize_plugins:
            self._call_stdio('error', 'The %s %s does not support tenant optimize' % (repositories[0].name, repositories[0].version))
            return False
        self._call_stdio('stop_loading', 'succeed')
        setattr(self.options, 'tenant_name', tenant_name)
        workflows = self.get_workflows('tenant_optimize', no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
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
        self._call_stdio('stop_loading', 'succeed')
        return self._reload_cluster(deploy, repositories)

    def _reload_cluster(self, deploy, repositories):
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

        self._call_stdio('stop_loading', 'succeed')

        self._call_stdio('start_loading', 'Load cluster param plugin')
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self.search_param_plugin_and_apply(repositories, new_deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)

        # Check the status for the deployed cluster
        workflows = self.get_workflows("status_check")
        if not self.run_workflow(workflows):
            sub_io = None
            if getattr(self.stdio, 'sub_io'):
                sub_io = self.stdio.sub_io(msg_lv=MsgLevel.ERROR)
            obd = self.fork(options=Values({'without_parameter': True}), stdio=sub_io)
            if not obd._start_cluster(deploy, repositories):
                if self.stdio:
                    self._call_stdio('error', err.EC_SOME_SERVER_STOPED.format())
                return False
        reload_args = {}
        for repo in repositories:
            reload_args[repo.name] = {"new_cluster_config": new_deploy_config.components[repo.name], "retry_times": 30}
            if repo.name in COMPS_OB:
                reload_args[repo.name]["install_utils_to_servers"] = self.install_utils_to_servers
                reload_args[repo.name]["get_repositories_utils"] = self.get_repositories_utils
        workflows = self.get_workflows('reload')
        if not self.run_workflow(workflows, **reload_args):
            deploy_config.dump()
            self._call_stdio('warn', 'Some configuration items reload failed')
            return False

        if deploy.apply_temp_deploy_config():
            self._call_stdio('print', '%s reload' % deploy.name)
            return True
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
            
        self._call_stdio('stop_loading', 'succeed')

        display_encrypt_password = None
        if self.enable_encrypt:
            epk = getattr(self.options, 'encryption_passkey')
            if epk:
                if not self.check_encryption_passkey(epk):
                    self._call_stdio('error', 'Encryption passkey is not correct')
                    return False
            else:
                display_encrypt_password = '******'

        components_kwargs = {}
        for repository in repositories:
            components_kwargs[repository.name] = {"display_encrypt_password": display_encrypt_password}
        # Get the client
        self.get_clients(deploy_config, repositories)
        workflows = self.get_workflows('display')
        return self.run_workflow(workflows, **components_kwargs)
        
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

        components = getattr(self.options, 'components', '')
        sort_components = deploy.deploy_config.sorted_components
        if components:
            components = components.split(',')
            dump = False
            for component in components:
                if component not in deploy_info.components:
                    self._call_stdio('error', 'No such component: %s' % component)
                    return False
            sort_components_map = {value: index for index, value in enumerate(sort_components)}
            components = sorted(components, key=lambda x: sort_components_map[x])
        else:
            components = sort_components

        servers = getattr(self.options, 'servers', '')
        server_list = servers.split(',') if servers else []
        for repository in repositories:
            if repository.name not in components:
                continue
            cluster_config = deploy_config.components[repository.name]
            cluster_servers = cluster_config.servers
            if servers:
                dump = False
                cluster_config.servers = [srv for srv in cluster_servers if srv.ip in server_list or srv.name in server_list]

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        repositories = self.sort_repository_by_depend(repositories, deploy_config)
        self.set_repositories(repositories)

        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        # Get the client
        ssh_clients = self.get_clients(deploy_config, repositories)
        workflows = self.get_workflows('stop')
        if not self.run_workflow(workflows, sorted_components=components):
            return False

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
        status = [DeployStatus.STATUS_STOPPED, DeployStatus.STATUS_RUNNING]
        if deploy_info.status not in status:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not restart an %s cluster.' % (name, deploy_info.status.value, deploy_info.status.value))
            return False
        
        if deploy_info.config_status == DeployConfigStatus.NEED_REDEPLOY:
            self._call_stdio('error', 'Deploy needs redeploy')
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

        self._call_stdio('stop_loading', 'succeed')

        self._call_stdio('start_loading', 'Load cluster param plugin')
        # Check whether the components have the parameter plugins and apply the plugins
        self.search_param_plugin_and_apply(repositories, deploy_config)
        if getattr(self.options, 'without_parameter', False) is False and deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
            apply_change = True
            new_deploy_config = deploy.temp_deploy_config
            self.search_param_plugin_and_apply(repositories, new_deploy_config)
        else:
            new_deploy_config = None
            apply_change = False

        self._call_stdio('stop_loading', 'succeed')

        update_deploy_status = True
        target_restart_components = getattr(self.options, 'components', '')
        if target_restart_components:
            target_restart_components = target_restart_components.split(',')
            for component in target_restart_components:
                if component not in deploy_info.components:
                    self._call_stdio('error', 'No such component: %s' % component)
                    return False
            if len(target_restart_components) != len(deploy_info.components):
                if apply_change:
                    self._call_stdio('error', 'Configurations are changed and must be applied to all components and servers.')
                    return False
                update_deploy_status = False
        else:
            target_restart_components = deploy_info.components.keys()

        servers = getattr(self.options, 'servers', '')
        if servers:
            server_list = servers.split(',')
            if apply_change:
                for repository in repositories:
                    cluster_config = deploy_config.components[repository.name]
                    for server in cluster_config.servers:
                        if server.name not in server_list:
                            self._call_stdio('error','Configurations are changed and must be applied to all components and servers.')
                            return False
        else:
            server_list = []

        # Get the client
        self.get_clients(deploy_config, repositories)
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
            deploy_config.change_deploy_config_password(False, False)

        need_restart_repositories = []
        component_num = len(target_restart_components)
        repositories = self.sort_repositories_by_depends(deploy_config, repositories)
        self.set_repositories(repositories)
        repository_dir_map = {}
        for repository in repositories:
            repository_dir_map[repository.name] = repository.repository_dir
        for repository in repositories:
            if repository.name not in target_restart_components:
                continue
            cluster_config = deploy_config.components[repository.name]
            if apply_change is False:
                cluster_servers = cluster_config.servers
                if servers:
                    cluster_config.servers = [srv for srv in cluster_servers if srv.ip in server_list or srv.name in server_list]
                if not cluster_config.servers:
                    component_num -= 1
                    continue

                start_all = cluster_servers == cluster_config.servers
                update_deploy_status = update_deploy_status and start_all
            need_restart_repositories.append(repository)

        restart_pre_workflows = self.get_workflows('restart_pre', need_restart_repositories)
        component_kwargs = {component: {"local_home_path": self.home_path, "repository_dir_map": repository_dir_map,
                                        "new_deploy_config": new_deploy_config, "new_clients": new_ssh_clients} for
                            component in target_restart_components}
        if not self.run_workflow(restart_pre_workflows, **component_kwargs):
            return False

        restart_workflows = self.get_workflows('restart', need_restart_repositories)
        component_kwargs = {component: {"local_home_path": self.home_path, "repository_dir_map": repository_dir_map, "new_deploy_config": new_deploy_config, "new_clients": new_ssh_clients} for component in target_restart_components}

        if not self.run_workflow(restart_workflows, no_found_act='no_exit', **component_kwargs):
            if new_ssh_clients:
                done_repositories = []
                for repository in need_restart_repositories:
                    if self.get_namespace(repository).get_return('chown_dir'):
                        done_repositories.append(done_repositories)
                if done_repositories:
                    self._call_stdio('start_loading', 'Rollback')
                    rollback_workflows = self.get_workflows('rollback', done_repositories)
                    if self.run_workflow(rollback_workflows, repositories=done_repositories):
                        self._call_stdio('stop_loading', 'succeed')
            return False

        if len(target_restart_components) != len(repositories) or servers:
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
        deploy_config.disable_encrypt_dump()
        self._call_stdio('start_loading', 'Get local repositories')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        self.set_repositories(repositories)
        self._call_stdio('stop_loading', 'succeed')

        workflows = self.get_workflows('standby_check', no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
            return False

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
        deploy_config.enable_encrypt_dump()
        if not self._deploy_cluster(deploy, repositories):
            return False
        if self.enable_encrypt:
            deploy_config.change_deploy_config_password(False, False)
        deploy_config.disable_encrypt_dump()
        if not self._start_cluster(deploy, repositories):
            return False
        deploy_config.enable_encrypt_dump()
        if not deploy_config.dump():
            return False
        return True

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

        workflows = self.get_workflows('standby_check', no_found_act='ignore')
        if not self.run_workflow(workflows, no_found_act='ignore'):
            return False

        self._call_stdio('verbose', 'Check deploy status')
        if deploy_info.status in [DeployStatus.STATUS_RUNNING, DeployStatus.STATUS_UPRADEING]:
            obd = self.fork(options=Values({'force': True}))
            if not obd._stop_cluster(deploy, repositories):
                return False
        elif deploy_info.status not in [DeployStatus.STATUS_STOPPED, DeployStatus.STATUS_DEPLOYED]:
            self._call_stdio('error', 'Deploy "%s" is %s. You could not destroy an undeployed cluster' % (name, deploy_info.status.value))
            return False

        self.search_param_plugin_and_apply(repositories, deploy_config)
        return self._destroy_cluster(deploy, repositories)

    def _destroy_cluster(self, deploy, repositories, dump=True):
        self._call_stdio('stop_loading', 'succeed')

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

        workflows = self.get_workflows("destroy")
        self.run_workflow(workflows, error_exit=False)

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
            workflow = self.get_workflows('reinstall_pre', repositories=[current_repository])
            if not self.run_workflow(workflow, repositories=[current_repository]):
                return False

        # install repo to remote servers
        if need_change_repo:
            if not self.install_repositories_to_servers(deploy_config, [dest_repository, ], install_plugins):
                return False
            sync_repositories = [dest_repository]
            repository = dest_repository

        # sync runtime dependencies
        if not self.sync_runtime_dependencies(sync_repositories):
            return False

        # start cluster if needed
        if need_restart and deploy_info.status == DeployStatus.STATUS_RUNNING:
            setattr(self.options, 'without_parameter', True)
            obd = self.fork(options=self.options)
            workflow = obd.get_workflows('reinstall', repositories=[current_repository])
            if not obd.run_workflow(workflow, repositories=[current_repository]) and getattr(self.options, 'force', False) is False:
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

        if not getattr(self.options, 'ignore_standby', False):
            workflows = self.get_workflows('standby_check', no_found_act='ignore')
            if not self.run_workflow(workflows, no_found_act='ignore'):
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

            self.search_param_plugin_and_apply([dest_repository], pre_deploy_config)
            start_check_workflows = self.get_workflows('start_check', repositories=[dest_repository])
            if not self.run_workflow(start_check_workflows, repositories=[dest_repository], no_found_act='ignore', **{dest_repository.name: {"cluster_config":cluster_config, "source_option":"upgrade"}}):
                return False

            upgrade_route_workflows = self.get_workflows('upgrade_route', repositories=[current_repository])
            if not self.run_workflow(upgrade_route_workflows, repositories=[current_repository], no_found_act='warn', **{current_repository.name: {"current_repository": current_repository, "dest_repository": dest_repository}}):
                return False

            use_images = []
            route = self.get_namespace(current_repository.name).get_return("upgrade_route").get_return("route") or []
            if route:
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
            self.set_repositories(repositories)
            upgrade_workflows = self.get_workflows('upgrade', repositories=[repository])
            component_kwargs = {repository.name: {
                "search_py_script_plugin": self.search_py_script_plugin,
                "local_home_path": self.home_path,
                "current_repository": current_repository,
                "upgrade_repositories": upgrade_repositories,
                "apply_param_plugin": lambda repository: self.search_param_plugin_and_apply([repository], deploy_config),
                "upgrade_ctx": upgrade_ctx,
                "install_repository_to_servers": self.install_repository_to_servers,
                "unuse_lib_repository": deploy_config.unuse_lib_repository,
                "script_query_timeout": script_query_timeout,
                "run_workflow": self.run_workflow,
                "get_workflows": self.get_workflows
            }}
            ret = self.run_workflow(upgrade_workflows, repositories=[repository], **component_kwargs)
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

    def _test_optimize_operation(self, repository, ob_repository, optimize_envs, connect_namespaces, stage=None, operation='optimize'):
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


        optimize_config = self.optimize_manager.optimize_config
        db_cursor = {}
        db_connect = {}
        for namespace in connect_namespaces:
            db, cursor = self._get_first_db_and_cursor_from_connect(namespace)
            if namespace.spacename in COMPS_OB or namespace.spacename in COMPS_ODP:
                db_cursor[namespace.spacename] = cursor
                db_connect[namespace.spacename] = db

        kwargs = {
           "stage": stage,
           "optimize_config": optimize_config,
           "optimize_envs": optimize_envs,
           "connect_namespaces": connect_namespaces,
           "ob_repository": ob_repository,
           "get_db_and_cursor": self._get_first_db_and_cursor_from_connect
       }
        workflow = self.get_workflow(repository, operation, 'optimize', **kwargs)
        optimize_workflow = Workflows(operation)
        optimize_workflow[repository.name] = workflow
        if not self.run_workflow(optimize_workflow):
            return False
        restart_components = self.get_namespace(repository.name).get_return("optimize").get_return("restart_components")
        
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
                kwargs = {
                    "connect_namespaces": connect_namespaces,
                    "ob_repository": ob_repository,
                    "restart_components": restart_components
                }
                db, cursor = self._get_first_db_and_cursor_from_connect(namespace)
                run_args = {}
                run_args["optimize"] = {
                    "cursor": cursor,
                    "tenant": optimize_envs.get('tenant')
                }
                workflow = self.get_workflow(repository, 'major_freeze', 'optimize', **kwargs)
                major_workflow = Workflows('major_freeze')
                major_workflow[repository.name] = workflow
                if not self.run_workflow(major_workflow, **run_args):
                    return False
        return True

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

        allow_components = COMPS_ODP + COMPS_OB
        if opts.component is None:
            for component_name in allow_components:
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
            for component_name in const.COMPS_OB:
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
            if repository.name in const.COMPS_OB:
                ob_repository = repository

        if not target_repository:
            self._call_stdio('error', 'Can not find the component for mysqltest, use `--component` to select component')
            return False
        if not ob_repository:
            self._call_stdio('error', 'Deploy {} must contain the component oceanbase or oceanbase-ce or oceanbase-standalone.'.format(deploy.name))
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

        env = opts.__dict__
        env['host'] = opts.test_server.ip

        namespace.set_variable('env', env)

        snap_kwargs = {}

        if fast_reboot:
            snap_configs = self.search_plugins(repositories, PluginType.SNAP_CONFIG, no_found_exit=False)
            snap_kwargs["snap_configs"] = snap_configs

        workflow = self.get_workflow(target_repository, 'test_pre', 'mysqltest', target_repository.version, **snap_kwargs)
        test_workflow = Workflows('test_pre')
        test_workflow[target_repository.name] = workflow
        ret = self.run_workflow(test_workflow)
        if not ret:
            return False

        use_snap = False
        if env['need_init'] or env['init_only']:
            if fast_reboot:
                connect_ret = self.get_namespace(target_repository.name).get_return('connect')
                db = connect_ret.get_return('connect')
                env['cursor'] = connect_ret.get_return('cursor')
                env['host'] = opts.test_server.ip
                env['port'] = db.port
                env['load_snap'] = True
                env['load_snap'] = False
                use_snap = True

            if env['init_only']:
                return True

        if fast_reboot and use_snap is False:
            self._call_stdio('start_loading', 'Check init')
            env['load_snap'] = True
            workflow = self.get_workflow(target_repository, 'init', 'mysqltest', target_repository.version)
            init_workflow = Workflows('init')
            init_workflow[target_repository.name] = workflow
            if not self.run_workflow(init_workflow):
                return False
            env['load_snap'] = False
            self._call_stdio('stop_loading', 'succeed')
            snap_num = 0
            for repository in repositories:
                if repository in snap_configs:
                    snap_kwargs = {repository.name: {"env": env, "snap_config": snap_configs[repository]}}
                    workflows = self.get_workflows('snap_check', [repository])
                    if not self.run_workflow(workflows, **snap_kwargs):
                        break
                    snap_num += 1
            use_snap = len(snap_configs) == snap_num
        env['load_snap'] = use_snap

        self._call_stdio('verbose', 'test set: {}'.format(env['test_set']))
        self._call_stdio('verbose', 'total: {}'.format(len(env['test_set'])))
        reboot_success = True
        while True:
            workflow = self.get_workflow(target_repository, 'run_collect', 'mysqltest', target_repository.version)
            run_collect_workflow = Workflows('run_collect')
            run_collect_workflow[target_repository.name] = workflow
            if not self.run_workflow(run_collect_workflow):
                break
            
            if self.get_namespace(target_repository.name).get_return('run_test').get_return('finished'):
                break
            if self.get_namespace(target_repository.name).get_return('run_test').get_return('reboot') and not env['disable_reboot']:
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
                                    workflow = self.get_workflow(repository, 'load_mysqltest_snap', 'mysqltest', **snap_kwargs)
                                    snap_workflow = Workflows('load_mysqltest_snap')
                                    snap_workflow[repository.name] = workflow
                                    if not self.run_workflow(snap_workflow):
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

                        workflow = self.get_workflow(repository, 'create_and_init_snap', 'mysqltest', **snap_kwargs)
                        snap_workflow = Workflows('create_and_init_snap')
                        snap_workflow[repository.name] = workflow
                        if not self.run_workflow(snap_workflow):
                            self._call_stdio('error', 'Failed to prepare for mysqltest')
                            return False
                        if fast_reboot and use_snap is False:
                            use_snap = True
                            connect_ret = self.get_namespace(target_repository.name).get_return('connect')
                            db = connect_ret.get_return('connect')
                            cursor = connect_ret.get_return('cursor')
                            env['cursor'] = cursor
                        reboot_success = True
                if not reboot_success:
                    env['collect_log'] = True
                    setattr(self.options, 'test_name', "reboot_failed")
                    collect_kwargs = {"mysqltest": {"test_name": "reboot_failed"}}
                    workflow = self.get_workflow(target_repository, 'collect_log', 'mysqltest')
                    collect_log_workflow = Workflows('collect_log')
                    collect_log_workflow[target_repository.name] = workflow
                    self.run_workflow(collect_log_workflow, **collect_kwargs)
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

        allow_components = COMPS_ODP + COMPS_OB
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
            if tmp_repository.name in const.COMPS_OB:
                ob_repository = tmp_repository
            if tmp_repository.name == opts.component:
                repository = tmp_repository
        if not ob_repository:
            self._call_stdio('error', 'Deploy {} must contain the component oceanbase or oceanbase-ce or oceanbase-standalone.'.format(deploy.name))
            return False
        plugin_version = ob_repository.version if ob_repository else repository.version
        setattr(opts, 'host', opts.test_server.ip)

        optimization = getattr(opts, 'optimization', 0)
        pre_test_kwargs = {
            "sys_namespace": self.get_namespace(ob_repository.name),
            "proxysys_namespace": self.get_namespace(repository.name),
            "deploy_config": deploy_config,
            "connect_namespaces": connect_namespaces
        }

        run_kwargs = {
            "sysbench": {
                "sys_namespace": self.get_namespace(ob_repository.name),
                "get_db_and_cursor": self._get_first_db_and_cursor_from_connect
            }
        }

        workflow = self.get_workflow(repository, 'pre_test', 'sysbench', plugin_version, **pre_test_kwargs)
        pre_workflow = Workflows('pre_test')
        pre_workflow[repository.name] = workflow
        if not self.run_workflow(pre_workflow, **run_kwargs):
            return False
        kwargs = self.get_namespace(repository.name).get_return("pre_test").kwargs
        optimization_init = False
        try:
            if optimization:
                self._test_optimize_init(test_name='sysbench', repository=repository)
                optimization_init = True
                if not self._test_optimize_operation(repository=repository, ob_repository=ob_repository, stage='test', connect_namespaces=connect_namespaces, optimize_envs=kwargs):
                    return False
            workflow = self.get_workflow(repository, 'run_test', 'sysbench', plugin_version)
            run_test_workflow = Workflows('run_test')
            run_test_workflow[repository.name] = workflow
            if not self.run_workflow(run_test_workflow, **run_kwargs):
                return False
        finally:
            if optimization and optimization_init:
                self._test_optimize_operation(repository=repository,  ob_repository=ob_repository, connect_namespaces=connect_namespaces, optimize_envs=kwargs, operation='recover')


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

        allow_components = const.COMPS_OB
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

        setattr(opts, 'host', opts.test_server.ip)

        optimization = getattr(opts, 'optimization', 0)

        workflow = self.get_workflow(repository, 'pre_test', 'tpch', repository.version)
        pre_workflow = Workflows('pre_test')
        pre_workflow[repository.name] = workflow
        if not self.run_workflow(pre_workflow):
            return False
        kwargs = self.get_namespace(repository.name).get_return('pre_test').kwargs
        optimization_init = False
        try:
            if optimization:
                self._test_optimize_init(test_name='tpch', repository=repository)
                optimization_init = True
                if not self._test_optimize_operation(
                        repository=repository, ob_repository=repository, stage='test',
                        connect_namespaces=[namespace], optimize_envs=kwargs):
                    return False
            workflow = self.get_workflow(repository, 'run_test', 'tpch', repository.version)
            run_test_workflow = Workflows('run_test')
            run_test_workflow[repository.name] = workflow
            run_test_kwargs = {"tpch": kwargs}
            if not self.run_workflow(run_test_workflow, **run_test_kwargs):
                return False
        except Exception as e:
            self._call_stdio('error', e)
            return False
        finally:
            if optimization and optimization_init:
                self._test_optimize_operation(
                    repository=repository, ob_repository=repository, connect_namespaces=[namespace],
                    optimize_envs=kwargs, operation='recover')

    def update_obd(self, version, install_prefix, install_path):
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

        for part in ['workflows', 'plugins', 'config_parser', 'optimize']:
            obd_part_dir = os.path.join(install_path, part)
            DirectoryUtil.rm(obd_part_dir, self.stdio)
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
        db_components = const.COMPS_OB
        allow_components = COMPS_ODP + COMPS_OB
        if opts.component is None:
            for component_name in allow_components:
                if component_name in deploy_config.components:
                    opts.component = component_name
                    break
        elif opts.component not in allow_components:
            self._call_stdio('error', '%s not support. %s is allowed' % (opts.component, allow_components))
            return False
        if opts.component not in deploy_config.components:
            self._call_stdio('error', 'Can not find the component` for tpcds, use `--component` to select component')
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

        allow_components = COMPS_ODP + COMPS_OB
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
        connect_namespaces = []
        for tmp_repository in repositories:
            if tmp_repository.name in const.COMPS_OB:
                ob_repository = tmp_repository
            if tmp_repository.name == opts.component:
                repository = tmp_repository
        if not ob_repository:
            self._call_stdio('error', 'Deploy {} must contain the component oceanbase or oceanbase-ce or oceanbase-standalone.'.format(deploy.name))
            return False
        plugin_version = ob_repository.version if ob_repository else repository.version
        setattr(opts, 'host', opts.test_server.ip)

        kwargs = {}

        optimization = getattr(opts, 'optimization', 0)
        test_only = getattr(opts, 'test_only', False)
        optimization_inited = False
        try:
            pre_test_kwargs = {
                "sys_namespace": self.get_namespace(ob_repository.name),
                "proxysys_namespace": self.get_namespace(repository.name),
                "deploy_config": deploy_config,
                "connect_namespaces": connect_namespaces
            }
            run_kwargs = {
                "tpcc": {
                    "get_db_and_cursor": self._get_first_db_and_cursor_from_connect,
                    "sys_namespace": self.get_namespace(ob_repository.name)
                }
            }
            workflow = self.get_workflow(repository, 'pre_test', 'tpcc', plugin_version, **pre_test_kwargs)
            pre_workflow = Workflows('pre_test')
            pre_workflow[repository.name] = workflow
            if not self.run_workflow(pre_workflow, **run_kwargs):
                return False
            else:
                ret = self.get_namespace(repository.name).get_return('pre_test').kwargs
                kwargs.update(ret)
            if optimization:
                self._test_optimize_init(test_name='tpcc', repository=repository)
                optimization_inited = True
                if not self._test_optimize_operation(repository=repository, ob_repository=ob_repository, stage='build',
                                                     connect_namespaces=connect_namespaces, optimize_envs=kwargs):
                    return False
            if not test_only:
                workflow = self.get_workflow(repository, 'build', 'tpcc', plugin_version)
                build_workflow = Workflows('build')
                build_workflow[repository.name] = workflow
                if not self.run_workflow(build_workflow, **run_kwargs):
                    return False
                else:
                    ret = self.get_namespace(repository.name).get_return('build').kwargs
                    kwargs.update(ret)
            if optimization:
                if not self._test_optimize_operation(repository=repository, ob_repository=ob_repository, stage='test',
                                                     connect_namespaces=connect_namespaces, optimize_envs=kwargs):
                    return False
            workflow = self.get_workflow(repository, 'run_test', 'tpcc', plugin_version)
            run_test_workflow = Workflows('run_test')
            run_test_workflow[repository.name] = workflow
            if not self.run_workflow(run_test_workflow, **run_kwargs):
                return False
            else:
                ret = self.get_namespace(repository.name).get_return('run_test').kwargs
                kwargs.update(ret)
            return True
        except Exception as e:
            self._call_stdio('exception', e)
            return False
        finally:
            if optimization and optimization_inited:
                self._test_optimize_operation(repository=repository, ob_repository=ob_repository,
                                              connect_namespaces=connect_namespaces, optimize_envs=kwargs, operation='recover')

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

        allow_components = COMPS_ODP + COMPS_OB
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

        workflows = self.get_workflows('db_connect', [repository])
        return self.run_workflow(workflows, repositories=[repository])

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


        repository = repositories[0]
        template = self.get_workflow(repository, 'check_opt', 'commands', '0.1')
        workflow = Workflows('check_opt')
        workflow[repository.name] = template
        if not self.run_workflow(workflow):
            return

        template = self.get_workflow(repository, 'commands', 'commands', '0.1')
        workflow = Workflows('commands')
        workflow[repository.name] = template
        if not self.run_workflow(workflow):
            return

        context = self.get_namespace(repository.name).get_variable('context')
        ret = self.get_namespace(repository.name).get_return('commands')
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

        allow_components = COMPS_ODP + COMPS_OB
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
            if component in const.COMPS_OB:
                break
        else:
            self._call_stdio('error', 'Dooba must contain the component oceanbase or oceanbase-ce or oceanbase-standalone.')
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
            if repository.name in const.COMPS_OB:
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

        if const.COMP_OB in deploy.deploy_config.components:
            return False

        repositories = self.load_local_repositories(deploy_info)
        if repositories == []:
            return
        self.set_repositories(repositories)

        workflows = self.get_workflows('telemetry')
        if not self.run_workflow(workflows):
            return False
        return True


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
            allow_components = const.COMPS_ODP
        else:
            allow_components = const.COMPS_OB

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
        need_install_repositories = [const.COMP_OB_CE]
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
        need_install_repositories = [const.COMP_OB_CE]
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
        mock_oceanbase_ce_repository = Repository(const.COMP_OB_CE, "/")
        mock_oceanbase_ce_repository.version = "4.2.1.4"
        configs = OrderedDict()
        component_name = const.COMP_OB_CE
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
            ssh_clients = self.get_clients(deploy_config, [mock_oceanbase_ce_repository])
            workflow = self.get_workflows('takeover', repositories=[mock_oceanbase_ce_repository], no_found_act='ignore')
            if not self.run_workflow(workflow, deploy_config=deploy_config, repositories=[mock_oceanbase_ce_repository], **{const.COMP_OB_CE: {'cluster_config': deploy_config.components[component_name], 'clients': ssh_clients, 'user_config': configs.get('user', None), 'obd_home': self.home_path}}):
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
            self.deploy.deploy_info.components[const.COMP_OB_CE]['md5'] = repository.md5
            self.deploy.deploy_info.status = DeployStatus.STATUS_RUNNING
            self.deploy.dump_deploy_info()
            display_plugins = self.search_py_script_plugin([repository], 'display')
            display_encrypt_password = None
            if self.enable_encrypt:
                display_encrypt_password = '******'
            components_kwargs = {}
            for repository in repositories:
                components_kwargs[repository.name] = {"display_encrypt_password": display_encrypt_password}
            workflow = self.get_workflows('display')
            if not self.run_workflow(workflow, **components_kwargs):
                return False
            return True
        except Exception as e:
            self._call_stdio('exception', '')
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
            if pkg.name in const.COMPS_OB and (pkg in hit_pkgs or pkg in hash_hit_pkgs or pkg in component_hit_pkgs):
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

    def binlog_create_instance(self, binlog_deploy_name, ob_deploy_name, tenant_name):
        # check tenant
        if tenant_name == 'sys':
            self._call_stdio('error', 'Creating binlog instance for the sys tenant is not support.')
            return False

        ob_deploy = self.get_deploy_with_allowed_status(ob_deploy_name, DeployStatus.STATUS_RUNNING)
        if not ob_deploy:
            return False

        binlog_deploy = self.get_deploy_with_allowed_status(binlog_deploy_name, DeployStatus.STATUS_RUNNING)
        if not binlog_deploy:
            return False
        self.set_deploy(binlog_deploy)

        obproxy_deployname = getattr(self.options, 'obproxy_deployname', None)
        if obproxy_deployname:
            proxy_deploy = self.get_deploy_with_allowed_status(obproxy_deployname, DeployStatus.STATUS_RUNNING)
            if not proxy_deploy:
                return False
        else:
            proxy_deploy = ob_deploy

        self._call_stdio('start_loading', 'Get local repositories')
        ob_cluster_repositories = self.load_local_repositories(ob_deploy.deploy_info, False)
        self.search_param_plugin_and_apply(ob_cluster_repositories, ob_deploy.deploy_config)
        if obproxy_deployname:
            proxy_cluster_repositories = self.load_local_repositories(proxy_deploy.deploy_info, False)
            ob_cluster_repositories += proxy_cluster_repositories
            self.search_param_plugin_and_apply(proxy_cluster_repositories, proxy_deploy.deploy_config)
        binlog_deployed_repositories = self.load_local_repositories(binlog_deploy.deploy_info, False)
        for repo in binlog_deployed_repositories:
            if repo.name == const.COMP_OBBINLOG_CE:
                break
        else:
            self._call_stdio('error', 'There must be "%s" component in deploy "%s".' % (const.COMP_OBBINLOG_CE, binlog_deploy_name))
            return False
        self.search_param_plugin_and_apply(binlog_deployed_repositories, binlog_deploy.deploy_config)
        self.set_repositories(binlog_deployed_repositories)
        self._call_stdio('stop_loading', 'succeed')

        # check obproxy component
        for repository in ob_cluster_repositories:
            if repository.name in const.COMPS_ODP:
                break
        else:
            self._call_stdio('error','There must be "obproxy" component in deploy "%s", or the options "proxy-cluster" needs to be provided.' % (ob_deploy_name))
            return False


        # create instance check
        workflows = self.get_workflows('create_instance_check', no_found_act='ignore')
        if not self.run_workflow(workflows, **{const.COMP_OBBINLOG_CE: {"tenant_name": tenant_name, "ob_deploy": ob_deploy, "proxy_deploy": proxy_deploy, "ob_cluster_repositories": ob_cluster_repositories}}):
            return False

        # create instance
        workflows = self.get_workflows('create_instance', no_found_act='ignore')
        if not self.run_workflow(workflows, **{const.COMP_OBBINLOG_CE: {"tenant_name": tenant_name, "ob_deploy": ob_deploy, "proxy_deploy": proxy_deploy, "ob_cluster_repositories": ob_cluster_repositories}}):
            return False

        return True

    def show_binlog_instance(self, deploy_name):
        deploy = self.get_deploy_with_allowed_status(deploy_name, DeployStatus.STATUS_RUNNING)
        if not deploy:
            return False
        self.set_deploy(deploy)

        ob_deploy = None
        ob_deploy_name = getattr(self.options, 'deploy_name', None)
        tenant_name = getattr(self.options, 'tenant_name', None)
        if (not ob_deploy_name and tenant_name) or (ob_deploy_name and not tenant_name):
            self._call_stdio('error', 'please specify `--deploy-name` and `--tenant-name` must be specified at the same time.')
            return False

        self._call_stdio('verbose', 'Deploy status judge')
        if ob_deploy_name:
            ob_deploy = self.get_deploy_with_allowed_status(ob_deploy_name, DeployStatus.STATUS_RUNNING)
            if not ob_deploy:
                return False

        self._call_stdio('start_loading', 'Get local repositories')
        repositories = self.load_local_repositories(deploy.deploy_info, False)
        self.search_param_plugin_and_apply(repositories, deploy.deploy_config)
        ob_repositories = None
        if ob_deploy_name:
            ob_repositories = self.load_local_repositories(ob_deploy.deploy_info, False)
            self.search_param_plugin_and_apply(ob_repositories, ob_deploy.deploy_config)
        self.set_repositories(repositories)
        self._call_stdio('stop_loading', 'succeed')

        for repo in repositories:
            if repo.name == const.COMP_OBBINLOG_CE:
                break
        else:
            self._call_stdio('error', 'There must be "%s" component in deploy "%s".' % (const.COMP_OBBINLOG_CE, deploy_name))
            return False
        if ob_repositories:
            for repository in ob_repositories:
                if repository.name in const.COMPS_OB:
                    break
            else:
                self._call_stdio('error', 'There must be "oceanbase" component in deploy "%s".' % ob_deploy_name)
                return False

        workflows = self.get_workflows('show_binlog_instances', no_found_act='ignore', **{"tenant_name": tenant_name})
        if not self.run_workflow(workflows, **{const.COMP_OBBINLOG_CE: {"tenant_name": tenant_name, "ob_deploy": ob_deploy, "ob_cluster_repositories": ob_repositories}}):
            return False
        return True

    def start_binlog_instances(self, binlog_deploy_name, ob_deploy_name, tenant_name):
        # check deploy name
        ob_deploy = self.get_deploy_with_allowed_status(ob_deploy_name, DeployStatus.STATUS_RUNNING)
        if not ob_deploy:
            return False

        binlog_deploy = self.get_deploy_with_allowed_status(binlog_deploy_name, DeployStatus.STATUS_RUNNING)
        if not binlog_deploy:
            return False
        self.set_deploy(binlog_deploy)

        self._call_stdio('start_loading', 'Get local repositories')
        binlog_deployed_repositories = self.load_local_repositories(binlog_deploy.deploy_info, False)
        self.search_param_plugin_and_apply(binlog_deployed_repositories, binlog_deploy.deploy_config)
        self.set_repositories(binlog_deployed_repositories)
        self._call_stdio('stop_loading', 'succeed')

        ob_cluster_repositories = self.load_local_repositories(ob_deploy.deploy_info, False)
        self.search_param_plugin_and_apply(ob_cluster_repositories, ob_deploy.deploy_config)

        for repo in binlog_deployed_repositories:
            if repo.name == const.COMP_OBBINLOG_CE:
                break
        else:
            self._call_stdio('error', 'There must be "%s" component in deploy "%s".' % (const.COMP_OBBINLOG_CE, binlog_deploy_name))
            return False

        for repository in ob_cluster_repositories:
            if repository.name in const.COMPS_OB:
                break
        else:
            self._call_stdio('error', 'There must be "oceanbase" component in deploy "%s".' % ob_deploy_name)
            return False

        workflows = self.get_workflows('instance_manager', no_found_act='ignore')
        if not self.run_workflow(workflows, **{const.COMP_OBBINLOG_CE: {"tenant_name": tenant_name, "source_option": "start", "ob_deploy": ob_deploy, "ob_cluster_repositories": ob_cluster_repositories}}):
            return False
        return True

    def stop_binlog_instances(self, binlog_deploy_name, ob_deploy_name, tenant_name):
        # check deploy name
        ob_deploy = self.get_deploy_with_allowed_status(ob_deploy_name, DeployStatus.STATUS_RUNNING)
        if not ob_deploy:
            return False

        binlog_deploy = self.get_deploy_with_allowed_status(binlog_deploy_name, DeployStatus.STATUS_RUNNING)
        if not binlog_deploy:
            return False
        self.set_deploy(binlog_deploy)

        self._call_stdio('start_loading', 'Get local repositories')
        binlog_deployed_repositories = self.load_local_repositories(binlog_deploy.deploy_info, False)
        self.search_param_plugin_and_apply(binlog_deployed_repositories, binlog_deploy.deploy_config)
        self.set_repositories(binlog_deployed_repositories)
        self._call_stdio('stop_loading', 'succeed')

        ob_cluster_repositories = self.load_local_repositories(ob_deploy.deploy_info, False)
        self.search_param_plugin_and_apply(ob_cluster_repositories, ob_deploy.deploy_config)

        for repo in binlog_deployed_repositories:
            if repo.name == const.COMP_OBBINLOG_CE:
                break
        else:
            self._call_stdio('error', 'There must be "%s" component in deploy "%s".' % (const.COMP_OBBINLOG_CE, binlog_deploy_name))
            return False

        for repository in ob_cluster_repositories:
            if repository.name in const.COMPS_OB:
                break
        else:
            self._call_stdio('error', 'There must be "oceanbase" component in deploy "%s".' % ob_deploy_name)
            return False

        workflows = self.get_workflows('instance_manager', no_found_act='ignore')
        if not self.run_workflow(workflows, **{const.COMP_OBBINLOG_CE: {"tenant_name": tenant_name, "source_option": "stop", "ob_deploy": ob_deploy, "ob_cluster_repositories": ob_cluster_repositories}}):
            return False
        return True

    def drop_binlog_instances(self, binlog_deploy_name, ob_deploy_name, tenant_name):
        # check deploy name
        ob_deploy = self.get_deploy_with_allowed_status(ob_deploy_name, DeployStatus.STATUS_RUNNING)
        if not ob_deploy:
            return False

        binlog_deploy = self.get_deploy_with_allowed_status(binlog_deploy_name, DeployStatus.STATUS_RUNNING)
        if not binlog_deploy:
            return False
        self.set_deploy(binlog_deploy)

        self._call_stdio('start_loading', 'Get local repositories')
        binlog_deployed_repositories = self.load_local_repositories(binlog_deploy.deploy_info, False)
        self.search_param_plugin_and_apply(binlog_deployed_repositories, binlog_deploy.deploy_config)
        self.set_repositories(binlog_deployed_repositories)
        self._call_stdio('stop_loading', 'succeed')

        ob_cluster_repositories = self.load_local_repositories(ob_deploy.deploy_info, False)
        self.search_param_plugin_and_apply(ob_cluster_repositories, ob_deploy.deploy_config)

        for repo in binlog_deployed_repositories:
            if repo.name == const.COMP_OBBINLOG_CE:
                break
        else:
            self._call_stdio('error', 'There must be "%s" component in deploy "%s".' % (const.COMP_OBBINLOG_CE, binlog_deploy_name))
            return False

        for repository in ob_cluster_repositories:
            if repository.name in const.COMPS_OB:
                break
        else:
            self._call_stdio('error', 'There must be "oceanbase" component in deploy "%s".' % ob_deploy_name)
            return False

        workflows = self.get_workflows('instance_manager', no_found_act='ignore')
        if not self.run_workflow(workflows, **{const.COMP_OBBINLOG_CE: {"tenant_name": tenant_name, "source_option": "drop", "ob_deploy": ob_deploy, "ob_cluster_repositories": ob_cluster_repositories}}):
            return False
        return True

    def get_deploy_with_allowed_status(self, deploy_name, allowed_deploy_status):
        deploy = self.deploy_manager.get_deploy_config(deploy_name)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % deploy_name)
            return None
        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status != allowed_deploy_status:
            self._call_stdio('error', 'Deploy "%s" is %s. it needs to be %s.' % (deploy_name, deploy_info.status.value, allowed_deploy_status.value))
            return None
        return deploy

    def set_sys_conf(self, repositories):
        for repository in repositories:
            if repository.name in const.COMPS_OB:
                break
        else:
            self._call_stdio('error', 'No such component: oceanbase.')
            return True
        workflows = self.get_workflows('set_sys_env', no_found_act='ignore')
        if not self.run_workflow(workflows):
            return False
        return True

    def init_cluster_env(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False

        deploy_info = deploy.deploy_info
        self._call_stdio('verbose', 'Deploy status judge')
        if deploy_info.status not in [DeployStatus.STATUS_DEPLOYED, DeployStatus.STATUS_STOPPED, DeployStatus.STATUS_RUNNING, DeployStatus.STATUS_UPRADEING]:
            self._call_stdio('error', 'Deploy "%s" is %s. can not support init env.' % (name, deploy_info.status.value))
            return False

        self._call_stdio('start_loading', 'Get local repositories')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info, False)
        self.set_repositories(repositories)
        self._call_stdio('stop_loading', 'succeed')

        for repository in repositories:
            if repository.name in const.COMPS_OB:
                break
        else:
            self._call_stdio('error', 'There must be "oceanbase" component in deploy "%s".' % name)
            return False

        self._call_stdio('verbose', 'Get deploy config')

        if not self.set_sys_conf(repositories):
            return False
        return True

    def register_license(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False

        deploy_info = deploy.deploy_info
        if deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('print', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False

        license = getattr(self.options, 'file', '')
        if not license:
            self._call_stdio('error', 'Use the --file option to specify the required license file。')
            return False

        self._call_stdio('verbose', 'Get deploy config')
        deploy_config = deploy.deploy_config

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        repositories = self.sort_repository_by_depend(repositories, deploy_config)
        for repository in repositories:
            if repository.name == COMP_OB_STANDALONE:
                break
        else:
            self._call_stdio('error', 'The current database version does not support license mechanism.')
            return
        self.set_repositories(repositories)
        self._call_stdio('stop_loading', 'succeed')
        self.get_clients(deploy_config, repositories)
        workflows = self.get_workflows('load_license', repositories=[repository])
        return self.run_workflow(workflows)

    def show_license(self, name):
        self._call_stdio('verbose', 'Get Deploy by name')
        deploy = self.deploy_manager.get_deploy_config(name)
        self.set_deploy(deploy)
        if not deploy:
            self._call_stdio('error', 'No such deploy: %s.' % name)
            return False

        deploy_info = deploy.deploy_info
        if deploy_info.status != DeployStatus.STATUS_RUNNING:
            self._call_stdio('print', 'Deploy "%s" is %s' % (name, deploy_info.status.value))
            return False

        self._call_stdio('verbose', 'Get deploy config')
        deploy_config = deploy.deploy_config

        self._call_stdio('start_loading', 'Get local repositories and plugins')
        # Get the repository
        repositories = self.load_local_repositories(deploy_info)
        repositories = self.sort_repository_by_depend(repositories, deploy_config)
        for repository in repositories:
            if repository.name == COMP_OB_STANDALONE:
                break
        else:
            self._call_stdio('error', 'The current database version does not support license mechanism.')
            return
        self.set_repositories(repositories)
        self._call_stdio('stop_loading', 'succeed')
        self.get_clients(deploy_config, repositories)
        workflows = self.get_workflows('show_license', repositories=[repository])
        return self.run_workflow(workflows)

    def get_ob_repo_by_normal_check_for_use_obshell(self, name, deploy):
        self.set_deploy(deploy)
        self._call_stdio('start_loading', 'Get local repositories')
        repositories = self.load_local_repositories(deploy.deploy_info, False)
        self.search_param_plugin_and_apply(repositories, deploy.deploy_config)
        self._call_stdio('stop_loading', 'succeed')

        for repository in repositories:
            if repository.name in const.COMPS_OB:
                if Version('4.2.0.0') <= repository.version <= Version('4.2.5.0'):
                    self._call_stdio('error', 'Oceanbase must be higher than version 4.2.5.0 .')
                    return None
                elif Version('4.3.0.0') <= repository.version <= Version('4.3.3.0'):
                    self._call_stdio('error', 'Oceanbase must be higher than version 4.3.3.0 .')
                    return None
                ob_repository = repository
                break
        else:
            self._call_stdio('error', 'There must be "oceanbase" component in deploy "%s".' % name)
            return None

        self.set_repositories([ob_repository])
        component_status = {}
        cluster_status = self.cluster_status_check([ob_repository], component_status)
        if cluster_status is False or cluster_status == 0:
            for repository in component_status:
                cluster_status = component_status[repository]
                for server in cluster_status:
                    if cluster_status[server] == 0:
                        self._call_stdio('print','%s: "%s" is not running, please execute `obd cluster start %s` to start and try again.' % (server, ob_repository.name, name))
                        return None

        return ob_repository

    def tenant_set_backup_config(self, name, tenant_name):
        # check deploy name
        deploy = self.get_deploy_with_allowed_status(name, DeployStatus.STATUS_RUNNING)
        if not deploy:
            return False

        if tenant_name == 'sys':
            self._call_stdio('error', 'Backup sys tenant is not support.')
            return False

        ob_repository = self.get_ob_repo_by_normal_check_for_use_obshell(name, deploy)
        if not ob_repository:
            return False

        workflows = self.get_workflows('tenant_set_backup_config')
        if not self.run_workflow(workflows, **{ob_repository.name: {"tenant_name": tenant_name}}):
            return False
        return True

    def tenant_backup(self, name, tenant_name):
        # check deploy name
        deploy = self.get_deploy_with_allowed_status(name, DeployStatus.STATUS_RUNNING)
        if not deploy:
            return False

        if tenant_name == 'sys':
            self._call_stdio('error', 'Backup sys tenant is not support.')
            return False

        ob_repository = self.get_ob_repo_by_normal_check_for_use_obshell(name, deploy)
        if not ob_repository:
            return False

        workflows = self.get_workflows('tenant_backup')
        if not self.run_workflow(workflows, **{ob_repository.name: {"tenant_name": tenant_name}}):
            return False
        self._call_stdio('print', 'View backup task details,please execute `obd cluster tenant backup-show %s %s`.' % (name, tenant_name))
        return True

    def tenant_restore(self, name, tenant_name, data_backup_uri, archive_log_uri):
        # check deploy name
        deploy = self.get_deploy_with_allowed_status(name, DeployStatus.STATUS_RUNNING)
        if not deploy:
            return False

        if tenant_name == 'sys':
            self._call_stdio('error', 'Restore sys tenant is not support.')
            return False

        ob_repository = self.get_ob_repo_by_normal_check_for_use_obshell(name, deploy)
        if not ob_repository:
            return False

        workflows = self.get_workflows('tenant_restore')
        if not self.run_workflow(workflows, **{ob_repository.name: {
            "tenant_name": tenant_name,
            "data_backup_uri": data_backup_uri,
            "archive_log_uri": archive_log_uri
            }
        }):
            return False
        self._call_stdio('print', 'View restore task details,please execute `obd cluster tenant restore-show %s %s`.' % (name, tenant_name))
        return True

    def query_backup_or_restore_task(self, name, tenant_name, task_type):
        # check deploy name
        deploy = self.get_deploy_with_allowed_status(name, DeployStatus.STATUS_RUNNING)
        if not deploy:
            return False

        ob_repository = self.get_ob_repo_by_normal_check_for_use_obshell(name, deploy)
        if not ob_repository:
            return False

        workflows = self.get_workflows('query_backup_or_restore_task')
        if not self.run_workflow(workflows, **{ob_repository.name: {"tenant_name": tenant_name, "task_type": task_type}}):
            return False
        return True

    def cancel_backup_or_restore_task(self, name, tenant_name, task_type):
        # check deploy name
        deploy = self.get_deploy_with_allowed_status(name, DeployStatus.STATUS_RUNNING)
        if not deploy:

            return False

        ob_repository = self.get_ob_repo_by_normal_check_for_use_obshell(name, deploy)
        if not ob_repository:
            return False

        workflows = self.get_workflows('cancel_backup_or_restore_task')
        if not self.run_workflow(workflows, **{ob_repository.name: {"tenant_name": tenant_name, "task_type": task_type}}):
            return False
        return True

    def check_encryption_passkey(self, epk):
        self._call_stdio('print', 'Check encryption passkey.')
        if tool.string_to_md5_32bytes(epk) == self.encrypted_passkey:
            return True
        return False

    def input_encryption_passkey(self, double_check=True, print_error=True):
        try_times = 2
        msg = 'Please enter the encryption passkey: '
        if double_check:
            msg = 'First time setting the encryption passkey. please enter the encryption passkey: '
        while try_times:
            epk = getpass.getpass(msg).strip()
            if not epk:
                msg = 'Encryption passkey cannot be empty, Please enter again: '
                try_times -= 1
            elif double_check:
                double_check_epk = getpass.getpass('Please enter the encryption passkey again: ')
                if epk != double_check_epk:
                    self._call_stdio('print', 'The two input encryption passkeys are inconsistent')
                    try_times -= 1
                else:
                    COMMAND_ENV.set(const.ENCRYPT_PASSKEY, tool.string_to_md5_32bytes(epk), save=True)
                    self._call_stdio('print', FormatText.success('First time setting the encryption passkey successful! '))
                    break
            else:
                break
        else:
            if print_error:
                self._call_stdio('error', 'Encryption passkey input error.')
                return False
            return ''
        return epk

    def encrypt_manager(self, enable):
        if enable:
            self._call_stdio('verbose', 'Get encrypt passkey')
            double_check = True
            if self.encrypted_passkey:
                double_check = False
                encryption_passkey = getattr(self.options, 'encryption_passkey') or self.input_encryption_passkey(double_check=double_check)
            else:
                encryption_passkey = self.input_encryption_passkey(double_check=double_check)
            if not encryption_passkey:
                return False
            if not double_check and not self.check_encryption_passkey(encryption_passkey):
                self._call_stdio('error', 'Encryption passkey error.')
                return False
        else:
            if self.encrypted_passkey:
                encryption_passkey = getattr(self.options, 'encryption_passkey') or self.input_encryption_passkey(False)
                if not encryption_passkey:
                    return False
                if not self.check_encryption_passkey(encryption_passkey):
                    self._call_stdio('error', 'Encryption passkey error.')
                    return False
        msg = 'Encrypt password'
        if not enable:
            msg = 'Decrypt password'
        self._call_stdio('start_loading', msg)
        configs = self.deploy_manager.get_deploy_configs(read_only=False)
        for deploy in configs:
            if deploy.deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
                self._call_stdio('error', 'The current is config is modified. Deploy "%s" %s.' % (deploy.name, deploy.deploy_info.config_status.value))
                return False
        first_encrypt = False
        if COMMAND_ENV.get(const.ENCRYPT_PASSWORD) != '1':
            first_encrypt = True
            self._call_stdio('verbose', 'Encrypt password')
        for deploy in configs:
            if deploy.deploy_config.inner_config.get_global_config(const.ENCRYPT_PASSWORD) != enable:
                self._call_stdio('verbose', '%s password for deploy %s' % ('encrypt' if enable else 'decrypt', deploy.name))
                deploy.deploy_config.change_deploy_config_password(enable, first_encrypt=first_encrypt)
                deploy.deploy_config.dump()
        self._call_stdio('stop_loading', 'succeed')
        if not enable:
            COMMAND_ENV.delete(const.ENCRYPT_PASSKEY, save=True)
            COMMAND_ENV.delete(const.ENCRYPT_PASSWORD, save=True)
        else:
            COMMAND_ENV.set(const.ENCRYPT_PASSWORD, '1', save=True)
        return True

    def set_encryption_passkey(self, new_epk):
        current_epk = getattr(self.options, 'current_passkey')
        force = getattr(self.options, 'force')
        if force:
            username = self._call_stdio('read', 'Please input username with sudo privileges. (default: root): ', blocked=True).strip() or 'root'
            password = getpass.getpass('please input %s password: ' % username)
            config = SshConfig(host='127.0.0.1', port='22', username=username, password=password)
            client = SshClient(config, stdio=self.stdio)
            ret = client.execute_command('echo %s | %s whoami' % (password, 'sudo -S' if username != 'root' else ''))
            if not ret:
                self._call_stdio('error', 'Force set must be run with root privileges')
                return False

        if not force and self.encrypted_passkey:
            if current_epk is None:
                self._call_stdio('error', 'Please use `-c` to input current encryption passkey .')
                return False
            if not self.check_encryption_passkey(current_epk):
                self._call_stdio('error', 'Current encryption passkey error.')
                return False

        if new_epk == '':
            self._call_stdio('print', ' `` passkey is not supported.')
            return True

        COMMAND_ENV.set(const.ENCRYPT_PASSKEY, tool.string_to_md5_32bytes(new_epk), save=True)
        self._call_stdio('print', 'Update encryption passkey successful.')
        return True

    def precheck_host(self, username, host, dev=False):
        self._call_stdio('verbose', 'ssh connect')
        password = getattr(self.options, 'password', None)
        clients = {}

        client = SshClient(
            SshConfig(
                host,
                username,
                password,
            ),
            self.stdio
        )
        if not client.connect():
            self._call_stdio('error', 'ssh connect failed, please check the password and network.(username: %s ip: %s password: %s)' % (username, host, password))
            return False
        clients[host] = client

        host_tool_repository = self.repository_manager.get_repository_allow_shadow('host_tool', '1.0')
        self.set_repositories([host_tool_repository])

        workflows = self.get_workflows('precheck')
        if not self.run_workflow(workflows, **{'host_tool': {'host_clients': clients}}):
            return False

        need_change_servers_vars = self.get_namespace('host_tool').get_return('precheck').get_return('need_change_servers_vars')
        print_data = []
        for v in need_change_servers_vars.values():
            print_data.extend(v)
        if not print_data:
            self._call_stdio('print', FormatText.success('No need to change system parameters'))
            return True
        self._call_stdio('print_list', print_data, ['ip', 'need_change_var', 'current_value', 'target_value'],
                         lambda x: [x['server'], x['var'], x['current_value'], x['value']],
                         title='System Parameter Change List')
        if dev:
            return 100
        return True

    def init_host(self, username, host, dev=False):
        self._call_stdio('verbose', 'ssh connect')
        password = getattr(self.options, 'password', None)
        clients = {}

        client = SshClient(
            SshConfig(
                host,
                username,
                password,
            ),
            self.stdio
        )
        if not client.connect():
            self._call_stdio('error', 'ssh connect failed, please check the password and network.(username: %s ip: %s password: %s)' % (username, host, password))
            return False
        clients[host] = client

        host_tool_repository = self.repository_manager.get_repository_allow_shadow('host_tool', '1.0')
        self.set_repositories([host_tool_repository])

        workflows = self.get_workflows('init')
        if not self.run_workflow(workflows, **{'host_tool': {'host_clients': clients}}):
            return False

        need_reboot_ips = self.get_namespace('host_tool').get_return('init').get_return('need_reboot_ips')
        if need_reboot_ips:
            if dev:
                return 101
            else:
                self._call_stdio('print', FormatText.warning('You must reboot the following servers to ensure the ulimit parameters take effect: （{servers}）.'.format(servers=','.join(list(need_reboot_ips)))))
        return True


