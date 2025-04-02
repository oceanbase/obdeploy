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
import os
import re
import time

from _types import Capacity, CapacityWithB
from tool import get_option


def start(plugin_context, multi_process_flag=False, start_env=None, *args, **kwargs):

    EXCLUDE_KEYS = plugin_context.get_variable('EXCLUDE_KEYS')
    CONFIG_MAPPER = plugin_context.get_variable('CONFIG_MAPPER')
    start_env = plugin_context.get_variable('start_env')
    without_parameter = plugin_context.get_variable('without_parameter')
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    options = plugin_context.options

    if not start_env:
        stdio.verbose('start env is not set')
        return plugin_context.return_false()

    global_config = cluster_config.get_global_conf()
    site_url = global_config.get('ocp_site_url', '')
    soft_dir = global_config.get('soft_dir', '')

    server_config = start_env[cluster_config.servers[0]]
    jdbc_host = plugin_context.get_variable('jdbc_host', default=server_config.get('jdbc_host', ''))
    jdbc_port = plugin_context.get_variable('jdbc_port', default=server_config.get('jdbc_port', ''))
    jdbc_url = server_config['jdbc_url']
    cluster_name = ''
    if server_config.get('jdbc_username', ''):
        jdbc_username = server_config['jdbc_username']
        if '#' in jdbc_username:
            cluster_name = '#' + jdbc_username.split('#')[1]
    jdbc_username = "{0}@{1}{2}".format(server_config['ocp_meta_username'], server_config['ocp_meta_tenant']['tenant_name'], cluster_name)
    jdbc_password = server_config['ocp_meta_password']
    jdbc_public_key = ''
    monitor_user = server_config['ocp_monitor_username']
    monitor_tenant = server_config['ocp_monitor_tenant']['tenant_name']
    monitor_password = server_config['ocp_monitor_password']
    monitor_db = server_config['ocp_monitor_db']

    stdio.verbose('metadb connect check')

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
        if pids and all([client.execute_command('ls /proc/%s' % pid) for pid in pids.split('\n')]):
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
        if server_config['admin_password'] != '********':
            admin_password = server_config['admin_password'].replace("'", """'"'"'""")
            environ_variable += "export OCP_INITIAL_ADMIN_PASSWORD=\'%s\'; \n" % admin_password
        if not without_parameter and not get_option(options, 'without_parameter', ''):
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
            cmd += ' --progress-log={}'.format(os.path.join(log_dir, 'bootstrap.log'))
            # set connection mode to direct to avoid obclient issue
            cmd += ' --with-property=obsdk.ob.connection.mode:direct'
            cmd += ' --with-property=ocp.iam.login.client.max-attempts:60'
            cmd += ' --with-property=ocp.iam.login.client.lockout-minutes:1'
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
            if not multi_process_flag and len(cluster_config.servers) > 1:
                break
            if len(cluster_config.servers) > 1 and node_num == 1:
                time.sleep(60)
                node_num += 1

    if success:
        stdio.stop_loading('succeed')
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    plugin_context.set_variable('server_pid', server_pid)
    plugin_context.set_variable('without_parameter', True)
    return plugin_context.return_true(need_bootstrap=True)
