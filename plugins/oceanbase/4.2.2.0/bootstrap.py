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


from __future__ import absolute_import, division, print_function

import time
from copy import deepcopy
from optparse import Values

from _deploy import InnerConfigItem
from tool import ConfigUtil



def is_bootstrap(cursor):
    sql = "select column_value from oceanbase.__all_core_table where table_name = '__all_global_stat' and column_name = 'baseline_schema_version'"
    ret = cursor.fetchone(sql, raise_exception=False, exc_level='verbose')
    if ret is False:
        return False
    return int(ret.get("column_value")) > 0


def bootstrap(plugin_context, need_bootstrap=True, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    cursor = plugin_context.get_return('connect').get_return('cursor')
    ocs_cursor = plugin_context.get_return('connect').get_return('ocs_cursor')
    added_components = [] if cluster_config.added_servers else cluster_config.get_deploy_added_components()
    changed_components = cluster_config.get_deploy_changed_components()
    be_depend = cluster_config.be_depends
    global_conf = cluster_config.get_global_conf()
    ocp_config = cluster_config.get_be_depend_config('ocp-server-ce', with_default=False)
    obagent_config = cluster_config.get_be_depend_config('obagent', with_default=False)
    bootstrap = []
    floor_servers = {}
    zones_config = {}
    inner_config = {
        InnerConfigItem('$_zone_idc'): 'idc'
    }

    if added_components:
        stdio.verbose('bootstrap for components: %s' % added_components)

    raise_cursor = cursor.raise_cursor
    if cluster_config.name in added_components and need_bootstrap:
        for server in cluster_config.servers:
            server_config = cluster_config.get_server_conf(server)
            zone = server_config['zone']
            if zone in floor_servers:
                floor_servers[zone].append('%s:%s' % (server.ip, server_config['rpc_port']))
            else:
                floor_servers[zone] = []
                zones_config[zone] = {}
                bootstrap.append('REGION "sys_region" ZONE "%s" SERVER "%s:%s"' % (server_config['zone'], server.ip, server_config['rpc_port']))

            zone_config = zones_config[zone]
            for key in server_config:
                if not isinstance(key, InnerConfigItem):
                    continue
                if key not in inner_config:
                    continue
                if key in zone_config:
                    continue
                zone_config[key] = server_config[key]
        try:
            sql = 'set session ob_query_timeout=1000000000'
            stdio.verbose('execute sql: %s' % sql)
            raise_cursor.execute(sql)
            sql = 'alter system bootstrap %s' % (','.join(bootstrap))
            stdio.start_loading('Cluster bootstrap')
            raise_cursor.execute(sql, exc_level='verbose')
            for zone in floor_servers:
                for addr in floor_servers[zone]:
                    sql = 'alter system add server "%s" zone "%s"' % (addr, zone)
                    raise_cursor.execute(sql)

            if global_conf.get('root_password') is not None:
                sql = 'alter user "root" IDENTIFIED BY %s'
                raise_cursor.execute(sql, [global_conf.get('root_password')])
            for zone in zones_config:
                zone_config = zones_config[zone]
                for key in zone_config:
                    sql = 'alter system modify zone %s set %s = %%s' % (zone, inner_config[key])
                    raise_cursor.execute(sql, [zone_config[key]])
            stdio.stop_loading('succeed')
        except:
            if not is_bootstrap(cursor):
                stdio.stop_loading('fail')
                return plugin_context.return_false()
            stdio.stop_loading('succeed')
    
        # wait for server online
        while True:
            servers = cursor.fetchall('select * from oceanbase.__all_server', raise_exception=False, exc_level='verbose')
            if servers and all([s.get('status') for s in servers]):
                break
            else:
                time.sleep(1)

    need_takeover_servers = []
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        ret = client.execute_command('ls %s/.meta' % server_config['home_path'])
        stdio.verbose(ret.stdout)
        stdio.verbose(ret.stderr)

        obshell_pid_path = '%s/run/obshell.pid' % home_path 
        obshell_pid = client.execute_command('cat %s' % obshell_pid_path).stdout.strip()
        if obshell_pid and client.execute_command('ls /proc/%s' % obshell_pid):
            stdio.verbose('%s obshell[pid: %s] started', server, obshell_pid)
        else:
            need_takeover_servers.append(server)
            ret = client.execute_command('strings %s/etc/observer.conf.bin' % home_path)
            stdio.verbose(ret.stdout)
            stdio.verbose(ret.stderr)

    if need_takeover_servers:
        stdio.start_loading('obshell taking over')
        for server in need_takeover_servers:
            # obshell admin start
            client = clients[server]
            server_config = cluster_config.get_server_conf(server)
            home_path = server_config['home_path']
            obshell_pid_path = '%s/run/obshell.pid' % home_path 
            obshell_pid = client.execute_command('cat %s' % obshell_pid_path).stdout.strip()
            if obshell_pid and client.execute_command('ls /proc/%s' % obshell_pid):
                stdio.verbose('%s obshell[pid: %s] started', server, obshell_pid)
            else:
                # start obshell
                server_config = cluster_config.get_server_conf(server)
                password = server_config.get('root_password', '')
                client.add_env('OB_ROOT_PASSWORD', password if client._is_local else ConfigUtil.passwd_format(password))
                cmd = 'cd %s; %s/bin/obshell admin start --ip %s --port %s'%(server_config['home_path'],server_config['home_path'], server.ip, server_config['obshell_port'])
                stdio.verbose('start obshell: %s' % cmd)
                if not client.execute_command(cmd):
                    stdio.stop_loading('fail')
                    stdio.error('%s obshell failed', server)
                    return

        time.sleep(3)
        retry_times = 600
        count = 0
        while count < retry_times:
            success = True
            for server in cluster_config.servers:
                # get status
                status = ocs_cursor[server].status_request(ignore_ConnectionError=True)
                if not status:
                    stdio.verbose('get status failed, count: %d' % count)
                    success = False
                    break
                if status.state == status.State.STATE_CONNECTION_AVAILABLE.value:
                    stdio.verbose('get status success')
            if not success:
                success = False
                count += 1
                time.sleep(1)
            else:
                break
        if not success:
            stdio.stop_loading('fail')
            stdio.error('obshell is not ready')
            return plugin_context.return_false()
        
        # find take over dag, maybe already finished
        while count < retry_times:
            success = False
            for server in cluster_config.servers:
                dag = ocs_cursor[server].get_agent_last_maintenance_dag_request()
                if dag and dag.is_take_over_or_rebuild(): # find the dag
                    # wait util dag finished
                    result = ocs_cursor[server].query_dag_util_finish(dag)
                    # TODO: 如果请求失败了，是否还需要重试呢
                    if result and result.is_succeed() and result.is_run():
                        # take over succeed
                        stdio.verbose('obshell take over succeed')
                        success = True
                        break
                    else:
                        count = retry_times
                        success = False
            if not success:
                stdio.verbose('find take over dag failed, count: %d' % count)
                success = False
                count += 1
                time.sleep(1)
            else:
                break
            
        if not success:
            stdio.stop_loading('fail')
            stdio.error('obshell take over failed')
            # TODO: 如果任务出错，提示用户是否需要重试（TAKE OVER 不可以回滚）
            return plugin_context.return_false()
    stdio.stop_loading('succeed')

    has_obproxy = False
    has_obproxy_scale_out = False
    for component_name in ['obproxy', 'obproxy-ce']:
        if component_name in added_components and component_name in be_depend:
            has_obproxy = True
            break
        if component_name in changed_components:
            has_obproxy_scale_out = True
            break
    if has_obproxy or ('proxyro_password' in global_conf and not has_obproxy_scale_out):
        value = global_conf['proxyro_password'] if global_conf.get('proxyro_password') is not None else ''
        sql = 'create user if not exists "proxyro" IDENTIFIED BY %s'
        raise_cursor.execute(sql, [value])
        sql = 'grant select on oceanbase.* to proxyro IDENTIFIED BY %s'
        raise_cursor.execute(sql, [value])

    has_oblogproxy = "oblogproxy" in added_components and "oblogproxy" in be_depend
    if has_oblogproxy or ('cdcro_password' in global_conf and 'oblogproxy' not in changed_components):
        value = global_conf['cdcro_password'] if global_conf.get('cdcro_password') is not None else ''
        sql = 'create user if not exists "cdcro" IDENTIFIED BY %s'
        raise_cursor.execute(sql, [value])
        sql = 'grant select on oceanbase.* to cdcro IDENTIFIED BY %s'
        raise_cursor.execute(sql, [value])

    has_obagent = "obagent" in added_components and "obagent" in be_depend
    if has_obagent or ('ocp_agent_monitor_password' in global_conf and 'obagent' not in changed_components):
        value = global_conf['ocp_agent_monitor_password'] if global_conf.get('ocp_agent_monitor_password') is not None else ''
        agent_user = cluster_config.get_global_conf_with_default().get('ocp_agent_monitor_username')
        sql = "create user if not exists '{username}' IDENTIFIED BY %s".format(username=agent_user)
        stdio.verbose(sql)
        raise_cursor.execute(sql, [value])
        sql = "grant select on oceanbase.* to '{username}' IDENTIFIED BY %s".format(username=agent_user)
        stdio.verbose(sql)
        raise_cursor.execute(sql, [value])

    # check the requirements of ocp meta and monitor tenant
    global_conf_with_default = deepcopy(cluster_config.get_global_conf_with_default())
    original_global_conf = cluster_config.get_original_global_conf()

    ocp_tenants = []
    tenants_componets_map = {
        "meta": ["ocp-express", "ocp-server", "ocp-server-ce"],
        "monitor": ["ocp-server", "ocp-server-ce"],
    }
    ocp_tenant_keys = ['tenant', 'db', 'username', 'password']
    for tenant in tenants_componets_map:
        components = tenants_componets_map[tenant]
        prefix = "ocp_%s_" % tenant
        if not any([component in added_components and component in be_depend for component in components]):
            for key in ocp_tenant_keys:
                config_key = prefix + key
                if config_key in global_conf:
                    break
            else:
                continue
        # set create tenant variable
        for key in global_conf_with_default:
            if key.startswith(prefix) and not original_global_conf.get(key, None):
                if ocp_config and ocp_config.get(key, None):
                    global_conf_with_default[key] = ocp_config[key]
                global_conf_with_default[prefix + 'tenant'][key.replace(prefix, '', 1)] = global_conf_with_default[key]
        tenant_info = global_conf_with_default[prefix + "tenant"]
        tenant_info["variables"] = "ob_tcp_invited_nodes='%'"
        tenant_info["create_if_not_exists"] = True
        tenant_info["database"] = global_conf_with_default[prefix + "db"]
        tenant_info["db_username"] = global_conf_with_default[prefix + "username"]
        tenant_info["db_password"] = global_conf_with_default.get(prefix + "password", "")
        tenant_info["{0}_root_password".format(tenant_info['tenant_name'])] = global_conf_with_default.get(prefix + "password", "")
        ocp_tenants.append(Values(tenant_info))
        plugin_context.set_variable("create_tenant_options", ocp_tenants)

    return plugin_context.return_true()
