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

import tempfile
import yaml

import const
from _types import Capacity
from tool import COMMAND_ENV


def confirm_config(plugin_context, client, cluster_name, *args, **kwargs):
    stdio = plugin_context.stdio
    ip = client.config.host
    user = client.config.username
    user_password = client.config.password
    oceanbase_config = plugin_context.get_return('oceanbase_config_input').get_return('oceanbase_config')
    tenant_config = plugin_context.get_return('tenant_config_input').get_return('tenant_config')
    component_config = plugin_context.get_return('component_config_input').get_return('component_config')
    mysql_port = oceanbase_config['mysql_port']
    rpc_port = oceanbase_config['rpc_port']
    obshell_port = oceanbase_config['obshell_port']
    cpu_count = oceanbase_config['cpu_count']
    memory_limit = oceanbase_config['memory_limit']
    home_path = oceanbase_config['home_path']
    data_dir = oceanbase_config['data_dir']
    log_dir = oceanbase_config['log_dir']
    datafile_maxsize = oceanbase_config['datafile_maxsize']
    log_disk_size = oceanbase_config['log_disk_size']
    stdio.print('')
    stdio.print('#Saved configurations:')
    stdio.print(f'cluster name: {cluster_name}')
    stdio.print(f'mysql port: {mysql_port}')
    stdio.print(f'rpc port: {rpc_port}')
    stdio.print(f'obshell port: {obshell_port}')
    stdio.print(f'cpu count: {cpu_count}')
    stdio.print(f'memory limit: {Capacity(memory_limit)}')
    stdio.print(f'home path: {home_path}' + '/' + 'oceanbase_name')
    stdio.print(f'data dir: {data_dir}')
    stdio.print(f'log dir: {log_dir}')
    stdio.print(f'datafile maxsize: {Capacity(datafile_maxsize)}')
    stdio.print(f'log disk size: {Capacity(log_disk_size)}')

    if tenant_config:
        tenant_name = tenant_config['tenant_name']
        tenant_cpu = tenant_config['max_cpu']
        tenant_memory = tenant_config['memory_size']
        tenant_log_disk_size = tenant_config['log_disk_size']
        stdio.print(f'tenant name: {tenant_name}')
        stdio.print(f'tenant cpu: {tenant_cpu}')
        stdio.print(f'tenant memory: {Capacity(tenant_memory)}')
        stdio.print(f'tenant log disk size: {Capacity(tenant_log_disk_size)}')

    if component_config:
        monagent_http_port = component_config['monagent_http_port']
        mgragent_http_port = component_config['mgragent_http_port']
        prometheus_port = component_config['prometheus_port']
        grafana_port = component_config['grafana_port']
        stdio.print(f'monagent http port: {monagent_http_port}')
        stdio.print(f'mgragent http port: {mgragent_http_port}')
        stdio.print(f'prometheus port: {prometheus_port}')
        stdio.print(f'grafana port: {grafana_port}')
    while True:
        confirm = stdio.confirm('Are you sure these configurations are correct?', default_option=True)
        if confirm:
            stdio.print("Configuration confirmed.")
            break
        else:
            stdio.print("Please execute the script again to input the information.")
            return False
    oceanbase_name = oceanbase_config['name']
    if oceanbase_name != const.COMP_OB_CE:
        COMMAND_ENV.set('TELEMETRY_MODE', 0, save=True)

    version = oceanbase_config['version']
    release = oceanbase_config['release']
    scenario = oceanbase_config['scenario']
    home_path = oceanbase_config['home_path']
    root_password = oceanbase_config['root_password']
    cluster_config = {
        'user':
            {
                'username': user,
                'password': user_password,
                'port': 22
            },
        oceanbase_name:
            {
                'version': str(version),
                'release': str(release),
                'servers': [ip],
                'global': {
                    'cluster_name': cluster_name,
                    'mysql_port': mysql_port,
                    'rpc_port': rpc_port,
                    'obshell_port': obshell_port,
                    'root_password': root_password,
                    'cpu_count': cpu_count,
                    'memory_limit': str(Capacity(memory_limit)),
                    'home_path': home_path + '/' + 'oceanbase_name',
                    'data_dir': data_dir,
                    'redo_dir': log_dir,
                    'datafile_size': '2G',
                    'datafile_maxsize': str(Capacity(datafile_maxsize)),
                    'datafile_next': str(Capacity(0.1 * datafile_maxsize)),
                    'log_disk_size': str(Capacity(log_disk_size)),
                    'system_memory': 0,
                    'zone': 'zone1'
                }
            },
    }
    if scenario:
        cluster_config[oceanbase_name]['global']['scenario'] = scenario
    if component_config:
        cluster_config['obagent'] = {
            'depends': [oceanbase_name],
            'servers': [ip],
            'global': {
                'home_path': f'{home_path}/obagent',
                'monagent_http_port': monagent_http_port,
                'mgragent_http_port': mgragent_http_port
            }
        }
        cluster_config['prometheus'] = {
            'depends': ['obagent'],
            'servers': [ip],
            'global': {
                'home_path': f'{home_path}/prometheus',
                'port': prometheus_port
            }
        }
        cluster_config['grafana'] = {
            'depends': ['prometheus'],
            'servers': [ip],
            'global': {
                'home_path': f'{home_path}/grafana',
                'port': grafana_port,
                'login_password': 'oceanbase'
            }
        }
    with tempfile.NamedTemporaryFile(delete=False, prefix="obd", suffix="yaml", mode="w", encoding="utf-8") as f:
        f.write(yaml.dump(cluster_config, sort_keys=False))
        cluster_config_yaml_path = f.name

    return plugin_context.return_true(cluster_config_yaml_path=cluster_config_yaml_path)