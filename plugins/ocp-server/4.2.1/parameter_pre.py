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

from copy import deepcopy
from optparse import Values

import const


def get_missing_required_parameters(parameters):
    results = []
    for key in ["jdbc_url", "jdbc_password", "jdbc_username"]:
        if parameters.get(key) is None:
            results.append(key)
    return results


def get_ocp_depend_config(cluster_config, stdio):
    # depends config
    env = {}
    depend_observer = False
    depend_info = {}
    ob_servers_conf = {}
    for comp in const.COMPS_OB:
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
    for comp in const.COMPS_ODP:
        if comp in cluster_config.depends:
            obproxy_servers = cluster_config.get_depend_servers(comp)
            obproxy_server = obproxy_servers[0]
            obproxy_server_config = cluster_config.get_depend_config(comp, obproxy_server)
            depend_info['server_ip'] = obproxy_server.ip
            depend_info['mysql_port'] = obproxy_server_config['listen_port']
            break
    for server in cluster_config.servers:
        default_server_config = deepcopy(cluster_config.get_server_conf_with_default(server))
        original_server_config = cluster_config.get_original_server_conf_with_global(server)
        missed_keys = get_missing_required_parameters(original_server_config)
        if missed_keys:
            if 'jdbc_url' in missed_keys and depend_observer:
                default_server_config['jdbc_url'] = 'jdbc:oceanbase://{}:{}/{}'.format(depend_info['server_ip'], depend_info['mysql_port'], depend_info['meta_db'] if not original_server_config.get('ocp_meta_db', None) else original_server_config['ocp_meta_db']) if not original_server_config.get('jdbc_url', None) else original_server_config['jdbc_url']
                default_server_config['jdbc_username'] = "{0}@{1}".format(default_server_config['ocp_meta_username'], default_server_config['ocp_meta_tenant']['tenant_name'])
                default_server_config['jdbc_password'] = depend_info['meta_password'] if not original_server_config.get('ocp_meta_password', None) else original_server_config['ocp_meta_password']
                default_server_config['jdbc_port'] = depend_info['mysql_port']
                default_server_config['jdbc_host'] = depend_info['server_ip']
                default_server_config['ocp_meta_username'] = depend_info['meta_user'] if not original_server_config.get('ocp_meta_username', None) else original_server_config['ocp_meta_username']
                default_server_config['ocp_meta_tenant']['tenant_name'] = depend_info['meta_tenant'] if not original_server_config.get('ocp_meta_tenant', None) else original_server_config['ocp_meta_tenant']['tenant_name']
                default_server_config['ocp_meta_password'] = depend_info['meta_password'] if not original_server_config.get('ocp_meta_password', None) else original_server_config['ocp_meta_password']
                default_server_config['ocp_meta_db'] = depend_info['meta_db'] if not original_server_config.get('ocp_meta_db', None) else original_server_config['ocp_meta_db']
                default_server_config['ocp_monitor_username'] = depend_info['monitor_user'] if not original_server_config.get('ocp_monitor_username', None) else original_server_config['ocp_monitor_username']
                default_server_config['ocp_monitor_tenant']['tenant_name'] = depend_info['monitor_tenant'] if not original_server_config.get('ocp_monitor_tenant', None) else original_server_config['ocp_monitor_tenant']['tenant_name']
                default_server_config['ocp_monitor_password'] = depend_info['monitor_password'] if not original_server_config.get('ocp_monitor_password', None) else original_server_config['ocp_monitor_password']
                default_server_config['ocp_monitor_db'] = depend_info['monitor_db'] if not original_server_config.get('ocp_monitor_db', None) else original_server_config['ocp_monitor_db']
        env[server] = default_server_config
    return env


def parameter_pre(plugin_context, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio

    env = get_ocp_depend_config(cluster_config, stdio)
    if not env:
        return plugin_context.return_false()

    plugin_context.set_variable('tmp_files', ['/tmp/.sandbox.token'])
    ocp_tenants = []
    tenants_componets_map = {
        "meta": ["ocp-express", "ocp-server", "ocp-server-ce"],
        "monitor": ["ocp-server", "ocp-server-ce"],
    }
    server_config = env[cluster_config.servers[0]]
    if kwargs.get('workflow_name', 'start') != 'destroy':
        for tenant in tenants_componets_map:
            prefix = "ocp_%s_" % tenant

            # set create tenant variable
            for key in server_config:
                if key.startswith(prefix) and server_config.get(key, None):
                    server_config[prefix + 'tenant'][key.replace(prefix, '', 1)] = server_config[key]
            tenant_info = server_config[prefix + "tenant"]
            tenant_info["variables"] = "ob_tcp_invited_nodes='%'"
            tenant_info["create_if_not_exists"] = True
            tenant_info["database"] = server_config[prefix + "db"]
            tenant_info["db_username"] = server_config[prefix + "username"]
            tenant_info["db_password"] = server_config.get(prefix + "password", "")
            tenant_info["{0}_root_password".format(tenant_info['tenant_name'])] = server_config.get(prefix + "password", "")
            ocp_tenants.append(Values(tenant_info))
    plugin_context.set_variable("create_tenant_options", ocp_tenants)

    plugin_context.set_variable('get_missing_required_parameters', get_missing_required_parameters)
    plugin_context.set_variable('start_env', env)
    return plugin_context.return_true(create_tenant_options=ocp_tenants)
