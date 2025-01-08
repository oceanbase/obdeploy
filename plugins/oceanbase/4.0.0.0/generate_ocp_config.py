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

from _types import Capacity
import _errno as err


def generate_ocp_config(plugin_context, generate_config_mini=False, generate_check=True, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    global_config = cluster_config.get_global_conf()
    update_global_conf = plugin_context.get_variable('update_global_conf')
    servers_info = plugin_context.get_variable('servers_info')
    added_components = cluster_config.get_deploy_added_components()
    be_depend = cluster_config.be_depends
    has_ocp = 'ocp-express' in added_components and 'ocp-express' in be_depend
    if any([key in global_config for key in ["ocp_meta_tenant", "ocp_meta_db", "ocp_meta_username", "ocp_meta_password"]]):
        has_ocp = True

    # ocp meta db
    SYS_TENANT_LOG_DISK_SCALE = 1
    if has_ocp:
        if 'ocp_meta_tenant_log_disk_size' not in global_config and 'log_disk_size' not in global_config.get('ocp_meta_tenant', {}):
            if generate_config_mini:
                update_global_conf('ocp_meta_tenant_log_disk_size', '6656M')
            else:
                meta_min_log_disk_size = 6 << 30
                expect_log_disk_size = (9 * 512 + 512 * len(cluster_config.servers) + 512 * 3) << 20
                max_available = 0
                sys_memory_size = None
                sys_log_disk_size = None
                if 'sys_tenant' in global_config:
                    if 'memory_size' in global_config['sys_tenant']:
                        sys_memory_size = global_config['sys_tenant']['memory_size']
                    if 'log_disk_size' in global_config['sys_tenant']:
                        sys_log_disk_size = global_config['sys_tenant']['log_disk_size']
                for server in cluster_config.servers:
                    # server_config = cluster_config.get_server_conf_with_default(server)
                    server_info = servers_info.get(server)
                    if not server_info:
                        continue
                    memory_limit = Capacity(server_info['memory_limit']).bytes
                    system_memory = Capacity(server_info['system_memory']).bytes
                    log_disk_size = Capacity(server_info['log_disk_size']).bytes
                    min_pool_memory = Capacity(server_info['min_pool_memory']).bytes
                    if not sys_log_disk_size:
                        if not sys_memory_size:
                            sys_memory_size = max(min_pool_memory, min(int((memory_limit - system_memory) * 0.25), 16 << 30))
                        sys_log_disk_size = sys_memory_size * SYS_TENANT_LOG_DISK_SCALE
                    max_available = max(max_available, log_disk_size - sys_log_disk_size)
                if expect_log_disk_size > max_available:
                    expect_log_disk_size = meta_min_log_disk_size
                if expect_log_disk_size > max_available and generate_check:
                    stdio.error(err.EC_OCP_EXPRESS_META_DB_NOT_ENOUGH_LOG_DISK_AVAILABLE.format(avail=max_available, need=expect_log_disk_size))
                cluster_config.update_global_conf('ocp_meta_tenant_log_disk_size', str(Capacity(expect_log_disk_size, 0)), save=False)
        if generate_config_mini and 'ocp_meta_tenant_memory_size' not in global_config and 'memory_size' not in global_config.get('ocp_meta_tenant', {}):
            update_global_conf('ocp_meta_tenant_memory_size', '1536M')

    return plugin_context.return_true()