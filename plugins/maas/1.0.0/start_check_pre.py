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

import _errno as err
from tool import set_plugin_context_variables, docker_run_sudo_prefix

success = True
production_mode = False


def start_check_pre(plugin_context, init_check_status=False, first_start=False, precheck=False, *args, **kwargs):

    def check_pass(server, item):
        status = check_status[server]
        if status[item].status == err.CheckStatus.WAIT:
            status[item].status = err.CheckStatus.PASS

    def check_fail(server, item, error, suggests=[]):
        status = check_status[server][item]
        if status.status == err.CheckStatus.WAIT:
            status.error = error
            status.suggests = suggests
            status.status = err.CheckStatus.FAIL

    def wait_2_pass(server):
        status = check_status[server]
        for item in status:
            check_pass(server, item)

    def critical(server, item, error, suggests=[]):
        global success
        success = False
        check_fail(server, item, error, suggests)
        print_with_suggests(error, suggests)

    def error(server, item, _error, suggests=[]):
        global success
        if plugin_context.dev_mode:
            stdio.warn(_error)
        else:
            check_fail(server, item, _error, suggests)
            print_with_suggests(_error, suggests)
            success = False

    def get_success():
        global success
        return success

    def change_success():
        global success
        success = True

    def print_with_suggests(error, suggests=[]):
        stdio.error('{}, {}'.format(error, suggests[0].msg if suggests else ''))

    check_status = {}
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    if len(cluster_config.servers) > 1:
        stdio.error('Maas only support single server')
        return plugin_context.return_false()

    for server in cluster_config.servers:
        check_status[server] = {
            'port': err.CheckStatus(),
            'path': err.CheckStatus(),
        }

    plugin_context.set_variable('start_check_status', check_status)
    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    resource_check_pass = False
    global_config = cluster_config.get_global_conf()
    container_name = global_config['container_name']
    exist_container_server = []
    for server in cluster_config.servers:
        client = plugin_context.clients[server]
        prefix = docker_run_sudo_prefix(client)
        if not precheck:
            ret = client.execute_command(
                '%sdocker ps --filter "name=%s" --format "{{json .}}" | head -1' % (prefix, container_name)).stdout.strip()
            if ret and first_start:
                exist_container_server.append(server.ip)
            if ret:
                container_info = json.loads(ret)
                if container_info.get('State') == 'running':
                    stdio.verbose('%s is running, skip' % server)
                    resource_check_pass = True
                    continue
    if exist_container_server:
        stdio.error('container %s already exists on server %s, please remove it first' % (container_name, ','.join(exist_container_server)))
        return plugin_context.return_false()

    variables_dict = {
        'start_check_status': check_status,
        'check_pass': check_pass,
        'resource_check_pass': resource_check_pass,
        'check_fail': check_fail,
        'wait_2_pass': wait_2_pass,
        'error': error,
        'critical': critical,
        'get_success': get_success,
    }
    change_success()
    set_plugin_context_variables(plugin_context, variables_dict)

    return plugin_context.return_true()

