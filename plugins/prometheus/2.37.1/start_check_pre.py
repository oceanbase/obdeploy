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
import _errno as err


stdio = None
success = True


def start_check_pre(plugin_context, init_check_status=False, work_dir_check=False, *args, **kwargs):
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
            check_pass(server ,item)

    def critical(server, item, error, suggests=[]):
        global success
        success = False
        check_fail(server, item, error, suggests)
        print_with_suggests(error, suggests)
        stdio.error(error)

    def get_success():
        global success
        return success


    def print_with_suggests(error, suggests=[]):
        stdio.error('{}, {}'.format(error, suggests[0].msg if suggests else ''))

    plugin_context.set_variable('check_pass', check_pass)
    plugin_context.set_variable('check_fail', check_fail)
    plugin_context.set_variable('wait_2_pass', wait_2_pass)
    plugin_context.set_variable('critical', critical)
    plugin_context.set_variable('get_success', get_success)

    cluster_config = plugin_context.cluster_config
    global stdio
    stdio = plugin_context.stdio
    check_status = {}
    plugin_context.set_variable('start_check_status', check_status)
    depends = ['obagent']
    for server in cluster_config.servers:
        check_status[server] = {
            'port': err.CheckStatus(),
        }
        if work_dir_check:
            check_status[server]['dir'] = err.CheckStatus()

    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    username = None
    password = None

    for comp in cluster_config.depends:
        if comp in depends:
            for server in cluster_config.get_depend_servers(comp):
                obagent_config = cluster_config.get_depend_config(comp, server)
                check_ret = True
                if username is not None and username != obagent_config.get('http_basic_auth_user', ''):
                    check_ret = False
                if password is not None and password != obagent_config.get('http_basic_auth_password', ''):
                    check_ret = False
                if not check_ret:
                    stdio.warn('The http basic auth of obagent is inconsistent, and some targets in the scrape_configs may not work.')
                    break
                password = obagent_config.get('http_basic_auth_password', '')
                username = obagent_config.get('http_basic_auth_user', '')
    return plugin_context.return_true()