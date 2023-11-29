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
from glob import glob
from copy import deepcopy
from const import CONST_OBD_HOME

from tool import Cursor, FileUtil, YamlLoader
from _errno import EC_OBSERVER_CAN_NOT_MIGRATE_IN


OBD_INSTALL_PRE = os.environ.get('OBD_INSTALL_PRE', '/')

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


def parse_size(size):
    _bytes = 0
    if isinstance(size, str):
        size = size.strip()
    if not isinstance(size, str) or size.isdigit():
        _bytes = int(size)
    else:
        units = {"B": 1, "K": 1 << 10, "M": 1 << 20, "G": 1 << 30, "T": 1 << 40}
        match = re.match(r'^(0|[1-9][0-9]*)\s*([B,K,M,G,T])$', size.upper())
        _bytes = int(match.group(1)) * units[match.group(2)]
    return _bytes


def format_size(size, precision=1):
    units = ['B', 'K', 'M', 'G', 'T', 'P']
    idx = 0
    if precision:
        div = 1024.0
        format = '%.' + str(precision) + 'f%s'
    else:
        div = 1024
        format = '%d%s'
    while idx < 5 and size >= 1024:
        size /= 1024.0
        idx += 1
    return format % (size, units[idx])


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
        ret = client.execute_command("""su - %s -c 'ls -l /proc/%s/fd/ |grep -E "socket:\[(%s)\]"'""" % (launch_user, pid, '|'.join(socket_inodes)))
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
    root_servers = []
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
        server_config = deepcopy(cluster_config.get_server_conf_with_default(server))
        original_server_config = cluster_config.get_original_server_conf(server)
        missed_keys = get_missing_required_parameters(original_server_config)
        if missed_keys:
            if 'jdbc_url' in missed_keys and depend_observer:
                server_config['jdbc_url'] = 'jdbc:oceanbase://{}:{}/{}'.format(depend_info['server_ip'],
                                                                               depend_info['mysql_port'],
                                                                               server_config['ocp_meta_db'])
                server_config['jdbc_username'] = '%s@%s' % (
                    server_config['ocp_meta_username'], server_config['ocp_meta_tenant']['tenant_name'])
                server_config['jdbc_password'] = server_config['ocp_meta_password']
                server_config['root_password'] = depend_info.get('root_password', '')
        env[server] = server_config
    return env


def start(plugin_context, start_env=None, cursor='', sys_cursor1='', without_ocp_parameter=False, *args, **kwargs):
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
            parsed_value = parse_size(value)
        except:
            stdio.exception("")
            raise Exception("Invalid option {}: {}".format(key, value))
        return parsed_value

    def error(*arg, **kwargs):
        stdio.error(*arg, **kwargs)
        stdio.stop_loading('fail')

    def create_tenant(cursor, name, max_cpu, memory_size, db_username, tenant_password, database, stdio):
        mode = get_option('mode', 'mysql').lower()
        if not mode in ['mysql', 'oracle']:
            error('No such tenant mode: %s.\n--mode must be `mysql` or `oracle`' % mode)
            return plugin_context.return_false()

        unit_name = '%s_unit' % name
        sql = 'select * from oceanbase.DBA_OB_UNIT_CONFIGS order by name'
        res = cursor.fetchall(sql)
        if res is False:
            return plugin_context.return_false()
        for row in res:
            if str(row['NAME']) == unit_name:
                unit_name += '1'

        pool_name = '%s_pool' % name

        sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
        tenant_exists = False
        res = cursor.fetchone(sql, [name])
        if res:
            if create_if_not_exists:
                tenant_exists = True
            else:
                error('Tenant %s already exists' % name)
                return plugin_context.return_false()
        elif res is False:
            return plugin_context.return_false()
        if not tenant_exists:
            stdio.start_loading('Create tenant %s' % name)
            zone_list = get_option('zone_list', set())
            MIN_CPU = 1
            MIN_MEMORY = 1073741824
            MIN_LOG_DISK_SIZE = 2147483648
            MIN_IOPS = 1024
            zone_obs_num = {}
            sql = "select zone, count(*) num from oceanbase.__all_server where status = 'active' group by zone"
            res = cursor.fetchall(sql, raise_exception=True)

            for row in res:
                zone_obs_num[str(row['zone'])] = row['num']

            if not zone_list:
                zone_list = zone_obs_num.keys()
            if isinstance(zone_list, str):
                zones = zone_list.replace(';', ',').split(',')
            else:
                zones = zone_list
            zone_list = "('%s')" % "','".join(zones)

            min_unit_num = min(zone_obs_num.items(), key=lambda x: x[1])[1]
            unit_num = get_option('unit_num', min_unit_num)
            if unit_num > min_unit_num:
                error('resource pool unit num is bigger than zone server count')
                return plugin_context.return_false()

            sql = "select count(*) num from oceanbase.__all_server where status = 'active' and start_service_time > 0"
            count = 30
            while count:
                num = cursor.fetchone(sql)
                if num is False:
                    error('%s : execute failed' % sql)
                    return plugin_context.return_false()
                num = num['num']
                if num >= unit_num:
                    break
                count -= 1
                time.sleep(1)
            if count == 0:
                stdio.error(EC_OBSERVER_CAN_NOT_MIGRATE_IN)
                return plugin_context.return_false()

            sql = "SELECT * FROM oceanbase.GV$OB_SERVERS where zone in %s" % zone_list
            servers_stats = cursor.fetchall(sql, raise_exception=True)
            cpu_available = servers_stats[0]['CPU_CAPACITY_MAX'] - servers_stats[0]['CPU_ASSIGNED_MAX']
            mem_available = servers_stats[0]['MEM_CAPACITY'] - servers_stats[0]['MEM_ASSIGNED']
            disk_available = servers_stats[0]['DATA_DISK_CAPACITY'] - servers_stats[0]['DATA_DISK_IN_USE']
            log_disk_available = servers_stats[0]['LOG_DISK_CAPACITY'] - servers_stats[0]['LOG_DISK_ASSIGNED']
            for servers_stat in servers_stats[1:]:
                cpu_available = min(servers_stat['CPU_CAPACITY_MAX'] - servers_stat['CPU_ASSIGNED_MAX'], cpu_available)
                mem_available = min(servers_stat['MEM_CAPACITY'] - servers_stat['MEM_ASSIGNED'], mem_available)
                disk_available = min(servers_stat['DATA_DISK_CAPACITY'] - servers_stat['DATA_DISK_IN_USE'],
                                     disk_available)
                log_disk_available = min(servers_stat['LOG_DISK_CAPACITY'] - servers_stat['LOG_DISK_ASSIGNED'],
                                         log_disk_available)

            if cpu_available < MIN_CPU:
                error('%s: resource not enough: cpu count less than %s' % (zone_list, MIN_CPU))
                return plugin_context.return_false()
            if mem_available < MIN_MEMORY:
                error('%s: resource not enough: memory less than %s' % (zone_list, format_size(MIN_MEMORY)))
                return plugin_context.return_false()
            if log_disk_available < MIN_LOG_DISK_SIZE:
                error(
                    '%s: resource not enough: log disk size less than %s' % (zone_list, format_size(MIN_MEMORY)))
                return plugin_context.return_false()

            # cpu options
            min_cpu = get_option('min_cpu', max_cpu)
            if cpu_available < max_cpu:
                error('resource not enough: cpu (Avail: %s, Need: %s)' % (cpu_available, max_cpu))
                return plugin_context.return_false()
            if max_cpu < min_cpu:
                error('min_cpu must less then max_cpu')
                return plugin_context.return_false()

            # memory options
            log_disk_size = get_parsed_option('log_disk_size', None)

            if memory_size is None:
                memory_size = mem_available
                if log_disk_size is None:
                    log_disk_size = log_disk_available

            if mem_available < memory_size:
                error('resource not enough: memory (Avail: %s, Need: %s)' % (
                    format_size(mem_available), format_size(memory_size)))
                return plugin_context.return_false()

            # log disk size options
            if log_disk_size is not None and log_disk_available < log_disk_size:
                error('resource not enough: log disk space (Avail: %s, Need: %s)' % (
                    format_size(disk_available), format_size(log_disk_size)))
                return plugin_context.return_false()

            # iops options
            max_iops = get_option('max_iops', None)
            min_iops = get_option('min_iops', None)
            iops_weight = get_option('iops_weight', None)
            if max_iops is not None and max_iops < MIN_IOPS:
                error('max_iops must greater than %d' % MIN_IOPS)
                return plugin_context.return_false()
            if max_iops is not None and min_iops is not None and max_iops < min_iops:
                error('min_iops must less then max_iops')
                return plugin_context.return_false()

            zone_num = len(zones)
            charset = get_option('charset', '')
            collate = get_option('collate', '')
            replica_num = get_option('replica_num', zone_num)
            logonly_replica_num = get_option('logonly_replica_num', 0)
            tablegroup = get_option('tablegroup', '')
            primary_zone = get_option('primary_zone', 'RANDOM')
            locality = get_option('locality', '')
            variables = get_option('variables', "ob_tcp_invited_nodes='%'")

            if replica_num == 0:
                replica_num = zone_num
            elif replica_num > zone_num:
                error('replica_num cannot be greater than zone num (%s)' % zone_num)
                return plugin_context.return_false()
            if not primary_zone:
                primary_zone = 'RANDOM'
            if logonly_replica_num > replica_num:
                error('logonly_replica_num cannot be greater than replica_num (%s)' % replica_num)
                return plugin_context.return_false()

            # create resource unit
            sql = "create resource unit %s max_cpu %.1f, memory_size %d" % (unit_name, max_cpu, memory_size)
            if min_cpu is not None:
                sql += ', min_cpu %.1f' % min_cpu
            if max_iops is not None:
                sql += ', max_iops %d' % max_iops
            if min_iops is not None:
                sql += ', min_iops %d' % min_iops
            if iops_weight is not None:
                sql += ', iops_weight %d' % iops_weight
            if log_disk_size is not None:
                sql += ', log_disk_size %d' % log_disk_size

            res = cursor.execute(sql, raise_exception=True)

            # create resource pool
            sql = "create resource pool %s unit='%s', unit_num=%d, zone_list=%s" % (
                pool_name, unit_name, unit_num, zone_list)
            res = cursor.execute(sql, raise_exception=True)

            # create tenant
            sql = "create tenant %s replica_num=%d,zone_list=%s,primary_zone='%s',resource_pool_list=('%s')"
            sql = sql % (name, replica_num, zone_list, primary_zone, pool_name)
            if charset:
                sql += ", charset = '%s'" % charset
            if collate:
                sql += ", collate = '%s'" % collate
            if logonly_replica_num:
                sql += ", logonly_replica_num = %d" % logonly_replica_num
            if tablegroup:
                sql += ", default tablegroup ='%s'" % tablegroup
            if locality:
                sql += ", locality = '%s'" % locality

            set_mode = "ob_compatibility_mode = '%s'" % mode
            if variables:
                sql += "set %s, %s" % (variables, set_mode)
            else:
                sql += "set %s" % set_mode
            res = cursor.execute(sql, raise_exception=True)
        stdio.stop_loading('succeed')
        if database:
            sql = 'create database if not exists {}'.format(database)
            if not exec_sql_in_tenant(sql=sql, cursor=cursor, tenant=name, password=tenant_password if tenant_exists else '', mode=mode) and not create_if_not_exists:
                stdio.error('failed to create database {}'.format(database))
                return plugin_context.return_false()

        db_password = tenant_password
        if db_username:
            sql = "create user if not exists '{username}' IDENTIFIED BY %s".format(username=db_username)
            sargs = [db_password]
            if exec_sql_in_tenant(sql=sql, cursor=cursor, tenant=name, password=tenant_password if tenant_exists else '', mode=mode, args=sargs):
                sql = "grant all on *.* to '{username}' WITH GRANT OPTION".format(username=db_username)
                if exec_sql_in_tenant(sql=sql, cursor=cursor, tenant=name, password=tenant_password if tenant_exists else '', mode=mode):
                    sql = 'alter user root IDENTIFIED BY %s'
                    if exec_sql_in_tenant(sql=sql, cursor=cursor, tenant=name, password=tenant_password if tenant_exists else '', mode=mode, args=sargs):
                        return True
            stdio.error('failed to create user {}'.format(db_username))
            return plugin_context.return_false()
        return True

    def _ocp_lib(client, home_path, soft_dir='', stdio=None):
        stdio.verbose('cp rpm & pos')
        OBD_HOME = os.path.join(os.environ.get(CONST_OBD_HOME, os.getenv('HOME')), '.obd')
        for rpm in glob(os.path.join(OBD_HOME, 'mirror/local/*ocp-agent-*.rpm')):
            name = os.path.basename(rpm)
            client.put_file(rpm, os.path.join(home_path, 'ocp-server/lib/', name))
            if soft_dir:
                client.put_file(rpm, os.path.join(soft_dir, name))

    def start_cluster(times=0):
        jdbc_host = jdbc_port = jdbc_url = jdbc_username = jdbc_password = jdbc_public_key = cursor = monitor_user = monitor_tenant = monitor_memory_size = monitor_max_cpu = monitor_password = monitor_db = meta_password = ''
        for server in cluster_config.servers:
            server_config = start_env[server]
            # check meta db connect before start
            jdbc_url = server_config['jdbc_url']
            jdbc_username = server_config['jdbc_username']
            jdbc_password = server_config['jdbc_password']
            root_password = server_config.get('root_password', '')
            cursor = get_option('metadb_cursor', '')
            cursor = kwargs.get('metadb_cursor', '') if cursor == '' else cursor
            matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", jdbc_url)
            stdio.verbose('metadb connect check')
            if matched:
                jdbc_host = matched.group(1)
                jdbc_port = matched.group(2)[1:]
                jdbc_database = matched.group(3)
                password = root_password if root_password else jdbc_password
                retries = 10
                while not cursor and retries and get_option("skip_create_tenant", 'False') == 'False':
                    try:
                        retries -= 1
                        time.sleep(2)
                        cursor = Cursor(ip=jdbc_host, port=jdbc_port, user='root@sys', password=password, stdio=stdio)
                    except:
                        pass

        global_config = cluster_config.get_global_conf()
        site_url = global_config.get('ocp_site_url', '')
        soft_dir = global_config.get('soft_dir', '')
        meta_user = global_config.get('ocp_meta_username', 'meta_user')
        meta_tenant = global_config.get('ocp_meta_tenant')['tenant_name']
        meta_max_cpu = global_config['ocp_meta_tenant'].get('max_cpu', 2)
        meta_memory_size = global_config['ocp_meta_tenant'].get('memory_size', '2G')
        meta_password = global_config.get('ocp_meta_password', '')
        meta_db = global_config.get('ocp_meta_db', 'meta_database')
        if global_config.get('ocp_monitor_tenant'):
            monitor_user = global_config.get('ocp_monitor_username', 'monitor_user')
            monitor_tenant = global_config['ocp_monitor_tenant']['tenant_name']
            monitor_max_cpu = global_config['ocp_monitor_tenant'].get('max_cpu', 2)
            monitor_memory_size = global_config['ocp_monitor_tenant'].get('memory_size', '4G')
            monitor_password = global_config.get('ocp_monitor_password', '')
            monitor_db = global_config.get('ocp_monitor_db', 'monitor_database')
        if get_option("skip_create_tenant", 'False') == 'False':
            if not times:
                if not create_tenant(cursor, meta_tenant, meta_max_cpu, parse_size(meta_memory_size), meta_user,
                                     meta_password,
                                     meta_db, stdio):
                    return plugin_context.return_false()
            meta_cursor = Cursor(jdbc_host, jdbc_port, meta_user, meta_tenant, meta_password, stdio)
            plugin_context.set_variable('meta_cursor', meta_cursor)

            if not times:
                if not create_tenant(cursor, monitor_tenant, monitor_max_cpu, parse_size(monitor_memory_size),
                                     monitor_user,
                                     monitor_password, monitor_db, stdio):
                    return plugin_context.return_false()
        if meta_tenant not in jdbc_username:
            jdbc_username = meta_user + '@' + meta_tenant
            jdbc_url = jdbc_url.rsplit('/', 1)[0] + '/' + meta_db
            jdbc_password = meta_password

        server_pid = {}
        success = True
        stdio.start_loading("Start ocp-server")
        for server in cluster_config.servers:
            client = clients[server]
            server_config = start_env[server]
            home_path = server_config['home_path']
            launch_user = server_config.get('launch_user', None)
            _ocp_lib(client, home_path, soft_dir, stdio)
            system_password = server_config["system_password"]
            port = server_config['port']
            if not site_url:
                site_url = 'http://{}:{}'.format(server.ip, port)
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
                jvm_memory_option = "-Xms{0} -Xmx{0}".format(format_size(parse_size(memory_size), 0).lower())
            extra_options = {
                "ocp.iam.encrypted-system-password": system_password
            }
            extra_options_str = ' '.join(["-D{}={}".format(k, v) for k, v in extra_options.items()])
            java_bin = server_config['java_bin']
            cmd = f'{java_bin} -jar {jvm_memory_option} {extra_options_str} {home_path}/lib/ocp-server.jar --bootstrap'
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
                        cmd += ' --with-property={}:{}'.format(CONFIG_MAPPER[key], server_config[key])
                cmd += ' --with-property=ocp.site.url:{}'.format(site_url)
                # set connection mode to direct to avoid obclient issue
                cmd += ' --with-property=obsdk.ob.connection.mode:direct'
            if server_config['admin_password'] != '********':
                admin_password = server_config['admin_password'].replace("'", """'"'"'""")
                environ_variable += "export OCP_INITIAL_ADMIN_PASSWORD=\'%s\';" % admin_password
            cmd += f' --with-property=ocp.file.local.built-in.dir:{home_path}/ocp-server/lib'
            cmd += f' --with-property=ocp.log.download.tmp.dir:{home_path}/logs/ocp'
            cmd += ' --with-property=ocp.file.local.dir:{}'.format(soft_dir) if soft_dir else f' --with-property=ocp.file.local.dir:{home_path}/data/files'
            real_cmd = environ_variable + cmd
            execute_cmd = "cd {}; {} > /dev/null 2>&1 &".format(home_path, real_cmd)
            if server_config.get('launch_user'):
                cmd_file = os.path.join(home_path, 'cmd.sh')
                client.write_file(execute_cmd, cmd_file)
                execute_cmd = "chmod +x {0};sudo chown -R {1} {0};sudo su - {1} -c '{0}' &".format(cmd_file, server_config['launch_user'])
            client.execute_command(execute_cmd, timeout=3600)
            time.sleep(10)
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

        if success:
            stdio.stop_loading('succeed')
        else:
            stdio.stop_loading('fail')
            return plugin_context.return_false()

        stdio.start_loading("ocp-server program health check")
        failed = []
        servers = server_pid.keys()
        count = 40
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
                                stdio.verbose('%s ocp-server[pid: %s] started', server, pid)
                        continue
                    if all([stat is False for stat in pids_stat.values()]):
                        failed.append('failed to start {} ocp-server'.format(server))
                    elif count:
                        tmp_servers.append(server)
                        stdio.verbose('failed to start %s ocp-server, remaining retries: %d' % (server, count))
                    else:
                        failed.append('failed to start {} ocp-server'.format(server))
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
        success = True
        for server in cluster_config.servers:
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            home_path = server_config['home_path']
            pid_path = os.path.join(home_path, 'run/ocp-server.pid')
            launch_user = server_config.get('launch_user', None)
            cmd = 'cat {}'.format(pid_path) 
            pids = client.execute_command('sudo ' + cmd if launch_user else cmd).stdout.strip().split('\n')
            success = False
            for pid in pids:
                cmd = 'ls /proc/{}'.format(pid)
                if pid and client.execute_command('sudo ' + cmd if launch_user else cmd):
                    cmd = 'ls /proc/{}/fd'.format(pid)
                    if client.execute_command('sudo ' + cmd if launch_user else cmd):
                        stdio.verbose('{} ocp-server[pid: {}] stopping...'.format(server, pid))
                        cmd = 'kill -9 {}'.format(pid)
                        client.execute_command('sudo ' + cmd if launch_user else cmd)
                        return True
                    else:
                        stdio.verbose('failed to stop ocp-server[pid:{}] in {}, permission deny'.format(pid, server))
                        success = False
                else:
                    stdio.verbose('{} ocp-server is not running'.format(server))
            if not success:
                stdio.stop_loading('fail')
                return plugin_context.return_true()

    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    create_if_not_exists = get_option('create_if_not_exists', True)
    sys_cursor = kwargs.get('sys_cursor')
    global tenant_cursor
    tenant_cursor = None

    if not start_env:
        start_env = get_ocp_depend_config(cluster_config, stdio)
        if not start_env:
            return plugin_context.return_false()

    if not without_ocp_parameter and not get_option('without_ocp_parameter', ''):
        if not start_cluster():
            stdio.error('start ocp-server failed')
            return plugin_context.return_false()
        if not stop_cluster():
            stdio.error('stop ocp-server failed')
            return plugin_context.return_false()
    if not start_cluster(1):
        stdio.error('start ocp-server failed')
        return plugin_context.return_false()
    time.sleep(10)
    return plugin_context.return_true()
