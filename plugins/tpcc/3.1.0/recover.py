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

from time import sleep


def recover(plugin_context, cursor, odp_cursor, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if value is None:
            value = default
        return value

    def execute(cursor, query, args=None):
        msg = query % tuple(args) if args is not None else query
        stdio.verbose('execute sql: %s' % msg)
        stdio.verbose("query: %s. args: %s" % (query, args))
        try:
            cursor.execute(query, args)
            return cursor.fetchone()
        except:
            msg = 'execute sql exception: %s' % msg
            stdio.exception(msg)
            raise Exception(msg)

    global stdio
    stdio = plugin_context.stdio
    options = plugin_context.options
    optimization = get_option('optimization') > 0
    tenant_name = get_option('tenant', 'test')

    tenant_variables_done = kwargs.get('tenant_variables_done', [])
    system_configs_done = kwargs.get('system_configs_done', [])
    odp_configs_done = kwargs.get('odp_configs_done', [])
    tenant_id = kwargs.get('tenant_id')
    stdio.verbose(cursor)
    stdio.verbose(vars(cursor))
    if optimization:
        stdio.start_loading('Recover')
        update_sql_t = "ALTER TENANT %s SET VARIABLES %%s = %%%%s" % tenant_name
        tenant_q = ' tenant="%s"' % tenant_name
        if not tenant_id:
            sql = "select * from oceanbase.gv$tenant where tenant_name = %s"
            stdio.verbose('execute sql: %s' % (sql % tenant_name))
            cursor.execute(sql, [tenant_name])
            tenant_meta = cursor.fetchone()
            if not tenant_meta:
                stdio.error('Tenant %s not exists. Use `obd cluster tenant create` to create tenant.' % tenant_name)
                return

        for config in tenant_variables_done[::-1]:
            if config[3](config[1], config[2]):
                sql = update_sql_t % config[0]
                execute(cursor, sql, [config[2]])
        for config in system_configs_done[::-1]:
            if config[0] == 'sleep':
                sleep(config[1])
                continue
            if config[3](config[1], config[2]):
                sql = 'alter system set %s=%%s' % config[0]
                if config[4]:
                    sql += tenant_q
                execute(cursor, sql, [config[2]])

        if odp_cursor:
            for config in odp_configs_done[::-1]:
                if config[3](config[1], config[2]):
                    sql = 'alter proxyconfig set %s=%%s' % config[0]
                    execute(odp_cursor, sql, [config[2]])
        stdio.stop_loading('succeed')
    return plugin_context.return_true()
