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

import json
import tempfile
import re
from copy import deepcopy
from collections import defaultdict
from uuid import uuid1 as uuid
from optparse import Values
from singleton_decorator import singleton
import yaml
from _deploy import DeployStatus, DeployConfigStatus
from _errno import CheckStatus, FixEval
from _plugin import PluginType
from _rpm import Version
from const import COMP_JRE, COMP_OCP_EXPRESS
from service.api.v1.deployments import DeploymentInfo
from service.handler.base_handler import BaseHandler
from service.handler.rsa_handler import RSAHandler
from service.model.deployments import DeploymentConfig, PreCheckResult, RecoverChangeParameter, TaskInfo, \
    ComponentInfo, PrecheckTaskResult, \
    DeployMode, ConnectionInfo, PreCheckInfo, RecoverAdvisement, DeploymentReport, Deployment, Auth, DeployConfig, \
    DeploymentStatus, Parameter, ScenarioType

from service.common import log, task, util, const
from service.common.task import TaskStatus, TaskResult
from service.common.task import Serial as serial
from service.common.task import AutoRegister as auto_register
from ssh import LocalClient
from tool import COMMAND_ENV
from const import TELEMETRY_COMPONENT_OB
from _environ import ENV_TELEMETRY_REPORTER


@singleton
class DeploymentHandler(BaseHandler):
    def get_deployment_by_name(self, name):
        deployment = self.obd.deploy_manager.get_deploy_config(name)
        if deployment is None:
            return None
        deployment_info = DeploymentInfo()
        deployment_info.name = deployment.name
        deployment_info.config_path = deployment.config_dir
        deployment_info.status = deployment.deploy_info.status.value.upper()
        deployment_info.config = self.context['deployment'][deployment.name] if self.context[
                                                                                    'deployment'] is not None else None
        deployment_info_copy = deepcopy(deployment_info)
        if deployment_info_copy.config and deployment_info_copy.config.auth and deployment_info_copy.config.auth.password:
            deployment_info_copy.config.auth.password = ''
        if deployment_info_copy.config and deployment_info_copy.config.components and deployment_info_copy.config.components.oceanbase and deployment_info_copy.config.components.oceanbase.root_password:
            deployment_info_copy.config.components.oceanbase.root_password = ''
        return deployment_info_copy

    def generate_deployment_config(self, name: str, config: DeploymentConfig):
        log.get_logger().debug('generate cluster config')
        cluster_config = {}
        if config.auth is not None:
            self.generate_auth_config(cluster_config, config.auth)
        if config.components.oceanbase is not None:
            self.generate_oceanbase_config(cluster_config, config, name, config.components.oceanbase)
        if config.components.obproxy is not None:
            cluster_config[config.components.obproxy.component] = self.generate_component_config(config, const.OBPROXY, ['cluster_name', 'prometheus_listen_port', 'listen_port', 'rpc_listen_port'])
        if config.components.obagent is not None:
            cluster_config[config.components.obagent.component] = self.generate_component_config(config, const.OBAGENT, ['monagent_http_port', 'mgragent_http_port'])
        if config.components.ocpexpress is not None:
            ocp_pwd = self.generate_component_config(config, const.OCP_EXPRESS, ['port', 'admin_passwd'])
            cluster_config[config.components.ocpexpress.component] = ocp_pwd
        if config.components.obconfigserver is not None:
            cluster_config[config.components.obconfigserver.component] = self.generate_component_config(config, const.OB_CONFIGSERVER, ['listen_port'])
        cluster_config_yaml_path = ''
        log.get_logger().info('dump config from path: %s' % cluster_config_yaml_path)
        with tempfile.NamedTemporaryFile(delete=False, prefix="obd", suffix="yaml", mode="w", encoding="utf-8") as f:
            f.write(yaml.dump(cluster_config, sort_keys=False))
            cluster_config_yaml_path = f.name
        self.context['deployment'][name] = config
        return cluster_config_yaml_path

    def generate_component_config(self, config, component_name, ext_keys=[]):
        comp_config = dict()
        input_comp_config = getattr(config.components, component_name)
        config_dict = input_comp_config.dict()
        for key in config_dict:
            if config_dict[key] and key in {'servers', 'version', 'package_hash', 'release'}:
                comp_config[key] = config_dict[key]

        if 'global' not in comp_config.keys():
            comp_config['global'] = dict()

        ext_keys.insert(0, 'home_path')
        for key in ext_keys:
            if config_dict[key]:
                if key == 'admin_passwd':
                    passwd = RSAHandler().decrypt_private_key(config_dict[key])
                    comp_config['global'][key] = passwd
                    continue
                comp_config['global'][key] = config_dict[key]

        if input_comp_config.home_path == '':
            comp_config['global']['home_path'] = config.home_path + '/' + component_name

        for parameter in input_comp_config.parameters:
            if not parameter.adaptive:
                if parameter.key.endswith('_password'):
                    passwd = RSAHandler().decrypt_private_key(parameter.value)
                    comp_config['global'][parameter.key] = passwd
                    continue
                comp_config['global'][parameter.key] = parameter.value
        return comp_config

    def generate_oceanbase_config(self, cluster_config, config, name, oceanbase):
        oceanbase_config = dict()
        config_dict = oceanbase.dict()
        for key in config_dict:
            if config_dict[key] and key in {'version', 'release', 'package_hash'}:
                oceanbase_config[key] = config_dict[key]
        servers = []
        if oceanbase.topology:
            for zone in oceanbase.topology:
                root_service = zone.rootservice
                servers.append(root_service)
            for zone in oceanbase.topology:
                root_service = zone.rootservice
                if root_service not in oceanbase_config.keys():
                    oceanbase_config[root_service] = {}
                oceanbase_config[root_service]['zone'] = zone.name
                for server in zone.servers:
                    ip = server.ip
                    if ip not in oceanbase_config.keys():
                        oceanbase_config[ip] = {}
                    if ip != root_service:
                        servers.append(server.ip)
                        oceanbase_config[ip]['zone'] = zone.name
                        if server.parameters:
                            for parameter in server.parameters:
                                for key, value in parameter:
                                    oceanbase_config[ip][key] = value
        oceanbase_config['servers'] = servers
        if 'global' not in oceanbase_config.keys():
            oceanbase_config['global'] = {}

        for key in config_dict:
            if config_dict[key] and key in {'mysql_port', 'rpc_port', 'home_path', 'data_dir', 'redo_dir', 'appname',
                                            'root_password'}:
                if key == 'root_password':
                    passwd = RSAHandler().decrypt_private_key(config_dict[key])
                    oceanbase_config['global'][key] = passwd
                    continue
                oceanbase_config['global'][key] = config_dict[key]

        if oceanbase.home_path == '':
            oceanbase_config['global']['home_path'] = config.home_path + '/oceanbase'

        if oceanbase.parameters:
            for parameter in oceanbase.parameters:
                if not parameter.adaptive:
                    oceanbase_config['global'][parameter.key] = parameter.value
        if oceanbase.component == const.OCEANBASE_CE:
            cluster_config[const.OCEANBASE_CE] = oceanbase_config
        elif oceanbase.component == const.OCEANBASE:
            cluster_config[const.OCEANBASE] = oceanbase_config
        else:
            log.get_logger().error('oceanbase component : %s not exist' % oceanbase.component)
            raise Exception('oceanbase component : %s not exist' % oceanbase.component)

    def generate_auth_config(self, cluster_config, auth):
        if 'user' not in cluster_config.keys():
            cluster_config['user'] = {}
        cluster_config['user']['username'] = auth.user
        if auth.password:
            passwd = RSAHandler().decrypt_private_key(auth.password)
            cluster_config['user']['password'] = passwd
        cluster_config['user']['port'] = auth.port

    def create_deployment(self, name: str, config_path: str):
        log.get_logger().debug('deploy cluster')
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        if deploy:
            deploy_info = deploy.deploy_info
            if deploy_info.status not in [DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_DESTROYED]:
                log.get_logger().error('Deploy "%s" is %s. You could not deploy an %s cluster.' % (
                    name, deploy_info.status.value, deploy_info.status.value))
                raise Exception('Deploy "%s" is %s. You could not deploy an %s cluster.' % (
                    name, deploy_info.status.value, deploy_info.status.value))
            if deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
                log.get_logger().debug('Apply temp deploy configuration')
                if not deploy.apply_temp_deploy_config():
                    log.get_logger().error('Failed to apply new deploy configuration')
                    raise Exception('Failed to apply new deploy configuration')

        deploy = self.obd.deploy_manager.create_deploy_config(name, config_path)
        if not deploy:
            log.get_logger().error('Failed to create deploy: %s. please check you configuration file' % name)
            raise Exception('Failed to create deploy: %s. please check you configuration file' % name)
        self.obd.set_deploy(deploy)
        log.get_logger().info('cluster config path: %s ' % config_path)
        return config_path

    def get_precheck_result(self, name):
        precheck_result = PreCheckResult()
        deploy = self.obd.deploy
        if not deploy:
            deploy = self.obd.deploy_manager.get_deploy_config(name)
            self.obd.set_deploy(deploy)
        components = deploy.deploy_config.components
        info = []
        total = 0
        finished = 0
        all_passed = True
        param_check_status = None
        connect_check_status = None
        if 'deployment' in self.context.keys():
            param_check_status = self.context['deployment']['param_check_status']
            connect_check_status = self.context['deployment']['connect_check_status']
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

    @serial("install")
    def install(self, name, background_tasks):
        task_manager = task.get_task_manager()
        task_info = task_manager.get_task_info(name, task_type="install")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception("task {0} exists and not finished".format(name))
        task_manager.del_task_info(name, task_type="install")
        background_tasks.add_task(self._do_install, name)

    @auto_register("install")
    def _do_install(self, name):
        log.get_logger().info("clean io buffer before start install")
        self.buffer.clear()
        log.get_logger().info("clean namespace for init")
        for c in self.obd.deploy.deploy_config.components:
            for plugin in const.INIT_PLUGINS:
                self.obd.namespaces[c].set_return(plugin, None)
        log.get_logger().info("clean namespace for start")
        for component in self.obd.deploy.deploy_config.components:
            for plugin in const.START_PLUGINS:
                self.obd.namespaces[component].set_return(plugin, None)

        log.get_logger().info("start do deploy %s", name)
        self.obd.set_options(Values())
        trace_id = str(uuid())
        self.context['component_trace']['deploy'] = trace_id
        ret = self.obd.stdio.init_trace_logger(self.obd.stdio.log_path, trace_id=trace_id, recreate=True)
        if ret is False:
            log.get_logger().warn("component deploy log init error")
        deploy_success = self.obd.deploy_cluster(name)
        if not deploy_success:
            log.get_logger().warn("deploy %s failed", name)
        log.get_logger().info("finish do deploy %s", name)
        log.get_logger().info("start do start %s", name)

        repositories = self.obd.load_local_repositories(self.obd.deploy.deploy_info, False)
        repositories = self.obd.sort_repository_by_depend(repositories, self.obd.deploy.deploy_config)
        start_success = True
        connection_info_list = list()
        for repository in repositories:
            opt = Values()
            setattr(opt, "components", repository.name)
            self.obd.set_options(opt)
            trace_id = str(uuid())
            self.context['component_trace'][repository.name] = trace_id
            ret = self.obd.stdio.init_trace_logger(self.obd.stdio.log_path, trace_id=trace_id, recreate=True)
            if ret is False:
                log.get_logger().warn("component: {}, start log init error".format(repository.name))
            ret = self.obd._start_cluster(self.obd.deploy, repositories)
            if not ret:
                log.get_logger().warn("failed to start component: %s", repository.name)
                start_success = False
            else:
                display_ret = self.obd.namespaces[repository.name].get_return("display")
                connection_info = self.__build_connection_info(repository.name, display_ret.get_return("info"))
                if connection_info is not None:
                    connection_info_list.append(connection_info)
        self.obd.set_options(Values)
        if not deploy_success:
            raise Exception("task {0} deploy failed".format(name))
        if not start_success:
            raise Exception("task {0} start failed".format(name))
        self.obd.deploy.update_deploy_status(DeployStatus.STATUS_RUNNING)
        log.get_logger().info("finish do start %s", name)
        self.context["connection_info"][name] = connection_info_list
        deployment_report = self.get_deployment_report(name)
        self.context["deployment_report"][name] = deployment_report
        self.obd.deploy.deploy_config.dump()

        ## get obd namespace data
        data = {}
        for component, _ in self.obd.namespaces.items():
            data[component] = _.get_variable('run_result')
        COMMAND_ENV.set(ENV_TELEMETRY_REPORTER, TELEMETRY_COMPONENT_OB, save=True)
        LocalClient.execute_command_background("nohup obd telemetry post %s --data='%s' > /dev/null &" % (name, json.dumps(data)))
        self.obd.set_deploy(None)

    def get_install_task_info(self, name):
        task_info = task.get_task_manager().get_task_info(name, task_type="install")
        if task_info is None:
            raise Exception("task {0} not found".format(name))
        deploy = self.get_deploy(name)
        components = deploy.deploy_config.components
        total_count = (len(const.START_PLUGINS) + len(const.INIT_PLUGINS)) * len(components)
        finished_count = 0
        current = ""
        task_result = TaskResult.RUNNING
        info_dict = dict()

        for component in components:
            info_dict[component] = ComponentInfo(component=component, status=TaskStatus.PENDING,
                                                 result=TaskResult.RUNNING)
            if component in self.obd.namespaces:
                for plugin in const.INIT_PLUGINS:
                    if self.obd.namespaces[component].get_return(plugin) is not None:
                        info_dict[component].status = TaskStatus.RUNNING
                        finished_count += 1
                        current = "{0}: {1} finished".format(component, plugin)
                        if not self.obd.namespaces[component].get_return(plugin):
                            info_dict[component].result = TaskResult.FAILED

        for component in components:
            for plugin in const.START_PLUGINS:
                if component not in self.obd.namespaces:
                    break
                if self.obd.namespaces[component].get_return(plugin) is not None:
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
        return TaskInfo(total=total_count, finished=finished_count if task_result != TaskResult.SUCCESSFUL else total_count, current=current, status=task_result, info=info_list,
                        msg=msg)

    def __build_connection_info(self, component, info):
        if info is None:
            log.get_logger().warn("component {0} info from display is None".format(component))
            return None
        return ConnectionInfo(component=component,
                              access_url="{0}:{1}".format(info['ip'], info['port']),
                              user=info['user'], password=info['password'],
                              connect_url=info['cmd'] if info['type'] == 'db' else info['url'])

    def list_connection_info(self, name):
        pwd_rege = r"-p'[^']*'\s*"
        if self.context["connection_info"][name] is not None:
            log.get_logger().info("get deployment {0} connection info from context".format(name))
            for item in self.context["connection_info"][name]:
                item.password = ''
                item.connect_url = re.sub(pwd_rege, '', item.connect_url)
            return self.context["connection_info"][name]
        deploy = self.get_deploy(name)
        connection_info_list = list()
        task_info = self.get_install_task_info(name)
        component_info = task_info.info
        for component, config in deploy.deploy_config.components.items():
            connection_info = None
            start_ok = False
            for c in component_info:
                if c.component == component and c.status == TaskStatus.FINISHED and c.result == TaskResult.SUCCESSFUL:
                    start_ok = True
            if not start_ok:
                log.get_logger().warn("component %s start failed", component)
                continue
            display_ret = self.obd.namespaces[component].get_return("display")
            connection_info = self.__build_connection_info(component, display_ret.get_return("info"))
            if connection_info is not None:
                connection_info_copy = deepcopy(connection_info)
                connection_info_copy.password = ''
                connection_info_copy.connect_url = re.sub(pwd_rege, '', connection_info_copy.connect_url)
                connection_info_list.append(connection_info_copy)
            else:
                log.get_logger().warn("can not get connection info for component: {0}".format(component))
        return connection_info_list

    def get_deploy(self, name):
        if self.obd.deploy is not None and self.obd.deploy.name == name:
            deploy = self.obd.deploy
        else:
            deploy = self.obd.deploy_manager.get_deploy_config(name)
        if not deploy:
            raise Exception("no such deploy {0}".format(name))
        return deploy

    @serial("precheck")
    def precheck(self, name, background_tasks):
        task_manager = task.get_task_manager()
        task_info = task_manager.get_task_info(name, task_type="precheck")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception("task {0} exists and not finished".format(name))
        deploy = self.obd.deploy
        if not deploy:
            raise Exception("no such deploy {0}".format(name))
        deploy_config = deploy.deploy_config
        # Get the repository
        pkgs, repositories, errors = self.obd.search_components_from_mirrors(deploy_config, only_info=True)
        if errors:
            raise Exception("{}".format('\n'.join(errors)))
        repositories.extend(pkgs)
        repositories = self.obd.sort_repository_by_depend(repositories, deploy_config)
        for repository in repositories:
            real_servers = set()
            cluster_config = deploy_config.components[repository.name]
            for server in cluster_config.servers:
                if server.ip in real_servers:
                    raise Exception(
                        "Deploying multiple {} instances on the same server is not supported.'".format(
                            repository.name))
                    return False
                real_servers.add(server.ip)
        self.obd.search_param_plugin_and_apply(repositories, deploy_config)
        self.obd.set_repositories(repositories)

        if 'deployment' in self.context.keys() and self.context['deployment'][name] is not None and self.context['deployment'][name].components.oceanbase is not None and self.context['deployment'][name].components.oceanbase.mode == DeployMode.DEMO.value:
            for repository in repositories:
                self.obd.get_namespace(repository.name).set_variable('generate_config_mini', True)

        start_check_plugins = self.obd.search_py_script_plugin(repositories, 'start_check', no_found_act='warn')

        self._precheck(name, repositories, start_check_plugins, init_check_status=True)
        info = task_manager.get_task_info(name, task_type="precheck")
        if info is not None and info.exception is not None:
            raise info.exception
        task_manager.del_task_info(name, task_type="precheck")
        background_tasks.add_task(self._precheck, name, repositories, start_check_plugins, init_check_status=False)

    def _init_check_status(self, check_key, servers, check_result={}):
        check_status = defaultdict(lambda: defaultdict(lambda: None))
        for server in servers:
            if server in check_result:
                status = check_result[server]
            else:
                status = CheckStatus()
            check_status[server] = {check_key: status}
        return check_status

    @auto_register('precheck')
    def _precheck(self, name, repositories, start_check_plugins, init_check_status=False):
        if init_check_status:
            self._init_precheck(repositories, start_check_plugins)
        else:
            self._do_precheck(repositories, start_check_plugins)

    def _init_precheck(self, repositories, start_check_plugins):
        param_check_status = {}
        servers_set = set()
        for repository in repositories:
            if repository not in start_check_plugins:
                continue
            repository_status = {}
            res = self.obd.call_plugin(start_check_plugins[repository], repository,
                                       init_check_status=True, work_dir_check=True, clients={})
            if not res and res.get_return("exception"):
                raise res.get_return("exception")
            servers = self.obd.deploy.deploy_config.components.get(repository.name).servers
            for server in servers:
                repository_status[server] = {'param': CheckStatus()}
                servers_set.add(server)
            param_check_status[repository.name] = repository_status

        self.context['deployment']['param_check_status'] = param_check_status
        server_connect_status = {}
        for server in servers_set:
            server_connect_status[server] = {'ssh': CheckStatus()}
        self.context['deployment']['connect_check_status'] = {'ssh': server_connect_status}
        self.context['deployment']['servers_set'] = servers_set

    def _do_precheck(self, repositories, start_check_plugins):
        ssh_clients, connect_status = self.obd.get_clients_with_connect_status(self.obd.deploy.deploy_config,
                                                                               repositories, fail_exit=False)
        check_status = self._init_check_status('ssh', self.context['deployment']['servers_set'], connect_status)
        self.context['deployment']['connect_check_status'] = {'ssh': check_status}
        for k, v in connect_status.items():
            if v.status == v.FAIL:
                return
        gen_config_plugins = self.obd.search_py_script_plugin(repositories, 'generate_config')
        if len(repositories) != len(gen_config_plugins):
            raise Exception("param_check: config error, check stop!")

        param_check_status, check_pass = self.obd.deploy_param_check_return_check_status(repositories, self.obd.deploy.deploy_config, gen_config_plugins=gen_config_plugins)
        param_check_status_result = {}
        for comp_name in param_check_status:
            status_res = param_check_status[comp_name]
            param_check_status_result[comp_name] = self._init_check_status('param', status_res.keys(), status_res)
        self.context['deployment']['param_check_status'] = param_check_status_result

        if not check_pass:
            return

        components = [comp_name for comp_name in self.obd.deploy.deploy_config.components.keys()]
        for repository in repositories:
            ret = self.obd.call_plugin(gen_config_plugins[repository], repository, generate_check=False,
                                       generate_consistent_config=True, auto_depend=True, components=components)
            if ret is None:
                raise Exception("generate config error")
            elif not ret and ret.get_return("exception"):
                raise ret.get_return("exception")
            if not self.obd.deploy.deploy_config.dump():
                raise Exception('generate config dump error,place check disk space!')

        for repository in repositories:
            java_check = True
            if repository.name == COMP_OCP_EXPRESS:
                jre_name = COMP_JRE
                install_plugin = self.obd.search_plugin(repository, PluginType.INSTALL)
                if install_plugin and jre_name in install_plugin.requirement_map(repository):
                    version = install_plugin.requirement_map(repository)[jre_name].version
                    min_version = install_plugin.requirement_map(repository)[jre_name].min_version
                    max_version = install_plugin.requirement_map(repository)[jre_name].max_version
                    if len(self.obd.search_images(jre_name, version=version, min_version=min_version, max_version=max_version)) > 0:
                        java_check = False
            res = self.obd.call_plugin(start_check_plugins[repository], repository, init_check_status=False, work_dir_check=True, precheck=True, java_check=java_check)
            if not res and res.get_return("exception"):
                raise res.get_return("exception")


    def get_deployment_report(self, name):
        if self.context["deployment_report"][name] is not None:
            log.get_logger().info("get deployment {0} report from context".format(name))
            return self.context["deployment_report"][name]
        deploy = self.get_deploy(name)
        report_list = list()
        for component, config in deploy.deploy_config.components.items():
            status = TaskResult.FAILED
            if self.obd.namespaces[component].get_return("display"):
                status = TaskResult.SUCCESSFUL
            report_list.append(
                DeploymentReport(name=component, version=config.version, servers=[s.ip for s in config.servers],
                                 status=status))
        return report_list

    def list_deployments_by_status(self, deployment_status):
        deployments = self.obd.deploy_manager.get_deploy_configs()
        deploys = []
        if deployment_status == DeploymentStatus.INSTALLING:
            # query installing task
            for deployment in deployments:
                task_info = task.get_task_manager().get_task_info(deployment.name, task_type="install")
                if task_info is not None and task_info.status == TaskStatus.RUNNING:
                    deploy = Deployment(name=deployment.name, status=deployment.deploy_info.status.value.upper())
                    deploys.append(deploy)
        elif deployment_status == DeploymentStatus.DRAFT:
            # query draft task
            obd_deploy_status = ['configured', 'deployed', 'destroyed']
            for deployment in deployments:
                if deployment.deploy_info.status.value in obd_deploy_status:
                    config = self.context['deployment'][deployment.name] if self.context['deployment'] is not None else None
                    if config is not None:
                        deploy = Deployment(name=deployment.name, status=deployment.deploy_info.status.value.upper())
                        deploys.append(deploy)
        return deploys

    @auto_register("destroy")
    def destroy_cluster(self, name):
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        if not deploy:
            raise Exception("no such deploy {0}".format(name))
        self.obd.set_deploy(deploy)
        repositories = self.obd.load_local_repositories(deploy.deploy_info)
        self.obd.set_repositories(repositories)
        self.obd.set_options(Values({'force_kill': True}))
        self.obd.search_param_plugin_and_apply(repositories, deploy.deploy_config)
        # set namespace return value to none before do destroy
        for component in self.obd.deploy.deploy_config.components:
            if component in self.obd.namespaces:
                self.obd.namespaces[component].set_return(const.DESTROY_PLUGIN, None)

        ret = self.obd._destroy_cluster(deploy, repositories)
        if not ret:
            raise Exception("destroy cluster {0} failed".format(name))
        deploy.update_deploy_status(DeployStatus.STATUS_CONFIGURED)
        self.obd.set_options(Values())
        return ret

    def get_destroy_task_info(self, name):
        task_info = task.get_task_manager().get_task_info(name, task_type="destroy")
        if task_info is None:
            raise Exception("task {0} not found".format(name))
        components = self.obd.deploy.deploy_config.components
        total_count = len(components)
        finished_count = 0
        current = ""
        task_result = TaskResult.RUNNING
        info_dict = dict()
        for c in self.obd.deploy.deploy_config.components:
            info_dict[c] = ComponentInfo(component=c, status=TaskStatus.PENDING, result=TaskResult.RUNNING)
            if c in self.obd.namespaces:
                if self.obd.namespaces[c].get_return(const.DESTROY_PLUGIN) is not None:
                    info_dict[c].status = TaskStatus.FINISHED
                    finished_count += 1
                    current = "{0}: {1} finished".format(c, const.DESTROY_PLUGIN)
                    if not self.obd.namespaces[c].get_return(const.DESTROY_PLUGIN):
                        info_dict[c].result = TaskResult.FAILED
                    else:
                        info_dict[c].result = TaskResult.SUCCESSFUL
        if task_info.status == TaskStatus.FINISHED:
            task_result = task_info.result
            for v in info_dict.values():
                if v.status != TaskStatus.FINISHED:
                    v.status = TaskStatus.FINISHED
                    finished_count += 1
                    if v.result != TaskResult.SUCCESSFUL:
                        v.result = TaskResult.FAILED
        info_list = list()
        for info in info_dict.values():
            info_list.append(info)
        msg = "" if task_info.result == TaskResult.SUCCESSFUL else '{0}'.format(task_info.exception)
        return TaskInfo(total=total_count, finished=finished_count, current=current, status=task_result, info=info_list,
                        msg=msg)

    def recover(self, name):
        deploy = self.obd.deploy
        if not deploy:
            deploy = self.obd.deploy_manager.get_deploy_config(name)
            self.obd.set_deploy(deploy)
        components = deploy.deploy_config.components
        param_check_status = None
        if 'deployment' in self.context.keys():
            param_check_status = self.context['deployment']['param_check_status']
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
                                self.context['deployment'][name] = DeploymentConfig(**json.loads(json.dumps(config_json)))
                deploy.deploy_config.dump()
                self.recreate_deployment(name)

        return recover_change_parameter_list

    def recreate_deployment(self, name):
        config = self.context['deployment'][name] if self.context['deployment'] is not None else None
        if config is not None:
            cluster_config_yaml_path = self.generate_deployment_config(name, config)
            self.create_deployment(name, cluster_config_yaml_path)

    def modify_config(self, component, name, fix_eval):
        if fix_eval.key == "parameters":
            raise Exception("try to change parameters")
        config = self.context['deployment'][name] if self.context['deployment'] is not None else None
        if config is None:
            log.get_logger().warn("config is none, no need to modify")
            raise Exception('config is none')
        config_dict = config.dict()
        if config_dict['components'] is None:
            log.get_logger().warn("component is none, no need to modify")
            raise Exception('component is none')
        old_value = None
        for value in config_dict['components'].values():
            if value is not None and 'component' in value.keys() and value['component'] == component:
                if fix_eval.key in value.keys():
                    old_value = value[fix_eval.key]
                    value[fix_eval.key] = fix_eval.value
                elif "parameters" in value.keys() and value["parameters"] is not None:
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

    def get_install_log_by_component(self, component_name):
        trace_id = self.context['component_trace'][component_name]
        cmd = 'grep -h "\[{}\]" {}* | sed "s/\[{}\] //g" '.format(trace_id, self.obd.stdio.log_path, trace_id)
        stdout = LocalClient.execute_command(cmd).stdout
        if not stdout:
            trace_id = self.context['component_trace']['deploy']
            cmd = 'grep -h "\[{}\]" {}* | sed "s/\[{}\] //g" '.format(trace_id, self.obd.stdio.log_path, trace_id)
            stdout = LocalClient.execute_command(cmd).stdout
        return stdout

    def get_scenario_by_version(self, version, language='zh-CN'):
        version = version.split('-')[0]
        if language == 'zh-CN':
            scenario_4_3_0_0 = [
                {
                    'type': 'Express OLTP',
                    'desc': '适用于贸易、支付核心系统、互联网高吞吐量应用程序等工作负载。没有外键等限制、没有存储过程、没有长交易、没有大交易、没有复杂的连接、没有复杂的子查询。',
                    'value': 'express_oltp'
                },
                {
                    'type': 'Complex OLTP',
                    'desc': '适用于银行、保险系统等工作负载。他们通常具有复杂的联接、复杂的相关子查询、用 PL 编写的批处理作业，以及长事务和大事务。有时对短时间运行的查询使用并行执行',
                    'value': 'complex_oltp'
                },
                {
                    'type': 'HTAP',
                    'desc': '适用于混合 OLAP 和 OLTP 工作负载。通常用于从活动运营数据、欺诈检测和个性化建议中获取即时见解',
                    'value': 'htap'
                },
                {
                    'type': 'OLAP',
                    'desc': '用于实时数据仓库分析场景',
                    'value': 'olap'
                },
                {
                    'type': 'OBKV',
                    'desc': '用于键值工作负载和类似 Hbase 的宽列工作负载，这些工作负载通常具有非常高的吞吐量并且对延迟敏感',
                    'value': 'kv'
                },
            ]
        else:
            scenario_4_3_0_0 = [
                {
                    'type': 'Express OLTP',
                    'desc': 'This is suitable for trading, core payment systems, high-throughput Internet applications, and other workloads. There are no limitations such as foreign keys, stored procedures, long transactions, large transactions, complex joins, or complex subqueries.',
                    'value': 'express_oltp'
                },
                {
                    'type': 'Complex OLTP',
                    'desc': 'This is suitable for workloads in industries like banking and insurance. They often have complex joins, complex correlated subqueries, batch jobs written in PL, and long, large transactions. Sometimes parallel execution is used for queries that run for a short time.',
                    'value': 'complex_oltp'
                },
                {
                    'type': 'HTAP',
                    'desc': 'This is suitable for mixed OLAP and OLTP workloads, typically used to obtain real-time insights from activity operational data, fraud detection, and personalized recommendations.',
                    'value': 'htap'
                },
                {
                    'type': 'OLAP',
                    'desc': 'This is suitable for real-time data warehouse analysis scenarios.',
                    'value': 'olap'
                },
                {
                    'type': 'OBKV',
                    'desc': 'This is suitable for key-value workloads and wide-column workloads similar to HBase, which often have very high throughput and are sensitive to latency.',
                    'value': 'kv'
                },
            ]
        data = []
        if Version(version) >= Version('4.3.0.0'):
            for scenario in scenario_4_3_0_0:
                data.append(ScenarioType(type=scenario['type'], desc=scenario['desc'], value=scenario['value']))
        return data
