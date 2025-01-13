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

import os
import re
import time

import _errno as err
from _rpm import Version
from tool import Cursor


def upgrade_check(plugin_context, meta_cursor=None, database='meta_database', init_check_status=False, java_check=True, *args, **kwargs):
    def check_pass(item):
        status = check_status[server]
        if status[item].status == err.CheckStatus.WAIT:
            status[item].status = err.CheckStatus.PASS
    def check_fail(item, error, suggests=[]):
        status = check_status[server][item]
        status.error = error
        status.suggests = suggests
        status.status = err.CheckStatus.FAIL
    def wait_2_pass():
        status = check_status[server]
        for item in status:
            check_pass(item)
    def alert(item, error, suggests=[]):
        global success
        stdio.warn(error)
    def error(item, _error, suggests=[]):
        global success
        success = False
        check_fail(item, _error, suggests)
        stdio.error(_error)
    def critical(item, error, suggests=[]):
        global success
        success = False
        check_fail(item, error, suggests)
        stdio.error(error)

    check_status = {}
    repositories = plugin_context.repositories
    options = plugin_context.options
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    plugin_context.set_variable('start_check_status', check_status)
    start_env = plugin_context.get_variable('start_env')

    for server in cluster_config.servers:
        check_status[server] = {
            'check_operation_task': err.CheckStatus(),
            'metadb_version': err.CheckStatus(),
            'java': err.CheckStatus(),
        }

    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    stdio.start_loading('Check before upgrade %s' % cluster_config.name)
    success = True

    for server in cluster_config.servers:
        check_pass('java')
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        try:
            # java version check
            if java_check:
                stdio.verbose('java check ')
                java_bin = server_config.get('java_bin', '/usr/bin/java')
                client.add_env('PATH', '%s/jre/bin:' % server_config['home_path'])
                ret = client.execute_command('%s -version' % java_bin if not server_config.get('launch_user', None) else 'sudo su - %s -c "%s -version"' % (server_config.get('launch_user', None), java_bin))
                stdio.verbose('java version %s' % ret)
                if not ret:
                    critical('java', err.EC_OCP_SERVER_JAVA_NOT_FOUND.format(server=server),
                            [err.SUG_OCP_SERVER_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0')])
                version_pattern = r'version\s+\"(\d+\.\d+\.\d+)(\_\d+)'
                found = re.search(version_pattern, ret.stdout) or re.search(version_pattern, ret.stderr)
                if not found:
                    error('java', err.EC_OCP_SERVER_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'),
                        [err.SUG_OCP_SERVER_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'), ])
                else:
                    java_major_version = found.group(1)
                    stdio.verbose('java_major_version %s' % java_major_version)
                    java_update_version = found.group(2)[1:]
                    stdio.verbose('java_update_version %s' % java_update_version)
                    if Version(java_major_version) != Version('1.8.0') or int(java_update_version) < 161:
                        critical('java', err.EC_OCP_SERVER_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'),
                                [err.SUG_OCP_SERVER_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'), ])
        except Exception as e:
            stdio.error(e)
            error('java', err.EC_OCP_SERVER_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'),
                  [err.SUG_OCP_SERVER_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'), ])
        if not meta_cursor:
            server_config = start_env[server]
            jdbc_url = server_config.get('jdbc_url', None)
            if jdbc_url:
                matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", jdbc_url)
                if not matched:
                    stdio.error('jdbc_url is not valid')
                    return plugin_context.return_false()
                host = matched.group(1)
                port = matched.group(2)[1:]
                meta_user = server_config['ocp_meta_username']
                meta_tenant = server_config['ocp_meta_tenant']['tenant_name']
                meta_password = server_config['ocp_meta_password']
                meta_cursor = Cursor(host, port, meta_user, meta_tenant, meta_password, stdio)
        sql = "select count(*) num from %s.task_instance where state not in ('FAILED', 'SUCCESSFUL', 'ABORTED');" % database
        if meta_cursor.fetchone(sql)['num'] > 0:
            success = False
            error('check_operation_task', err.EC_OCP_SERVER_RUNNING_TASK)
        else:
            check_pass('check_operation_task')

        sql = "select ob_version();"
        v1 = meta_cursor.fetchone(sql)['ob_version()']
        if Version(v1) > Version('2.2.50'):
            check_pass('metadb_version')
        else:
            success = False
            error('metadb_version', err.EC_OCP_SERVER_METADB_VERSION)

        bootstrap_flag = os.path.join(server_config['home_path'], '.bootstrapped')
        if not client.execute_command('ls %s' % bootstrap_flag):
            client.execute_command('touch %s' % bootstrap_flag)

    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()



