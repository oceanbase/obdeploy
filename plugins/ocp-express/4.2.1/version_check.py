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

import _errno as err
from _rpm import Version


def version_check(plugin_context, **kwargs):
    critical = plugin_context.get_variable('check_fail')
    cluster_config = plugin_context.cluster_config
    servers = cluster_config.servers
    stdio = plugin_context.stdio
    versions_check = {
        "oceanbase version": {
            'comps': ['oceanbase', 'oceanbase-ce'],
            'min_version': Version('4.0')
        },
        "obagent version": {
            'comps': ['obagent'],
            'min_version': Version('4.2.1')
        }
    }
    repo_versions = {}
    for repository in plugin_context.repositories:
        repo_versions[repository.name] = repository.version

    for check_item in versions_check:
        for comp in versions_check[check_item]['comps']:
            if comp not in cluster_config.depends:
                continue
            depend_comp_version = repo_versions.get(comp)
            if depend_comp_version is None:
                stdio.verbose('failed to get {} version, skip version check'.format(comp))
                continue
            min_version = versions_check[check_item]['min_version']
            if depend_comp_version < min_version:
                critical(servers[0], check_item, err.EC_OCP_EXPRESS_DEPENDS_COMP_VERSION.format(ocp_express_version=cluster_config.version, comp=comp, comp_version=min_version))
    return plugin_context.return_true()