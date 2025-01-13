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


class TenantNode:
    def __init__(self, name, ip_list='', tenant_id=None, primary_ip_list=[], primary_tenant_id=None, primary_tenant='', standby_tenant=None):
        self.name = name
        self.ip_list = ip_list
        self.tenant_id = tenant_id
        self.primary_tenant_id = primary_tenant_id
        self.primary_ip_list = primary_ip_list
        self.primary_tenant = primary_tenant
        self.standby_tenant = standby_tenant if standby_tenant else []

site = []


def generate_file_tree_global(node, depth, stdio):
    global site
    nodes_list = node.standby_tenant
    if len(nodes_list) < 1:
        return

    last_node = nodes_list[-1]
    if not node.primary_tenant:
        stdio.print('{}:{}'.format(node.name[0], node.name[1]))
    for node in nodes_list:
        string_list = ["│   " for _ in range(depth - site.__len__())]
        for s in site:
            string_list.insert(s, "    ")

        if node != last_node:
            string_list.append("├── ")
        else:
            string_list.append("└── ")
            site.append(depth)

        stdio.print("".join(string_list) + '{}:{}'.format(node.name[0], node.name[1]))
        if node.standby_tenant:
            generate_file_tree_global(node, depth + 1, stdio)
        if node == last_node:
            site.pop()


def print_standby_graph(plugin_context, cursors={}, need_list_standby=False, relation_tenants={}, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(plugin_context.options, key, default)
        if not value:
            value = default
        return value
    tenant_name = get_option('tenant', '')
    deploy_name = plugin_context.deploy_name
    graph = get_option('graph', False)
    stdio = plugin_context.stdio
    if not cursors:
        stdio.error('Connect to OceanBase failed.')
        return
    tenant_nodes = []
    if graph and need_list_standby:
        stdio.start_loading('query primary-standby relation')
        for deploy_name_tenant in relation_tenants:
            relation_deploy_name = deploy_name_tenant[0]
            relation_tenant_name = deploy_name_tenant[1]
            cursor = cursors.get(relation_deploy_name)
            if not cursor:
                stdio.verbose("Connect to {} failed.".format(relation_deploy_name))
                continue
            primary_ip_list = []
            primary_info_dict = {}
            ret = cursor.fetchone("select TENANT_ROLE from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s", (relation_tenant_name, ), raise_exception=False)
            if not ret:
                stdio.warn("tenant {} not exists in deploy_name:{}".format(relation_tenant_name, deploy_name))
                continue
            if ret['TENANT_ROLE'] == 'STANDBY':
                res = cursor.fetchone('select a.VALUE as `VALUE` from oceanbase.cdb_ob_log_restore_source as a, oceanbase.DBA_OB_TENANTS as b where a.TENANT_ID=b.TENANT_ID and b.TENANT_NAME = %s', (relation_tenant_name, ), raise_exception=False)
                if not res:
                    stdio.error('Query {}:{} primary info failed.'.format(relation_deploy_name, relation_tenant_name))
                    stdio.stop_loading('fail')
                    return
                else:
                    primary_info_arr = res['VALUE'].split(',')
                    for primary_info in primary_info_arr:
                        kv = primary_info.split('=')
                        primary_info_dict[kv[0]] = kv[1]
                    primary_ip_list = primary_info_dict.get('IP_LIST').split(';')
                    primary_ip_list.sort()

            res = cursor.fetchone('select TENANT_ID, group_concat(host separator ";") as ip_list from (select concat(svr_ip,":",SQL_PORT) as host,TENANT_ID from oceanbase.cdb_ob_access_point where tenant_name=%s)', (relation_tenant_name, ), raise_exception=True)
            if not res:
                stdio.error('Query {}:{} ip_list failed.'.format(relation_deploy_name, relation_tenant_name))
                stdio.stop_loading('fail')
                return
            if not res['ip_list']:
                stdio.warn('{}:{} is not exist.'.format(relation_deploy_name, relation_tenant_name))
                continue
            ip_list = res['ip_list'].split(';')
            ip_list.sort()
            primary_tenant_id = int(primary_info_dict['TENANT_ID']) if primary_info_dict else None
            tenant_nodes.append(TenantNode(name=deploy_name_tenant, tenant_id=res['TENANT_ID'], primary_tenant_id=primary_tenant_id, ip_list=ip_list, primary_ip_list=primary_ip_list))

    for tenant_node in tenant_nodes:
        primary_ip_list = tenant_node.primary_ip_list
        if primary_ip_list:
            for node in tenant_nodes:
                if node.tenant_id == tenant_node.primary_tenant_id and node.ip_list == tenant_node.primary_ip_list:
                    tenant_node.primary_tenant = node
                    node.standby_tenant.append(tenant_node)
                    break
            if not tenant_node.primary_tenant:
                stdio.error('Standby tenant {} find primary tenant failed'.format(tenant_node.name))
                stdio.stop_loading('fail')
    stdio.stop_loading('succeed')
    if tenant_nodes:
        need_print_graph = False
        for node in tenant_nodes:
            if node.name[0] == deploy_name and (node.primary_tenant or node.standby_tenant):
                if tenant_name:
                    if node.name[1] == tenant_name:
                        need_print_graph = True
                else:
                    need_print_graph = True

        if need_print_graph:
            stdio.print('\nprimary-standby relation topology graph\n')
            for node in tenant_nodes:
                if not node.primary_tenant:
                    generate_file_tree_global(node, 0, stdio)
                    stdio.print('')

    return plugin_context.return_true()