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

import copy
import json
import yaml
import tempfile
from optparse import Values
from uuid import uuid1 as uuid
from singleton_decorator import singleton

from _rpm import Version
from _plugin import PluginType
from _errno import CheckStatus, FixEval
from collections import defaultdict
from const import COMP_JRE
from ssh import LocalClient
from _mirror import MirrorRepositoryType
from _deploy import DeployStatus, DeployConfigStatus
from service.handler.base_handler import BaseHandler
from service.handler.rsa_handler import RSAHandler
from service.common import log, task, const, util
from service.common.task import Serial as serial
from service.common.task import AutoRegister as auto_register
from service.model.service_info import DeployName
from service.common.task import TaskStatus, TaskResult
from service.model.components import ComponentInfo
from service.model.metadb import RecoverChangeParameter
from service.model.deployments import Parameter, PrecheckTaskResult, TaskInfo, PreCheckInfo, RecoverAdvisement, PreCheckResult, ComponentInfo as DeployComponentInfo
from service.model.component_change import ComponentChangeInfo, BestComponentInfo, ComponentChangeConfig, ComponentsChangeInfoDisplay, ComponentChangeInfoDisplay, ComponentServer, ComponentsServer, ComponentLog, ComponentDepends, ConfigPath


@singleton
class ComponentChangeHandler(BaseHandler):

    def get_components(self, component_filter=const.VERSION_FILTER):
        local_packages = self.obd.mirror_manager.local_mirror.get_all_pkg_info()
        remote_packages = list()
        remote_mirrors = self.obd.mirror_manager.get_remote_mirrors()
        for mirror in remote_mirrors:
            remote_packages.extend(mirror.get_all_pkg_info())
        local_packages.sort()
        remote_packages.sort()
        local_pkg_idx = len(local_packages) - 1
        remote_pkg_idx = len(remote_packages) - 1
        component_dict = defaultdict(list)
        while local_pkg_idx >= 0 and remote_pkg_idx >= 0:
            local_pkg = local_packages[local_pkg_idx]
            remote_pkg = remote_packages[remote_pkg_idx]
            if local_pkg >= remote_pkg:
                size = getattr(local_pkg, 'size', const.PKG_ESTIMATED_SIZE[local_pkg.name])
                size = const.PKG_ESTIMATED_SIZE[local_pkg.name] if not size else size
                component_dict[local_pkg.name].append(
                    ComponentInfo(version=local_pkg.version, md5=local_pkg.md5, release=local_pkg.release,
                                  arch=local_pkg.arch, type=MirrorRepositoryType.LOCAL.value,
                                  estimated_size=size))
                local_pkg_idx -= 1
            else:
                if len(component_dict[remote_pkg.name]) > 0 and component_dict[remote_pkg.name][-1].md5 == remote_pkg.md5:
                    log.get_logger().debug("already found local package %s", remote_pkg)
                else:
                    size = getattr(remote_pkg, 'size', const.PKG_ESTIMATED_SIZE[remote_pkg.name])
                    size = const.PKG_ESTIMATED_SIZE[remote_pkg.name] if not size else size
                    component_dict[remote_pkg.name].append(
                        ComponentInfo(version=remote_pkg.version, md5=remote_pkg.md5, release=remote_pkg.release,
                                      arch=remote_pkg.arch, type=MirrorRepositoryType.REMOTE.value,
                                      estimated_size=size))
                remote_pkg_idx -= 1
        if local_pkg_idx >= 0:
            for pkg in local_packages[local_pkg_idx::-1]:
                size = getattr(pkg, 'size', const.PKG_ESTIMATED_SIZE[pkg.name])
                size = const.PKG_ESTIMATED_SIZE[pkg.name] if not size else size
                component_dict[pkg.name].append(
                    ComponentInfo(version=pkg.version, md5=pkg.md5, release=pkg.release, arch=pkg.arch, type=MirrorRepositoryType.LOCAL.value,
                                estimated_size=size))
        if remote_pkg_idx >= 0:
            for pkg in remote_packages[remote_pkg_idx::-1]:
                size = getattr(pkg, 'size', const.PKG_ESTIMATED_SIZE[pkg.name])
                size = const.PKG_ESTIMATED_SIZE[pkg.name] if not size else size
                component_dict[pkg.name].append(
                    ComponentInfo(version=pkg.version, md5=pkg.md5, release=pkg.release, arch=pkg.arch, type=MirrorRepositoryType.REMOTE.value,
                                estimated_size=size))
        for component, version in component_filter.items():
            if component in component_dict.keys():
                log.get_logger().debug("filter component: {0} above version: {1}".format(component, version))
                log.get_logger().debug("original components: {0}".format(component_dict[component]))
                component_dict[component] = list(filter(lambda c: Version(c.version) >= Version(version), component_dict[component]))
                log.get_logger().debug("filtered components: {0}".format(component_dict[component]))
        return component_dict

    def get_deployments_name(self):
        deploys = self.obd.deploy_manager.get_deploy_configs()
        log.get_logger().info('deploys: %s' % deploys)
        ret = []
        for deploy in deploys:
            deploy_config = deploy.deploy_config
            deploy_info = deploy.deploy_info
            if deploy.deploy_info.status == DeployStatus.STATUS_RUNNING and deploy.deploy_info.config_status == DeployConfigStatus.UNCHNAGE:
                create_data = deploy_info.create_date if deploy_info.create_date else ''
                if const.OCEANBASE in deploy_config.components.keys():
                    cluster_config = deploy_config.components[const.OCEANBASE]
                    deploy_name = DeployName(name=deploy.name, deploy_user=deploy_config.user.username, ob_servers=[server.ip for server in cluster_config.servers], ob_version=deploy_info.components[const.OCEANBASE]['version'], create_date=create_data)
                    self.context['ob_servers'][deploy.name] = cluster_config.servers
                    ret.append(deploy_name)
                if const.OCEANBASE_CE in deploy_config.components.keys():
                    cluster_config = deploy_config.components[const.OCEANBASE_CE]
                    deploy_name = DeployName(name=deploy.name, deploy_user=deploy_config.user.username, ob_servers=[server.ip for server in cluster_config.servers], ob_version=deploy_info.components[const.OCEANBASE_CE]['version'], create_date=create_data)
                    self.context['ob_servers'][deploy.name] = cluster_config.servers
                    ret.append(deploy_name)
        return ret

    def get_deployment_info(self, name):
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        self.obd.set_deploy(deploy)

        deploy_config = deploy.deploy_config
        deploy_info = deploy.deploy_info
        components = deploy_config.components.keys()
        component_change_info = ComponentChangeInfo(component_list=[])
        for component in components:
            version = deploy_info.components[component]['version']
            cluster_config = deploy_config.components[component]
            if component == const.OCEANBASE or component == const.OCEANBASE_CE:
                default_config = cluster_config.get_global_conf_with_default()
                appname = default_config.get('appname', '')
                self.context['ob_component'][name] = component
                self.context['ob_version'][name] = version
                self.context['appname'][name] = appname
                continue
            component_change_info.component_list.append(BestComponentInfo(component_name=component, version=version, deployed=1, node=', '.join([server.ip for server in cluster_config.servers])))

        component_dict = self.get_components()
        undeployed_components = set(list(const.CHANGED_COMPONENTS)) - set(components)
        for component in undeployed_components:
            component_change_info.component_list.append(BestComponentInfo(component_name=component, deployed=0, component_info=component_dict[component]))
        self.context['component_change_info'][name] = component_change_info
        return component_change_info

    def get_deployment_depends(self, name):
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        self.obd.set_deploy(deploy)
        deploy_config = deploy.deploy_config
        components = deploy_config.components.keys()
        component_depends = []
        for component in components:
            cluster_config = deploy_config.components[component]
            depends = list(cluster_config.depends)
            component_depends.append(ComponentDepends(component_name=component, depends=depends))
        return component_depends

    def generate_component_config(self, config, component_name, ext_keys=[], depend_component=[], ob_servers=None):
        comp_config = dict()
        input_comp_config = getattr(config, component_name)
        config_dict = input_comp_config.dict()
        for key in config_dict:
            if config_dict[key] and key in {'servers', 'version', 'package_hash', 'release'}:
                if ob_servers and key == 'servers':
                    config_dict['servers'] = list()
                    for server in ob_servers:
                        if server._name:
                            config_dict['servers'].append({'name': server.name, 'ip': server.ip})
                        else:
                            config_dict['servers'].append(server.ip)
                comp_config[key] = config_dict[key]

        if 'global' not in comp_config.keys():
            comp_config['global'] = dict()

        comp_config['global']['home_path'] = config.home_path + '/' + component_name
        for key in ext_keys:
            if config_dict[key]:
                if key == 'admin_passwd':
                    passwd = RSAHandler().decrypt_private_key(config_dict[key])
                    comp_config['global'][key] = passwd
                    continue
                if key == 'obproxy_sys_password':
                    passwd = RSAHandler().decrypt_private_key(config_dict[key])
                    comp_config['global'][key] = passwd
                    continue
                comp_config['global'][key] = config_dict[key]

        if depend_component:
            comp_config['depends'] = list()
            comp_config['depends'].extend(depend_component)

        if input_comp_config.parameters:
            for parameter in input_comp_config.parameters:
                if not parameter.adaptive:
                    if parameter.key == 'http_basic_auth_password':
                        passwd = RSAHandler().decrypt_private_key(config_dict[parameter.key])
                        comp_config['global'][parameter.key] = passwd
                        continue
                    comp_config['global'][parameter.key] = parameter.value
        return comp_config

    def create_component_change_path(self, name, config, mem_save=True):
        cluster_config = {}

        if config.obconfigserver:
            cluster_config[config.obconfigserver.component] = self.generate_component_config(config, 'obconfigserver', ['listen_port'])
        if config.obproxy:
            if not config.obproxy.cluster_name and self.context['appname'][name]:
                config.obproxy.cluster_name = self.context['appname'][name]
            cluster_config[config.obproxy.component] = self.generate_component_config(config, 'obproxy', ['cluster_name', 'prometheus_listen_port', 'listen_port', 'rpc_listen_port', 'obproxy_sys_password'], [self.context['ob_component'][name]])
        if config.obagent:
            cluster_config[config.obagent.component] = self.generate_component_config(config, config.obagent.component, ['monagent_http_port', 'mgragent_http_port'], [self.context['ob_component'][name]], self.context['ob_servers'][name])
        if config.ocpexpress:
            depend_component = [self.context['ob_component'][name]]
            if config.obproxy or const.OBPROXY_CE in self.obd.deploy.deploy_config.components:
                depend_component.append(const.OBPROXY_CE)
            if const.OBPROXY in self.obd.deploy.deploy_config.components:
                depend_component.append(const.OBPROXY)
            if config.obagent or const.OBAGENT in self.obd.deploy.deploy_config.components:
                depend_component.append(const.OBAGENT)
            cluster_config[config.ocpexpress.component] = self.generate_component_config(config, 'ocpexpress', ['port', 'admin_passwd'], depend_component)

        with tempfile.NamedTemporaryFile(delete=False, prefix="component_change", suffix=".yaml", mode="w", encoding="utf-8") as f:
            f.write(yaml.dump(cluster_config, sort_keys=False))
            cluster_config_yaml_path = f.name
        log.get_logger().info('dump config from path: %s' % cluster_config_yaml_path)
        if mem_save:
            self.context['component_change_deployment_info'][name] = config
            self.context['component_change_path'][name] = cluster_config_yaml_path
        return cluster_config_yaml_path

    def create_component_change_deployment(self, name, path, mode, mem_save=True):
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        self.obd.set_deploy(deploy)
        deploy_config = self.obd.deploy.deploy_config
        deploy_info = self.obd.deploy.deploy_info
        deploy_config.set_undumpable()
        self.context['mode'][name] = mode
        if mode == 'add_component':
            current_repositories = self.obd.load_local_repositories(deploy_info)
            self.obd.set_repositories(current_repositories)
            self.obd.search_param_plugin_and_apply(current_repositories, deploy_config)
            if not deploy_config.add_components(path):
                raise Exception('add component failed')
            self.obd.set_deploy(deploy)
            if mem_save:
                self.context['new_obd'][name] = self.obd.fork(deploy=self.obd.deploy_manager.create_deploy_config(name + 'component_change', path))
            return True
        if mode == 'scale_out':
            pass

    def get_config_path(self, name):
        return ConfigPath(config_path=self.context['component_change_path'][name])

    @serial("component_change_precheck")
    def component_change_precheck(self, name, background_tasks):
        task_manager = task.get_task_manager()
        task_info = task_manager.get_task_info(name, task_type="component_change_precheck")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception(f"task {name} exists and not finished")

        deploy_config = self.obd.deploy.deploy_config
        pkgs, repositories, errors = self.obd.search_components_from_mirrors(deploy_config, only_info=True, components=deploy_config.added_components)
        if errors:
            raise Exception("{}".format('\n'.join(errors)))
        repositories.extend(pkgs)
        repositories = self.obd.sort_repository_by_depend(repositories, deploy_config)
        self.context['new_obd'][name].set_repositories(repositories)
        self.context['origin_repository'][name] = self.obd.repositories
        all_repositories = self.obd.repositories + repositories
        self.obd.set_repositories(all_repositories)
        self.obd._call_stdio('start_loading', 'Get added repositories and plugins')
        self.obd.search_param_plugin_and_apply(repositories, deploy_config)
        self.obd._call_stdio('stop_loading', 'succeed')

        start_check_plugins = self.obd.search_py_script_plugin(repositories, 'start_check', no_found_act='warn')
        self._precheck(name, repositories, start_check_plugins, init_check_status=True)
        info = task_manager.get_task_info(name, task_type="component_change_precheck")
        if info is not None and info.exception is not None:
            exception = copy.deepcopy(info.exception)
            info.exception = None
            raise exception
        task_manager.del_task_info(name, task_type="component_change_precheck")
        background_tasks.add_task(self._precheck, name, repositories, start_check_plugins, init_check_status=False)
        self.obd.set_deploy(self.obd.deploy)

    def _init_check_status(self, check_key, servers, check_result={}):
        check_status = defaultdict(lambda: defaultdict(lambda: None))
        for server in servers:
            if server in check_result:
                status = check_result[server]
            else:
                status = CheckStatus()
            check_status[server] = {check_key: status}
        return check_status

    @auto_register('component_change_precheck')
    def _precheck(self, name, repositories, start_check_plugins, init_check_status=False):
        if init_check_status:
            self._init_precheck(repositories, start_check_plugins)
        else:
            self._do_precheck(repositories, start_check_plugins)

    def _init_precheck(self, repositories, start_check_plugins):
        log.get_logger().info('init precheck')
        param_check_status = {}
        servers_set = set()
        for repository in repositories:
            if repository not in start_check_plugins:
                continue
            repository_status = {}
            res = self.obd.call_plugin(start_check_plugins[repository], repository, init_check_status=True, work_dir_check=True, clients={})
            if not res and res.get_return("exception"):
                raise res.get_return("exception")
            servers = self.obd.deploy.deploy_config.components.get(repository.name).servers
            for server in servers:
                repository_status[server] = {'param': CheckStatus()}
                servers_set.add(server)
            param_check_status[repository.name] = repository_status

        self.context['component_change_deployment']['param_check_status'] = param_check_status
        server_connect_status = {}
        for server in servers_set:
            server_connect_status[server] = {'ssh': CheckStatus()}
        self.context['component_change_deployment']['connect_check_status'] = {'ssh': server_connect_status}
        self.context['component_change_deployment']['servers_set'] = servers_set

    def _do_precheck(self, repositories, start_check_plugins):
        self.context['component_change_deployment']['chcek_pass'] = True
        log.get_logger().info('start precheck')
        log.get_logger().info('ssh check')
        ssh_clients, connect_status = self.obd.get_clients_with_connect_status(self.obd.deploy.deploy_config, repositories, fail_exit=False)
        log.get_logger().info('connect_status: ', connect_status)
        check_status = self._init_check_status('ssh', self.context['component_change_deployment']['servers_set'], connect_status)
        self.context['component_change_deployment']['connect_check_status'] = {'ssh': check_status}
        for k, v in connect_status.items():
            if v.status == v.FAIL:
                self.context['component_change_deployment_ssh']['ssh'] = False
                log.get_logger().info('ssh check failed')
                return
        log.get_logger().info('ssh check succeed')
        gen_config_plugins = self.obd.search_py_script_plugin(repositories, 'generate_config')
        if len(repositories) != len(gen_config_plugins):
            raise Exception("param_check: config error, check stop!")

        param_check_status, check_pass = self.obd.deploy_param_check_return_check_status(repositories, self.obd.deploy.deploy_config, gen_config_plugins=gen_config_plugins)
        param_check_status_result = {}
        for comp_name in param_check_status:
            status_res = param_check_status[comp_name]
            param_check_status_result[comp_name] = self._init_check_status('param', status_res.keys(), status_res)
        self.context['component_change_deployment']['param_check_status'] = param_check_status_result

        log.get_logger().debug('precheck param check status: %s' % param_check_status)
        log.get_logger().debug('precheck param check status res: %s' % check_pass)
        if not check_pass:
            self.context['component_change_deployment']['chcek_pass'] = False
            return

        components = [comp_name for comp_name in self.obd.deploy.deploy_config.components.keys()]
        for repository in repositories:
            ret = self.obd.call_plugin(gen_config_plugins[repository], repository, generate_check=False, generate_consistent_config=True, auto_depend=True, components=components)
            if ret is None:
                raise Exception("generate config error")
            elif not ret and ret.get_return("exception"):
                raise ret.get_return("exception")

        log.get_logger().info('generate config succeed')
        ssh_clients = self.obd.get_clients(self.obd.deploy.deploy_config, repositories)
        for repository in repositories:
            log.get_logger().info('begin start_check: %s' % repository.name)
            java_check = True
            if repository.name == const.OCP_EXPRESS:
                jre_name = COMP_JRE
                install_plugin = self.obd.search_plugin(repository, PluginType.INSTALL)
                if install_plugin and jre_name in install_plugin.requirement_map(repository):
                    version = install_plugin.requirement_map(repository)[jre_name].version
                    min_version = install_plugin.requirement_map(repository)[jre_name].min_version
                    max_version = install_plugin.requirement_map(repository)[jre_name].max_version
                    if len(self.obd.search_images(jre_name, version=version, min_version=min_version, max_version=max_version)) > 0:
                        java_check = False
            res = self.obd.call_plugin(start_check_plugins[repository], repository, init_check_status=False, work_dir_check=True, precheck=True, java_check=java_check, clients=ssh_clients)
            if not res and res.get_return("exception"):
                raise res.get_return("exception")
            log.get_logger().info('end start_check: %s' % repository.name)

    def get_precheck_result(self, name):
        precheck_result = PreCheckResult()
        deploy = self.obd.deploy
        if not deploy:
            deploy = self.obd.deploy_manager.get_deploy_config(name)
            self.obd.set_deploy(deploy)
        components = deploy.deploy_config._added_components
        info = []
        total = 0
        finished = 0
        all_passed = True
        param_check_status = None
        connect_check_status = None
        if 'component_change_deployment' in self.context.keys():
            param_check_status = self.context['component_change_deployment']['param_check_status']
            connect_check_status = self.context['component_change_deployment']['connect_check_status']
        connect_check_status_flag = True
        for component in components:
            namespace_union = {}
            namespace = self.obd.get_namespace(component)
            if namespace:
                variables = namespace.variables
                if 'start_check_status' in variables.keys():
                    namespace_union = util.recursive_update_dict(namespace_union, variables.get('start_check_status'))
            if param_check_status is not None:
                namespace_union = util.recursive_update_dict(namespace_union, param_check_status[component])
            if connect_check_status is not None and connect_check_status_flag and 'ssh' in connect_check_status.keys():
                namespace_union = util.recursive_update_dict(namespace_union, connect_check_status['ssh'])
                connect_check_status_flag = False

            if namespace_union:
                for server, result in namespace_union.items():
                    if result is None:
                        log.get_logger().warn("precheck for server: {} is None".format(server.ip))
                        continue
                    all_passed, finished, total = self.parse_precheck_result(all_passed, component, finished, info, server, total, result)
        info.sort(key=lambda p: p.status)

        task_info = task.get_task_manager().get_task_info(name, task_type="precheck")
        if task_info is not None:
            if task_info.status == TaskStatus.FINISHED:
                precheck_result.status = task_info.result
                if task_info.result == TaskResult.FAILED:
                    precheck_result.message = '{}'.format(task_info.exception)
            else:
                precheck_result.status = TaskResult.RUNNING
        precheck_result.info = info
        precheck_result.total = total
        if total == 0:
            all_passed = False
        precheck_result.all_passed = all_passed
        precheck_result.finished = total if precheck_result.status == TaskResult.SUCCESSFUL else finished
        if total == finished:
            precheck_result.status = TaskResult.SUCCESSFUL
        if all_passed == False and (self.context['component_change_deployment']['chcek_pass'] == False or self.context['component_change_deployment_ssh']['ssh'] == False) and precheck_result.finished >= len(components):
            precheck_result.status = TaskResult.SUCCESSFUL
        return precheck_result

    def parse_precheck_result(self, all_passed, component, finished, info, server, total, result):
        for k, v in result.items():
            total += 1
            check_info = PreCheckInfo(name='{}:{}'.format(component, k), server=server.ip)
            if v.status == v.PASS:
                check_info.result = PrecheckTaskResult.PASSED
                check_info.status = TaskStatus.FINISHED
                finished += 1
            elif v.status == v.FAIL:
                check_info.result = PrecheckTaskResult.FAILED
                check_info.status = TaskStatus.FINISHED
                all_passed = False

                check_info.code = v.error.code
                check_info.description = v.error.msg
                check_info.recoverable = len(v.suggests) > 0 and v.suggests[0].auto_fix
                msg = v.suggests[0].msg if len(v.suggests) > 0 and v.suggests[0].msg is not None else ''
                advisement = RecoverAdvisement(description=msg)
                check_info.advisement = advisement

                finished += 1
            elif v.status == v.WAIT:
                check_info.status = TaskStatus.PENDING
                all_passed = False
            info.append(check_info)
        return all_passed, finished, total

    def recover(self, name):
        log.get_logger().info('recover config')
        deploy = self.obd.deploy
        if not deploy:
            raise Exception('error get component change conf')

        components = deploy.deploy_config.components
        param_check_status = {}
        if 'component_change_deployment' in self.context.keys():
            param_check_status = self.context['component_change_deployment']['param_check_status']
        recover_change_parameter_list = []
        for component in components:
            namespace_union = {}
            if component in self.obd.namespaces:
                namespace = self.obd.get_namespace(component)
                if namespace:
                    util.recursive_update_dict(namespace_union, namespace.variables.get('start_check_status', {}))
                util.recursive_update_dict(namespace_union, param_check_status.get('component', {}))

                for server, precheck_result in namespace_union.items():
                    if precheck_result is None:
                        log.get_logger().warn('component : {},precheck_result is None'.format(component))
                        continue
                    for k, v in precheck_result.items():
                        if v.status == v.FAIL and v.suggests is not None and v.suggests[0].auto_fix and v.suggests[0].fix_eval:
                            for fix_eval in v.suggests[0].fix_eval:
                                if fix_eval.operation == FixEval.SET:
                                    config_json = None
                                    old_value = None
                                    if fix_eval.is_global:
                                        deploy.deploy_config.update_component_global_conf(name, fix_eval.key, fix_eval.value, save=False)
                                    else:
                                        deploy.deploy_config.update_component_server_conf(name, server, fix_eval.key, fix_eval.value, save=False)
                                else:
                                    config_json, old_value = self.modify_config(component, name, fix_eval)

                                if config_json is None:
                                    log.get_logger().warn('config json is None')
                                    continue
                                recover_change_parameter = RecoverChangeParameter(name=fix_eval.key, old_value=old_value, new_value=fix_eval.value)
                                recover_change_parameter_list.append(recover_change_parameter)
                                self.context['component_change_deployment_info'][name] = ComponentChangeConfig(**json.loads(json.dumps(config_json)))
                self.recreate_deployment(name)

        return recover_change_parameter_list

    def recreate_deployment(self, name):
        log.get_logger().info('recreate component_change deployment')
        config = self.context['component_change_deployment_info'][name]
        log.get_logger().info('config: %s' % config)
        if config is not None:
            cluster_config_yaml_path = self.create_component_change_path(name, config)
            self.create_component_change_deployment(name, cluster_config_yaml_path, self.context['mode'][name])

    def modify_config(self, component, name, fix_eval):
        log.get_logger().info('modify component_change config')
        if fix_eval.key == "parameters":
            raise Exception("try to change parameters")
        config = self.context['component_change_deployment_info'][name] if self.context['component_change_deployment_info'] is not None else None
        if config is None:
            log.get_logger().warn("config is none, no need to modify")
            raise Exception('config is none')
        log.get_logger().info('%s component_change config: %s' % (name, config))
        config = config['config']
        config_dict = config.dict()
        if config_dict['components'] is None:
            log.get_logger().warn("component is none, no need to modify")
            raise Exception('component is none')
        old_value = None
        for value in config_dict['components'].values():
            if value is not None and 'component' in value.keys() and value['component'] == component:
                log.get_logger().info('old value: %s' % value)
                if fix_eval.key in value.keys():
                    log.get_logger().info('new value: %s' % fix_eval.value)
                    old_value = value[fix_eval.key]
                    value[fix_eval.key] = fix_eval.value
                elif "parameters" in value.keys() and value["parameters"] is not None:
                    log.get_logger().info('new value: %s' % fix_eval.value)
                    for parameter_dict in value["parameters"]:
                        parameter = Parameter(**parameter_dict)
                        if parameter.key == fix_eval.key:
                            if fix_eval.operation == FixEval.DEL:
                                old_value = parameter.value
                                value["parameters"].remove(parameter_dict)
                            else:
                                parameter_dict[fix_eval.key] = fix_eval.value
                return config_dict, old_value
        return None, None

    @serial("component_change")
    def add_components(self, name, background_tasks):
        task_manager = task.get_task_manager()
        task_info = task_manager.get_task_info(name, task_type="component_change")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception("task {0} exists and not finished".format(name))
        task_manager.del_task_info(name, task_type="component_change")
        background_tasks.add_task(self._add_components, name)

    @auto_register("component_change")
    def _add_components(self, name):
        log.get_logger().info("clean io buffer before start install")
        self.buffer.clear()
        log.get_logger().info("clean namespace for init")
        for component in self.context['new_obd'][name].deploy.deploy_config.components:
            for plugin in const.INIT_PLUGINS:
                self.obd.namespaces[component].set_return(plugin, None)
        log.get_logger().info("clean namespace for start")
        for component in self.context['new_obd'][name].deploy.deploy_config.components:
            for plugin in const.START_PLUGINS:
                self.obd.namespaces[component].set_return(plugin, None)

        repositories, install_plugins = self.obd.search_components_from_mirrors_and_install(self.obd.deploy.deploy_config, components=self.obd.deploy.deploy_config.added_components)
        if not repositories or not install_plugins:
            return False
        self.context['new_obd'][name].set_repositories(repositories)
        repositories = self.context['origin_repository'][name] + repositories
        self.obd.set_repositories(repositories)
        scale_out_check_plugins = self.obd.search_py_script_plugin(repositories, 'scale_out_check', no_found_act='ignore')

        trace_id = str(uuid())
        self.context['component_trace']['deploy'] = trace_id
        ret = self.obd.stdio.init_trace_logger(self.obd.stdio.log_path, trace_id=trace_id, recreate=True)
        if ret is False:
            log.get_logger().warn("component deploy log init error")

        check_pass = True
        for repository in repositories:
            if repository not in scale_out_check_plugins:
                continue
            ret = self.obd.call_plugin(scale_out_check_plugins[repository], repository)
            if not ret:
                self.obd._call_stdio('verbose', '%s scale out check failed.' % repository.name)
                check_pass = False
        if not check_pass:
            log.get_logger().error('component scale out check failed')
            return False

        succeed = True
        # prepare for added components
        for repository in repositories:
            if repository in scale_out_check_plugins:
                plugin_return = self.obd.get_namespace(repository.name).get_return(scale_out_check_plugins[repository].name)
                plugins_list = plugin_return.get_return('plugins', [])
                for plugin_name in plugins_list:
                    plugin = self.obd.search_py_script_plugin([repository], plugin_name)
                    if repository in plugin:
                        succeed = succeed and self.obd.call_plugin(plugin[repository], repository)
        if not succeed:
            log.get_logger().error('scale out check return plugin failed')
            return False

        self.obd._call_stdio('verbose', 'Start to deploy additional servers')
        if not self.obd._deploy_cluster(self.obd.deploy, self.context['new_obd'][name].repositories, dump=False):
            log.get_logger().error('failed to deploy additional servers')
            return False

        self.obd.deploy.deploy_config.enable_mem_mode()
        self.obd._call_stdio('verbose', 'Start to start additional servers')
        error_repositories = []
        succeed_repositories = []
        for repository in self.context['new_obd'][name].repositories:
            opt = Values()
            self.obd.set_options(opt)
            trace_id = str(uuid())
            self.context['component_trace'][repository.name] = trace_id
            ret = self.obd.stdio.init_trace_logger(self.obd.stdio.log_path, trace_id=trace_id, recreate=True)
            if ret is False:
                log.get_logger().error("component: {}, start log init error".format(repository.name))
            if not self.obd._start_cluster(self.obd.deploy, [repository]):
                log.get_logger().error("failed to start component: %s", repository.name)
                error_repositories.append(repository.name)
                continue
            succeed_repositories.append(repository.name)
        dump_components = list(set(succeed_repositories) - set(error_repositories))
        log.get_logger().info('error components: %s' % ','.join(error_repositories))
        if error_repositories:
            log.get_logger().info('start dump succeed component: %s' % ','.join(dump_components))
            for component in error_repositories:
                if component in self.obd.deploy.deploy_config._src_data:
                    del self.obd.deploy.deploy_config._src_data[component]
                    del self.obd.deploy.deploy_config.components[component]
                if component in self.obd.deploy.deploy_info.components:
                    del self.obd.deploy.deploy_info.components[component]

        self.obd.deploy.deploy_config.set_dumpable()
        for repository in repositories:
            if repository.name not in error_repositories:
                self.obd.deploy.use_model(repository.name, repository, False)

        if not self.obd.deploy.deploy_config.dump():
            self.obd._call_stdio('error', 'Failed to dump new deploy config')
            log.get_logger().error("failed to dump new deploy config")
            return False
        self.obd.deploy.dump_deploy_info()
        self.obd.set_deploy(self.obd.deploy)

    def scale_out(self, name, background_tasks):
        pass

    def get_component_change_task_info(self, name):
        task_info = task.get_task_manager().get_task_info(name, task_type="component_change")
        if task_info is None:
            raise Exception("task {0} not found".format(name))
        components = self.context['new_obd'][name].deploy.deploy_config.components
        total_count = (len(const.START_PLUGINS) + len(const.INIT_PLUGINS)) * len(components)
        finished_count = 1
        current = ""
        task_result = TaskResult.RUNNING
        info_dict = dict()

        for component in components:
            info_dict[component] = DeployComponentInfo(component=component, status=TaskStatus.PENDING, result=TaskResult.RUNNING)
            if component in self.obd.namespaces:
                for plugin in const.INIT_PLUGINS:
                    if self.obd.namespaces[component].get_return(plugin).value is not None:
                        info_dict[component].status = TaskStatus.RUNNING
                        finished_count += 1
                        current = "{0}: {1} finished".format(component, plugin)
                        if not self.obd.namespaces[component].get_return(plugin):
                            info_dict[component].result = TaskResult.FAILED

        for component in components:
            for plugin in const.START_PLUGINS:
                if component not in self.obd.namespaces:
                    break
                if self.obd.namespaces[component].get_return(plugin).value is not None:
                    info_dict[component].status = TaskStatus.RUNNING
                    finished_count += 1
                    current = "{0}: {1} finished".format(component, plugin)
                    if not self.obd.namespaces[component].get_return(plugin):
                        info_dict[component].result = TaskResult.FAILED
                    else:
                        if plugin == const.START_PLUGINS[-1]:
                            info_dict[component].result = TaskResult.SUCCESSFUL

        if task_info.status == TaskStatus.FINISHED:
            task_result = task_info.result
            for v in info_dict.values():
                v.status = TaskStatus.FINISHED
                if v.result != TaskResult.SUCCESSFUL:
                    v.result = TaskResult.FAILED
        info_list = list()
        for info in info_dict.values():
            info_list.append(info)
        msg = "" if task_info.result == TaskResult.SUCCESSFUL else '{0}'.format(task_info.exception)
        if all(info.result == TaskResult.SUCCESSFUL for info in info_list):
            for info in info_list:
                info.status = TaskStatus.FINISHED
            status = TaskResult.SUCCESSFUL
        elif any(info.result == TaskResult.RUNNING for info in info_list):
            status = TaskResult.RUNNING
        else:
            for info in info_list:
                info.status = TaskStatus.FINISHED
            status = TaskResult.FAILED
        return TaskInfo(total=total_count, finished=finished_count if task_result != TaskResult.SUCCESSFUL else total_count, current=current, status=status, info=info_list, msg=msg)

    def get_component_change_log_by_component(self, component_name, mode):
        data = []
        stdout = ''
        for component in component_name:
            trace_id = self.context['component_trace'][component]
            cmd = 'grep -h "\[{}\]" {}* | sed "s/\[{}\] //g" '.format(trace_id, self.obd.stdio.log_path, trace_id)
            stdout = LocalClient.execute_command(cmd).stdout
            if not stdout:
                trace_id = self.context['component_trace']['deploy']
                cmd = 'grep -h "\[{}\]" {}* | sed "s/\[{}\] //g" '.format(trace_id, self.obd.stdio.log_path, trace_id)
                stdout = LocalClient.execute_command(cmd).stdout
            data.append(ComponentLog(component_name=component, log=stdout))
        if mode == 'add_component':
            return stdout
        if mode == 'del_component':
            return data

    def get_component_change_detail(self, name):
        config = self.context['component_change_deployment_info'][name]
        if not config:
            raise Exception(f'error get config for deploy:{name}')
        data = ComponentsChangeInfoDisplay(components_change_info=[])
        deploy_config = self.obd.deploy.deploy_config
        if config.obproxy:
            if config.obproxy.component in deploy_config.components:
                cluster_config = deploy_config.components[config.obproxy.component]
                original_global_conf = cluster_config.get_original_global_conf()
                component_change_display = ComponentChangeInfoDisplay(component_name=config.obproxy.component)
                server = config.obproxy.servers[0]
                port = str(config.obproxy.listen_port)
                password = original_global_conf.get('obproxy_sys_password', '')
                component_change_display.address = server + ':' + port
                component_change_display.username = 'root@proxysys'
                component_change_display.password = ''
                component_change_display.access_string = f"obclient -h{server} -P{port} -uroot@proxysys -Doceanbase -A"
                data.components_change_info.append(component_change_display)
        if config.obagent:
            component_change_display = ComponentChangeInfoDisplay(component_name=config.obagent.component)
            component_change_display.address = ''
            component_change_display.username = ''
            component_change_display.password = ''
            component_change_display.access_string = ''
            data.components_change_info.append(component_change_display)
        if config.obconfigserver:
            component_change_display = ComponentChangeInfoDisplay(component_name=config.obconfigserver.component)
            server = config.obconfigserver.servers[0]
            port = str(config.obconfigserver.listen_port)
            component_change_display.address = ''
            component_change_display.username = ''
            component_change_display.password = ''
            component_change_display.access_string = f"curl -s 'http://{server}:{port}/services?Action=GetObProxyConfig'"
            data.components_change_info.append(component_change_display)
        if config.ocpexpress:
            component_change_display = ComponentChangeInfoDisplay(component_name=config.ocpexpress.component)
            if config.ocpexpress.component in deploy_config.components:
                cluster_config = deploy_config.components[config.ocpexpress.component]
                original_global_conf = cluster_config.get_original_global_conf()
                component_change_display.address = 'http://' + config.ocpexpress.servers[0] + ':' + str(config.ocpexpress.port)
                component_change_display.username = 'admin'
                component_change_display.password = ''
                component_change_display.access_string = 'http://' + config.ocpexpress.servers[0] + ':' + str(config.ocpexpress.port)
                data.components_change_info.append(component_change_display)
        return data

    def node_check(self, name, components):
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        if not deploy:
            raise Exception(f'error get deploy for name: {name}')
        self.obd.set_deploy(deploy)
        deploy_config = deploy.deploy_config
        deploy_info = deploy.deploy_info
        all_repositories = self.obd.load_local_repositories(deploy_info)
        self.obd.set_repositories(all_repositories)
        repositories = self.obd.get_component_repositories(deploy_info, components)
        self.obd.search_param_plugin_and_apply(all_repositories, deploy_config)
        ssh_clients, connect_status = self.obd.get_clients_with_connect_status(deploy_config, repositories, fail_exit=False)
        failed_servers = []
        for k, v in connect_status.items():
            if v.status == v.FAIL:
                failed_servers.append(k)
        componets_server = ComponentsServer(components_server=[])
        for component in components:
            cluster_config = deploy_config.components[component]
            component_server = ComponentServer(component_name=component, failed_servers=[server.ip for server in list(set(cluster_config.servers) & set(failed_servers))])
            componets_server.components_server.append(component_server)
        return componets_server

    @serial("del_component")
    def del_component(self, name, components, force, background_tasks):
        task_manager = task.get_task_manager()
        task_info = task_manager.get_task_info(name, task_type="del_component")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception("task {0} exists and not finished".format(name))
        task_manager.del_task_info(name, task_type="del_component")
        background_tasks.add_task(self._del_component, name, components, force)

    @auto_register("del_component")
    def _del_component(self, name, components, force):
        self.context['del_component'][name] = components

        deploy = self.obd.deploy_manager.get_deploy_config(name)
        self.obd.set_deploy(deploy)
        deploy_info = deploy.deploy_info
        deploy_config = deploy.deploy_config

        trace_id = str(uuid())
        self.context['component_trace']['deploy'] = trace_id
        ret = self.obd.stdio.init_trace_logger(self.obd.stdio.log_path, trace_id=trace_id, recreate=True)
        if ret is False:
            log.get_logger().warn("component deploy log init error")

        if not components:
            self.obd._call_stdio('error', 'Components is required.')
            log.get_logger().error('Components is required.')
            return False

        deploy_config.set_undumpable()
        self.obd._call_stdio('start_loading', 'Get local repositories and plugins')
        all_repositories = self.obd.load_local_repositories(deploy_info)
        self.obd.set_repositories(all_repositories)
        repositories = self.obd.get_component_repositories(deploy_info, components)
        self.obd.search_param_plugin_and_apply(all_repositories, deploy_config)
        self.obd._call_stdio('stop_loading', 'succeed')

        scale_in_check_plugins = self.obd.search_py_script_plugin(all_repositories, 'scale_in_check', no_found_act='ignore')
        check_pass = True
        for repository in all_repositories:
            if repository not in scale_in_check_plugins:
                continue
            ret = self.obd.call_plugin(scale_in_check_plugins[repository], repository)
            if not ret:
                self.obd._call_stdio('verbose', '%s scale in check failed.' % repository.name)
                log.get_logger().error('%s scale in check failed.' % repository.name)
                check_pass = False
        if not check_pass:
            return False

        if not deploy_config.del_components(components, dryrun=True):
            self.obd._call_stdio('error', 'Failed to delete components for %s' % name)
            log.get_logger().error('Failed to delete components for %s' % name)
            return False

        error_component = []
        for repository in repositories:
            opt = Values()
            setattr(opt, 'force', force)
            self.obd.set_options(opt)
            trace_id = str(uuid())
            self.context['component_trace'][repository.name] = trace_id
            ret = self.obd.stdio.init_trace_logger(self.obd.stdio.log_path, trace_id=trace_id, recreate=True)
            if ret is False:
                log.get_logger().warn("component: {}, start log init error".format(repository.name))

            self.obd._call_stdio('verbose', 'Start to stop target components')
            self.obd.set_repositories([repository])
            if not self.obd._stop_cluster(deploy, [repository], dump=False):
                self.obd._call_stdio('warn', f'failed to stop component {repository.name}')
                error_component.append(repository.name)

            self.obd._call_stdio('verbose', 'Start to destroy target components')
            if not self.obd._destroy_cluster(deploy, [repository], dump=False):
                error_component.append(repository.name)
        if error_component:
            self.obd._call_stdio('warn', 'failed to stop component {}'.format(','.join([r.name for r in error_component])))
            log.get_logger().error('failed to stop component {}'.format(','.join([r.name for r in error_component])))
            return False

        if not deploy_config.del_components(components):
            self.obd._call_stdio('error', 'Failed to delete components for %s' % name)
            log.get_logger().error('Failed to delete components for %s' % name)
            return False

        deploy_config.set_dumpable()
        for repository in repositories:
            deploy.unuse_model(repository.name, False)
        deploy.dump_deploy_info()

        if not deploy_config.dump():
            self.obd._call_stdio('error', 'Failed to dump new deploy config')
            log.get_logger().error('Failed to dump new deploy config')
            return False
        log.get_logger().warn(f"del components({','.join(components)}) success")
        self.obd.set_deploy(self.obd.deploy)

    def get_del_component_task_info(self, name):
        task_info = task.get_task_manager().get_task_info(name, task_type="del_component")
        if task_info is None:
            raise Exception("task {0} not found".format(name))
        components = self.context['del_component'][name]
        if not components:
            return None
        total_count = len(const.DEL_COMPONENT_PLUGINS) * len(components)
        finished_count = 0
        current = ""
        task_result = TaskResult.RUNNING
        info_dict = dict()
        for c in components:
            info_dict[c] = DeployComponentInfo(component=c, status=TaskStatus.PENDING, result=TaskResult.RUNNING)
            for plugin in const.DEL_COMPONENT_PLUGINS:
                if c not in self.obd.namespaces:
                    break
                
                if self.obd.namespaces[c].get_return(plugin).value is not None:
                    info_dict[c].status = TaskStatus.RUNNING
                    finished_count += 1
                    current = "{0}: {1} finished".format(c, plugin)
                    if not self.obd.namespaces[c].get_return(plugin):
                        info_dict[c].result = TaskResult.FAILED
                    else:
                        if plugin == const.DEL_COMPONENT_PLUGINS[-1]:
                            info_dict[c].result = TaskResult.SUCCESSFUL
        if task_info.status == TaskStatus.FINISHED:
            for v in info_dict.values():
                v.status = TaskStatus.FINISHED
                if v.result != TaskResult.SUCCESSFUL:
                    v.result = TaskResult.FAILED

        info_list = list()
        for info in info_dict.values():
            info_list.append(info)
        msg = "" if task_info.result == TaskResult.SUCCESSFUL else '{0}'.format(task_info.exception)
        if all(info.result == TaskResult.SUCCESSFUL for info in info_list):
            status = TaskResult.SUCCESSFUL
            for info in info_list:
                info.status = TaskStatus.FINISHED
        elif any(info.result == TaskResult.RUNNING for info in info_list):
            status = TaskResult.RUNNING
        else:
            status = TaskResult.FAILED
            for info in info_list:
                info.status = TaskStatus.FINISHED
        return TaskInfo(total=total_count, finished=finished_count, current=current, status=status, info=info_list, msg=msg)

    def remove_component(self, name, components):
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        self.obd.set_deploy(deploy)
        deploy_info = deploy.deploy_info
        deploy_config = deploy.deploy_config

        for component in components:
            if component in [const.OCEANBASE_CE, const.OCEANBASE]:
                raise Exception('not support remove oceanbase')

        all_repositories = self.obd.load_local_repositories(deploy_info)
        self.obd.set_repositories(all_repositories)
        repositories = self.obd.get_component_repositories(deploy_info, components)
        self.obd.search_param_plugin_and_apply(all_repositories, deploy_config)

        deploy_config.set_undumpable()
        if not deploy_config.del_components(components):
            log.get_logger().error('Failed to delete components for %s' % name)
            return False
        deploy_config.set_dumpable()

        for repository in repositories:
            deploy.unuse_model(repository.name, False)
        deploy.dump_deploy_info()

        if not deploy_config.dump():
            log.get_logger().error('Failed to dump new deploy config')
            return False
        log.get_logger().info(f"force del components({','.join(components)}) success")
        return components