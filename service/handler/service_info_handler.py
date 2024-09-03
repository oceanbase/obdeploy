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

import re
import os
import copy
from singleton_decorator import singleton

from _deploy import UserConfig, DeployStatus
from tool import Cursor, NetUtil
from ssh import LocalClient, SshConfig, SshClient
from service.handler.base_handler import BaseHandler
from service.common import log, const
from service.model.service_info import ServiceInfo, DeployNames
from service.model.server import OcpServerInfo, InstallerMode, ComponentInfo, MsgInfo
from service.model.metadb import DatabaseConnection
from service.model.ocp import OcpDeploymentConfig
from service.model.deployments import OCPDeploymnetConfig, OcpServer, OcpComponentConfig, Auth
from service.model.parameter import Parameter
from service.model.ssh import SshAuth
from service.model.tenant import TenantConfig, TenantUser, TenantResource
from service.handler.ocp_handler import OcpHandler
from service.handler.rsa_handler import RSAHandler


@singleton
class ServiceInfoHandler(BaseHandler):

    def get_service_info(self):
        info = ServiceInfo(user=UserConfig.DEFAULT.get('username'))
        return info

    def version_convert_to_int(self, version):
        return int(version.split('.')[0]) * 1000 ** 2 + int(version.split('.')[1]) * 1000 + int(
            version.split('.')[2])

    def version_compare(self, v1, v2):
        v1_int = self.version_convert_to_int(v1)
        v2_int = self.version_convert_to_int(v2)
        return v1_int - v2_int

    def install_repositories(self):
        pkgs = self.obd.mirror_manager.get_pkgs_info('ocp-server')
        versions = [pkg.version for pkg in pkgs]
        return versions

    def execute_command_in_docker(self, contain_id, shell_command):
        return LocalClient.execute_command(
            "sudo docker exec %s bash -c '%s'" % (contain_id, shell_command)).stdout.strip()

    def get_missing_required_parameters(self, parameters):
        results = []
        for key in ["jdbc_url", "jdbc_username", "jdbc_password"]:
            if parameters.get(key) is None:
                results.append(key)
        return results

    def get_ocp_depend_config(self, cluster_config, stdio):
        # depends config
        env = {}
        depend_observer = False
        depend_info = {}
        ob_servers_conf = {}
        for comp in ["oceanbase", "oceanbase-ce"]:
            ob_zones = {}
            if comp in cluster_config.depends:
                depend_observer = True
                ob_servers = cluster_config.get_depend_servers(comp)
                for ob_server in ob_servers:
                    ob_servers_conf[ob_server] = ob_server_conf = cluster_config.get_depend_config(comp, ob_server)
                    if 'server_ip' not in depend_info:
                        depend_info['server_ip'] = ob_server.ip
                        depend_info['mysql_port'] = ob_server_conf['mysql_port']
                        depend_info['meta_tenant'] = ob_server_conf['ocp_meta_tenant']['tenant_name']
                        depend_info['meta_user'] = ob_server_conf['ocp_meta_username']
                        depend_info['meta_password'] = ob_server_conf['ocp_meta_password']
                        depend_info['meta_db'] = ob_server_conf['ocp_meta_db']
                        depend_info['monitor_tenant'] = ob_server_conf['ocp_monitor_tenant']['tenant_name']
                        depend_info['monitor_user'] = ob_server_conf['ocp_monitor_username']
                        depend_info['monitor_password'] = ob_server_conf['ocp_monitor_password']
                        depend_info['monitor_db'] = ob_server_conf['ocp_monitor_db']
                    zone = ob_server_conf['zone']
                    if zone not in ob_zones:
                        ob_zones[zone] = ob_server
                break
        for comp in ['obproxy', 'obproxy-ce']:
            if comp in cluster_config.depends:
                obproxy_servers = cluster_config.get_depend_servers(comp)
                obproxy_server = obproxy_servers[0]
                obproxy_server_config = cluster_config.get_depend_config(comp, obproxy_server)
                depend_info['server_ip'] = obproxy_server.ip
                depend_info['mysql_port'] = obproxy_server_config['listen_port']
                break

        for server in cluster_config.servers:
            server_config = copy.deepcopy(cluster_config.get_server_conf_with_default(server))
            original_server_config = cluster_config.get_original_server_conf_with_global(server)
            missed_keys = self.get_missing_required_parameters(original_server_config)
            if missed_keys:
                if 'jdbc_url' in missed_keys and depend_observer:
                    if not server_config.get('ocp_meta_tenant', None):
                        server_config['ocp_meta_tenant'] = {}
                    if not server_config.get('ocp_monitor_tenant', None):
                        server_config['ocp_monitor_tenant'] = {}
                    server_config['jdbc_url'] = 'jdbc:oceanbase://{}:{}/{}'.format(depend_info['server_ip'], depend_info['mysql_port'], depend_info['meta_db'] if not original_server_config.get('ocp_meta_db', None) else original_server_config['ocp_meta_db']) if not original_server_config.get('jdbc_url', None) else original_server_config['jdbc_url']
                    server_config['ocp_meta_username'] = depend_info['meta_user'] if not original_server_config.get('ocp_meta_username', None) else original_server_config['ocp_meta_username']
                    server_config['ocp_meta_tenant']['tenant_name'] = depend_info['meta_tenant'] if not original_server_config.get('ocp_meta_tenant', None) else original_server_config['ocp_meta_tenant']['tenant_name']
                    server_config['ocp_meta_password'] = depend_info['meta_password'] if not original_server_config.get('ocp_meta_password', None) else original_server_config['ocp_meta_password']
                    server_config['ocp_meta_db'] = depend_info['meta_db'] if not original_server_config.get('ocp_meta_db', None) else original_server_config['ocp_meta_db']
                    server_config['ocp_monitor_username'] = depend_info['monitor_user'] if not original_server_config.get('ocp_monitor_username', None) else original_server_config['ocp_monitor_username']
                    server_config['ocp_monitor_tenant']['tenant_name'] = depend_info['monitor_tenant'] if not original_server_config.get('ocp_monitor_tenant', None) else original_server_config['ocp_monitor_tenant']['tenant_name']
                    server_config['ocp_monitor_password'] = depend_info['monitor_password'] if not original_server_config.get('ocp_monitor_password', None) else original_server_config['ocp_monitor_password']
                    server_config['ocp_monitor_db'] = depend_info['monitor_db'] if not original_server_config.get('ocp_monitor_db', None) else original_server_config['ocp_monitor_db']
                    server_config['jdbc_username'] = '%s@%s' % (
                        server_config['ocp_meta_username'], server_config['ocp_meta_tenant']['tenant_name'])
                    server_config['jdbc_password'] = server_config['ocp_meta_password']
                    server_config['root_password'] = depend_info.get('root_password', '')
            env[server] = server_config
        return env

    def generate_config(self, cluster_name):
        log.get_logger().info('do command upgrade with context: {}'.format(self.context))
        servers = self.context['upgrade_servers']
        if len(servers) == 0:
            raise Exception("no server to upgrade")
        ssh_port = self.context['upgrade_ssh_port']
        username = self.context['upgrade_user']
        password = self.context['upgrade_user_password']
        log.get_logger().info('use command to get info')

        # get monitordb connection info from metadb
        monitor_user_config = self.context['metadb_cursor'].fetchone("select default_value, value from {0}.config_properties where `key` = 'ocp.monitordb.username'".format(self.context['connection_info'][cluster_name].database))
        monitor_user = monitor_user_config['value'] if monitor_user_config['value'] else monitor_user_config['default_value']
        monitor_password_config = self.context['metadb_cursor'].fetchone("select default_value, value from {0}.config_properties where `key` = 'ocp.monitordb.password'".format(self.context['connection_info'][cluster_name].database))
        monitor_password = monitor_password_config['value'] if monitor_password_config['value'] else monitor_password_config['default_value']
        monitor_database_config = self.context['metadb_cursor'].fetchone("select default_value, value from {0}.config_properties where `key` = 'ocp.monitordb.database'".format(self.context['connection_info'][cluster_name].database))
        monitor_database = monitor_database_config['value'] if monitor_database_config['value'] else monitor_database_config['default_value']
        log.get_logger().info('successfully get monior config from metadb')

        server_port_config = self.context['metadb_cursor'].fetchone("select default_value, value from {0}.config_properties where `key` = 'server.port'".format(self.context['connection_info'][cluster_name].database))
        server_port = server_port_config['value'] if server_port_config['value'] else server_port_config['default_value']
        log.get_logger().info('successfully get ocp-server port: %s' % server_port)

        # get memory info and home_path using ssh client
        ssh_config = SshConfig(servers[0], username=self.context['upgrade_user'], password=self.context['upgrade_user_password'], port=self.context['upgrade_ssh_port'])
        ssh_client = SshClient(ssh_config)
        res = ssh_client.execute_command("ps -ef | grep java | grep 'ocp-server.*.jar' | grep -v grep")
        if not res:
            raise Exception("failed to query ocp process info")
        memory_xmx = res.stdout.split("Xmx")[1].split(" ")[0]
        home_path = res.stdout.split("/lib/ocp-server")[0].split(' ')[-1]

        # check whether ocp docker exists
        res = ssh_client.execute_command("sudo docker ps | grep ocp-all-in-one ")
        if res:
            log.get_logger().info("found ocp docker")
        home_path = "/home/{0}/ocp-server".format(self.context['upgrade_user']) if self.context['upgrade_user'] != 'root' else "/root/ocp-server"
        auth = Auth(user=username, port=ssh_port, password=password)
        jdbc_username = self.context['connection_info'][cluster_name].user
        user_name = jdbc_username.split('@')[0]
        tenant_name = jdbc_username.split('@')[1].split('#')[0] if '#' in jdbc_username else jdbc_username.split('@')[1]
        self.context['meta']['tenant_name'] = tenant_name
        tenant_user = TenantUser(tenant_name=tenant_name, user_name=user_name, user_database=self.context['connection_info'][cluster_name].database)
        meta_tenant = TenantConfig(name=tenant_user, password=self.context['connection_info'][cluster_name].password)

        monitor_tenant_name = monitor_user.split('@')[1].split('#')[0] if '#' in monitor_user else monitor_user.split('@')[1]
        self.context['monitor']['tenant_name'] = monitor_tenant_name
        monitor_tenant_username = monitor_user.split('@')[0]
        monitor_tenant_user = TenantUser(tenant_name=monitor_tenant_name, user_name=monitor_tenant_username, user_database=monitor_database)
        monitor_tenant = TenantConfig(name=monitor_tenant_user, password=monitor_password)
        ocp_server = OcpServer(component='ocp-server-ce', metadb=self.context['connection_info'][cluster_name], meta_tenant=meta_tenant, monitor_tenant=monitor_tenant, admin_password='********',
                               home_path=home_path, servers=servers, port=server_port, memory_size=memory_xmx)
        components = OcpComponentConfig(ocpserver=ocp_server)
        data = OCPDeploymnetConfig(auth=auth, components=components)
        log.get_logger().info('create deployment config: %s' % data)

        ocp_handler = OcpHandler()
        try:
            cluster_config_yaml_path = ocp_handler.create_ocp_config_path(data)
            log.get_logger().info('upgrade path: %s' % cluster_config_yaml_path)
            deployment_id = ocp_handler.create_ocp_deployment(cluster_name, cluster_config_yaml_path)
            log.get_logger().info('upgrade id: %s' % deployment_id)
        except Exception as ex:
            log.get_logger().error(ex)

    def create_ocp_info(self, cluster_name):
        deploy = self.obd.deploy_manager.get_deploy_config(cluster_name)
        log.get_logger().info('deploy: %s' % deploy)
        if deploy and deploy.deploy_info.status in [DeployStatus.STATUS_RUNNING, DeployStatus.STATUS_UPRADEING]:
            deploy_config = deploy.deploy_config
            if const.OCP_SERVER in deploy_config.components:
                cluster_config = deploy_config.components[const.OCP_SERVER]
                global_config = cluster_config.get_global_conf()
                if not global_config.get('ocp_meta_username', ''):
                    jdbc_url = global_config['jdbc_url']
                    matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", jdbc_url)
                    if matched:
                        cluster_config.update_global_conf('ocp_meta_db', matched.group(3))
                    cluster_config.update_global_conf('ocp_meta_username', global_config['jdbc_username'].split('@')[0])
                    cluster_config.update_global_conf('ocp_meta_password', global_config['jdbc_password'])
                    cluster_config.update_global_conf('ocp_meta_tenant',
                                                      {'tenant_name': global_config['jdbc_username'].split('@')[1]})
            self.obd.set_deploy(deploy)
        else:
            self.generate_config(cluster_name)

    def get_deployments_name(self):
        deploys = self.obd.deploy_manager.get_deploy_configs()
        log.get_logger().info('deploys: %s' % deploys)
        ret = DeployNames()
        for _ in deploys:
            if _.deploy_info.status == DeployStatus.STATUS_RUNNING and \
                    (const.OCP_SERVER in _.deploy_config.components or const.OCP_SERVER_CE in _.deploy_config.components):
                ret.name.append(_.name)
        return ret

    def get_metadb_connection(self, name):
        metadb = DatabaseConnection(cluster_name=name)
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        log.get_logger().info('deploys: %s' % deploy)
        if deploy is None:
            res = LocalClient.execute_command("sudo docker ps | grep ocp-all-in-one | awk '{print $1}'").stdout.strip()
            log.get_logger().info('docker ps: %s' % res)
            if res:
                metadb.host = self.execute_command_in_docker(res, 'env | grep  OCP_METADB_HOST').split('=')[1]
                metadb.port = self.execute_command_in_docker(res, 'env | grep  OCP_METADB_PORT').split('=')[1]
                metadb.user = self.execute_command_in_docker(res, 'env | grep  OCP_METADB_USER').split('=')[1]
                metadb.password = self.execute_command_in_docker(res, 'env | grep  OCP_METADB_PASSWORD').split('=')[1]
                metadb.database = self.execute_command_in_docker(res, 'env | grep  OCP_METADB_DBNAME').split('=')[1]
                try:
                    self.context['metadb_cursor'] = Cursor(ip=metadb.host, port=metadb.port, user=metadb.user,
                                                           password=metadb.password, stdio=self.obd.stdio)
                except:
                    log.get_logger().error('Automatic database connection failed, please input manually.')
                metadb_copy = copy.deepcopy(metadb)
                metadb_copy.password = ''
                return metadb_copy
            return metadb
        if deploy.deploy_info.status != DeployStatus.STATUS_RUNNING:
            raise Exception ("previous deploy is not running")
        deploy_config = deploy.deploy_config
        repositories = self.obd.load_local_repositories(deploy.deploy_info, False)
        self.obd.search_param_plugin_and_apply(repositories, deploy_config)
        if const.OCP_SERVER in deploy_config.components:
            cluster_config = deploy_config.components[const.OCP_SERVER]
        elif const.OCP_SERVER_CE in deploy_config.components:
            cluster_config = deploy_config.components[const.OCP_SERVER_CE]
        else:
            return metadb
        servers = cluster_config.servers
        start_env = self.get_ocp_depend_config(cluster_config, self.obd.stdio)
        for server in servers:
            server_config = start_env[server]
            jdbc_url = server_config['jdbc_url']
            metadb.user = server_config['jdbc_username']
            metadb.password = server_config['jdbc_password']
            matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", jdbc_url)
            if matched:
                metadb.host = matched.group(1)
                metadb.port = int(matched.group(2)[1:])
                metadb.database = matched.group(3)
            if server_config.get('ocp_meta_tenant', ''):
                if 'sys' in metadb.user:
                    try:
                        self.context['sys_cursor'] = Cursor(ip=metadb.host, port=metadb.port, user=metadb.user, password=metadb.password, stdio=self.obd.stdio)
                    except:
                        log.get_logger().error('Automatic database connection failed, please input manually.')
                metadb.user = server_config['ocp_meta_username'] + '@' + server_config['ocp_meta_tenant']['tenant_name']
                metadb.password = server_config['ocp_meta_password']
                metadb.database = server_config['ocp_meta_db']
            self.context["connection_info"][metadb.cluster_name] = metadb
            try:
                self.context['metadb_cursor'] = Cursor(ip=metadb.host, port=metadb.port, user=metadb.user, password=metadb.password, stdio=self.obd.stdio)
            except:
                log.get_logger().error('Automatic database connection failed, please input manually.')
            break
        metadb_copy = copy.deepcopy(metadb)
        metadb_copy.password = ''
        return metadb_copy

    def get_component_agent(self, metadb):
        try:
            user = ''
            self.context["connection_info"][metadb.cluster_name] = metadb
            self.context['meta_database'] = metadb.database
            meta_password = RSAHandler().decrypt_private_key(metadb.password) if metadb.password else metadb.password
            self.context['metadb_cursor'] = Cursor(ip=metadb.host, port=metadb.port, user=metadb.user, password=meta_password,
                                                   stdio=self.obd.stdio)
            log.get_logger().info('cursor: %s' % self.context['metadb_cursor'])
            monitor_tenant_sql = "select `value` from %s.config_properties where `key` = 'ocp.monitordb.username'" % metadb.database
            monitor_tenant = self.context['metadb_cursor'].fetchone(monitor_tenant_sql, raise_exception=True)
            log.get_logger().info('monitor_tenant: %s' % monitor_tenant)
            self.context['meta']['tenant_name'] = metadb.user.split('@')[1].split('#')[0] if '#' in metadb.user else metadb.user.split('@')[1]
            self.context['monitor']['tenant_name'] = monitor_tenant['value'].split('@')[1].split('#')[0] if '#' in monitor_tenant['value'] else monitor_tenant['value'].split('@')[1]
            tips = False
            if monitor_tenant and monitor_tenant.get('value') in metadb.user:
                tips = True
            sql = "select id from %s.distributed_server" % metadb.database
            res = self.context['metadb_cursor'].fetchall(sql, raise_exception=True)
            log.get_logger().info('ocp server ip: %s' % res)
            component_servers = []
            component_info = []
            for _ in res:
                component_servers.append(_['id'].split(':')[0])
            component_info.append(ComponentInfo(name=const.OCP_SERVER_CE, ip=component_servers))
            ocp_version = self.context['metadb_cursor'].fetchone(
                "select `value` from %s.config_properties where `key` = 'ocp.version'" % metadb.database, raise_exception=True)['value']
            log.get_logger().info('ocp version: %s' % ocp_version)
            log.get_logger().info('get obd user')
            deploy = self.obd.deploy_manager.get_deploy_config(metadb.cluster_name)
            log.get_logger().info('deploy: %s' % deploy)
            if deploy and deploy.deploy_info.status in [DeployStatus.STATUS_RUNNING, DeployStatus.STATUS_UPRADEING]:
                deploy_config = deploy.deploy_config
                user = deploy_config.user.username
            return OcpServerInfo(user=user, ocp_version=ocp_version, component=component_info, tips=tips)
        except Exception as e:
            log.get_logger().error('failed to get ocp info: %s' % e)
            log.get_logger().error('Please ensure the use of the meta tenant.')
            raise Exception('Failed to get ocp info, Please ensure the use of the meta tenant.')

