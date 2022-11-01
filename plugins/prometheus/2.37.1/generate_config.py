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


def generate_config(plugin_context, deploy_config, auto_depend=False, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    success = True
    have_depend = False
    depends = ['obagent']
    stdio.start_loading('Generate prometheus configuration')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        if not server_config.get('home_path'):
            stdio.error("prometheus %s: missing configuration 'home_path' in configuration file" % server)
            success = False
    if not success:
        stdio.stop_loading('fail')
        return

    for comp in cluster_config.depends:
        if comp in depends:
            have_depend = True

    if not have_depend and auto_depend:
        for depend in depends:
            if cluster_config.add_depend_component(depend):
                break
    stdio.stop_loading('succeed')
    plugin_context.return_true()