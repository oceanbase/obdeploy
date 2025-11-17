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

from const import COMP_OB_SEEKDB

def init_pre(plugin_context, env, *args, **kwargs):
    repository = kwargs.get("repository")
    if 'init_sql_files' in env and env['init_sql_files']:
        init_sql = env['init_sql_files'].split(',')
    else:
        exec_init = 'init.sql'
        exec_init_ce = 'init_for_ce.sql'
        if repository.name == COMP_OB_SEEKDB:
            init_sql = [exec_init]
        else:
            exec_init_user = 'init_user.sql|root@mysql|test'
            exec_init_user_for_oracle = 'init_user_oracle.sql|SYS@oracle|SYS'
        if env['is_business']:
            init_sql = [exec_init, exec_init_user_for_oracle, exec_init_user]
        elif repository.name != COMP_OB_SEEKDB:
            init_sql = [exec_init_ce, exec_init_user]
    plugin_context.set_variable('init_sql', init_sql)
    return plugin_context.return_true()