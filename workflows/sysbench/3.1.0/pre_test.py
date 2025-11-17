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

import const

def pre_test(plugin_context, workflow, repository, *args, **kwargs):
    sys_namespace = kwargs.get("sys_namespace")
    proxysys_namespace = kwargs.get("proxysys_namespace")
    deploy_config = kwargs.get("deploy_config")
    connect_namespaces = kwargs.get("connect_namespaces")
    opts = plugin_context.options
    target_repository_version = '4.0.0.0' if repository.name == const.COMP_OB_SEEKDB else repository.version

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

    workflow.add_with_component_version_kwargs(const.STAGE_SECOND, 'sysbench', target_repository_version, {"repository": repository}, 'parameter_pre')
    workflow.add_with_component_version_kwargs(const.STAGE_THIRD, 'sysbench', target_repository_version, {"repository": repository, **kwargs}, 'pre_test')
    return plugin_context.return_true()
