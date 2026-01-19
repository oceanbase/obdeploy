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

import const
import _errno as err
from tool import Cursor


def init_db(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    global_config = cluster_config.get_global_conf_with_default()
    for comp in const.COMPS_OB:
        if comp in cluster_config.depends:
            ob_servers = cluster_config.get_depend_servers(comp)
            ob_config = cluster_config.get_depend_config(comp, ob_servers[0])
            db_host = ob_servers[0].ip
            db_port = ob_config.get('mysql_port')
            ob_tenant_user = 'root@' + global_config['ob_tenant_name']
            ob_tenant_password = global_config['ob_tenant_password'] or ob_config.get('powerrag_tenant_password')
            cursor = Cursor(ip=db_host, user=ob_tenant_user, port=int(db_port), tenant='', password=ob_tenant_password, stdio=stdio)
            break
    else:
        stdio.error('no ob server found')
        return plugin_context.return_false()

    stdio.start_loading('init db')

    # create database
    global_config = cluster_config.get_global_conf_with_default()
    powerrag_db = global_config.get('powerrag_db', 'powerrag')
    ragflow_db = global_config.get('ragflow_db', 'ragflow')
    doc_oceanbase_dbname = global_config.get('doc_oceanbase_dbname', 'ragflow_doc')
    dify_db = global_config.get('dify_db', 'dify')
    dify_plugin_db = global_config.get('dify_plugin_db', 'dify_plugin')
    celery_db_name = global_config.get('celery_db_name', 'celery_db')

    try:
        create_db_sql = f"""
            CREATE DATABASE IF NOT EXISTS {powerrag_db};
            CREATE DATABASE IF NOT EXISTS {ragflow_db};
            CREATE DATABASE IF NOT EXISTS {doc_oceanbase_dbname};
            CREATE DATABASE IF NOT EXISTS {dify_db};
            CREATE DATABASE IF NOT EXISTS {dify_plugin_db};
            CREATE DATABASE IF NOT EXISTS {celery_db_name};"""

        cursor.execute(create_db_sql)
        cursor.reconnect()

        create_table_sql = f"""
         CREATE TABLE IF NOT EXISTS caches (id bigint(20) NOT NULL AUTO_INCREMENT,
                cache_key varchar(255) NOT NULL,
                cache_value blob NOT NULL,
                expire_time datetime DEFAULT NULL,
                created_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE KEY caches_cache_key_key (cache_key),
                KEY caches_cache_key_idx (cache_key),
                KEY caches_expire_time_idx (expire_time));
        """
        cursor.execute(f'use {dify_db}')
        cursor.execute(create_table_sql)
    except Exception as e:
        stdio.error(f'create database failed, error: {e}')
        return plugin_context.return_false()

    cluster_config = plugin_context.cluster_config
    server = cluster_config.servers[0]
    server_config = cluster_config.get_server_conf(server)
    clients = plugin_context.clients
    client = clients[server]
    bootstrap_path = os.path.join(server_config['home_path'], '.bootstrap')
    client.execute_command('touch %s' % bootstrap_path)

    stdio.stop_loading('succeed')
    return plugin_context.return_true()

