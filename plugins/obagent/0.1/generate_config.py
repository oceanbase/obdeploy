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


def generate_config(plugin_context, auto_depend=False, return_generate_keys=False, *args, **kwargs):
    if return_generate_keys:
        return plugin_context.return_true(generate_keys=['ob_monitor_status'])

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    have_depend = False
    depends = ['oceanbase', 'oceanbase-ce']
    server_depends = {}
    generate_configs = {'global': {}}
    plugin_context.set_variable('generate_configs', generate_configs)
    stdio.start_loading('Generate obagent configuration')

    for comp in cluster_config.depends:
        if comp in depends:
            have_depend = True
            for server in cluster_config.servers:
                server_depends[server] = []
                obs_config = cluster_config.get_depend_config(comp, server)
                if obs_config is not None:
                    server_depends[server].append(comp)

    if have_depend:
        for server in cluster_config.servers:
            for comp in depends:
                if comp in server_depends[server]:
                    break
            else:
                cluster_config.update_server_conf(server, 'ob_monitor_status', 'inactive', False)
                generate_configs[server]['ob_monitor_status'] = 'inactive'
    else:
        cluster_config.update_global_conf('ob_monitor_status', 'inactive', False)
        generate_configs['global']['ob_monitor_status'] = 'inactive'
        if auto_depend:
            for depend in depends:
                if cluster_config.add_depend_component(depend):
                    cluster_config.update_global_conf('ob_monitor_status', 'active', False)
                    generate_configs['global']['ob_monitor_status'] = 'active'
                    break

    stdio.stop_loading('succeed')
    plugin_context.return_true()
