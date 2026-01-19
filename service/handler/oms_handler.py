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

import copy
import os
import time
import tempfile
import yaml
import json
from optparse import Values
from singleton_decorator import singleton
from collections import defaultdict

from _rpm import Version
from _types import Capacity
from service.handler.base_handler import BaseHandler
from service.handler.rsa_handler import RSAHandler
from service.common import log, task, util, const
from service.common.task import Serial as serial
from service.common.task import AutoRegister as auto_register
from service.model.deployments import OMSDeploymentStatus, DeploymentStatus, Deployment
from service.model.task import TaskStatus, TaskResult, TaskInfo, PreCheckResult, PrecheckTaskInfo, PrecheckEventResult, TaskStepInfo
from _deploy import DeployStatus, DeployConfigStatus
from _errno import CheckStatus
from ssh import LocalClient
from tool import YamlLoader


@singleton
class OmsHandler(BaseHandler):

    def get_oms_images(self, servers, username, password, port, pwd_decrypt=True):
        password = RSAHandler().decrypt_private_key(password) if password is not None and pwd_decrypt else password
        ssh_info = {"servers": servers, "username": username, "password": password, "port": port}
        image_name = 'oceanbase/' + const.OMS_CE
        repository = self.obd.repository_manager.get_repository_allow_shadow(const.OMS_CE, '1.0.0')
        self.obd.set_repositories([repository])

        data = {
            "oms_images": [],
            "connect_error": "",
            "get_images_error": ""
        }
        workflows = self.obd.get_workflows('get_docker_images')
        if not self.obd.run_workflow(workflows, **{repository.name: {"ssh_info": ssh_info, "image_name": image_name}}):
            connect_error = self.obd.get_namespace(const.OMS_CE).get_return('get_docker_images').get_return('connect_error') or ''
            if connect_error:
                data['connect_error'] = connect_error
                return data
        oms_images = self.obd.get_namespace(const.OMS_CE).get_return('get_docker_images').get_return('images')
        search_images_error = self.obd.get_namespace(const.OMS_CE).get_return('get_docker_images').get_return('search_images_error')
        if search_images_error:
            data['get_images_error'] = search_images_error
        data['oms_images'] = oms_images
        return data

    def create_oms_config_path(self, config):
        cluster_config = {}
        if config.auth is not None:
            self.generate_auth_config(cluster_config, config.auth)
        self.generate_oms_config(cluster_config, config)

        cluster_config_yaml_path = ''
        log.get_logger().info('dump oms config from path: %s' % cluster_config_yaml_path)
        with tempfile.NamedTemporaryFile(delete=False, prefix="oms", suffix="yaml", mode="w", encoding="utf-8") as f:
            f.write(yaml.dump(cluster_config, sort_keys=False))
            cluster_config_yaml_path = f.name
        self.context['id'] = self.context['id'] + 1 if self.context['id'] else 1
        log.get_logger().info('oms deployment id: %s' % self.context['id'])
        status = self.context['oms_deployment_info'][self.context['id']]['status'] if self.context['oms_deployment_info'][self.context['id']] and self.context['oms_deployment_info'][self.context['id']]['status'] else OMSDeploymentStatus.INIT

        self.context['oms_path'] = cluster_config_yaml_path
        self.context['oms_deployment_info'][self.context['id']] = {'status': status, 'config': config, 'oms_start_success_time': time.time()}
        return cluster_config_yaml_path

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
        log.get_logger().info('oms server cluster config path: %s ' % config_path)
        self.context['oms_deployment_id'][self.context['id']] = name
        return self.context['id']

    def generate_auth_config(self, cluster_config, auth):
        if 'user' not in cluster_config.keys():
            cluster_config['user'] = {}
        cluster_config['user']['username'] = auth.user
        passwd = RSAHandler().decrypt_private_key(auth.password) if auth.password is not None else auth.password
        cluster_config['user']['password'] = passwd
        cluster_config['user']['port'] = auth.port

    def generate_oms_config(self, cluster_config, config):
        global_config = {}
        cluster_config[const.OMS_CE] = {}
        oms_config = cluster_config[const.OMS_CE]
        regions = []
        oms_config["type"] = "docker"
        oms_config["tag"] = config.image.split(':')[1]
        oms_config["image_name"] = config.image.split(':')[0]
        oms_config["servers"] = config.servers.split(',')

        for key, value in vars(config).items():
            if value is None:
                continue
            if value and key not in ('auth', 'regions'):
                if key in ["image", "servers"]:
                    continue
                global_config[key] = value
            if key == "regions":
                regions = value
            if key in ["oms_meta_password", "tsdb_password"]:
                global_config[key] = RSAHandler().decrypt_private_key(value) if value else value

        global_config['regions'] = regions
        oms_config['global'] = global_config

    @serial("oms_precheck")
    def oms_precheck(self, id, background_tasks):
        task_manager = task.get_task_manager()
        app_name = self.context['oms_deployment_id'][id]
        log.get_logger().info('precheck start: %s' % app_name)
        if not app_name:
            raise Exception(f"no such deploy for id: {id}")
        task_info = task_manager.get_task_info(app_name, task_type="oms_precheck")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception(f"task {app_name} exists and not finished")
        deploy = self.obd.deploy
        if not deploy:
            raise Exception("no such deploy for name:{0}".format(app_name))
        deploy_info = deploy.deploy_info
        if deploy_info.status == DeployStatus.STATUS_DEPLOYED:
            self.obd.deploy_cluster(app_name)
        deploy_config = deploy.deploy_config
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
                real_servers.add(server.ip)
        self.obd.search_param_plugin_and_apply(repositories, deploy_config)
        self.obd.set_repositories(repositories)

        self._precheck(app_name, repositories, init_check_status=True)
        info = task_manager.get_task_info(app_name, task_type="oms_precheck")
        if info is not None and info.exception is not None:
            exception = copy.deepcopy(info.exception)
            info.exception = None
            raise exception
        task_manager.del_task_info(app_name, task_type="oms_precheck")
        background_tasks.add_task(self._precheck, app_name, repositories, init_check_status=False)
        self.context['oms_deployment']['task_id'] = self.context['oms_deployment']['task_id'] + 1 if \
        self.context['oms_deployment']['task_id'] else 1
        log.get_logger().info('task id: %d' % self.context['oms_deployment']['task_id'])
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'oms_precheck'
        ret = TaskInfo(id=self.context['oms_deployment']['task_id'], status=task_status, result=task_res, message=task_message, total='port, connect_db')
        log.get_logger().info('task ret: %s' % ret)
        self.context['task_info'][self.context['oms_deployment'][ret.id]] = ret
        return ret

    def _init_check_status(self, check_key, servers, check_result={}):
        check_status = defaultdict(lambda: defaultdict(lambda: None))
        for server in servers:
            if server in check_result:
                status = check_result[server]
            else:
                status = CheckStatus()
            check_status[server] = {check_key: status}
        return check_status

    @auto_register('oms_precheck')
    def _precheck(self, name, repositories, init_check_status=False):
        if init_check_status:
            self._init_precheck(repositories)
        else:
            self._do_precheck(repositories)

    def _init_precheck(self, repositories):
        log.get_logger().info('init precheck')
        param_check_status = {}
        servers_set = set()

        self.obd.ssh_clients = {}
        kwargs = {repository.name: {'clients': {}} for repository in repositories}
        init_check_status_workflows = self.obd.get_workflows('init_check_status', no_found_act='ignore',
                                                             repositories=repositories)
        workflows_ret = self.obd.run_workflow(init_check_status_workflows, no_found_act='ignore',
                                              repositories=repositories, **kwargs)

        for repository in repositories:
            if not self.obd.namespaces.get(repository.name):
                continue
            if not workflows_ret and self.obd.namespaces.get(repository.name).get_return('exception'):
                raise self.obd.namespaces.get(repository.name).get_return('exception')
            repository_status = {}
            servers = self.obd.deploy.deploy_config.components.get(repository.name).servers
            for server in servers:
                repository_status[server] = {'param': CheckStatus()}
                servers_set.add(server)
            param_check_status[repository.name] = repository_status

        self.context['oms_deployment']['param_check_status'] = param_check_status
        server_connect_status = {}
        for server in servers_set:
            server_connect_status[server] = {'ssh': CheckStatus()}
        self.context['oms_deployment']['connect_check_status'] = {'ssh': server_connect_status}
        self.context['oms_deployment']['servers_set'] = servers_set

    def _do_precheck(self, repositories):
        self.context['oms_deployment_ssh'][self.context['id']] = 'success'
        log.get_logger().info('start precheck')
        log.get_logger().info('ssh check')
        ssh_clients, connect_status = self.obd.get_clients_with_connect_status(self.obd.deploy.deploy_config,
                                                                               repositories, fail_exit=False)
        log.get_logger().info('connect_status: ', connect_status)
        check_status = self._init_check_status('ssh', self.context['oms_deployment']['servers_set'], connect_status)
        self.context['oms_deployment']['connect_check_status'] = {'ssh': check_status}
        for k, v in connect_status.items():
            if v.status == v.FAIL:
                self.context['oms_deployment_ssh'][self.context['id']] = 'fail'
                log.get_logger().info('ssh check failed')
                return
        log.get_logger().info('ssh check succeed')

        param_check_status, check_pass = self.obd.deploy_param_check_return_check_status(repositories,
                                                                                         self.obd.deploy.deploy_config)
        param_check_status_result = {}
        for comp_name in param_check_status:
            status_res = param_check_status[comp_name]
            param_check_status_result[comp_name] = self._init_check_status('param', status_res.keys(), status_res)
        self.context['oms_deployment']['param_check_status'] = param_check_status_result

        log.get_logger().debug('precheck param check status: %s' % param_check_status)
        log.get_logger().debug('precheck param check status res: %s' % check_pass)
        if not check_pass:
            return

        components = [comp_name for comp_name in self.obd.deploy.deploy_config.components.keys()]
        workflows = self.obd.get_workflows('generate_config', repositories=repositories)
        component_kwargs = {
            repository.name: {"generate_check": False, "generate_consistent_config": True, "auto_depend": True,
                              "components": components} for repository in repositories}
        workflow_ret = self.obd.run_workflow(workflows, repositories=repositories, error_exit=False, **component_kwargs)
        if not workflow_ret:
            for repository in repositories:
                for plugin_ret in self.obd.get_namespace(repository.name).all_plugin_ret.values():
                    if plugin_ret.get_return("exception"):
                        raise plugin_ret.get_return("exception")
            raise Exception('generate config error!')
        if not self.obd.deploy.deploy_config.dump():
            raise Exception('generate config dump error,place check disk space!')

        log.get_logger().info('generate config succeed')
        ssh_clients = self.obd.get_clients(self.obd.deploy.deploy_config, repositories)

        component_kwargs = {}
        log.get_logger().info('start start_check')
        for repository in repositories:
            component_kwargs[repository.name] = {"work_dir_check": True, "precheck": True, "clients": ssh_clients,}
        workflows = self.obd.get_workflows('start_check', no_found_act='ignore', repositories=repositories)
        if not self.obd.run_workflow(workflows, repositories=repositories, no_found_act='ignore', error_exit=False,
                                     **component_kwargs):
            for repository in repositories:
                for plugin_ret in self.obd.get_namespace(repository.name).all_plugin_ret.values():
                    if plugin_ret.get_return("exception"):
                        raise plugin_ret.get_return("exception")
        log.get_logger().info('end start_check')

    def get_precheck_result(self, id, task_id):
        log.get_logger().info('get oms precheck result')
        precheck_result = PrecheckTaskInfo()
        deploy = self.obd.deploy
        name = self.context['oms_deployment_id'][id]
        if not name:
            raise Exception(f"no such deploy for id: {id}")
        if not deploy:
            deploy = self.obd.deploy_manager.get_deploy_config(name)
            self.obd.set_deploy(deploy)
        components = deploy.deploy_config.components

        param_check_status = None
        connect_check_status = None
        check_result = []
        task_info = self.context['task_info'][self.context['oms_deployment'][task_id]]
        all_passed = []
        precheck_result.task_info = task_info
        task_info.info = []

        for component in components:
            namespace_union = {}
            namespace = self.obd.get_namespace(component)
            if namespace:
                variables = namespace.variables
                if 'start_check_status' in variables.keys():
                    namespace_union = util.recursive_update_dict(namespace_union, variables.get('start_check_status'))

            log.get_logger().debug('namespace_union: %s' % namespace_union)
            if namespace_union:
                for server, result in namespace_union.items():
                    if result is None:
                        log.get_logger().warn("precheck for server: {} is None".format(server.ip))
                        continue
                    all_passed.append(self.parse_precheck_result(component, check_result, task_info, server, result))
        check_result.sort(key=lambda p: p.result)
        precheck_result.precheck_result = check_result
        status_flag = [i.status for i in task_info.info]
        if TaskStatus.RUNNING not in status_flag:
            task_info.status = TaskStatus.FINISHED
            task_info.result = TaskResult.SUCCESSFUL if all(all_passed) else TaskResult.FAILED
        precheck_result.task_info = task_info
        if self.context['oms_deployment_ssh'][id] == 'fail' and TaskStatus.FINISHED in status_flag:
            precheck_result.task_info.result = TaskResult.FAILED
            precheck_result.task_info.status = TaskStatus.FINISHED
        return precheck_result

    def parse_precheck_result(self, component, check_result, task_info, server, result):
        all_passed = True
        task_info.finished = ''
        for k, v in result.items():
            check_info = PreCheckResult(name='{}:{}'.format(component, k), server=server.ip)
            task_info.current = '{}:{}'.format(component, k)
            log.get_logger().debug('precheck result current: %s' % task_info.current)
            info = TaskStepInfo(name='{}:{}'.format(component, k))
            if v.status == v.PASS:
                check_info.result = PrecheckEventResult.PASSED
                info.status = TaskStatus.FINISHED
                info.result = TaskResult.SUCCESSFUL
                task_info.finished += k + ' '
            elif v.status == v.FAIL:
                check_info.result = PrecheckEventResult.FAILED
                check_info.code = v.error.code
                check_info.description = v.error.msg
                check_info.recoverable = len(v.suggests) > 0 and v.suggests[0].auto_fix
                check_info.advisement = v.suggests[0].msg if len(v.suggests) > 0 and v.suggests[
                    0].msg is not None else ''
                all_passed = False
                info.status = TaskStatus.FINISHED
                info.result = TaskResult.FAILED
                task_info.finished += k + ' '
            elif v.status == v.WAIT:
                check_info.result = PrecheckEventResult.RUNNING
                task_info.status = TaskStatus.RUNNING
                task_info.result = TaskResult.RUNNING
                info.status = TaskStatus.RUNNING
                info.result = TaskResult.RUNNING
            task_info.info.append(info)
            check_result.append(check_info)
        return all_passed

    @serial("install")
    def install(self, id, background_tasks):
        task_manager = task.get_task_manager()
        task_info = task_manager.get_task_info(id, task_type="install")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception("task {0} exists and not finished".format(id))
        task_manager.del_task_info(id, task_type="install")
        self.context['oms_deployment']['task_id'] = self.context['oms_deployment']['task_id'] + 1 if self.context['oms_deployment']['task_id'] else 1
        background_tasks.add_task(self._do_install, id, self.context['oms_deployment']['task_id'])
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'install'
        ret = TaskInfo(id=self.context['oms_deployment']['task_id'], status=task_status, result=task_res, total='init start_check, start, connect, bootstrap, display', message=task_message)
        self.context['task_info'][self.context['oms_deployment'][ret.id]] = ret
        return ret

    @auto_register("install")
    def _do_install(self, id, task_id):
        self.context['deploy_status'][task_id] = self.context['process_installed'][task_id] = ''
        log.get_logger().info("clean io buffer before start install")
        self.buffer.clear()
        log.get_logger().info("clean namespace for init")
        for c in self.obd.deploy.deploy_config.components:
            for plugin in const.INIT_PLUGINS:
                if c in self.obd.namespaces:
                    self.obd.namespaces[c].set_return(plugin, None)
        log.get_logger().info("clean namespace for start")
        for component in self.obd.deploy.deploy_config.components:
            for plugin in const.START_PLUGINS:
                if component in self.obd.namespaces:
                    self.obd.namespaces[component]._variables = {'run_result': self.obd.namespaces[component].variables['run_result']}
                    self.obd.namespaces[component].set_return(plugin, None)

        name = self.context['oms_deployment_id'][id]
        deploy = self.obd.deploy
        log.get_logger().info("start deploy %s", name)
        opt = Values()
        setattr(opt, "clean", True)
        setattr(opt, "force", True)
        self.obd.set_options(opt)

        try:
            deploy_success = self.obd.deploy_cluster(name)
            if not deploy_success:
                log.get_logger().warn("deploy %s failed", name)
                raise Exception('deploy failed')
        except:
            self.obd._call_stdio('exception', '')
            self.context['deploy_status'][task_id] = 'failed'
            raise Exception('deploy failed')
        log.get_logger().info("deploy %s succeed", name)

        repositories = self.obd.load_local_repositories(self.obd.deploy.deploy_info, False)
        repositories = self.obd.sort_repository_by_depend(repositories, self.obd.deploy.deploy_config)
        start_success = True
        for repository in repositories:
            log.get_logger().info("begin start %s", repository.name)
            opt = Values()
            setattr(opt, "components", repository.name)
            setattr(opt, "strict_check", False)
            self.obd.set_options(opt)
            self.obd.set_repositories(repositories)
            ret = self.obd._start_cluster(self.obd.deploy, [repository], components_kwargs={repository.name: {"web_start": True}})
            if not ret:
                log.get_logger().warn("failed to start component: %s", repository.name)
                self.context['deploy_status'][task_id] = 'failed'
                start_success = False
            log.get_logger().info("end start %s", repository.name)
        self.obd.set_repositories(repositories)
        if not start_success:
            raise Exception("task {0} start failed".format(name))
        self.obd.deploy.update_deploy_status(DeployStatus.STATUS_RUNNING)
        log.get_logger().info("finish do start %s", name)
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        self.obd.set_deploy(deploy)
        self.context['process_installed'][task_id] = 'done'


    def get_install_task_info(self, id, task_id):
        log.get_logger().info('get oms install task info')
        name = self.context['oms_deployment_id'][id]
        task_info = self.context['task_info'][self.context['oms_deployment'][task_id]]
        if task_info is None:
            raise Exception("task {0} not found".format(task_id))
        task_info.status = TaskStatus.RUNNING
        task_info.result = TaskResult.RUNNING
        task_info.info = []
        task_info.finished = ''
        failed = 0
        if not self.obd.deploy:
            return task_info
        for component in self.obd.deploy.deploy_config.components:
            if component in self.obd.namespaces:
                for plugin in const.INIT_PLUGINS:
                    task_info.current = f'{component}-{plugin}'
                    step_info = TaskStepInfo(name=f'{component}-{plugin}', status=TaskStatus.RUNNING, result=TaskResult.RUNNING)
                    if self.obd.namespaces[component].get_return(plugin).value is not None:
                        if not self.obd.namespaces[component].get_return(plugin):
                            failed += 1
                            step_info.result = TaskResult.FAILED
                        else:
                            step_info.result = TaskResult.SUCCESSFUL
                    step_info.status = TaskStatus.FINISHED
                    task_info.info.append(step_info)
                    task_info.finished += f'{component}-{plugin} '

        for component in self.obd.deploy.deploy_config.components:
            for plugin in const.START_PLUGINS:
                step_info = TaskStepInfo(name=f'{component}-{plugin}', status=TaskStatus.RUNNING, result=TaskResult.RUNNING)
                task_info.current = f'{component}-{plugin}'
                if component not in self.obd.namespaces:
                    break
                if self.obd.namespaces[component].get_return(plugin).value is not None:
                    if not self.obd.namespaces[component].get_return(plugin):
                        step_info.result = TaskResult.FAILED
                        failed += 1
                    else:
                        step_info.result = TaskResult.SUCCESSFUL
                step_info.status = TaskStatus.FINISHED
                task_info.info.append(step_info)
                task_info.finished += f'{component}-{plugin} '

        if self.obd.deploy.deploy_info.status == DeployStatus.STATUS_RUNNING and self.context['process_installed'][task_id] == 'done':
            self.context['oms_deployment_info'][id]['oms_start_success_time'] = time.time()
            task_info.result = TaskResult.SUCCESSFUL
            task_info.status = TaskStatus.FINISHED

        if failed or self.context['deploy_status'][task_id] == 'failed':
            task_info.result = TaskResult.FAILED
            task_info.status = TaskStatus.FINISHED
        return task_info

    @serial("reinstall")
    def reinstall(self, id, background_tasks):
        log.get_logger().info('start reinstall')
        task_manager = task.get_task_manager()
        task_info = task_manager.get_task_info(id, task_type="reinstall")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception("task {0} exists and not finished".format(id))
        task_manager.del_task_info(id, task_type="reinstall")
        self.context['oms_deployment']['task_id'] = self.context['oms_deployment']['task_id'] + 1 if self.context['oms_deployment'][
            'task_id'] else 1
        background_tasks.add_task(self._do_reinstall, id, self.context['oms_deployment']['task_id'])
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'reinstall'
        ret = TaskInfo(id=self.context['oms_deployment']['task_id'], status=task_status, result=task_res,
                       total='destroy init start_check, start, connect, bootstrap, display', message=task_message)
        self.context['task_info'][self.context['oms_deployment'][ret.id]] = ret
        return ret

    @auto_register("reinstall")
    def _do_reinstall(self, id, task_id):
        log.get_logger().info("clean io buffer before start reinstall")
        self.buffer.clear()
        log.get_logger().info("clean namespace for init")
        for c in self.obd.deploy.deploy_config.components:
            for plugin in const.INIT_PLUGINS:
                if c in self.obd.namespaces:
                    self.obd.namespaces[c].set_return(plugin, None)
        log.get_logger().info("clean namespace for start")
        for component in self.obd.deploy.deploy_config.components:
            for plugin in const.START_PLUGINS:
                if component in self.obd.namespaces:
                    self.obd.namespaces[component]._variables = {'run_result': self.obd.namespaces[component].variables['run_result']}
                    self.obd.namespaces[component].set_return(plugin, None)

        name = self.context['oms_deployment_id'][id]
        repositories = self.obd.repositories
        log.get_logger().info('start destroy %s' % name)
        opt = Values()
        setattr(opt, "force_kill", True)
        self.obd.set_options(opt)
        if not self.obd._destroy_cluster(self.obd.deploy, repositories):
            raise Exception('destroy failed')

        self.obd.set_repositories([])
        deploy = self.obd.deploy_manager.create_deploy_config(name, self.context['oms_path'])
        if not deploy:
            raise Exception("no such deploy for name:{0}".format(name))
        deploy_config = deploy.deploy_config
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
                real_servers.add(server.ip)
        self.obd.search_param_plugin_and_apply(repositories, deploy_config)
        self.obd.set_repositories(repositories)

        kwargs = {}
        components = [comp_name for comp_name in self.obd.deploy.deploy_config.components.keys()]
        for repository in repositories:
            kwargs[repository.name] = {"generate_consistent_config": True, "generate_check": False, "auto_depend": True, "components": components}
        workflows = self.obd.get_workflows("generate_config")
        if not self.obd.run_workflow(workflows, **kwargs):
            for repository in repositories:
                if self.obd.get_namespace(repository.name).get_return('exception'):
                    raise self.obd.get_namespace(repository.name).get_return('exception')
            raise Exception("generate config error")
        if not self.obd.deploy.deploy_config.dump():
            raise Exception('generate config dump error,place check disk space!')

        log.get_logger().info("start deploy %s", name)
        opt = Values()
        setattr(opt, "clean", True)
        setattr(opt, "force", True)
        self.obd.set_options(opt)
        deploy_success = self.obd.deploy_cluster(name)
        if not deploy_success:
            log.get_logger().warn("deploy %s failed", name)
            raise Exception('deploy failed')
        log.get_logger().info("deploy %s succeed", name)

        repositories = self.obd.load_local_repositories(self.obd.deploy.deploy_info, False)
        repositories = self.obd.sort_repository_by_depend(repositories, self.obd.deploy.deploy_config)
        start_success = True
        for repository in repositories:
            opt = Values()
            setattr(opt, "components", repository.name)
            setattr(opt, "strict_check", False)
            self.obd.set_options(opt)
            self.obd.set_repositories([repository])
            ret = self.obd._start_cluster(self.obd.deploy, [repository], components_kwargs={repository.name: {"web_start": True}})
            if not ret:
                log.get_logger().warn("failed to start component: %s", repository.name)
                start_success = False
        if not start_success:
            raise Exception("task {0} start failed".format(name))

        self.obd.deploy.update_deploy_status(DeployStatus.STATUS_RUNNING)
        self.context['process_installed'][task_id] = 'done'
        log.get_logger().info("finish do start %s", name)
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        self.obd.set_deploy(deploy)
        self.context['process_installed'][task_id] = 'done'

    def get_reinstall_task_info(self, id, task_id):
        name = self.context['oms_deployment_id'][id]
        task_info = self.context['task_info'][self.context['oms_deployment'][task_id]]
        if task_info is None:
            raise Exception("task {0} not found".format(task_id))
        task_info.status = TaskStatus.RUNNING
        task_info.result = TaskResult.RUNNING
        task_info.info = []
        task_info.finished = ''
        failed = 0

        for c in self.obd.deploy.deploy_config.components:
            step_info = TaskStepInfo(name=f'{c}-{const.DESTROY_PLUGIN}', status=TaskStatus.RUNNING,
                                     result=TaskResult.RUNNING)
            if c in self.obd.namespaces:
                if self.obd.namespaces[c].get_return(const.DESTROY_PLUGIN).value is not None:
                    task_info.status = TaskStatus.RUNNING
                    task_info.current = f'{c}-{const.DESTROY_PLUGIN}'
                    step_info.status = TaskStatus.FINISHED
                    if not self.obd.namespaces[c].get_return(const.DESTROY_PLUGIN):
                        step_info.result = TaskResult.FAILED
                        failed += 1
                    else:
                        step_info.result = TaskResult.SUCCESSFUL
                    task_info.info.append(step_info)
                    task_info.finished += f'{c}-{const.DESTROY_PLUGIN} '

        for component in self.obd.deploy.deploy_config.components:
            if component in self.obd.namespaces:
                for plugin in const.INIT_PLUGINS:
                    task_info.current = f'{component}-{plugin}'
                    step_info = TaskStepInfo(name=f'{component}-{plugin}', status=TaskStatus.RUNNING, result=TaskResult.RUNNING)
                    if self.obd.namespaces[component].get_return(plugin).value is not None:
                        if not self.obd.namespaces[component].get_return(plugin):
                            failed += 1
                            step_info.result = TaskResult.FAILED
                        else:
                            step_info.result = TaskResult.SUCCESSFUL
                    step_info.status = TaskStatus.FINISHED
                    task_info.info.append(step_info)
                    task_info.finished += f'{component}-{plugin} '

        for component in self.obd.deploy.deploy_config.components:
            for plugin in const.START_PLUGINS:
                step_info = TaskStepInfo(name=f'{component}-{plugin}', status=TaskStatus.RUNNING, result=TaskResult.RUNNING)
                task_info.current = f'{component}-{plugin}'
                if component not in self.obd.namespaces:
                    break
                if self.obd.namespaces[component].get_return(plugin).value is not None:
                    if not self.obd.namespaces[component].get_return(plugin):
                        step_info.result = TaskResult.FAILED
                        failed += 1
                    else:
                        step_info.result = TaskResult.SUCCESSFUL
                step_info.status = TaskStatus.FINISHED
                task_info.info.append(step_info)
                task_info.finished += f'{component}-{plugin} '

        if self.obd.deploy.deploy_info.status == DeployStatus.STATUS_RUNNING and self.context['process_installed'][task_id] == 'done':
            self.context['oms_deployment_info'][id]['oms_start_success_time'] = time.time()
            task_info.result = TaskResult.SUCCESSFUL
            task_info.status = TaskStatus.FINISHED

        if failed:
            task_info.result = TaskResult.FAILED
            task_info.status = TaskStatus.FINISHED
        return task_info

    @serial("destroy")
    def destroy(self, id, background_tasks):
        task_manager = task.get_task_manager()
        task_info = task_manager.get_task_info(id, task_type="destroy")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception("task {0} exists and not finished".format(id))
        task_manager.del_task_info(id, task_type="destroy")
        background_tasks.add_task(self._destroy_cluster, id)
        self.context['oms_deployment']['task_id'] = self.context['oms_deployment']['task_id'] + 1 \
            if self.context['oms_deployment']['task_id'] else 1
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'destroy'
        ret = TaskInfo(id=self.context['oms_deployment']['task_id'], status=task_status, result=task_res,
                       total='destroy', message=task_message)
        self.context['task_info'][self.context['oms_deployment'][ret.id]] = ret
        return ret

    @auto_register("destroy")
    def _destroy_cluster(self, id):
        name = self.context['oms_deployment_id'][id]
        if not name:
            raise Exception(f"no such deploy for id: {id}")
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        if not deploy:
            raise Exception("no such deploy for id: {0}".format(id))
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

    def get_destroy_task_info(self, id, task_id):
        name = self.context['oms_deployment_id'][id]
        task_info = self.context['task_info'][self.context['oms_deployment'][task_id]]
        if task_info is None:
            raise Exception("task {0} not found".format(task_id))
        task_info.status = TaskStatus.RUNNING
        task_info.result = TaskResult.RUNNING
        task_info.info = []
        task_info.finished = ''

        failed = 0
        for c in self.obd.deploy.deploy_config.components:
            step_info = TaskStepInfo(name=f'{c}-{const.DESTROY_PLUGIN}', status=TaskStatus.RUNNING, result=TaskResult.RUNNING)
            if c in self.obd.namespaces:
                if self.obd.namespaces[c].get_return(const.DESTROY_PLUGIN).value is not None:
                    task_info.status = TaskStatus.RUNNING
                    task_info.current = f'{c}-{const.DESTROY_PLUGIN}'
                    step_info.status = TaskStatus.FINISHED
                    if not self.obd.namespaces[c].get_return(const.DESTROY_PLUGIN):
                        step_info.result = TaskResult.FAILED
                        failed += 1
                    else:
                        step_info.result = TaskResult.SUCCESSFUL
                    task_info.info.append(step_info)
                    task_info.finished += f'{c}-{const.DESTROY_PLUGIN} '
        if self.obd.deploy.deploy_info.status == DeployStatus.STATUS_CONFIGURED:
            task_info.result = TaskResult.SUCCESSFUL
            task_info.status = TaskStatus.FINISHED

        if failed:
            task_info.result = TaskResult.FAILED
            task_info.status = TaskStatus.FINISHED
        return task_info

    def list_oms_deployments(self):
        deployments = self.obd.deploy_manager.get_deploy_configs()
        deploys = []
        obd_deploy_status = ['running', 'stopped', 'upgrading']
        for deployment in deployments:
            deploy = self.obd.deploy_manager.get_deploy_config(deployment.name)
            for oms in [const.OMS, const.OMS_CE]:
                if oms in deploy.deploy_config.components and deployment.deploy_info.status.value in obd_deploy_status:
                    deploy = Deployment(name=deployment.name, status=deployment.deploy_info.status.value.upper())
                    deploys.append(deploy)
        return deploys

    def get_upgrade_info(self, name):
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        if not deploy:
            raise Exception("no such deploy {0}".format(name))
        self.obd.set_deploy(deploy)
        deploy_info = deploy.deploy_info
        if deploy_info.status not in [DeployStatus.STATUS_RUNNING, DeployStatus.STATUS_STOPPED, DeployStatus.STATUS_UPRADEING]:
            raise Exception("deploy {0} status is {1}, not support upgrade.".format(name, deploy_info.status))
        deploy_config = deploy.deploy_config
        pkgs, repositories, errors = self.obd.search_components_from_mirrors(deploy_config, only_info=True)
        if errors:
            raise Exception("{}".format('\n'.join(errors)))
        self.obd.set_repositories(repositories)
        current_version = None
        usable_images = []
        for component in deploy_config.components.keys():
            for oms in [const.OMS, const.OMS_CE]:
                if oms == component:
                    config = deploy_config.components[component]
                    servers = ','.join([server.ip for server in config.servers])
                    user_config = deploy_config.user
                    current_version = deploy_config.components[component].version
                    usable_images = self.get_oms_images(servers, user_config.username, user_config.password, user_config.port, False)
                    break
        if not usable_images['oms_images']:
            raise Exception("no usable images found.")

        dest_repositories = []
        data = {
            "current_version": current_version,
            "dest_versions":dest_repositories
        }
        for image in usable_images['oms_images']:
            if Version(image['version']) > current_version:
                dest_repositories.append(image)
        return data

    @serial("upgrade_precheck")
    def upgrade_precheck(self, cluster_name, background_tasks, path):
        task_manager = task.get_task_manager()
        if not cluster_name:
            raise Exception(f"no such deploy for cluster_name: {cluster_name}")
        task_info = task_manager.get_task_info(cluster_name, task_type="upgrade_precheck")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception(f"task {cluster_name} exists and not finished")
        deploy = self.obd.deploy
        if not deploy:
            raise Exception(f"no such deploy: {cluster_name}")
        self.context["oms_upgrade"] = {"upgrade_path": path}
        deploy_config = deploy.deploy_config
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
        repositories = [repository for repository in repositories if repository.name in [const.OMS, const.OMS_CE]]
        self.obd.set_repositories(repositories)

        self._upgrade_precheck(cluster_name, repositories, init_check_status=True)
        info = task_manager.get_task_info(cluster_name, task_type="upgrade_check")
        if info is not None and info.exception is not None:
            raise info.exception
        task_manager.del_task_info(cluster_name, task_type="upgrade_check")
        background_tasks.add_task(self._upgrade_precheck, cluster_name, repositories, init_check_status=False)
        self.context['oms_deployment']['task_id'] = self.context['oms_deployment']['task_id'] + 1 if self.context['oms_deployment'][
            'task_id'] else 1
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'upgrade_check'
        ret = TaskInfo(id=self.context['oms_deployment']['task_id'], status=task_status, result=task_res,
                       message=task_message, total='task, machine, ob_version')
        self.context['task_info'][self.context['oms_deployment'][ret.id]] = ret
        return ret

    @auto_register('upgrade_precheck')
    def _upgrade_precheck(self, name, repositories, init_check_status=False):
        if init_check_status:
            self._init_upgrade_precheck(repositories)
        else:
            self._do_upgrade_precheck(repositories)

    def _init_upgrade_precheck(self, repositories):
        repo_kwargs = {repository.name: {"init_check_status": True, 'path': ''} for repository in repositories}
        init_check_status_workflows = self.obd.get_workflows('web_upgrade_check', no_found_act='ignore', repositories=repositories)
        self.obd.run_workflow(init_check_status_workflows, no_found_act='ignore', repositories=repositories, **repo_kwargs)
        for repository in repositories:
            if self.obd.get_namespace(repository.name).get_return('exception'):
                raise self.obd.get_namespace(repository.name).get_return('exception')

    def _do_upgrade_precheck(self, repositories):
        ssh_clients = self.obd.get_clients(self.obd.deploy.deploy_config, repositories)
        log.get_logger().info('start upgrade_check')
        path = self.context['oms_upgrade']['upgrade_path']
        repo_kwargs = {repository.name: {"path": path} for repository in repositories}
        workflows = self.obd.get_workflows('web_upgrade_check', no_found_act='ignore', repositories=repositories)
        if not self.obd.run_workflow(workflows, repositories=repositories, no_found_act='ignore', error_exit=False, **repo_kwargs):
            for repository in repositories:
                if self.obd.get_namespace(repository.name).get_return('exception'):
                    raise self.obd.get_namespace(repository.name).get_return('exception')
        log.get_logger().info('end upgrade_check')

    def get_upgrade_precheck_result(self, cluster_name, task_id):
        precheck_result = PrecheckTaskInfo()
        deploy = self.obd.deploy
        if not deploy:
            deploy = self.obd.deploy_manager.get_deploy_config(cluster_name)
            self.obd.set_deploy(deploy)
        components = deploy.deploy_config.components
        task_info = self.context['task_info'][self.context['oms_deployment'][task_id]]
        check_result = []
        task_info.info = []
        if not task_info:
            raise Exception(f"no such task_info for task_id: {task_id}")

        all_passed = False
        for component in components:
            namespace_union = {}
            namespace = self.obd.get_namespace(component)
            if namespace:
                variables = namespace.variables
                if 'start_check_status' in variables.keys():
                    namespace_union = util.recursive_update_dict(namespace_union, variables.get('start_check_status'))
            if namespace_union:
                for server, result in namespace_union.items():
                    if result is None:
                        log.get_logger().warn("precheck for server: {} is None".format(server.ip))
                        continue
                    all_passed = self.parse_precheck_result(component, check_result, task_info, server, result)
                    precheck_result.precheck_result = check_result
                    precheck_result.task_info = task_info
        status_flag = [i.status for i in task_info.info]
        log.get_logger().info('task status: %s' % status_flag)
        if TaskResult.RUNNING not in status_flag:
            task_info.status = TaskStatus.FINISHED
            task_info.result = TaskResult.SUCCESSFUL if all_passed else TaskResult.FAILED
        return precheck_result


    @serial("upgrade")
    def upgrade_oms(self, cluster_name, version, image_name, upgrade_mode, background_tasks):
        default_oms_files_path = None
        if upgrade_mode == 'online':
            default_oms_files_path = self.context['oms_upgrade']['upgrade_path']
            if not default_oms_files_path:
                raise Exception("upgrade_path is required for online upgrade")
        task_manager = task.get_task_manager()
        task_info = task_manager.get_task_info(cluster_name, task_type="oms_upgrade")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception(f"task {cluster_name} exists and not finished")
        task_manager.del_task_info(cluster_name, task_type="upgrade")
        if Version('4.2.11') > Version(version):
            raise Exception("version must be greater than 4.2.11")
        if const.OMS_CE not in image_name:
            image_name = image_name.replace(const.OMS, const.OMS_CE)
        background_tasks.add_task(self._upgrade, cluster_name, version, image_name, upgrade_mode, default_oms_files_path)
        self.context['oms_deployment']['task_id'] = self.context['oms_deployment']['task_id'] + 1 if self.context['oms_deployment']['task_id'] else 1
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'upgrade'
        ret = TaskInfo(id=self.context['oms_deployment']['task_id'], status=task_status, result=task_res, total='upgrade', message=task_message)
        self.context['task_info'][self.context['oms_deployment'][ret.id]] = ret
        return ret

    @auto_register('upgrade')
    def _upgrade(self, cluster_name, version, image_name, upgrade_mode, default_oms_files_path):
        self.context['upgrade']['succeed'] = None
        log.get_logger().info("clean io buffer before start install")
        self.buffer.clear()
        log.get_logger().info("clean namespace for init")
        for c in self.obd.deploy.deploy_config.components:
            for plugin in const.INIT_PLUGINS:
                if c in self.obd.namespaces:
                    self.obd.namespaces[c].set_return(plugin, None)
        log.get_logger().info("clean namespace for start")
        for component in self.obd.deploy.deploy_config.components:
            for plugin in const.START_PLUGINS:
                if component in self.obd.namespaces:
                    self.obd.namespaces[component].set_return(plugin, None)

        deploy = self.obd.deploy
        if not deploy:
            raise Exception(f"no such deploy: {cluster_name}")

        self.obd.set_options(Values({'component': const.OMS_CE, "image_name": image_name, "tag": version, "version": None, "disable_oms_backup": True}))
        if not self.obd.upgrade_cluster(cluster_name, upgrade_mode, comp_kwargs={"default_oms_files_path": default_oms_files_path}, web=True):
            self.context['upgrade']['succeed'] = False
            return False
        self.context['upgrade']['succeed'] = True
        return True

    def get_oms_upgrade_task(self, task_id):
        task_info = self.context['task_info'][self.context['oms_deployment'][task_id]]
        if task_info is None:
            raise Exception("task {0} not found".format(task_id))
        task_info.status = TaskStatus.RUNNING
        task_info.result = TaskResult.RUNNING
        task_info.info = []
        task_info.finished = ''

        if self.context['upgrade']['succeed'] is False:
            task_info.result = TaskResult.FAILED
            task_info.status = TaskStatus.FINISHED
        if self.context['upgrade']['succeed'] is True:
            task_info.result = TaskResult.SUCCESSFUL
            task_info.status = TaskStatus.FINISHED
        return task_info

    def takeover_oms(self, cluster_name, host, container_name, user, password, port):
        password = RSAHandler().decrypt_private_key(password) if password is not None else password
        ssh_info = {"host": host, "username": user, "password": password, "port": port}
        repository = self.obd.repository_manager.get_repository_allow_shadow(const.OMS_CE, '1.0.0')
        self.obd.set_repositories([repository])
        data = {
            "nodes": '',
            "success": False,
            "error": ''
        }

        workflows = self.obd.get_workflows('get_takeover_config')
        if not self.obd.run_workflow(workflows, **{repository.name: {"ssh_info": ssh_info, "container_name": container_name}}):
            error = self.obd.get_namespace(const.OMS_CE).get_return('get_takeover_config').get_return('error') or []
            data['error'] = error
            return data

        config = self.obd.get_namespace(const.OMS_CE).get_return('get_takeover_config').get_return('cluster_config')
        data['nodes'] = self.obd.get_namespace(const.OMS_CE).get_return('get_takeover_config').get_return('servers')
        data['version'] = self.obd.get_namespace(const.OMS_CE).get_return('get_takeover_config').get_return('version')

        cluster_config_yaml_path = ''
        log.get_logger().info('dump oms config from path: %s' % cluster_config_yaml_path)
        yaml = YamlLoader()
        with tempfile.NamedTemporaryFile(delete=False, prefix="oms", suffix="yaml", mode="w", encoding="utf-8") as f:
            f.write(yaml.dumps(config))
            cluster_config_yaml_path = f.name

        deploy = self.obd.deploy_manager.create_deploy_config(cluster_name, cluster_config_yaml_path)
        if not deploy:
            log.get_logger().error('Failed to create deploy: %s. please check you configuration file' % cluster_name)
            raise Exception('Failed to create deploy: %s. please check you configuration file' % cluster_name)
        self.obd.set_deploy(deploy)
        deploy_config = deploy.deploy_config
        repositories, _ = self.obd.search_components_from_mirrors_and_install(deploy_config, raise_exception=False)
        self.obd.repositories = repositories
        for repository in repositories:
            deploy.use_model(repository.name, repository, False)
        repository = repositories[0]
        self.obd.deploy.deploy_info.components[const.OMS_CE]['md5'] = repository.md5
        self.obd.deploy.deploy_info.status = DeployStatus.STATUS_RUNNING
        self.obd.deploy.dump_deploy_info()
        data['success'] = True
        return data

    def display(self):
        workflows = self.obd.get_workflows('display')
        if not self.obd.run_workflow(workflows, repositories=self.obd.repositories):
            raise Exception('display failed')
        else:
            url = self.obd.get_namespace(const.OMS_CE).get_return('display').get_return('url') or ''
            return url

    def meta_info_backup(self, backup_path, pre_check):
        data = {"error": '', 'success': False}
        exist_ret = LocalClient.execute_command(
            f"if [ -e '{backup_path}' ]; then echo exist; else echo not_exist; fi").stdout.strip()
        if exist_ret == 'exist':
            check_empty_ret = LocalClient.execute_command(
                f"if [ -d '{backup_path}' ]; then "
                f"res=$(find '{backup_path}' -maxdepth 1 -mindepth 1 -not -name 'lost+found' -not -name '.DS_Store' 2>/dev/null | head -n 1); "
                f"if [ -n \"$res\" ]; then echo not_empty; else echo empty; fi; "
                f"else echo not_dir; fi"
            ).stdout.strip()
            if check_empty_ret == 'not_empty':
                data['error'] = 'backup_path is exist and not empty'
                return data

        ret = LocalClient.execute_command(f"mkdir -p {backup_path}")
        if not ret:
            error = ret.stderr
            data['error'] = error
            return data
        if Capacity(LocalClient.execute_command(f"df -BG {backup_path} | awk 'NR==2 {{print $4}}'").stdout.strip()).bytes < 2 << 30:
            data['error'] = 'backup_path is not enough space. (need: 2G)'
            return data
        else:
            LocalClient.execute_command(f"rm -rf {backup_path}")

        if pre_check:
            data['success'] = True
            return data
        workflows = self.obd.get_workflows('meta_backup')
        if not self.obd.run_workflow(workflows, **{const.OMS_CE: {"backup_path": backup_path}}):
            data['error'] = 'backup failed. See the obd log for details..'
            return data
        else:
            data['success'] = True
            return data