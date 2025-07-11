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
import const
from _types import Capacity


def alter_sys_unit(plugin_context, **kwargs):
    need_bootstrap = plugin_context.get_variable('need_bootstrap')
    if not need_bootstrap:
        return plugin_context.return_true()
    cursor = plugin_context.get_return('connect').get_return('cursor')
    for repository in plugin_context.repositories:
        if repository.name == const.COMP_OB_STANDALONE:
            if Capacity(plugin_context.cluster_config.get_global_conf_with_default().get('memory_limit')).bytes < 128 << 30:
                rv = cursor.fetchone("SHOW PARAMETERS  LIKE '__min_full_resource_pool_memory';")
                if rv:
                    __min_full_resource_pool_memory = rv['value']
                    if int(__min_full_resource_pool_memory) > 1073741824:
                        cursor.execute("ALTER SYSTEM SET __min_full_resource_pool_memory=1073741824;", raise_exception=True)
                cursor.execute('use oceanbase;')
                log_disk_rv = cursor.fetchone("select LOG_DISK_SIZE from DBA_OB_UNIT_CONFIGS where name = 'sys_unit_config';", raise_exception=True)
                log_disk_size_with_byte = (int(log_disk_rv['LOG_DISK_SIZE']) - int(__min_full_resource_pool_memory)) + (1 << 30)
                if log_disk_size_with_byte < 2 << 30:
                    log_disk_size_with_byte = 2 << 30
                LOG_DISK_SIZE = Capacity(log_disk_size_with_byte)
                cursor.execute(f"ALTER RESOURCE UNIT sys_unit_config MEMORY_SIZE '1G', LOG_DISK_SIZE '{str(LOG_DISK_SIZE)}';;", raise_exception=True)
                if rv:
                    cursor.execute(f"ALTER SYSTEM SET __min_full_resource_pool_memory={str(__min_full_resource_pool_memory)};", raise_exception=True)
    return plugin_context.return_true()
