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


def init_pre(plugin_context, env, *args, **kwargs):
    if 'init_sql_files' in env and env['init_sql_files']:
        init_sql = env['init_sql_files'].split(',')
    else:
        exec_init = 'init.sql'
        exec_init_ce = 'init_for_ce.sql'
        exec_init_user = 'init_user.sql|root@mysql|test'
        exec_init_user_for_oracle = 'init_user_oracle.sql|SYS@oracle|SYS'
        if env['is_business']:
            init_sql = [exec_init, exec_init_user_for_oracle, exec_init_user]
        else:
            init_sql = [exec_init_ce, exec_init_user]
    plugin_context.set_variable('init_sql', init_sql)
    return plugin_context.return_true()
