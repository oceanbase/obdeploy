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
            'min_version': Version('1.3.0')
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