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

import const
def pre_test(plugin_context, workflow, repository, *args, **kwargs):
    sys_namespace = kwargs.get("sys_namespace")
    proxysys_namespace = kwargs.get("proxysys_namespace")
    deploy_config = kwargs.get("deploy_config")
    connect_namespaces = kwargs.get("connect_namespaces")
    opts = plugin_context.options

    if repository.name in const.COMPS_ODP:
        for component_name in deploy_config.components:
            if component_name in const.COMPS_OB:
                ob_cluster_config = deploy_config.components[component_name]
                sys_namespace.set_variable("connect_proxysys", False)
                sys_namespace.set_variable("user", "root")
                sys_namespace.set_variable("password", ob_cluster_config.get_global_conf().get('root_password', ''))
                sys_namespace.set_variable("target_server",  opts.test_server)
                break
        proxysys_namespace.set_variable("component_name", repository)
        proxysys_namespace.set_variable("target_server", opts.test_server)
        workflow.add_with_component_version_kwargs(const.STAGE_FIRST, repository.name, repository.version, {"spacename": proxysys_namespace.spacename}, 'connect')
        connect_namespaces.append(proxysys_namespace)
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, repository.name, repository.version, {"spacename": sys_namespace.spacename}, 'connect')
    connect_namespaces.append(sys_namespace)

    workflow.add_with_component_version_kwargs(const.STAGE_SECOND, 'sysbench', repository.version, {"repository": repository}, 'parameter_pre')
    workflow.add_with_component_version_kwargs(const.STAGE_THIRD, 'sysbench', repository.version, {"repository": repository, **kwargs}, 'pre_test')
    return plugin_context.return_true()
