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

import copy

import _errno as err
from _types import Capacity


def ocp_tenant_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio

    critical = plugin_context.get_variable('critical')
    ocp_need_bootstrap = plugin_context.get_variable('ocp_need_bootstrap')
    parameter_check = plugin_context.get_variable('parameter_check')
    servers_memory = plugin_context.get_variable('servers_memory')
    servers_min_pool_memory = plugin_context.get_variable('servers_min_pool_memory')
    servers_log_disk_size = plugin_context.get_variable('servers_log_disk_size')
    get_system_memory = plugin_context.get_variable('get_system_memory')
    check_item_status_pass = plugin_context.get_variable('check_item_status_pass')
    wait_2_pass = plugin_context.get_variable('wait_2_pass')
    server = cluster_config.servers[0]

    global_conf = cluster_config.get_global_conf()
    has_ocp = 'ocp-express' in plugin_context.components or 'ocp-server-ce' in plugin_context.components or 'ocp-server' in plugin_context.components
    if not has_ocp and any([key.startswith('ocp_meta') for key in global_conf]):
        has_ocp = True
    if has_ocp and ocp_need_bootstrap and parameter_check:
        global_conf_with_default = copy.deepcopy(cluster_config.get_global_conf_with_default())
        original_global_conf = cluster_config.get_original_global_conf()
        tenants_componets_map = {
            "meta": ["ocp-express", "ocp-server", "ocp-server-ce"],
            "monitor": ["ocp-server", "ocp-server-ce"],
        }
        tenant_memory = tenant_log_disk = memory_limit = system_memory = log_disk_size = sys_log_disk_size = 0
        for tenant, component_list in tenants_componets_map.items():
            prefix = "ocp_%s_tenant_" % tenant
            tenant_key = "ocp_%s_tenant" % tenant
            for key in global_conf_with_default:
                if key.startswith(prefix) and not original_global_conf.get(key, None):
                    global_conf_with_default['ocp_%s_tenant' % tenant][key.replace(prefix, '', 1)] = global_conf_with_default[key]
            if set(list(plugin_context.components)) & set(component_list):
                tenant_memory_default = global_conf_with_default[tenant_key].get('memory_size', '0')
                tenant_memory += Capacity(original_global_conf.get(tenant_key, {}).get('memory_size', tenant_memory_default)).bytes
                tenant_log_disk_default = global_conf_with_default[tenant_key].get('log_disk_size', '0')
                tenant_log_disk += Capacity(original_global_conf.get(tenant_key, {}).get('log_disk_size', tenant_log_disk_default)).bytes

        servers_sys_memory = {}
        if tenant_memory:
            sys_memory_size = global_conf.get('__min_full_resource_pool_memory', 2 << 30)
            if 'sys_tenant' in global_conf and 'memory_size' in global_conf['sys_tenant']:
                sys_memory_size = global_conf['sys_tenant']['memory_size']
            for server in cluster_config.servers:
                if server.ip not in servers_memory or server not in servers_memory[server.ip]['servers'] or server not in servers_min_pool_memory:
                    stdio.verbose('skip server {} for missing some memory info.'.format(server))
                    continue
                memory_limit = servers_memory[server.ip]['servers'][server]['num']
                system_memory = servers_memory[server.ip]['servers'][server]['system_memory']
                min_pool_memory = servers_min_pool_memory[server]
                if system_memory == 0:
                    system_memory = get_system_memory(memory_limit)
                if tenant_memory + system_memory + sys_memory_size <= memory_limit:
                    break
            else:
                ocp_meta_tenant_mem = original_global_conf.get('ocp_meta_tenant', {}).get('memory_size', global_conf_with_default['ocp_meta_tenant'].get('memory_size', '0'))
                ocp_monitor_tenant_mem = original_global_conf.get('ocp_monitor_tenant', {}).get('memory_size', global_conf_with_default['ocp_monitor_tenant'].get('memory_size', '0'))
                critical(server, 'ocp tenant memory', err.EC_OCP_SERVER_NOT_EXIST_METADB_TENANT_MEMORY_NOT_ENOUGH.format(avail=Capacity(memory_limit - system_memory - sys_memory_size), need=Capacity(tenant_memory), memory_limit=Capacity(memory_limit), system_memory=Capacity(system_memory), sys_tenant_memory=Capacity(sys_memory_size), ocp_meta_tenant_memory=Capacity(ocp_meta_tenant_mem), ocp_monitor_tenant_memory=Capacity(ocp_monitor_tenant_mem)), [err.SUG_OCP_SERVER_NOT_EXIST_METADB_TENANT_NOT_ENOUGH.format()])

        if tenant_log_disk:
            for server in cluster_config.servers:
                log_disk_size = servers_log_disk_size[server]
                sys_log_disk_size = servers_sys_memory.get(server, 0)
                if tenant_log_disk + sys_log_disk_size <= log_disk_size:
                    break
            else:
                critical(server, 'ocp tenant disk', err.EC_OCP_SERVER_RESOURCE_NOT_ENOUGH.format(resource='log_disk_size', avail=Capacity(log_disk_size - sys_log_disk_size), need=Capacity(tenant_log_disk)))
    for server in cluster_config.servers:
        wait_2_pass(server)

    success = plugin_context.get_variable('get_success')()
    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        kernel_check_items = plugin_context.get_variable('kernel_check_items')
        for check_item in kernel_check_items:
            if check_item_status_pass(check_item['check_item']):
                system_env_error = True
                break
        else:
            if not check_item_status_pass('aio') or not check_item_status_pass('ulimit'):
                system_env_error = True
        return plugin_context.return_false(system_env_error=system_env_error)
