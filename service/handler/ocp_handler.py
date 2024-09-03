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
import os
import time
import tempfile
import yaml
import json
from optparse import Values
from singleton_decorator import singleton
from collections import defaultdict

from service.handler.base_handler import BaseHandler
from service.handler.rsa_handler import RSAHandler
from service.common import log, task, util, const
from service.common.task import Serial as serial
from service.common.task import AutoRegister as auto_register
from service.model.deployments import Parameter, OCPDeploymentStatus, OCPDeploymnetConfig
from service.model.database import DatabaseConnection
from service.model.ssh import SshAuthMethod
from service.model.ocp import ObserverResource, OcpResource, MetadbResource, OcpInfo, OcpInstalledInfo, OcpUpgradeLostAddress
from service.model.metadb import RecoverChangeParameter
from service.model.resource import DiskInfo, ServerResource
from service.model.task import TaskStatus, TaskResult, TaskInfo, PreCheckResult, PrecheckTaskInfo, PrecheckEventResult, TaskStepInfo
from _deploy import DeployStatus, DeployConfigStatus, UserConfig
from _errno import CheckStatus, FixEval
from _repository import Repository
from _plugin import PluginType
from ssh import SshClient, SshConfig, LocalClient
from tool import Cursor
from const import COMP_JRE, COMPS_OCP
from tool import COMMAND_ENV
from const import TELEMETRY_COMPONENT_OCP
from _environ import ENV_TELEMETRY_REPORTER



@singleton
class OcpHandler(BaseHandler):

    def create_ocp_config_path(self, config):
        cluster_config = {}

        home_path = config.home_path
        launch_user = config.launch_user
        if config.auth is not None:
            self.generate_auth_config(cluster_config, config.auth)
        if config.components.oceanbase is not None:
            self.generate_metadb_config(cluster_config, config.components.oceanbase, home_path)
        if config.components.obproxy is not None and config.components.oceanbase is not None:
            self.generate_obproxy_config(cluster_config, config.components.obproxy, home_path, config.components.oceanbase.component)
        if config.components.ocpserver is not None:
            ob_component = obp_component = None
            if config.components.obproxy is not None:
                ob_component = config.components.oceanbase.component
            if config.components.obproxy is not None:
                obp_component = config.components.obproxy.component
            self.generate_ocp_config(cluster_config, config.components.ocpserver, home_path, launch_user, ob_component, obp_component)

        cluster_config_yaml_path = ''
        log.get_logger().info('dump ocp-server config from path: %s' % cluster_config_yaml_path)
        with tempfile.NamedTemporaryFile(delete=False, prefix="ocp-server", suffix="yaml", mode="w", encoding="utf-8") as f:
            f.write(yaml.dump(cluster_config, sort_keys=False))
            cluster_config_yaml_path = f.name
        self.context['id'] = self.context['id'] + 1 if self.context['id'] else 1
        log.get_logger().info('ocp deployment id: %s' % self.context['id'])
        status = self.context['ocp_deployment_info'][self.context['id']]['status'] \
            if self.context['ocp_deployment_info'][self.context['id']] and self.context['ocp_deployment_info'][self.context['id']]['status'] \
            else OCPDeploymentStatus.INIT

        self.context['ocp_path'] = cluster_config_yaml_path
        self.context['ocp_deployment_info'][self.context['id']] = {'status': status, 'config': config, 'ocp_start_success_time': time.time()}
        return cluster_config_yaml_path

    def generate_auth_config(self, cluster_config, auth):
        if 'user' not in cluster_config.keys():
            cluster_config['user'] = {}
        cluster_config['user']['username'] = auth.user
        passwd = RSAHandler().decrypt_private_key(auth.password) if auth.password is not None else auth.password
        cluster_config['user']['password'] = passwd
        cluster_config['user']['port'] = auth.port

    def generate_metadb_config(self, cluster_config, oceanbase, home_path):
        oceanbase_config = dict()
        config_dict = oceanbase.dict()
        for key in config_dict:
            if config_dict[key] and key in ('version', 'release', 'package_hash'):
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
            if config_dict[key] and key in ['mysql_port', 'rpc_port', 'home_path', 'data_dir', 'redo_dir', 'appname',
                                            'root_password']:
                if key == 'root_password':
                    passwd = RSAHandler().decrypt_private_key(config_dict[key])
                    oceanbase_config['global'][key] = passwd
                    continue
                oceanbase_config['global'][key] = config_dict[key]

        if oceanbase.home_path == '':
            oceanbase_config['global']['home_path'] = home_path + '/oceanbase'

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

    def generate_obproxy_config(self, cluster_config, obproxy_config, home_path, ob_component):
        comp_config = dict()
        config_dict = obproxy_config.dict()
        for key in config_dict:
            if config_dict[key] and key in ('servers', 'version', 'package_hash', 'release'):
                comp_config[key] = config_dict[key]

        if 'global' not in comp_config.keys():
            comp_config['global'] = dict()

        for key in config_dict:
            if config_dict[key] and key in ('cluster_name', 'prometheus_listen_port', 'listen_port', 'home_path'):
                comp_config['global'][key] = config_dict[key]

        comp_config['global']['enable_obproxy_rpc_service'] = False

        if obproxy_config.home_path == '':
            comp_config['global']['home_path'] = home_path + '/obproxy'

        for parameter in obproxy_config.parameters:
            if not parameter.adaptive:
                if parameter.key == 'obproxy_sys_password':
                    passwd = RSAHandler().decrypt_private_key(parameter.value)
                    comp_config['global'][parameter.key] = passwd
                    continue
                comp_config['global'][parameter.key] = parameter.value
        if 'depends' not in comp_config.keys():
            comp_config['depends'] = list()
            comp_config['depends'].append(ob_component)
        if obproxy_config.component == const.OBPROXY_CE:
            cluster_config[const.OBPROXY_CE] = comp_config
        elif obproxy_config.component == const.OBPROXY:
            cluster_config[const.OBPROXY] = comp_config
        else:
            log.get_logger().error('obproxy component : %s not exist' % obproxy_config.component)
            raise Exception('obproxy component : %s not exist' % obproxy_config.component)

    def generate_ocp_config(self, cluster_config, config, home_path, launch_user, ob_component=None, obp_component=None):
        log.get_logger().debug('generate ocp config')
        ocp_config = dict()
        config_dict = config.dict()
        for key in config_dict:
            if config_dict[key] and key in ('servers', 'version', 'package_hash', 'release'):
                ocp_config[key] = config_dict[key]

        if 'global' not in ocp_config.keys():
            ocp_config['global'] = {}

        for key in config_dict:
            if config_dict[key] and key in ('port', 'admin_password', 'memory_size', 'manage_info', 'home_path', 'soft_dir', 'log_dir', 'ocp_site_url', 'launch_user'):
                if key == 'admin_password':
                    passwd = RSAHandler().decrypt_private_key(config_dict[key])
                    ocp_config['global'][key] = passwd
                    continue
                ocp_config['global'][key] = config_dict[key]

        if launch_user:
            ocp_config['global']['launch_user'] = launch_user

        if config.metadb:
            ocp_config['global']['jdbc_url'] = 'jdbc:oceanbase://' + config_dict['metadb']['host'] + ':' + str(config_dict['metadb']['port']) + config_dict['metadb']['database']
            ocp_config['global']['jdbc_username'] = config_dict['metadb']['user']
            ocp_config['global']['jdbc_password'] = RSAHandler().decrypt_private_key(config_dict['metadb']['password'])

        if config.meta_tenant:
            tenant_config = cluster_config[ob_component] if ob_component is not None else ocp_config
            tenant_config['global']['ocp_meta_tenant'] = {}
            tenant_config['global']['ocp_meta_tenant']['tenant_name'] = config_dict['meta_tenant']['name']['tenant_name']
            tenant_config['global']['ocp_meta_tenant']['max_cpu'] = config_dict['meta_tenant']['resource']['cpu']
            tenant_config['global']['ocp_meta_tenant']['memory_size'] = str(config_dict['meta_tenant']['resource']['memory']) + 'G'
            tenant_config['global']['ocp_meta_username'] = config_dict['meta_tenant']['name']['user_name']
            tenant_config['global']['ocp_meta_password'] = RSAHandler().decrypt_private_key(config_dict['meta_tenant']['password'])
            tenant_config['global']['ocp_meta_db'] = config_dict['meta_tenant']['name']['user_database'] if config_dict['meta_tenant']['name']['user_database'] != '' else 'meta_database'
            self.context['meta_tenant'] = config_dict['meta_tenant']['name']['tenant_name']

        if config.monitor_tenant:
            tenant_config = cluster_config[ob_component] if ob_component is not None else ocp_config
            tenant_config['global']['ocp_monitor_tenant'] = {}
            tenant_config['global']['ocp_monitor_tenant']['tenant_name'] = config_dict['monitor_tenant']['name']['tenant_name']
            tenant_config['global']['ocp_monitor_tenant']['max_cpu'] = config_dict['monitor_tenant']['resource']['cpu']
            tenant_config['global']['ocp_monitor_tenant']['memory_size'] = str(config_dict['monitor_tenant']['resource']['memory']) + 'G'
            tenant_config['global']['ocp_monitor_username'] = config_dict['monitor_tenant']['name']['user_name']
            tenant_config['global']['ocp_monitor_password'] = RSAHandler().decrypt_private_key(config_dict['monitor_tenant']['password'])
            tenant_config['global']['ocp_monitor_db'] = config_dict['monitor_tenant']['name']['user_database'] if config_dict['monitor_tenant']['name']['user_database'] != '' else 'monitor_database'
            self.context['monitor_tenant'] = config_dict['monitor_tenant']['name']['tenant_name']

        if config.home_path == '':
            ocp_config['global']['home_path'] = home_path + '/ocp-server'

        if config.soft_dir == '':
            ocp_config['global']['soft_dir'] = ocp_config['global']['home_path'] + '/data/files/'

        if config.log_dir == '':
            ocp_config['global']['log_dir'] = ocp_config['global']['home_path'] + '/log'

        if config.parameters:
            for parameter in config.parameters:
                if not parameter.adaptive:
                    ocp_config['global'][parameter.key] = parameter.value
        if not ob_component:
            if config_dict['metadb']:
                ocp_config['global']['jdbc_url'] = 'jdbc:oceanbase://' + config_dict['metadb']['host'] + ':' + str(
                    config_dict['metadb']['port']) + '/' + (config_dict['meta_tenant']['name']['user_database'] if config_dict['meta_tenant']['name']['user_database'] != '' else 'meta_database')
        if 'depends' not in ocp_config.keys() and ob_component and obp_component:
            ocp_config['depends'] = list()
            ocp_config['depends'].append(ob_component)
            ocp_config['depends'].append(obp_component)
        if config.component == const.OCP_SERVER_CE:
            cluster_config[const.OCP_SERVER_CE] = ocp_config
        elif config.component == const.OCP_SERVER:
            cluster_config[const.OCP_SERVER] = ocp_config
        else:
            log.get_logger().error('ocp-server component : %s not exist' % config.component)
            raise Exception('ocp-server component : %s not exist' % config.component)

    def create_ocp_deployment(self, name: str, config_path: str):
        log.get_logger().debug('deploy cluster')
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        if deploy:
            deploy_info = deploy.deploy_info
            if deploy_info.status == DeployStatus.STATUS_DEPLOYED:
                log.get_logger().debug('start destroy(ocp) %s' % name)
                self.obd.set_options(Values({'force_kill': True}))
                if self.obd.repositories:
                    self.obd.set_repositories(self.obd.repositories)
                    self.obd._destroy_cluster(self.obd.deploy, self.obd.repositories)
                else:
                    self.obd.destroy_cluster(name)
                log.get_logger().info('destroy %s(ocp) end' % name)
                deploy.update_deploy_status(DeployStatus.STATUS_CONFIGURED)
            deploy = self.obd.deploy_manager.get_deploy_config(name)
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
        log.get_logger().info('ocp server cluster config path: %s ' % config_path)
        self.context['ocp_deployment_id'][self.context['id']] = name
        return self.context['id']

    def check_user(self, user):
        self.context['upgrade_servers'] = user.servers
        user.password = RSAHandler().decrypt_private_key(user.password) if user.password else user.password
        for ip in user.servers:
            log.get_logger().info('ip: %s, port: %s, user: %s, password: %s' % (ip, user.port, user.user, user.password))
            self.context['upgrade_user'] = user.user
            self.context['upgrade_user_password'] = user.password
            self.context['upgrade_ssh_port'] = user.port if user.port else 22
            config = SshConfig(host=ip, port=user.port, username=user.user, password=user.password)
            client = SshClient(config)
            res = client.connect(self.obd.stdio, exit=False)
            if res != True:
                raise Exception("{user}@{ip} connect failed: username or password error".format(user=user.user, ip=ip))
            if not (client.execute_command('[ `id -u` == "0" ]') or client.execute_command('sudo -n true')):
                raise Exception('Please execute `bash -c \'echo "{user} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers`\' as root in {ip}.'.format(user=user.user, ip=ip))
        return True

    def generate_secure_ocp_deployment(self, ocp_deployment):
        log.get_logger().info('generate secure ocp_deployment')
        config = copy.deepcopy(ocp_deployment)
        config.admin_password = ''
        if config.meta_tenant:
            config.meta_tenant.password = ''
        if config.monitor_tenant:
            config.monitor_tenant.password = ''
        if config.components.oceanbase.password:
            config.components.oceanbase.password = ''
        if config.auth:
            config.auth.password = ''
        return config

    def list_ocp_deployments(self):
        log.get_logger().info('list secure ocp_deployment')
        data = []
        for id, ocp_deployment_info in self.context['ocp_deployment_info'].items():
            if ocp_deployment_info:
                copy_ocp_deployment_info = copy.deepcopy(ocp_deployment_info)
                copy_ocp_deployment_info['config'].admin_password = ''
                if copy_ocp_deployment_info['config'].meta_tenant:
                    copy_ocp_deployment_info['config'].meta_tenant.password = ''
                if copy_ocp_deployment_info['config'].monitor_tenant:
                    copy_ocp_deployment_info['config'].monitor_tenant.password = ''
                if copy_ocp_deployment_info['config'].metadb.password:
                    copy_ocp_deployment_info['config'].metadb.password = ''
                if copy_ocp_deployment_info['config'].auth:
                    copy_ocp_deployment_info['config'].auth.password = ''
                data.append(ocp_deployment_info)
        return data

    def get_ocp_deployment(self, id):
        log.get_logger().info('get id(%s) secure ocp_deployment' % id)
        if id not in self.context['ocp_deployment_info']:
            raise Exception(f'id: {id} not deployment')
        data = self.context['ocp_deployment_info'][id]
        copy_data = copy.deepcopy(data)
        copy_data['config'].admin_password = ''
        if copy_data['config'].meta_tenant:
            copy_data['config'].meta_tenant.password = ''
        if copy_data['config'].monitor_tenant:
            copy_data['config'].monitor_tenant.password = ''
        if copy_data['config'].metadb.password:
            copy_data['config'].metadb.password = ''
        if copy_data['config'].auth:
            copy_data['config'].auth.password = ''
        return copy_data['config']

    @serial("ocp_precheck")
    def ocp_precheck(self, id, background_tasks):
        task_manager = task.get_task_manager()
        app_name = self.context['ocp_deployment_id'][id]
        log.get_logger().info('precheck start: %s' % app_name)
        if not app_name:
            raise Exception(f"no such deploy for id: {id}")
        task_info = task_manager.get_task_info(app_name, task_type="ocp_precheck")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception(f"task {app_name} exists and not finished")
        deploy = self.obd.deploy
        if not deploy:
            raise Exception("no such deploy for name:{0}".format(app_name))
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
        self.obd.set_repositories(repositories)

        start_check_plugins = self.obd.search_py_script_plugin(repositories, 'start_check', no_found_act='warn')
        log.get_logger().debug('start_check plugins: %s' % start_check_plugins)
        self._precheck(app_name, repositories, start_check_plugins, init_check_status=True)
        info = task_manager.get_task_info(app_name, task_type="ocp_precheck")
        if info is not None and info.exception is not None:
            exception = copy.deepcopy(info.exception)
            info.exception = None
            raise exception
        task_manager.del_task_info(app_name, task_type="ocp_precheck")
        background_tasks.add_task(self._precheck, app_name, repositories, start_check_plugins, init_check_status=False)
        self.context['ocp_deployment']['task_id'] = self.context['ocp_deployment']['task_id'] + 1 if self.context['ocp_deployment']['task_id'] else 1
        log.get_logger().info('task id: %d' % self.context['ocp_deployment']['task_id'])
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'ocp_precheck'
        ret = TaskInfo(id=self.context['ocp_deployment']['task_id'], status=task_status, result=task_res, message=task_message, total='port, java, disk, mem, oceanbase version')
        log.get_logger().info('task ret: %s' % ret)
        self.context['task_info'][self.context['ocp_deployment'][ret.id]] = ret
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

    @auto_register('ocp_precheck')
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

        self.context['ocp_deployment']['param_check_status'] = param_check_status
        server_connect_status = {}
        for server in servers_set:
            server_connect_status[server] = {'ssh': CheckStatus()}
        self.context['ocp_deployment']['connect_check_status'] = {'ssh': server_connect_status}
        self.context['ocp_deployment']['servers_set'] = servers_set

    def _do_precheck(self, repositories, start_check_plugins):
        log.get_logger().info('start precheck')
        log.get_logger().info('ssh check')
        ssh_clients, connect_status = self.obd.get_clients_with_connect_status(self.obd.deploy.deploy_config, repositories, fail_exit=False)
        log.get_logger().info('connect_status: ', connect_status)
        check_status = self._init_check_status('ssh', self.context['ocp_deployment']['servers_set'], connect_status)
        self.context['ocp_deployment']['connect_check_status'] = {'ssh': check_status}
        for k, v in connect_status.items():
            if v.status == v.FAIL:
                self.context['ocp_deployment_ssh'][self.context['id']] = 'fail'
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
        self.context['ocp_deployment']['param_check_status'] = param_check_status_result

        log.get_logger().debug('precheck param check status: %s' % param_check_status)
        log.get_logger().debug('precheck param check status res: %s' % check_pass)
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

        log.get_logger().info('generate config succeed')
        ssh_clients = self.obd.get_clients(self.obd.deploy.deploy_config, repositories)
        for repository in repositories:
            log.get_logger().info('begin start_check: %s' % repository.name)
            java_check = True
            if repository.name in COMPS_OCP:
                jre_name = COMP_JRE
                install_plugin = self.obd.search_plugin(repository, PluginType.INSTALL)
                if install_plugin and jre_name in install_plugin.requirement_map(repository):
                    version = install_plugin.requirement_map(repository)[jre_name].version
                    min_version = install_plugin.requirement_map(repository)[jre_name].min_version
                    max_version = install_plugin.requirement_map(repository)[jre_name].max_version
                    if len(self.obd.search_images(jre_name, version=version, min_version=min_version, max_version=max_version)) > 0:
                        java_check = False
            res = self.obd.call_plugin(start_check_plugins[repository], repository, init_check_status=False,
                                       work_dir_check=True, precheck=True, java_check=java_check, clients=ssh_clients, source_option = 'start_check',
                                       sys_cursor=self.context['metadb_cursor'], components=list(self.obd.deploy.deploy_config.components.keys()))
            if not res and res.get_return("exception"):
                raise res.get_return("exception")
            log.get_logger().info('end start_check: %s' % repository.name)

    def get_precheck_result(self, id, task_id):
        log.get_logger().info('get ocp precheck result')
        precheck_result = PrecheckTaskInfo()
        deploy = self.obd.deploy
        name = self.context['ocp_deployment_id'][id]
        if not name:
            raise Exception(f"no such deploy for id: {id}")
        if not deploy:
            deploy = self.obd.deploy_manager.get_deploy_config(name)
            self.obd.set_deploy(deploy)
        components = deploy.deploy_config.components

        param_check_status = None
        connect_check_status = None
        check_result = []
        task_info = self.context['task_info'][self.context['ocp_deployment'][task_id]]
        all_passed = []
        precheck_result.task_info = task_info
        task_info.info = []

        if 'ocp_deployment' in self.context.keys():
            param_check_status = self.context['ocp_deployment']['param_check_status']
            connect_check_status = self.context['ocp_deployment']['connect_check_status']
        for component in components:
            namespace_union = {}
            namespace = self.obd.get_namespace(component)
            if namespace:
                variables = namespace.variables
                if 'start_check_status' in variables.keys():
                    namespace_union = util.recursive_update_dict(namespace_union, variables.get('start_check_status'))
            if param_check_status:
                namespace_union = util.recursive_update_dict(namespace_union, param_check_status[component])
            if connect_check_status and 'ssh' in connect_check_status.keys():
                namespace_union = util.recursive_update_dict(namespace_union, connect_check_status['ssh'])

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
        if self.context['ocp_deployment_ssh'][id] == 'fail' and TaskStatus.FINISHED in status_flag:
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
                check_info.advisement = v.suggests[0].msg if len(v.suggests) > 0 and v.suggests[0].msg is not None else ''
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

    def recover(self, id):
        log.get_logger().info('recover config')
        deploy = self.obd.deploy
        name = self.context['ocp_deployment_id'][id]
        if not deploy:
            deploy = self.obd.deploy_manager.get_deploy_config(name)
            self.obd.set_deploy(deploy)

        components = deploy.deploy_config.components
        param_check_status = {}
        if 'ocp_deployment' in self.context.keys():
            param_check_status = self.context['ocp_deployment']['param_check_status']
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
                        log.get_logger().debug('k: %s, v: %s' % (k, v))
                        log.get_logger().debug('status: %s' % v.status)
                        if v.status == v.FAIL and v.suggests is not None and v.suggests[0].auto_fix and v.suggests[0].fix_eval:
                            log.get_logger().debug('auto_fix : %s' % v.suggests[0].auto_fix)
                            log.get_logger().debug('fix_eval: %s' % v.suggests[0].fix_eval)
                            for fix_eval in v.suggests[0].fix_eval:
                                if fix_eval.operation == FixEval.SET:
                                    config_json = None
                                    old_value = None
                                    if fix_eval.is_global:
                                        deploy.deploy_config.update_component_global_conf(name, fix_eval.key, fix_eval.value, save=False)
                                    else:
                                        deploy.deploy_config.update_component_server_conf(name, server, fix_eval.key, fix_eval.value, save=False)
                                else:
                                    config_json, old_value = self.modify_config(component, id, fix_eval)

                                if config_json is None:
                                    log.get_logger().warn('config json is None')
                                    continue
                                recover_change_parameter = RecoverChangeParameter(name=fix_eval.key, old_value=old_value, new_value=fix_eval.value)
                                recover_change_parameter_list.append(recover_change_parameter)
                                self.context['ocp_deployment_info'][id]['config'] = OCPDeploymnetConfig(**json.loads(json.dumps(config_json)))
                deploy.deploy_config.dump()
                self.recreate_deployment(id)

        return recover_change_parameter_list

    def recreate_deployment(self, id):
        log.get_logger().info('recreate ocp deployment')
        config = self.context['ocp_deployment_info'][id]['config'] if self.context['ocp_deployment_info'][id]['config'] is not None else None
        log.get_logger().info('config: %s' % config)
        if config is not None:
            cluster_config_yaml_path = self.create_ocp_config_path(config)
            self.create_ocp_deployment(self.context['ocp_deployment_id'][id], cluster_config_yaml_path)

    def modify_config(self, component, id, fix_eval):
        log.get_logger().info('modify ocp config')
        if fix_eval.key == "parameters":
            raise Exception("try to change parameters")
        config = self.context['ocp_deployment_info'][id] if self.context['ocp_deployment_info'] is not None else None
        if config is None:
            log.get_logger().warn("config is none, no need to modify")
            raise Exception('config is none')
        log.get_logger().info('%s ocp config: %s' % (id, config))
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

    @serial("install")
    def install(self, id, background_tasks):
        task_manager = task.get_task_manager()
        task_info = task_manager.get_task_info(id, task_type="install")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception("task {0} exists and not finished".format(id))
        task_manager.del_task_info(id, task_type="install")
        self.context['ocp_deployment']['task_id'] = self.context['ocp_deployment']['task_id'] + 1 if self.context['ocp_deployment']['task_id'] else 1
        background_tasks.add_task(self._do_install, id, self.context['ocp_deployment']['task_id'])
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'install'
        ret = TaskInfo(id=self.context['ocp_deployment']['task_id'], status=task_status, result=task_res, total='init start_check, start, connect, bootstrap, display', message=task_message)
        self.context['task_info'][self.context['ocp_deployment'][ret.id]] = ret
        return ret

    def _create_tenant(self):
        metadb_version = self.context['metadb_cursor'].fetchone("select ob_version() as version")["version"]
        mock_oceanbase_repository = Repository("oceanbase-ce", "/")
        mock_oceanbase_repository.version = metadb_version
        repositories = [mock_oceanbase_repository]
        create_tenant_plugins = self.obd.search_py_script_plugin(repositories, "create_tenant")
        ocp_config = self.obd.deploy.deploy_config.components["ocp-server-ce"]
        global_conf_with_default = ocp_config.get_global_conf_with_default()
        meta_tenant_config = global_conf_with_default['ocp_meta_tenant']
        meta_tenant_config["variables"] = "ob_tcp_invited_nodes='%'"
        meta_tenant_config["create_if_not_exists"] = True
        meta_tenant_config["database"] = global_conf_with_default["ocp_meta_db"]
        meta_tenant_config["db_username"] = global_conf_with_default["ocp_meta_username"]
        meta_tenant_config["db_password"] = global_conf_with_default.get("ocp_meta_password", "")
        meta_tenant_config[meta_tenant_config['tenant_name'] + "_root_password"] = global_conf_with_default.get("ocp_meta_password", "")
        monitor_tenant_config = global_conf_with_default['ocp_monitor_tenant']
        monitor_tenant_config["variables"] = "ob_tcp_invited_nodes='%'"
        monitor_tenant_config["create_if_not_exists"] = True
        monitor_tenant_config["database"] = global_conf_with_default["ocp_monitor_db"]
        monitor_tenant_config["db_username"] = global_conf_with_default["ocp_monitor_username"]
        monitor_tenant_config["db_password"] = global_conf_with_default.get("ocp_monitor_password", "")
        monitor_tenant_config[monitor_tenant_config['tenant_name'] + "_root_password"] = global_conf_with_default.get("ocp_monitor_password", "")

        ssh_clients = self.obd.get_clients(self.obd.deploy.deploy_config, self.obd.load_local_repositories(self.obd.deploy.deploy_info, False))

        deploy = self.obd.deploy
        self.obd.set_deploy(None)
        log.get_logger().info("start create meta tenant")
        create_meta_ret = self.obd.call_plugin(create_tenant_plugins[mock_oceanbase_repository], mock_oceanbase_repository, cluster_config=ocp_config, cursor=self.context['metadb_cursor'], create_tenant_options=[Values(meta_tenant_config)], clients=ssh_clients)
        if not create_meta_ret:
            self.obd.set_deploy(deploy)
            raise Exception("Create meta tenant failed")
        log.get_logger().info("start create monitor tenant")
        create_monitor_ret = self.obd.call_plugin(create_tenant_plugins[mock_oceanbase_repository], mock_oceanbase_repository, cluster_config=ocp_config, cursor=self.context['metadb_cursor'], create_tenant_options=[Values(monitor_tenant_config)], clients=ssh_clients)
        if not create_monitor_ret:
            self.obd.set_deploy(deploy)
            raise Exception("Create monitor tenant failed")
        self.obd.set_deploy(deploy)


    @auto_register("install")
    def _do_install(self, id, task_id):
        self.context['deploy_status'] = self.context['process_installed'] = ''
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

        name = self.context['ocp_deployment_id'][id]
        deploy = self.obd.deploy
        log.get_logger().info("start deploy %s", name)
        opt = Values()
        setattr(opt, "clean", True)
        setattr(opt, "force", True)
        self.obd.set_options(opt)

        try:
            # add create tenant operations before deploy ocp if it uses an existing OceanBase as it's metadb cluster
            if 'oceanbase-ce' not in self.obd.deploy.deploy_config.components['ocp-server-ce'].depends:
                log.get_logger().info("not depends on oceanbase, create tenant first")
                self._create_tenant()
            deploy_success = self.obd.deploy_cluster(name)
            if not deploy_success:
                log.get_logger().warn("deploy %s failed", name)
                raise Exception('deploy failed')
        except:
            self.obd._call_stdio('exception', '')
            self.context['deploy_status'] = 'failed'
            raise Exception('deploy failed')
        log.get_logger().info("deploy %s succeed", name)

        repositories = self.obd.load_local_repositories(self.obd.deploy.deploy_info, False)
        repositories = self.obd.sort_repository_by_depend(repositories, self.obd.deploy.deploy_config)
        start_success = True
        oceanbase_repository = None
        for repository in repositories:
            log.get_logger().info("begin start %s", repository.name)
            opt = Values()
            setattr(opt, "components", repository.name)
            setattr(opt, "strict_check", False)
            setattr(opt, "metadb_cursor", self.context['metadb_cursor'])
            self.obd.set_options(opt)
            if repository.name == const.OCEANBASE_CE:
                oceanbase_repository = repository
            ret = self.obd._start_cluster(self.obd.deploy, repositories)
            if not ret:
                log.get_logger().warn("failed to start component: %s", repository.name)
                start_success = False
            log.get_logger().info("end start %s", repository.name)
        if not start_success:
            if len(repositories) > 1 and oceanbase_repository:
                drop_tenant_plugins = self.obd.search_py_script_plugin([repository for repository in repositories if repository.name == const.OCEANBASE_CE], 'drop_tenant', no_found_act='warn')
                config = self.context['ocp_deployment_info'][id]['config'].components.oceanbase
                cursor = Cursor(ip=config.topology[0].servers[0].ip, port=config.mysql_port, user='root',
                                password=config.root_password, stdio=self.obd.stdio)
                opt = Values()
                setattr(opt, "tenant_name", self.context['meta_tenant'])
                self.obd.set_options(opt)
                self.obd.call_plugin(drop_tenant_plugins[oceanbase_repository], oceanbase_repository, cursor=cursor)
                opt = Values()
                setattr(opt, "tenant_name", self.context['monitor_tenant'])
                self.obd.set_options(opt)
                self.obd.call_plugin(drop_tenant_plugins[oceanbase_repository], oceanbase_repository, cursor=cursor)
            raise Exception("task {0} start failed".format(name))
        self.obd.deploy.update_deploy_status(DeployStatus.STATUS_RUNNING)
        log.get_logger().info("finish do start %s", name)
        if not self.context['ocp_deployment_info'][id]['config'].components.ocpserver.metadb:
            log.get_logger().info("begin take_over metadb")
            config = self.context['ocp_deployment_info'][id]['config']
            servers = config.components.ocpserver.servers
            port = config.components.ocpserver.port
            password = config.components.ocpserver.admin_password
            password = RSAHandler().decrypt_private_key(password)
            address = ['http://' + str(server) + ':' + str(port) for server in servers]
            self.obd.options._update_loose({"address": address[0], "user": 'admin', "password": password})
            self.obd.export_to_ocp(name)
            log.get_logger().info("finish take_over metadb")
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        self.obd.set_deploy(deploy)
        self.context['process_installed'] = 'done'

        ## get obd namespace data and report telemetry
        data = {}
        for component, _ in self.obd.namespaces.items():
            data[component] = _.get_variable('run_result')
        COMMAND_ENV.set(ENV_TELEMETRY_REPORTER, TELEMETRY_COMPONENT_OCP, save=True)
        LocalClient.execute_command_background("nohup obd telemetry post %s --data='%s' > /dev/null &" % (name, json.dumps(data)))

    def get_install_task_info(self, id, task_id):
        log.get_logger().info('get ocp install task info')
        name = self.context['ocp_deployment_id'][id]
        task_info = self.context['task_info'][self.context['ocp_deployment'][task_id]]
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

        if self.obd.deploy.deploy_info.status == DeployStatus.STATUS_RUNNING and self.context['process_installed'] == 'done':
            self.context['ocp_deployment_info'][id]['ocp_start_success_time'] = time.time()
            task_info.result = TaskResult.SUCCESSFUL
            task_info.status = TaskStatus.FINISHED

        if failed or self.context['deploy_status'] == 'failed':
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
        self.context['ocp_deployment']['task_id'] = self.context['ocp_deployment']['task_id'] + 1 if self.context['ocp_deployment'][
            'task_id'] else 1
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'reinstall'
        ret = TaskInfo(id=self.context['ocp_deployment']['task_id'], status=task_status, result=task_res,
                       total='destroy init start_check, start, connect, bootstrap, display', message=task_message)
        self.context['task_info'][self.context['ocp_deployment'][ret.id]] = ret
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

        name = self.context['ocp_deployment_id'][id]
        repositories = self.obd.repositories
        log.get_logger().info('start destroy %s' % name)
        opt = Values()
        setattr(opt, "force_kill", True)
        self.obd.set_options(opt)
        if not self.obd._destroy_cluster(self.obd.deploy, repositories):
            raise Exception('destroy failed')

        self.obd.set_repositories([])
        deploy = self.obd.deploy_manager.create_deploy_config(name, self.context['ocp_path'])
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

        gen_config_plugins = self.obd.search_py_script_plugin(repositories, 'generate_config')
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
            setattr(opt, "metadb_cursor", self.context['metadb_cursor'])
            self.obd.set_options(opt)
            ret = self.obd._start_cluster(self.obd.deploy, repositories)
            if not ret:
                log.get_logger().warn("failed to start component: %s", repository.name)
                start_success = False
        if not start_success:
            raise Exception("task {0} start failed".format(name))

        self.obd.deploy.update_deploy_status(DeployStatus.STATUS_RUNNING)
        self.context['process_installed'] = 'done'
        log.get_logger().info("finish do start %s", name)

    def get_reinstall_task_info(self, id, task_id):
        name = self.context['ocp_deployment_id'][id]
        task_info = self.context['task_info'][self.context['ocp_deployment'][task_id]]
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

        if self.obd.deploy.deploy_info.status == DeployStatus.STATUS_RUNNING and self.context['process_installed'] == 'done':
            self.context['ocp_deployment_info'][id]['ocp_start_success_time'] = time.time()
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
        self.context['ocp_deployment']['task_id'] = self.context['ocp_deployment']['task_id'] + 1 \
            if self.context['ocp_deployment']['task_id'] else 1
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'destroy'
        ret = TaskInfo(id=self.context['ocp_deployment']['task_id'], status=task_status, result=task_res,
                       total='destroy', message=task_message)
        self.context['task_info'][self.context['ocp_deployment'][ret.id]] = ret
        return ret

    @auto_register("destroy")
    def _destroy_cluster(self, id):
        name = self.context['ocp_deployment_id'][id]
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
        name = self.context['ocp_deployment_id'][id]
        task_info = self.context['task_info'][self.context['ocp_deployment'][task_id]]
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

    def create_ocp_info(self, metadb):
        deploy = self.obd.deploy
        if not deploy:
            raise Exception("no such deploy")
        self.obd.set_deploy(deploy)

        deploy = self.obd.deploy
        if not deploy:
            raise Exception(f"no such deploy")
        deploy_config = deploy.deploy_config
        pkgs, repositories, errors = self.obd.search_components_from_mirrors(deploy_config, only_info=True)
        if errors:
            raise Exception("{}".format('\n'.join(errors)))
        repositories.extend(pkgs)
        repositories = self.obd.sort_repository_by_depend(repositories, deploy_config)

        ocp_servers = []
        for repository in repositories:
            cluster_config = deploy_config.components[repository.name]
            for server in cluster_config.servers:
                ocp_servers.append(server.ip)

        current_version = repositories[0].version
        self.context['ocp_info'][metadb.cluster_name] = OcpInfo(cluster_name=metadb.cluster_name, status=self.context['ocp_deployment_info'][self.context['id']]['status'], current_version=current_version, ocp_servers=ocp_servers)
        return self.context['ocp_info'][metadb.cluster_name]

    def get_ocp_info(self, cluster_name):
        if self.context['ocp_info'][cluster_name]:
            return self.context['ocp_info'][cluster_name]

    @serial("upgrade_precheck")
    def upgrade_precheck(self, cluster_name, background_tasks):
        task_manager = task.get_task_manager()
        if not cluster_name:
            raise Exception(f"no such deploy for cluster_name: {cluster_name}")
        task_info = task_manager.get_task_info(cluster_name, task_type="upgrade_precheck")
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
        try:
            ssh_clients = self.obd.get_clients(deploy_config, repositories)
        except:
            deploy_config.user.username = self.context['upgrade_user']
            deploy_config.user.password = self.context['upgrade_user_password']
            ssh_clients = self.obd.get_clients(deploy_config, repositories)
            deploy_config.dump()
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
        repositories = [repository for repository in repositories if repository.name in ['ocp-server', 'ocp-server-ce']]
        self.obd.set_repositories(repositories)

        start_check_plugins = self.obd.search_py_script_plugin(repositories, 'upgrade_check', no_found_act='warn')

        self._upgrade_precheck(cluster_name, repositories, start_check_plugins, init_check_status=True)
        info = task_manager.get_task_info(cluster_name, task_type="upgrade_check")
        if info is not None and info.exception is not None:
            raise info.exception
        task_manager.del_task_info(cluster_name, task_type="upgrade_check")
        background_tasks.add_task(self._upgrade_precheck, cluster_name, repositories, start_check_plugins,
                                  init_check_status=False)
        self.context['ocp_deployment']['task_id'] = self.context['ocp_deployment']['task_id'] + 1 if self.context['ocp_deployment'][
            'task_id'] else 1
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'upgrade_check'
        ret = TaskInfo(id=self.context['ocp_deployment']['task_id'], status=task_status, result=task_res,
                       message=task_message, total='task, machine, ob_version')
        self.context['task_info'][self.context['ocp_deployment'][ret.id]] = ret
        return ret

    @auto_register('upgrade_precheck')
    def _upgrade_precheck(self, name, repositories, start_check_plugins, init_check_status=False):
        if init_check_status:
            self._init_upgrade_precheck(repositories, start_check_plugins)
        else:
            self._do_upgrade_precheck(repositories, start_check_plugins)

    def _init_upgrade_precheck(self, repositories, start_check_plugins):
        param_check_status = {}
        servers_set = set()
        for repository in repositories:
            if repository not in start_check_plugins:
                continue
            repository_status = {}
            res = self.obd.call_plugin(start_check_plugins[repository], repository, init_check_status=True, meta_cursor=self.context['metadb_cursor'])
            if not res and res.get_return("exception"):
                raise res.get_return("exception")
            servers = self.obd.deploy.deploy_config.components.get(repository.name).servers
            for server in servers:
                repository_status[server] = {'param': CheckStatus()}
                servers_set.add(server)
            param_check_status[repository.name] = repository_status

    def _do_upgrade_precheck(self, repositories, start_check_plugins):
        gen_config_plugins = self.obd.search_py_script_plugin(repositories, 'generate_config')
        if len(repositories) != len(gen_config_plugins):
            raise Exception("param_check: config error, check stop!")

        components = [comp_name for comp_name in self.obd.deploy.deploy_config.components.keys()]
        for repository in repositories:
            ret = self.obd.call_plugin(gen_config_plugins[repository], repository, generate_check=False, generate_consistent_config=True, auto_depend=True, components=components)
            if ret is None:
                raise Exception("generate config error")
            elif not ret and ret.get_return("exception"):
                raise ret.get_return("exception")
            if not self.obd.deploy.deploy_config.dump():
                raise Exception('generate config dump error,place check disk space!')

        for repository in repositories:
            java_check = True
            if repository.name in COMPS_OCP:
                jre_name = COMP_JRE
                install_plugin = self.obd.search_plugin(repository, PluginType.INSTALL)
                if install_plugin and jre_name in install_plugin.requirement_map(repository):
                    version = install_plugin.requirement_map(repository)[jre_name].version
                    min_version = install_plugin.requirement_map(repository)[jre_name].min_version
                    max_version = install_plugin.requirement_map(repository)[jre_name].max_version
                    if len(self.obd.search_images(jre_name, version=version, min_version=min_version, max_version=max_version)) > 0:
                        java_check = False
            res = self.obd.call_plugin(start_check_plugins[repository], repository, database=self.context['meta_database'],
                                       meta_cursor=self.context['metadb_cursor'], java_check=java_check)
            if not res and res.get_return("exception"):
                raise res.get_return("exception")

    def get_upgrade_precheck_result(self, cluster_name, task_id):
        precheck_result = PrecheckTaskInfo()
        deploy = self.obd.deploy
        if not deploy:
            deploy = self.obd.deploy_manager.get_deploy_config(cluster_name)
            self.obd.set_deploy(deploy)
        components = deploy.deploy_config.components
        task_info = self.context['task_info'][self.context['ocp_deployment'][task_id]]
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
    def upgrade_ocp(self, cluster_name, version, usable, background_tasks):
        task_manager = task.get_task_manager()
        task_info = task_manager.get_task_info(cluster_name, task_type="ocp_upgrade")
        if task_info is not None and task_info.status != TaskStatus.FINISHED:
            raise Exception(f"task {cluster_name} exists and not finished")
        task_manager.del_task_info(cluster_name, task_type="upgrade")
        self.obd.set_options(Values({"component": 'ocp-server', "version": version, "usable": usable}))
        background_tasks.add_task(self._upgrade, 'id', cluster_name, self.context['meta']['tenant_name'], self.context['monitor']['tenant_name'])
        self.context['ocp_deployment']['task_id'] = self.context['ocp_deployment']['task_id'] + 1 if self.context['ocp_deployment']['task_id'] else 1
        task_status = TaskStatus.RUNNING.value
        task_res = TaskResult.RUNNING.value
        task_message = 'upgrade'
        ret = TaskInfo(id=self.context['ocp_deployment']['task_id'], status=task_status, result=task_res, total='upgrade', message=task_message)
        self.context['task_info'][self.context['ocp_deployment'][ret.id]] = ret
        return ret

    @auto_register('upgrade')
    def _upgrade(self, id, app_name, meta_tenant, monitor_tenant):
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
            raise Exception(f"no such deploy: {app_name}")
        deploy_config = deploy.deploy_config
        deploy_info = deploy.deploy_info
        pkgs, repositories, errors = self.obd.search_components_from_mirrors(deploy_config, only_info=True)
        if errors:
            raise Exception("{}".format('\n'.join(errors)))
        repositories.extend(pkgs)
        repositories = self.obd.sort_repository_by_depend(repositories, deploy_config)
        self.obd.search_param_plugin_and_apply(repositories, deploy_config)
        repositories = [repository for repository in repositories if repository.name in ['ocp-server', 'ocp-server-ce']]
        self.obd.set_repositories(repositories)
        setattr(self.obd.options, 'component', repositories[0].name)

        try:
            if deploy_info.status == DeployStatus.STATUS_RUNNING:
                if not self._ocp_upgrade_use_obd(repositories, deploy, meta_tenant, monitor_tenant):
                    self.context['upgrade']['succeed'] = False
                    return
            else:
                if not self._ocp_upgrade_from_new_deployment(repositories, deploy, pkgs, app_name, meta_tenant, monitor_tenant):
                    self.context['upgrade']['succeed'] = False
                    return
            log.get_logger().info("finish do upgrade %s", app_name)
            self.obd.deploy.update_deploy_status(DeployStatus.STATUS_RUNNING)
            self.context['upgrade']['succeed'] = True
        except Exception as e:
            self.obd._call_stdio('exception', '')
            log.get_logger().error("upgrade %s failed, reason: %s" % (app_name, e))
            self.obd.stdio.error("upgrade %s failed, reason: %s" % (app_name, e))
            self.context['upgrade']['succeed'] = False

    def _ocp_upgrade_use_obd(self, repositories, deploy, meta_tenant, monitor_tenant):
        try:
            log.get_logger().info('use obd upgrade ocp')
            deploy_config = deploy.deploy_config
            deploy_info = deploy.deploy_info
            component = getattr(self.obd.options, 'component')
            version = getattr(self.obd.options, 'version')
            if component == const.OCP_SERVER and (version == '4.0.3' or version == '4.2.0' or version == '4.2.1'):
                component = const.OCP_SERVER_CE
                deploy_config.components[const.OCP_SERVER_CE] = deploy_config.components[const.OCP_SERVER]
                deploy_config._src_data[const.OCP_SERVER_CE] = deploy_config._src_data[const.OCP_SERVER]
            usable = getattr(self.obd.options, 'usable', '')
            disable = getattr(self.obd.options, 'disable', '')
            cluster_config = deploy_config.components[const.OCP_SERVER_CE]
            cluster_config.update_component_attr("meta_tenant", meta_tenant, save=True)
            cluster_config.update_component_attr("monitor_tenant", monitor_tenant, save=True)

            opt = Values()
            setattr(opt, "without_ocp_parameter", True)
            self.obd.set_options(opt)

            current_repository = None
            for current_repository in repositories:
                if current_repository.version == '4.0.3':
                    setattr(opt, "switch_monitor_tenant_flag", 'True')
                    self.obd.set_options(opt)
                if current_repository.name == component:
                    break

            if not version:
                self.obd._call_stdio('error', 'Specify the target version.')
                raise Exception('Specify the upgrade version.')

            if usable:
                usable = usable.split(',')
            if disable:
                disable = disable.split(',')

            self.obd._call_stdio('verbose', 'search target version')
            images = self.obd.search_images(component, version=version, disable=disable, usable=usable)
            if not images:
                self.obd._call_stdio('error', 'No such package %s-%s' % (component, version))
                raise Exception('No such package %s-%s' % (component, version))
            if len(images) > 1:
                self.obd._call_stdio(
                    'print_list',
                    images,
                    ['name', 'version', 'release', 'arch', 'md5'],
                    lambda x: [x.name, x.version, x.release, x.arch, x.md5],
                    title='%s %s Candidates' % (component, version)
                )
                self.obd._call_stdio('error', 'Too many match')
                raise Exception('Too many match')

            if isinstance(images[0], Repository):
                pkg = self.obd.mirror_manager.get_exact_pkg(name=images[0].name, md5=images[0].md5)
                if pkg:
                    repositories = []
                    pkgs = [pkg]
                else:
                    repositories = [images[0]]
                    pkgs = []
            else:
                repositories = []
                pkg = self.obd.mirror_manager.get_exact_pkg(name=images[0].name, md5=images[0].md5)
                pkgs = [pkg]

            install_plugins = self.obd.get_install_plugin_and_install(repositories, pkgs)
            if not install_plugins:
                raise Exception('install plugin error')

            dest_repository = repositories[0]
            if dest_repository is None:
                self.obd._call_stdio('error', 'Target version not found')
                raise Exception('Target version not found')

            if dest_repository == current_repository:
                self.obd._call_stdio('print', 'The current version is already %s.\nNoting to do.' % current_repository)
                return True
            ssh_clients = self.obd.get_clients(deploy_config, [current_repository])
            cluster_config = deploy_config.components[current_repository.name]

            upgrade_repositories = [current_repository]
            upgrade_repositories.append(dest_repository)
            self.obd.set_repositories(upgrade_repositories)

            self.obd._call_stdio(
                'print_list',
                upgrade_repositories,
                ['name', 'version', 'release', 'arch', 'md5', 'mark'],
                lambda x: [x.name, x.version, x.release, x.arch, x.md5,
                           'start' if x == current_repository else 'dest' if x == dest_repository else ''],
                title='Packages Will Be Used'
            )

            index = 1
            upgrade_ctx = {
                'route': [],
                'upgrade_repositories': [
                    {
                        'version': repository.version,
                        'hash': repository.md5
                    } for repository in upgrade_repositories
                ],
                'index': 1
            }
            deploy.start_upgrade(component, **upgrade_ctx)

            install_plugins = self.obd.get_install_plugin_and_install(upgrade_repositories, [])
            if not install_plugins:
                raise Exception('install upgrade plugin error')

            if not self.obd.install_repositories_to_servers(deploy_config, upgrade_repositories[1:], install_plugins):
                raise Exception('install upgrade plugin error to server')

            repository = upgrade_repositories[upgrade_ctx['index']]
            repositories = [repository]
            upgrade_plugin = self.obd.search_py_script_plugin(repositories, 'upgrade')[repository]
            self.obd.set_repositories(repositories)
            ret = self.obd.call_plugin(
                upgrade_plugin, repository,
                search_py_script_plugin=self.obd.search_py_script_plugin,
                local_home_path=self.obd.home_path,
                current_repository=current_repository,
                upgrade_repositories=upgrade_repositories,
                apply_param_plugin=lambda repository: self.obd.search_param_plugin_and_apply([repository],
                                                                                             deploy_config),
                metadb_cursor=self.context['metadb_cursor'],
                sys_cursor=self.context['sys_cursor']
            )
            deploy.update_upgrade_ctx(**upgrade_ctx)
            if not ret:
                self.obd.deploy.update_deploy_status(DeployStatus.STATUS_RUNNING)
                raise Exception('call upgrade plugin error')
            deploy.stop_upgrade(dest_repository)
            if version == '4.2.1':
                if const.OCP_SERVER in deploy_config._src_data:
                    del deploy_config._src_data[const.OCP_SERVER]
                if const.OCP_SERVER in deploy_config.components:
                    del deploy_config.components[const.OCP_SERVER]
                if const.OCP_SERVER in deploy_info.components:
                    del deploy_info.components[const.OCP_SERVER]
                if const.OCEANBASE_CE in deploy_config.components:
                    del deploy_config.components[const.OCEANBASE_CE]
                if const.OCEANBASE_CE in deploy_config._src_data and const.OBPROXY_CE not in deploy_info.components:
                    del deploy_config._src_data[const.OCEANBASE_CE]
                if const.OCEANBASE_CE in deploy_info.components and const.OBPROXY_CE not in deploy_info.components:
                    del deploy_info.components[const.OCEANBASE_CE]
                deploy_config.dump()
            return True
        except Exception as e:
            self.obd._call_stdio('exception', '')
            log.get_logger().error("use obd upgrade failed, reason: %s" % e)
            self.obd.stdio.error("use obd upgrade failed, reason: %s" % e)
            return False

    def _ocp_upgrade_from_new_deployment(self, repositories, deploy, pkgs, name, meta_tenant, monitor_tenant):
        deploy_config = deploy.deploy_config
        try:

            component = getattr(self.obd.options, 'component')
            version = getattr(self.obd.options, 'version')
            usable = getattr(self.obd.options, 'usable', '')
            disable = getattr(self.obd.options, 'disable', '')
            if not version:
                self.obd._call_stdio('error', 'Specify the target version.')
                raise Exception('Specify the upgrade version.')

            cluster_config = deploy_config.components[const.OCP_SERVER_CE]
            cluster_config.update_component_attr("meta_tenant", meta_tenant, save=True)
            cluster_config.update_component_attr("monitor_tenant", monitor_tenant, save=True)
            deploy_config._src_data[const.OCP_SERVER_CE]['version'] = version
            deploy_config._src_data[const.OCP_SERVER_CE]['package_hash'] = usable
            deploy_config.dump()
            self.obd.set_deploy(deploy)

            if usable:
                usable = usable.split(',')
            if disable:
                disable = disable.split(',')

            self.obd._call_stdio('verbose', 'search target version')
            images = self.obd.search_images(component, version=version, disable=disable, usable=usable)
            if not images:
                self.obd._call_stdio('error', 'No such package %s-%s' % (component, version))
                raise Exception('No such package %s-%s' % (component, version))
            if len(images) > 1:
                self.obd._call_stdio(
                    'print_list',
                    images,
                    ['name', 'version', 'release', 'arch', 'md5'],
                    lambda x: [x.name, x.version, x.release, x.arch, x.md5],
                    title='%s %s Candidates' % (component, version)
                )
                self.obd._call_stdio('error', 'Too many match')
                raise Exception('Too many match')

            if isinstance(images[0], Repository):
                pkg = self.obd.mirror_manager.get_exact_pkg(name=images[0].name, md5=images[0].md5)
                if pkg:
                    repositories = []
                    pkgs = [pkg]
                else:
                    repositories = [images[0]]
                    pkgs = []
            else:
                repositories = []
                pkg = self.obd.mirror_manager.get_exact_pkg(name=images[0].name, md5=images[0].md5)
                pkgs = [pkg]

            self.obd.set_repositories(repositories)
            ssh_clients = self.obd.get_clients(deploy_config, repositories)

            # kill docker and ocp process on upgrade servers
            for server in self.context['upgrade_servers']:
                ssh_config = SshConfig(server, username=self.context['upgrade_user'], password=self.context['upgrade_user_password'], port=self.context['upgrade_ssh_port'])
                ssh_client = SshClient(ssh_config)
                log.get_logger().info("kill ocp process on host: {}".format(server))
                kill_docker_res = ssh_client.execute_command("sudo docker ps | grep ocp-all-in-one | awk '{print $1}' | xargs sudo docker stop")
                log.get_logger().info("stop container get result {0} {1} {2}".format(kill_docker_res.code, kill_docker_res.stdout, kill_docker_res.stderr))
                kill_process_res = ssh_client.execute_command("ps -ef | grep java | grep 'ocp-server.jar' | grep -v grep | awk '{print $2}' | xargs kill -9 ")
                log.get_logger().info("stop ocp process get result {0} {1} {2}".format(kill_process_res.code, kill_process_res.stdout, kill_process_res.stderr))


            install_plugins = self.obd.get_install_plugin_and_install(repositories, pkgs)
            if not install_plugins:
                return False
            if not self.obd.install_repositories_to_servers(deploy_config, repositories, install_plugins):
                return False
            start_success = True
            repositories = list(set(repositories))
            for repository in repositories:
                opt = Values()
                setattr(opt, "components", repository.name)
                setattr(opt, "strict_check", False)
                setattr(opt, "clean", True)
                setattr(opt, "force", True)
                setattr(opt, "metadb_cursor", self.context['metadb_cursor'])
                self.obd.set_options(opt)
                log.get_logger().info('begin deploy')
                ret = self.obd.deploy_cluster(name)
                log.get_logger().info('finished deploy')
                if not ret:
                    log.get_logger().error("failed to deploy component: %s", repository.name)
                    raise Exception("failed to deploy component: %s", repository.name)
                opt = Values()
                setattr(opt, "without_parameter", True)
                setattr(opt, "skip_password_check", True)
                setattr(opt, "source_option", 'upgrade')
                self.obd.set_options(opt)
                log.get_logger().info('begin start ocp')
                ret = self.obd.start_cluster(name)
                log.get_logger().info('finished start ocp')
                if not ret:
                    log.get_logger().error("failed to start component: %s", repository.name)
                    raise Exception("failed to deploy component: %s", repository.name)
            return True
        except Exception as e:
            self.obd._call_stdio('exception', '')
            log.get_logger().error("use create new deployment upgrade failed, reason: %s" % e)
            self.obd.stdio.error("use create new deployment upgrade failed, reason: %s" % e)
            return False

    def get_ocp_upgrade_task(self, cluster_name, task_id):
        task_info = self.context['task_info'][self.context['ocp_deployment'][task_id]]
        if task_info is None:
            raise Exception("task {0} not found".format(task_id))
        task_info.status = TaskStatus.RUNNING
        task_info.result = TaskResult.RUNNING
        task_info.info = []
        task_info.finished = ''

        for component in self.obd.deploy.deploy_config.components:
            plugin = const.UPGRADE_PLUGINS
            step_info = TaskStepInfo(name=f'{component}-{plugin}', status=TaskStatus.RUNNING, result=TaskResult.RUNNING)
            task_info.current = f'{component}-{plugin}'
            if component not in self.obd.namespaces:
                break
            if self.obd.namespaces[component].get_return('stop').value is not None:
                if not self.obd.namespaces[component].get_return('stop'):
                    step_info.result = TaskResult.FAILED
                else:
                    step_info.result = TaskResult.SUCCESSFUL
                step_info.status = TaskStatus.FINISHED

            if self.obd.namespaces[component].get_return('start').value is not None:
                if not self.obd.namespaces[component].get_return('start'):
                    step_info.result = TaskResult.FAILED
                else:
                    step_info.result = TaskResult.SUCCESSFUL
                step_info.status = TaskStatus.FINISHED

            if self.obd.namespaces[component].get_return('display').value is not None:
                if not self.obd.namespaces[component].get_return('display'):
                    step_info.result = TaskResult.FAILED
                else:
                    step_info.result = TaskResult.SUCCESSFUL
                step_info.status = TaskStatus.FINISHED

            task_info.info.append(step_info)
            task_info.finished += f'{component}-{plugin} '

        status_flag = [i.result for i in task_info.info]
        if TaskResult.FAILED in status_flag or self.context['upgrade']['succeed'] is False:
            task_info.result = TaskResult.FAILED
            task_info.status = TaskStatus.FINISHED

        if self.obd.deploy.deploy_info.status == DeployStatus.STATUS_RUNNING and self.context['upgrade']['succeed']:
            task_info.result = TaskResult.SUCCESSFUL
            task_info.status = TaskStatus.FINISHED
        return task_info

    def get_installed_ocp_info(self, id):
        if time.time() - self.context['ocp_deployment_info'][id]['ocp_start_success_time'] >= 600:
            return OcpInstalledInfo(url=[], password='')
        config = self.context['ocp_deployment_info'][id]['config']
        servers = config.components.ocpserver.servers
        port = config.components.ocpserver.port
        password = ''
        address = ['http://' + str(server) + ':' + str(port) for server in servers]
        return OcpInstalledInfo(url=address, password=password)

    def get_not_upgrade_host(self):
        sql = "select inner_ip_address, ssh_port, version from {0}.compute_host, " \
              "{0}.compute_host_agent where compute_host.id = compute_host_agent.host_id".format(self.context['meta_database'])
        log.get_logger().info('sql: %s' % sql)
        ret = self.context['metadb_cursor'].fetchall(sql)

        data = OcpUpgradeLostAddress(address=[])
        if ret is False:
            raise Exception('error get cursor')
        if ret:
            log.get_logger().info('ret: %s' % ret)
            for _ in ret:
                data.address.append(_['inner_ip_address'])
        return data




