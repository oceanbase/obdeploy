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

import copy
import os
import re
import time
from copy import deepcopy

from tool import Cursor
from _types import Capacity, CapacityWithB


PRI_KEY_FILE = '.ocp-server'
PUB_KEY_FILE = '.ocp-server.pub'


EXCLUDE_KEYS = [
        "home_path", "cluster_name", "ob_cluster_id", "admin_password", "memory_xms", "memory_xmx", "ocpCPU",
        "root_sys_password", "server_addresses", "system_password", "memory_size", 'jdbc_url', 'jdbc_username',
        'jdbc_password', "ocp_meta_tenant", "ocp_meta_tenant_log_disk_size", "ocp_meta_username", "ocp_meta_password",

    ]

CONFIG_MAPPER = {
        "port": "server.port",
        "session_timeout": "server.servlet.session.timeout",
        "login_encrypt_enabled": "ocp.login.encryption.enabled",
        "login_encrypt_public_key": "ocp.login.encryption.public-key",
        "login_encrypt_private_key": "ocp.login.encryption.private-key",
        "enable_basic_auth": "ocp.iam.auth.basic.enabled",
        "enable_csrf": "ocp.iam.csrf.enabled",
        "vault_key": "ocp.express.vault.secret-key",
        "druid_name": "spring.datasource.druid.name",
        "druid_init_size": "spring.datasource.druid.initial-size",
        "druid_min_idle": "spring.datasource.druid.min-idle",
        "druid_max_active": "spring.datasource.druid.max-active",
        "druid_test_while_idle": "spring.datasource.druid.test-while-idle",
        "druid_validation_query": "spring.datasource.druid.validation-query",
        "druid_max_wait": "spring.datasource.druid.max-wait",
        "druid_keep_alive": "spring.datasource.druid.keep-alive",
        "logging_pattern_console": "logging.pattern.console",
        "logging_pattern_file": "logging.pattern.file",
        "logging_file_name": "logging.file.name",
        "logging_file_max_size": "logging.file.max-size",
        "logging_file_total_size_cap": "logging.file.total-size-cap",
        "logging_file_clean_when_start": "logging.file.clean-history-on-start",
        "logging_file_max_history": "logging.file.max-history",
        "logging_level_web": "logging.level.web",
        "default_timezone": "ocp.system.default.timezone",
        "default_lang": "ocp.system.default.language",
        "obsdk_sql_query_limit": "ocp.monitor.collect.obsdk.sql-query-row-limit",
        "exporter_inactive_threshold": "ocp.monitor.exporter.inactive.threshold.seconds",
        "monitor_collect_interval": "ocp.metric.collect.interval.second",
        "montior_retention_days": "ocp.monitor.data.retention-days",
        "obsdk_cache_size": "obsdk.connector.holder.capacity",
        "obsdk_max_idle": "obsdk.connector.max-idle.seconds",
        "obsdk_cleanup_period": "obsdk.connector.cleanup.period.seconds",
        "obsdk_print_sql": "obsdk.print.sql",
        "obsdk_slow_query_threshold": "obsdk.slow.query.threshold.millis",
        "obsdk_init_timeout": "obsdk.connector.init.timeout.millis",
        "obsdk_init_core_size": "obsdk.connector.init.executor.thread-count",
        "obsdk_global_timeout": "obsdk.operation.global.timeout.millis",
        "obsdk_connect_timeout": "obsdk.socket.connect.timeout.millis",
        "obsdk_read_timeout": "obsdk.socket.read.timeout.millis"
    }


def exec_sql_in_tenant(sql, cursor, tenant, password, mode, retries=10, args=None):
    user = 'SYS' if mode == 'oracle' else 'root'
    tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, password=password)
    while not tenant_cursor and retries:
        retries -= 1
        time.sleep(2)
        tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, password=password)
    return tenant_cursor.execute(sql, args)


def get_port_socket_inode(client, port, stdio):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp*,udp*}' | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    stdio.verbose(res.stdout)
    return res.stdout.strip().split('\n')


def confirm_port(client, pid, port, stdio, launch_user=None):
    socket_inodes = get_port_socket_inode(client, port, stdio)
    if not socket_inodes:
        return False
    if launch_user:
        ret = client.execute_command("""sudo su - %s -c 'ls -l /proc/%s/fd/ |grep -E "socket:\[(%s)\]"'""" % (launch_user, pid, '|'.join(socket_inodes)))
    else:
        ret = client.execute_command("ls -l /proc/%s/fd/ |grep -E 'socket:\[(%s)\]'" % (pid, '|'.join(socket_inodes)))
    if ret and ret.stdout.strip():
        return True
    return False


def get_missing_required_parameters(parameters):
    results = []
    for key in ["jdbc_url", "jdbc_password", "jdbc_username", "cluster_name", "ob_cluster_id", "root_sys_password",
                "server_addresses", "agent_username", "agent_password"]:
        if parameters.get(key) is None:
            results.append(key)
    return results


def get_ocp_depend_config(cluster_config, stdio):
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
        default_server_config = deepcopy(cluster_config.get_server_conf_with_default(server))
        server_config = deepcopy(cluster_config.get_server_conf(server))
        original_server_config = cluster_config.get_original_server_conf_with_global(server)
        missed_keys = get_missing_required_parameters(original_server_config)
        if missed_keys:
            if 'jdbc_url' in missed_keys and depend_observer:
                default_server_config['jdbc_url'] = 'jdbc:oceanbase://{}:{}/{}'.format(depend_info['server_ip'], depend_info['mysql_port'], depend_info['meta_db'] if not original_server_config.get('ocp_meta_db', None) else original_server_config['ocp_meta_db']) if not original_server_config.get('jdbc_url', None) else original_server_config['jdbc_url']
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


def start(plugin_context, start_env=None, source_option='start', without_parameter=False, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if not value:
            value = default
        return value

    def get_parsed_option(key, default=''):
        value = get_option(key=key, default=default)
        if value is None:
            return value
        try:
            parsed_value = Capacity(value).bytes
        except:
            stdio.exception("")
            raise Exception("Invalid option {}: {}".format(key, value))
        return parsed_value

    def error(*arg, **kwargs):
        stdio.error(*arg, **kwargs)
        stdio.stop_loading('fail')

    def start_cluster(times=0):
        server_config = start_env[cluster_config.servers[0]]
        # check meta db connect before start
        jdbc_url = server_config['jdbc_url']
        jdbc_username = "{0}@{1}".format(server_config['ocp_meta_username'], server_config['ocp_meta_tenant']['tenant_name'])
        jdbc_password = server_config['ocp_meta_password']
        jdbc_public_key = ''
        meta_user = server_config['ocp_meta_username']
        meta_tenant = server_config['ocp_meta_tenant']['tenant_name']
        meta_password = server_config['ocp_meta_password']
        monitor_user = server_config['ocp_monitor_username']
        monitor_tenant = server_config['ocp_monitor_tenant']['tenant_name']
        monitor_password = server_config['ocp_monitor_password']
        monitor_db = server_config['ocp_monitor_db']

        matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", jdbc_url)
        stdio.verbose('metadb connect check')
        if matched:
            jdbc_host = matched.group(1)
            jdbc_port = matched.group(2)[1:]
        else:
            stdio.error("jdbc_url is not valid")
            return False

        global_config = cluster_config.get_global_conf()
        site_url = global_config.get('ocp_site_url', '')
        soft_dir = global_config.get('soft_dir', '')

        retries = 10
        meta_cursor = monitor_cursor = ''
        while retries:
            retries -= 1
            try:
                meta_cursor = Cursor(jdbc_host, jdbc_port, meta_user, meta_tenant, meta_password, stdio)
                meta_cursor.execute("show databases;", raise_exception=False, exc_level='verbose')
                monitor_cursor = Cursor(jdbc_host, jdbc_port, monitor_user, monitor_tenant, monitor_password, stdio)
                monitor_cursor.execute("show databases;", raise_exception=False, exc_level='verbose')
                stdio.verbose(f'meta tenant and monitor tenant connect successful')
                break
            except:
                stdio.verbose(f'meta tenant or monitor tenant connect failed, retrying({retries})')
                if retries == 0:
                    stdio.error('meta tenant or monitor tenant connect failed')
                    return False
                time.sleep(1)

        if meta_cursor and meta_user != 'root':
            sql = f"""ALTER USER root IDENTIFIED BY %s"""
            meta_cursor.execute(sql, args=[meta_password], raise_exception=False, exc_level='verbose')
        plugin_context.set_variable('meta_cursor', meta_cursor)

        if monitor_cursor and monitor_user != 'root':
            sql = f"""ALTER USER root IDENTIFIED BY %s"""
            monitor_cursor.execute(sql, args=[monitor_password], raise_exception=False, exc_level='verbose')
        plugin_context.set_variable('monitor_cursor', monitor_cursor)

        server_pid = {}
        success = True
        node_num = 1
        stdio.start_loading("Start %s" % cluster_config.name)
        for server in cluster_config.servers:
            client = clients[server]
            server_config = start_env[server]
            home_path = server_config['home_path']
            launch_user = server_config.get('launch_user', None)
            system_password = server_config["system_password"]
            pid_path = os.path.join(home_path, 'run/ocp-server.pid')
            pids = client.execute_command("cat %s" % pid_path).stdout.strip()
            if not times and pids and all([client.execute_command('ls /proc/%s' % pid) for pid in pids.split('\n')]):
                server_pid[server] = pids
                continue

            memory_xms = server_config.get('memory_xms', None)
            memory_xmx = server_config.get('memory_xmx', None)
            if memory_xms or memory_xmx:
                jvm_memory_option = "-Xms{0} -Xmx{1}".format(memory_xms, memory_xmx)
            else:
                memory_size = server_config.get('memory_size', '1G')
                jvm_memory_option = "-Xms{0} -Xmx{0}".format(str(Capacity(memory_size)).lower())
            extra_options = {
                "ocp.iam.encrypted-system-password": system_password
            }
            extra_options_str = ' '.join(["-D{}={}".format(k, v) for k, v in extra_options.items()])
            java_bin = server_config['java_bin']
            client.add_env('PATH', '%s/jre/bin:' % server_config['home_path'])
            cmd = f'{java_bin} -Dfile.encoding=UTF-8 -jar {jvm_memory_option} {extra_options_str} {home_path}/lib/ocp-server.jar --bootstrap'
            jar_cmd = copy.deepcopy(cmd)
            if "log_dir" not in server_config:
                log_dir = os.path.join(home_path, 'log')
            else:
                log_dir = server_config["log_dir"]
            server_config["logging_file_name"] = os.path.join(log_dir, 'ocp-server.log')
            jdbc_password_to_str = jdbc_password.replace("'", """'"'"'""")
            environ_variable = 'export JDBC_URL=%s; export JDBC_USERNAME=%s;' \
                               'export JDBC_PASSWORD=\'%s\'; ' \
                               'export JDBC_PUBLIC_KEY=%s;' % (
                                   jdbc_url, jdbc_username, jdbc_password_to_str, jdbc_public_key
                               )
            if not times:
                cmd += ' --progress-log={}'.format(os.path.join(log_dir, 'bootstrap.log'))
                for key in server_config:
                    if key == 'jdbc_url' and monitor_user:
                        monitor_password = monitor_password.replace("'", """'"'"'""")
                        cmd += f' --with-property=ocp.monitordb.host:{jdbc_host}' \
                               f' --with-property=ocp.monitordb.username:{monitor_user + "@" + monitor_tenant}' \
                               f' --with-property=ocp.monitordb.port:{jdbc_port}' \
                               f' --with-property=ocp.monitordb.password:\'{monitor_password}\'' \
                               f' --with-property=ocp.monitordb.database:{monitor_db}'
                    if key not in EXCLUDE_KEYS and key in CONFIG_MAPPER:
                        if key == 'logging_file_total_size_cap':
                            cmd += ' --with-property=ocp.logging.file.total.size.cap:{}'.format(CapacityWithB(server_config[key]))
                            continue
                        cmd += ' --with-property={}:{}'.format(CONFIG_MAPPER[key], server_config[key])
                if site_url:
                    cmd += ' --with-property=ocp.site.url:{}'.format(site_url)
                # set connection mode to direct to avoid obclient issue
                cmd += ' --with-property=obsdk.ob.connection.mode:direct'
                cmd += ' --with-property=ocp.iam.login.client.max-attempts:60'
                cmd += ' --with-property=ocp.iam.login.client.lockout-minutes:1'
            if not without_parameter and not get_option('without_parameter', ''):
                if server_config['admin_password'] != '********':
                    admin_password = server_config['admin_password'].replace("'", """'"'"'""")
                    environ_variable += "export OCP_INITIAL_ADMIN_PASSWORD=\'%s\';" % admin_password
                cmd += f' --with-property=ocp.file.local.built-in.dir:{home_path}/ocp-server/lib'
                cmd += f' --with-property=ocp.log.download.tmp.dir:{home_path}/logs/ocp'
                cmd += ' --with-property=ocp.file.local.dir:{}'.format(soft_dir) if soft_dir else f' --with-property=ocp.file.local.dir:{home_path}/data/files'
            real_cmd = environ_variable + cmd
            execute_cmd = "cd {}; {} > /dev/null 2>&1 &".format(home_path, real_cmd)
            if launch_user:
                cmd_file = os.path.join(home_path, 'cmd.sh')
                client.write_file(execute_cmd, cmd_file)
                execute_cmd = "chmod +x {0};sudo chown -R {1} {0};sudo su - {1} -c '{0}' &".format(cmd_file, launch_user)
            client.execute_command(execute_cmd, timeout=3600)
            ret = client.execute_command(
                "ps -aux | grep -F '%s' | grep -v grep | awk '{print $2}' " % jar_cmd)
            if ret:
                server_pid[server] = ret.stdout.strip()
                if not server_pid[server]:
                    stdio.error("failed to start {} ocp server".format(server))
                    success = False
                    continue
                client.write_file(server_pid[server], os.path.join(home_path, 'run/ocp-server.pid'))
                if times == 0 and len(cluster_config.servers) > 1:
                    break
                if len(cluster_config.servers) > 1 and node_num == 1:
                    time.sleep(60)
                    node_num += 1

        if success:
            stdio.stop_loading('succeed')
        else:
            stdio.stop_loading('fail')
            return plugin_context.return_false()

        stdio.start_loading("%s program health check" % cluster_config.name)
        failed = []
        servers = server_pid.keys()
        count = 120
        while servers and count:
            count -= 1
            tmp_servers = []
            for server in servers:
                server_config = cluster_config.get_server_conf(server)
                client = clients[server]
                stdio.verbose('%s program health check' % server)
                pids_stat = {}
                launch_user = server_config.get('launch_user', None)
                if server in server_pid:
                    for pid in server_pid[server].split("\n"):
                        pids_stat[pid] = None
                        cmd = 'ls /proc/{}'.format(pid) if not launch_user else 'sudo ls /proc/{}'.format(pid)
                        if not client.execute_command(cmd):
                            pids_stat[pid] = False
                            continue
                        confirm = confirm_port(client, pid, int(server_config["port"]), stdio, launch_user)
                        if confirm:
                            pids_stat[pid] = True
                            break
                    if any(pids_stat.values()):
                        for pid in pids_stat:
                            if pids_stat[pid]:
                                stdio.verbose('%s %s[pid: %s] started', server, cluster_config.name, pid)
                        continue
                    if all([stat is False for stat in pids_stat.values()]):
                        failed.append('failed to start {} {}'.format(server, cluster_config.name))
                    elif count:
                        tmp_servers.append(server)
                        stdio.verbose('failed to start %s %s, remaining retries: %d' % (server, cluster_config.name, count))
                    else:
                        failed.append('failed to start {} {}'.format(server, cluster_config.name))
            servers = tmp_servers
            if servers and count:
                time.sleep(15)

        if failed:
            stdio.stop_loading('failed')
            for msg in failed:
                stdio.error(msg)
            return plugin_context.return_false()
        else:
            stdio.stop_loading('succeed')
            plugin_context.return_true(need_bootstrap=False)
            return True

    def stop_cluster():
        for server in cluster_config.servers:
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            home_path = server_config['home_path']
            pid_path = os.path.join(home_path, 'run/ocp-server.pid')
            launch_user = server_config.get('launch_user', None)
            cmd = 'cat {}'.format(pid_path) 
            pids = client.execute_command('sudo ' + cmd if launch_user else cmd).stdout.strip().split('\n')
            success = True
            for pid in pids:
                cmd = 'ls /proc/{}'.format(pid)
                if pid and client.execute_command('sudo ' + cmd if launch_user else cmd):
                    cmd = 'ls /proc/{}/fd'.format(pid)
                    if client.execute_command('sudo ' + cmd if launch_user else cmd):
                        stdio.verbose('{} {}[pid: {}] stopping...'.format(server, cluster_config.name, pid))
                        cmd = 'kill -9 {}'.format(pid)
                        client.execute_command('sudo ' + cmd if launch_user else cmd)
                        return True
                    else:
                        stdio.verbose('failed to stop {}[pid:{}] in {}, permission deny'.format(cluster_config.name, pid, server))
                        success = False
                else:
                    stdio.verbose('{} {} is not running'.format(server, cluster_config.name))
            if not success:
                stdio.stop_loading('fail')
                return plugin_context.return_true()

    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    stdio = plugin_context.stdio
    global tenant_cursor
    tenant_cursor = None

    if not start_env:
        start_env = get_ocp_depend_config(cluster_config, stdio)
        if not start_env:
            return plugin_context.return_false()

    if not without_parameter and not get_option('without_parameter', ''):
        if not start_cluster():
            stdio.error('start %s failed' % cluster_config.name)
            return plugin_context.return_false()
        if not stop_cluster():
            stdio.error('stop %s failed' % cluster_config.name)
            return plugin_context.return_false()
    if not start_cluster(1):
        stdio.error('start %s failed' % cluster_config.name)
        return plugin_context.return_false()
    plugin_context.set_variable('start_env', start_env)

    return plugin_context.return_true(need_bootstrap=True)
