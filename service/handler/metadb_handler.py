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
import yaml
import tempfile
from collections import defaultdict
from optparse import Values
from singleton_decorator import singleton

from service.handler.base_handler import BaseHandler
from service.handler.rsa_handler import RSAHandler
from service.common import log, task, util, const
from service.common.task import Serial as serial
from service.common.task import AutoRegister as auto_register
from service.model.ssh import SshAuthMethod
from service.model.metadb import MetadbDeploymentInfo, RecoverChangeParameter, MetadbDeploymentConfig, Flag
from service.model.deployments import OCPDeploymentStatus
from service.model.parameter import Parameter
from service.model.resource import DiskInfo, Disk, MetaDBResource, ResourceCheckResult
from service.model.database import DatabaseConnection
from service.model.task import TaskStatus, TaskResult, TaskInfo, PreCheckResult, PrecheckTaskInfo, PrecheckEventResult, TaskStepInfo
from _deploy import DeployStatus, DeployConfigStatus
from _errno import CheckStatus, FixEval
from tool import Cursor


@singleton
class MetadbHandler(BaseHandler):

    def generate_metadb_config_path(self, config):
        cluster_config = {}

        if config is not None:
            self.generate_metadb_config(cluster_config, config)
            if config.auth is not None:
                self.generate_auth_config(cluster_config, config.auth)

        with tempfile.NamedTemporaryFile(delete=False, prefix="ocp", suffix=".yaml", mode="w", encoding="utf-8") as f:
            f.write(yaml.dump(cluster_config, sort_keys=False))
            cluster_config_yaml_path = f.name
        log.get_logger().info('dump metadb config from path: %s' % cluster_config_yaml_path)
        self.context['id'] = self.context['id'] + 1 if self.context['id'] else 1
        self.context['deployment_info'][self.context['id']] = {'status': OCPDeploymentStatus.INIT.value, 'config': config, 'connection': None}
        self.context['meta_path'] = cluster_config_yaml_path
        return cluster_config_yaml_path

    def generate_auth_config(self, cluster_config, auth):
        if 'user' not in cluster_config.keys():
            cluster_config['user'] = {}
        cluster_config['user']['username'] = auth.user
        cluster_config['user']['password'] = auth.password
        cluster_config['user']['private_key'] = '' if auth.auth_method == SshAuthMethod.PASSWORD else auth.private_key
        cluster_config['user']['port'] = auth.port

    def generate_metadb_config(self, cluster_config, config):
        log.get_logger().debug('generate metadb config')
        oceanbase_config = dict()
        config_dict = config.dict()

        if config_dict.get('servers'):
            oceanbase_config['servers'] = config.servers

        if 'global' not in oceanbase_config.keys():
            oceanbase_config['global'] = {}

        for key in config_dict:
            if config_dict[key] and key in {'sql_port', 'rpc_port', 'home_path', 'data_dir', 'log_dir', 'appname',
                                            'root_password', 'devname'}:
                if key == 'sql_port':
                    oceanbase_config['global']['mysql_port'] = config_dict[key]
                    continue
                if key == 'data_dir':
                    oceanbase_config['global']['data_dir'] = config_dict[key]
                    continue
                if key == 'log_dir':
                    oceanbase_config['global']['redo_dir'] = config_dict[key]
                    continue
                oceanbase_config['global'][key] = config_dict[key]

        if config.home_path == '':
            oceanbase_config['global']['home_path'] = config.home_path + '/oceanbase'

        if config.parameters:
            for parameter in config.parameters:
                oceanbase_config['global'][parameter.name] = parameter.value
        cluster_config[const.OCEANBASE_CE] = oceanbase_config

    def create_deployment(self, name: str, config_path: str):
        log.get_logger().info('in deploy metadb stage')
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        if deploy:
            deploy_info = deploy.deploy_info
            if deploy_info.status == DeployStatus.STATUS_DEPLOYED:
                self.destroy_name(name, deploy)
            deploy = self.obd.deploy_manager.get_deploy_config(name)
            deploy_info = deploy.deploy_info
            if deploy_info.status not in [DeployStatus.STATUS_CONFIGURED, DeployStatus.STATUS_DESTROYED]:
                log.get_logger().error('Deploy "%s" is %s. You could not deploy an %s cluster.' % (
                    name, deploy_info.status.value, deploy_info.status.value))
                raise Exception('Deploy "%s" is %s. You could not deploy an %s cluster.' % (
                    name, deploy_info.status.value, deploy_info.status.value))
            if deploy_info.config_status != DeployConfigStatus.UNCHNAGE:
                log.get_logger().info('Apply temp deploy configuration')
                if not deploy.apply_temp_deploy_config():
                    log.get_logger().error('Failed to apply new deploy configuration')
                    raise Exception('Failed to apply new deploy configuration')

        deploy = self.obd.deploy_manager.create_deploy_config(name, config_path)
        if not deploy:
            log.get_logger().error('Failed to create deploy: %s. please check you configuration file' % name)
            raise Exception('Failed to create deploy: %s. please check you configuration file' % name)
        self.obd.set_deploy(deploy)
        log.get_logger().info('cluster config path: %s ' % config_path)
        self.context['deployment_id'][self.context['id']] = name
        return self.context['id']

    def generate_secure_metadb_deployment(self, metadb_deployment):
        metadb_deployment_copy = copy.deepcopy(metadb_deployment)
        metadb_deployment_copy.root_password = ''
        if metadb_deployment_copy.auth:
            metadb_deployment_copy.auth.password = ''
        return metadb_deployment_copy

    def destroy_name(self, name, deploy):
        self.obd.set_options(Values({'force_kill': True}))
        log.get_logger().info('start destroy %s' % name)
        if self.obd.repositories:
            repositories = [repository for repository in self.obd.repositories if repository.name == 'oceanbase-ce']
            self.obd.set_repositories(repositories)
            self.obd._destroy_cluster(self.obd.deploy, repositories)
        else:
            self.obd.destroy_cluster(name)
            log.get_logger().info('destroy %s end' % name)
        deploy.update_deploy_status(DeployStatus.STATUS_CONFIGURED)

    def list_metadb_deployments(self):
        data = []
        for id, deployment_info in self.context['deployment_info'].items():
            if deployment_info:
                meta_deployment_info = MetadbDeploymentInfo()
                meta_deployment_info.id = id
                meta_deployment_info.status = deployment_info['status']
                deployment_info['config'].root_password = ''
                if deployment_info['config'].auth:
                    deployment_info['config'].auth.password = ''
                meta_deployment_info.config = deployment_info['config']
                meta_deployment_info.connection = deployment_info['connection']
                data.append(meta_deployment_info)
        return data

    def get_server_disk_info(self, client, paths, data):
        for path in paths:
            for _ in client.execute_command(
                    "df --block-size=1g %s | awk '{if(NR>1)print}'" % path).stdout.strip().split('\n'):
                _ = [i for i in _.split(' ') if i != '']
                dev = _[0]
                mount_path = _[5]
                total_size = _[1]
                free_size = _[3]
                _disk_info = DiskInfo(dev=dev, mount_path=mount_path, total_size=total_size, free_size=free_size)
                data.append(Disk(path=path, disk_info=_disk_info))
        return data

    def get_server_memory_info(self, client, resource_check_results, address):
        memory_free = client.execute_command(
            "cat /proc/meminfo|grep MemFree|cut -f2 -d:|uniq | awk '{print $1}'").stdout.strip()
        memory_higher_limit = int(int(memory_free) / 1024 / 1024)
        memory_default = max(int(int(int(memory_free) / 1024 / 1024) * 0.7), 6)
        memory_lower_limit = 6

        if memory_higher_limit < memory_lower_limit:
            resource_check_results.append(ResourceCheckResult(
                address=address, name='memory_limit', check_result=False,
                error_message=[f'{address}: memory is not enough'])
            )
        return memory_higher_limit, memory_default, memory_lower_limit

    def check_dir_empty(self, client, paths, address, resource_check_results, user):
        def check_directory(client, path, path_name):
            check_result = ResourceCheckResult(address=address, name=path_name)
            ret = client.execute_command(f'ls {path}')
            if not ret or ret.stdout.strip():
                check_result.check_result = False
                check_result.error_message.append(f'{address}: {path} is not empty')
            return check_result

        for path in paths:
            if not client.execute_command('mkdir -p %s' % path):
                raise Exception('%s@%s: dir Permission denied' % (user, address))
        resource_check_results.append(check_directory(client, paths[0], 'home_path'))
        resource_check_results.append(check_directory(client, paths[1], 'data_dir'))
        resource_check_results.append(check_directory(client, paths[2], 'log_diir'))
        return resource_check_results

    def cal_cluster_resource(self, resource_check_results, address, paths, data):
        flag = Flag.not_matched.value
        data_size_default = 10
        log_size_default = 20
        if data[0].disk_info.mount_path == data[1].disk_info.mount_path == data[2].disk_info.mount_path:
            data_size_default = int((int(data[0].disk_info.free_size) - 20) * 0.6)
            log_size_default = int((int(data[0].disk_info.free_size) - 20) * 0.4)
            flag = Flag.same_disk.value
        elif data[1].disk_info.mount_path == data[2].disk_info.mount_path:
            data_size_default = int((int(data[1].disk_info.free_size) - 20) * 0.6)
            log_size_default = int((int(data[2].disk_info.free_size) - 20) * 0.4)
            flag = Flag.data_and_log_same_disk.value
        elif data[0].disk_info.mount_path == data[1].disk_info.mount_path or data[0].disk_info.mount_path == data[
            2].disk_info.mount_path:
            data_size_default = int(data[1].disk_info.free_size) - 20
            log_size_default = int(data[2].disk_info.free_size) - 20
            flag = Flag.home_data_or_home_log_same_disk.value
        elif data[1].disk_info.mount_path != data[2].disk_info.mount_path:
            data_size_default = int(int(data[1].disk_info.free_size) * 0.9)
            log_size_default = int(int(data[2].disk_info.free_size) * 0.9)
            flag = Flag.data_log_different_disk.value

        if data_size_default > int(data[1].disk_info.free_size) or data_size_default < 1:
            resource_check_results[-2].check_result = False
            resource_check_results[-2].error_message.append(f'{address}:{paths[1]} disk resource is not enough')

        if log_size_default > int(data[2].disk_info.free_size) or log_size_default < 20:
            resource_check_results[-1].check_result = False
            resource_check_results[-1].error_message.append(f'{address}:{paths[2]} disk resource is not enough')
        return data_size_default, log_size_default, flag

    def check_machine_resource(self, id):
        if id not in self.context['deployment_id']:
            raise Exception(f'no such deployment for id {id}')
        deploy = self.obd.deploy
        if not deploy:
            raise Exception("no such deploy for name:{0}".format(self.context['deployment_id'][id]))
        deploy_config = deploy.deploy_config
        pkgs, repositories, errors = self.obd.search_components_from_mirrors(deploy_config, only_info=True)
        if errors:
            raise Exception("{}".format('\n'.join(errors)))
        self.obd.search_param_plugin_and_apply(repositories, deploy_config)
        self.obd.set_repositories(repositories)

        install_plugins = self.obd.get_install_plugin_and_install(repositories, pkgs)

        ssh_clients, connect_status = self.obd.get_clients_with_connect_status(deploy_config, repositories)

        config = self.context['deployment_info'][id]['config']
        paths = [config.home_path, config.data_dir, config.log_dir]

        resource_check_results = []
        data = []
        metadb_resource = []
        for server in ssh_clients:
            client = ssh_clients[server]
            address = server.ip

            self.check_dir_empty(client, paths, address, resource_check_results, config.auth.user)
            self.get_server_disk_info(client, paths, data)
            data_size_default, log_size_default, flag = self.cal_cluster_resource(paths, address, resource_check_results, data)
            memory_higher_limit, memory_default, memory_lower_limit = self.get_server_memory_info(client, address, resource_check_results)
            metadb_resource.append(MetaDBResource(
                address=address, disk=data, memory_limit_lower_limit=memory_lower_limit,
                memory_limit_higher_limit=memory_higher_limit, data_size_default=data_size_default,
                memory_limit_default=memory_default, log_size_default=log_size_default, flag=flag
            ))
        self.context[id]['metadb_resource'] = metadb_resource
        return resource_check_results

    def get_machine_resource(self, id):
        if self.context[id]['metadb_resource']:
            return self.context[id]['metadb_resource']
        self.check_machine_resource(id)
        return self.context[id]['metadb_resource'] if self.context[id]['metadb_resource'] else []

    @serial("precheck")
    def precheck(self, id, background_tasks):
        task_manager = task.get_task_manager()
        cluster_name = self.context['deployment_id'][id]
        if not cluster_name:
            raise Exception(f"no such deploy for id: {id}")
        task_info = task_manager.get_task_info(cluster_name, task_type="precheck")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception(f"task {cluster_name} exists and not finished")
        deploy = self.obd.deploy
        if not deploy:
            raise Exception(f"no such deploy: {cluster_name}")
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
                        "Deploying multiple {} instances on the same server is not supported.'".format(repository.name))
                real_servers.add(server.ip)
        self.obd.search_param_plugin_and_apply(repositories, deploy_config)
        self.obd.set_repositories(repositories)

        start_check_plugins = self.obd.search_py_script_plugin(repositories, 'start_check', no_found_act='warn')

        self._precheck(cluster_name, repositories, start_check_plugins, init_check_status=True)
        info = task_manager.get_task_info(cluster_name, task_type="precheck")
        if info is not None and info.exception is not None:
            exception = copy.deepcopy(info.exception)
            info.exception = None
            raise exception
        task_manager.del_task_info(cluster_name, task_type="precheck")
        background_tasks.add_task(self._precheck, cluster_name, repositories, start_check_plugins, init_check_status=False)
        self.context['deployment']['task_id'] = self.context['deployment']['task_id'] + 1 if self.context['deployment']['task_id'] else 1
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'precheck'
        ret = TaskInfo(id=self.context['deployment']['task_id'], status=task_status, result=task_res, message=task_message)
        self.context['task_info'][self.context['deployment'][ret.id]] = ret
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

    def __build_connection_info(self, id, component, info):
        if info is None:
            log.get_logger().warn("component {0} info from display is None".format(component))
            return None
        self.context['sys_cursor'] = Cursor(ip=info['ip'], port=info['port'], user=info['user'], password=info['password'],
                                            stdio=self.obd.stdio)
        return DatabaseConnection(id=id, host=info['ip'], port=info['port'], user=info['user'], password=info['password'], database='oceanbase')

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
            res = self.obd.call_plugin(start_check_plugins[repository], repository, init_check_status=True, work_dir_check=True, clients={})
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
        ssh_clients, connect_status = self.obd.get_clients_with_connect_status(self.obd.deploy.deploy_config, repositories, fail_exit=False)
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
            res = self.obd.call_plugin(start_check_plugins[repository], repository, init_check_status=False, work_dir_check=True, precheck=True)
            if not res and res.get_return("exception"):
                raise res.get_return("exception")

    def get_precheck_result(self, id, task_id):
        precheck_result = PrecheckTaskInfo()
        deploy = self.obd.deploy
        name = self.context['deployment_id'][id]
        if not name:
            raise Exception(f"no such deploy for id: {id}")
        if not deploy:
            deploy = self.obd.deploy_manager.get_deploy_config(name)
            self.obd.set_deploy(deploy)
        components = deploy.deploy_config.components
        param_check_status = None
        connect_check_status = None
        task_info = self.context['task_info'][self.context['deployment'][task_id]]
        if not task_info:
            raise Exception(f"no such task_info for task_id: {task_id}")

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
                    check_result = self.parse_precheck_result(component, task_info, server, result)
                    precheck_result.precheck_result = check_result
                    precheck_result.task_info = task_info
        return precheck_result

    def parse_precheck_result(self, component, task_info, server, result):
        check_result = []
        all_passed = True
        task_info.info = []
        task_info.finished = ''
        for k, v in result.items():
            check_info = PreCheckResult(name='{}:{}'.format(component, k), server=server.ip)
            task_info.current = '{}:{}'.format(component, k)
            info = TaskStepInfo(name='{}:{}'.format(component, k))
            if v.status == v.PASS:
                check_info.result = PrecheckEventResult.PASSED
                info.status = TaskStatus.FINISHED
                info.result = TaskResult.SUCCESSFUL
                task_info.finished += k + ' '
            elif v.status == v.FAIL:
                check_info.result = PrecheckEventResult.FAILED
                check_info.code = v.error.code
                check_info.advisement = v.error.msg
                check_info.recoverable = len(v.suggests) > 0 and v.suggests[0].auto_fix
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
        status_flag = [i.result for i in task_info.info]
        if TaskResult.RUNNING not in status_flag:
            task_info.status = TaskStatus.FINISHED
            task_info.result = TaskResult.SUCCESSFUL if all_passed else TaskResult.FAILED
        check_result.sort(key=lambda p: p.result)
        return check_result

    def recover(self, id):
        deploy = self.obd.deploy
        name = self.context['deployment_id'][id]
        if not name:
            raise Exception(f"no such deploy for id: {id}")
        if not deploy:
            deploy = self.obd.deploy_manager.get_deploy_config(name)
            self.obd.set_deploy(deploy)

        components = deploy.deploy_config.components
        param_check_status = {}
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
                                    config_json, old_value = self.modify_config(id, fix_eval)

                                if config_json is None:
                                    log.get_logger().warn('config json is None')
                                    continue
                                recover_change_parameter = RecoverChangeParameter(name=fix_eval.key, old_value=old_value, new_value=fix_eval.value)
                                recover_change_parameter_list.append(recover_change_parameter)
                deploy.deploy_config.dump()
                self.recreate_deployment(id)

        return recover_change_parameter_list

    def recreate_deployment(self, id):
        config = self.context['deployment_info'][id]['config'] if self.context['deployment_info'] is not None else None
        name = self.context['deployment_id'][id]
        if config is not None:
            cluster_config_yaml_path = self.generate_metadb_config_path(config)
            self.create_deployment(name, cluster_config_yaml_path)

    def modify_config(self, id, fix_eval):
        if fix_eval.key == "parameters":
            raise Exception("try to change parameters")
        config = self.context['deployment_info'][id]['config'] if self.context['deployment_info'] is not None else None
        if config is None:
            log.get_logger().warn("config is none, no need to modify")
            raise Exception('config is none')
        config_dict = config.dict()
        old_value = None
        if fix_eval.key in config_dict:
            del config_dict[fix_eval.key]
        elif "parameters" in config_dict.keys() and config_dict["parameters"] is not None:
            for index, parameter_dict in enumerate(config_dict["parameters"]):
                parameter = Parameter(**parameter_dict)
                if parameter.name == fix_eval.key:
                    del config_dict['parameters'][index]
        self.context['deployment_info'][id]['config'] = MetadbDeploymentConfig(**config_dict)
        return config_dict, old_value

    @serial("install")
    def install(self, id, background_tasks):
        task_manager = task.get_task_manager()
        task_info = task_manager.get_task_info(id, task_type="install")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception("task {0} exists and not finished".format(id))
        task_manager.del_task_info(id, task_type="install")
        background_tasks.add_task(self._do_install, id)
        self.context['deployment']['task_id'] = self.context['deployment']['task_id'] + 1 if self.context['deployment']['task_id'] else 1
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'install'
        ret = TaskInfo(id=self.context['deployment']['task_id'], status=task_status, result=task_res, total='init start_check, start, connect, bootstrap, display', message=task_message)
        self.context['task_info'][self.context['deployment'][ret.id]] = ret
        return ret

    @auto_register("install")
    def _do_install(self, id):
        name = self.context['deployment_id'][id]
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
        opt = Values()
        setattr(opt, "clean", True)
        setattr(opt, "force", True)
        self.obd.set_options(opt)
        deploy_success = self.obd.deploy_cluster(name)
        if not deploy_success:
            log.get_logger().warn("deploy %s failed", name)
        log.get_logger().info("start %s", name)

        repositories = self.obd.load_local_repositories(self.obd.deploy.deploy_info, False)
        repositories = [repository for repository in repositories if repository.name == 'oceanbase-ce']
        start_success = True
        for repository in repositories:
            opt = Values()
            setattr(opt, "components", repository.name)
            setattr(opt, "strict_check", False)
            self.obd.set_options(opt)
            ret = self.obd._start_cluster(self.obd.deploy, repositories)
            if not ret:
                log.get_logger().warn("failed to start component: %s", repository.name)
                start_success = False
            else:
                display_ret = self.obd.namespaces[repository.name].get_return("display")
                connection_info = self.__build_connection_info(id, repository.name, display_ret.get_return("info"))
                if connection_info is not None:
                    self.context["connection_info"][id] = connection_info
        if not start_success:
            raise Exception("task {0} start failed".format(name))
        self.obd.deploy.update_deploy_status(DeployStatus.STATUS_RUNNING)
        log.get_logger().info("finish do start %s", name)

    def get_install_task_info(self, id, task_id):
        name = self.context['deployment_id'][id]
        task_info = self.context['task_info'][self.context['deployment'][task_id]]
        if task_info is None:
            raise Exception("task {0} not found".format(task_id))
        task_info.status = TaskStatus.RUNNING
        task_info.result = TaskResult.RUNNING
        task_info.info = []
        failed = 0

        self.context['deployment']['failed'] = 0 if not self.context['deployment']['failed'] else \
            self.context['deployment']['failed']

        for component in self.obd.deploy.deploy_config.components:
            if component in self.obd.namespaces:
                for plugin in const.INIT_PLUGINS:
                    task_info.current = f'{component}-{plugin}'
                    step_info = TaskStepInfo(name=f'{component}-{plugin}', status=TaskStatus.RUNNING, result=TaskResult.RUNNING)
                    if self.obd.namespaces[component].get_return(plugin) is not None:
                        if not self.obd.namespaces[component].get_return(plugin):
                            failed += 1
                            step_info.result = TaskResult.FAILED
                        else:
                            step_info.result = TaskResult.SUCCESSFUL
                    step_info.status = TaskStatus.FINISHED
                    task_info.info.append(step_info)
                    task_info.finished += f'{component}-{plugin} '

        for component in self.obd.deploy.deploy_config.components:
            if component in self.obd.namespaces:
                for plugin in const.START_PLUGINS:
                    step_info = TaskStepInfo(name=f'{component}-{plugin}', status=TaskStatus.RUNNING, result=TaskResult.RUNNING)
                    task_info.current = f'{component}-{plugin}'
                    if component not in self.obd.namespaces:
                        break
                    if self.obd.namespaces[component].get_return(plugin) is not None:
                        if not self.obd.namespaces[component].get_return(plugin):
                            step_info.result = TaskResult.FAILED
                            failed += 1
                        else:
                            step_info.result = TaskResult.SUCCESSFUL
                    step_info.status = TaskStatus.FINISHED
                    task_info.info.append(step_info)
                    task_info.finished += f'{component}-{plugin} '

        if self.obd.deploy.deploy_info.status == DeployStatus.STATUS_RUNNING:
            task_info.result = TaskResult.SUCCESSFUL
            task_info.status = TaskStatus.FINISHED

        if failed or self.context['deployment']['failed'] >= 300:
            self.context['deployment']['failed'] = 0
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
        background_tasks.add_task(self._do_reinstall, id)
        self.context['deployment']['task_id'] = self.context['deployment']['task_id'] + 1 if \
        self.context['deployment'][
            'task_id'] else 1
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'reinstall'
        ret = TaskInfo(id=self.context['deployment']['task_id'], status=task_status, result=task_res,
                       total='destroy init start_check, start, connect, bootstrap, display', message=task_message)
        self.context['task_info'][self.context['deployment'][ret.id]] = ret
        return ret

    @auto_register("reinstall")
    def _do_reinstall(self, id):
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
                    self.obd.namespaces[component].set_return(plugin, None)

        name = self.context['deployment_id'][id]
        log.get_logger().info('start destroy %s' % name)
        opt = Values()
        setattr(opt, "force_kill", True)
        setattr(opt, "force", True)
        setattr(opt, "clean", True)
        self.obd.set_options(opt)
        if not self.obd.redeploy_cluster(name):
            raise Exception('reinstall failed')

        self.obd.deploy.update_deploy_status(DeployStatus.STATUS_RUNNING)
        log.get_logger().info("finish do start %s", name)

    def get_reinstall_task_info(self, id, task_id):
        name = self.context['deployment_id'][id]
        task_info = self.context['task_info'][self.context['deployment'][task_id]]
        if task_info is None:
            raise Exception("task {0} not found".format(task_id))
        task_info.status = TaskStatus.RUNNING
        task_info.result = TaskResult.RUNNING
        task_info.info = []
        task_info.finished = ''
        failed = 0
        self.context['deployment']['failed'] = 0 if not self.context['deployment']['failed'] else \
        self.context['deployment']['failed']

        for c in self.obd.deploy.deploy_config.components:
            step_info = TaskStepInfo(name=f'{c}-{const.DESTROY_PLUGIN}', status=TaskStatus.RUNNING,
                                     result=TaskResult.RUNNING)
            if c in self.obd.namespaces:
                if self.obd.namespaces[c].get_return(const.DESTROY_PLUGIN) is not None:
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
                    step_info = TaskStepInfo(name=f'{component}-{plugin}', status=TaskStatus.RUNNING,
                                             result=TaskResult.RUNNING)
                    if self.obd.namespaces[component].get_return(plugin) is not None:
                        if not self.obd.namespaces[component].get_return(plugin):
                            failed += 1
                            step_info.result = TaskResult.FAILED
                        else:
                            step_info.result = TaskResult.SUCCESSFUL
                    else:
                        self.context['deployment']['failed'] += 1
                    step_info.status = TaskStatus.FINISHED
                    task_info.info.append(step_info)
                    task_info.finished += f'{component}-{plugin} '

        for component in self.obd.deploy.deploy_config.components:
            for plugin in const.START_PLUGINS:
                step_info = TaskStepInfo(name=f'{component}-{plugin}', status=TaskStatus.RUNNING,
                                         result=TaskResult.RUNNING)
                task_info.current = f'{component}-{plugin}'
                if component not in self.obd.namespaces:
                    break
                if self.obd.namespaces[component].get_return(plugin) is not None:
                    if not self.obd.namespaces[component].get_return(plugin):
                        step_info.result = TaskResult.FAILED
                        failed += 1
                    else:
                        step_info.result = TaskResult.SUCCESSFUL
                step_info.status = TaskStatus.FINISHED
                task_info.info.append(step_info)
                task_info.finished += f'{component}-{plugin} '

        if self.obd.deploy.deploy_info.status == DeployStatus.STATUS_RUNNING:
            task_info.result = TaskResult.SUCCESSFUL
            task_info.status = TaskStatus.FINISHED

        if failed or self.context['deployment']['failed'] >= 300:
            self.context['deployment']['failed'] = 0
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
        self.context['deployment']['task_id'] = self.context['deployment']['task_id'] + 1 if self.context['deployment'][
            'task_id'] else 1
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'destroy'
        ret = TaskInfo(id=self.context['deployment']['task_id'], status=task_status, result=task_res,
                       total='destroy', message=task_message)
        self.context['task_info'][self.context['deployment'][ret.id]] = ret
        return ret

    @auto_register("destroy")
    def _destroy_cluster(self, id):

        name = self.context['deployment_id'][id]
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

        ret = self.obd._destroy_cluster(deploy, repositories)
        if not ret:
            raise Exception("destroy cluster {0} failed".format(name))
        deploy.update_deploy_status(DeployStatus.STATUS_CONFIGURED)
        self.obd.set_options(Values())

    def get_destroy_task_info(self, id, task_id):
        name = self.context['deployment_id'][id]
        task_info = self.context['task_info'][self.context['deployment'][task_id]]
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
                if self.obd.namespaces[c].get_return(const.DESTROY_PLUGIN) is not None:
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

    def create_connection_info(self, info, sys=False):
        self.context["connection_info"][info.cluster_name] = info
        passwd = RSAHandler().decrypt_private_key(info.password)
        info.password = passwd
        log.get_logger().info(
            f'connection host: {info.host}, port: {info.port}, user: {info.user}, password: {info.password}'
        )
        if sys and '@' in info.user and info.user.split('#')[0].split('@')[1] != 'sys':
            raise Exception('The incoming user must belong to the sys tenant.')
        self.context['meta_database'] = info.database
        self.context['metadb_cursor'] = Cursor(ip=info.host, port=info.port, user=info.user, password=info.password, stdio=self.obd.stdio)
        connection_info = DatabaseConnection(id=info.cluster_name, host=info.host, port=info.port, user=info.user, password=info.password, database=info.database)
        connection_info_copy = copy.deepcopy(connection_info)
        connection_info_copy.password = ''
        return connection_info_copy

    def get_connection_info(self, cluster_name):
        if not self.context["connection_info"]:
            return None
        if not self.context["connection_info"].get(cluster_name):
            return None
        connection_info_copy = copy.deepcopy(self.context['connection_info'][cluster_name])
        connection_info_copy.password = ''
        return connection_info_copy