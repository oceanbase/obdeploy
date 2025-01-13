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

import json
import os
from optparse import Values
from copy import deepcopy

import const
from tool import FileUtil, EnvVariables



def parameter_pre(plugin_context, *args, **kwargs):
    repositories = plugin_context.repositories
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    ob_sys_username = 'root'
    depend_info = {}
    binlog_tenant = []
    for comp in const.COMPS_OB:
        if comp in cluster_config.depends:
            ob_config = cluster_config.get_depend_config(comp)
            ob_servers = cluster_config.get_depend_servers(comp)
            depend_info['database_ip'] = ob_servers[0].ip
            depend_info['database_port'] = ob_config['mysql_port']
            depend_info['database_name'] = ob_config['binlog_meta_tenant']['database']
            depend_info['user'] = ob_config['binlog_meta_tenant']['username'] + '@' + ob_config['binlog_meta_tenant']['tenant_name']
            depend_info['password'] = ob_config['binlog_meta_tenant']['password']
            depend_info['root_password'] = ob_config['root_password']

            tenant_info = ob_config['binlog_meta_tenant']
            tenant_info["variables"] = "ob_tcp_invited_nodes='%'"
            tenant_info["create_if_not_exists"] = True
            tenant_info["db_username"] = ob_config['binlog_meta_tenant']['username']
            tenant_info["db_password"] = ob_config['binlog_meta_tenant']['password']
            tenant_info[ob_config['binlog_meta_tenant']['tenant_name'] + '_root_password'] = depend_info['password'] = ob_config['binlog_meta_tenant']['password']
            binlog_tenant.append(Values(tenant_info))
            break
    for comp in const.COMPS_ODP:
        if comp in cluster_config.depends:
            odp_config = cluster_config.get_depend_config(comp)
            odp_servers = cluster_config.get_depend_servers(comp)
            depend_info['database_ip'] = odp_servers[0].ip
            depend_info['database_port'] = odp_config['listen_port']
            break

    repository_dir = None
    for repository in repositories:
        if repository.name == cluster_config.name:
            repository_dir = repository.repository_dir
            break
    with FileUtil.open(os.path.join(repository_dir, 'conf/conf.json')) as f:
        config = json.load(f)

    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']
        config['oblogreader_path'] = '{}/run'.format(home_path)
        custom_config = cluster_config.get_server_conf(server)
        config = {k: custom_config.get(k, v) for k, v in config.items()}
        config.update(depend_info)
        home_path = custom_config['home_path']
        environments = deepcopy(cluster_config.get_environments())
        if 'LD_LIBRARY_PATH' not in environments:
            environments['LD_LIBRARY_PATH'] = '%s/lib' % home_path
        with EnvVariables(environments, client):
            ob_sys_username = ob_sys_username if ob_sys_username is not None else custom_config.get('ob_sys_username')
            config['ob_sys_username'] = client.execute_command("{}/bin/logproxy -x {}".format(home_path, ob_sys_username)).stdout.strip() if ob_sys_username else ""
            ob_sys_password = depend_info.get('root_password') if depend_info.get('root_password') is not None else custom_config.get('ob_sys_password')
            config['ob_sys_password'] = client.execute_command("{}/bin/logproxy -x {}".format(home_path, ob_sys_password)).stdout.strip() if ob_sys_password else ""
        config['binlog_log_bin_basename'] = custom_config.get('binlog_dir') if custom_config.get('binlog_dir') else '%s/run' % home_path
        config['node_ip'] = server.ip
        config['database_ip'] = depend_info.get('database_ip') if depend_info.get('database_ip') is not None else custom_config.get('meta_host')
        config['database_port'] = depend_info.get('database_port') if depend_info.get('database_port') is not None else custom_config.get('meta_port')
        config['user'] = depend_info.get('user') if depend_info.get('user') is not None else custom_config.get('meta_username')
        config['password'] = depend_info.get('password') if depend_info.get('password') is not None else custom_config.get('meta_password')
        config['database_name'] = depend_info.get('database_name') if depend_info.get('database_name') is not None else custom_config.get('meta_db')
        config['enable_resource_check'] = False
        if not custom_config.get('binlog_obcdc_ce_path_template'):
            source_binlog_path = config['binlog_obcdc_ce_path_template']
            config['binlog_obcdc_ce_path_template'] = os.path.join(home_path, source_binlog_path[source_binlog_path.find('/obcdc/') + 1:])
        if not custom_config.get('oblogreader_obcdc_ce_path_template'):
            source_oblogreader_path = config['oblogreader_obcdc_ce_path_template']
            config['oblogreader_obcdc_ce_path_template'] = os.path.join(home_path, source_oblogreader_path[source_oblogreader_path.find('/obcdc/') + 1:])
        if not custom_config.get('bin_path'):
            config['bin_path'] = '{}/bin'.format(home_path)
        if not custom_config.get('oblogreader_path'):
            config['oblogreader_path'] = '{}/run'.format(home_path)

        if 'binlog_dir' in config:
            config.pop('binlog_dir')
        json_config = json.dumps(config, indent=4)
        conf_path = '{}/conf/conf.json'.format(home_path)
        if not client.write_file(json_config, conf_path):
            stdio.error('failed to write config file {}'.format(conf_path))
            return plugin_context.return_false()
    plugin_context.set_variable('binlog_config', config)
    return plugin_context.return_true(create_tenant_options=binlog_tenant)