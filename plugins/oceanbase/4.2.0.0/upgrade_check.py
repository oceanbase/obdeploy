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

import os

from _rpm import Version
from _stdio import FormatText


def upgrade_check(plugin_context, current_repository, upgrade_repositories, route, cursor, *args, **kwargs):
    options = plugin_context.options
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    skip_check = getattr(options, 'skip_check', False)
    ignore_standby = getattr(options, 'ignore_standby', False)

    if not ignore_standby:
        standby_tenants = plugin_context.get_variable('standby_tenants')
        need_upgrade_standbys = []
        for standby in standby_tenants:
            standby_deploy_name = standby[0]
            standby_version = standby[2]
            if standby_deploy_name not in need_upgrade_standbys:
                if Version(standby_version) <= current_repository.version:
                    need_upgrade_standbys.append(standby_deploy_name)
        if need_upgrade_standbys:
            stdio.warn('Found standby tenant in {0}, upgrade current cluster may cause data synchronization error with standby tenants'.format(need_upgrade_standbys))
            stdio.warn(FormatText.success('Recommendation: upgrade clusters {0} first or switchover standby tenant to primary tenant or you can rerun upgrade with "--ignore-standby" option if you want to proceed despite the risks'.format(need_upgrade_standbys)))
            stdio.error('Check standby tenant version error.')
            return False

    can_skip = ['upgrade_checker.py', 'upgrade_post_checker.py']
    large_upgrade_need = ['upgrade_pre.py', 'upgrade_post.py']
    zones = set()
    for server in cluster_config.servers:
        config = cluster_config.get_server_conf_with_default(server)
        zone = config['zone']
        zones.add(zone)

    if len(zones) > 2:
        tenants = cursor.fetchall("""select a.tenant_name, a.tenant_id, group_concat(zone_list separator ';') as zone_list from oceanbase.DBA_OB_TENANTS as a left join (
                                  select zone_list, tenant_id from oceanbase.DBA_OB_RESOURCE_POOLS ) as b 
                                  on a.tenant_id = b.tenant_id where a.tenant_name not like 'META$%' group by tenant_id""")
        if tenants is False:
            return
        for tenant in tenants:
            zone_list = tenant.get('zone_list', '').split(';')
            if len(set(zone_list)) < 3:
                stdio.error('Tenant %s does not meet rolling upgrade conditions (zone number greater than 2).' % tenant.get('tenant_name'))
                return

    succeed = True
    n, i = len(route), 1
    while i < n:
        cant_use = False
        node = route[i]
        repository = upgrade_repositories[i]
        stdio.verbose('route %s-%s use %s. file check begin.' % (node.get('version'), node.get('release'), repository))
        script_dir = os.path.join(repository.repository_dir, 'etc/direct_upgrade') if node.get('direct_upgrade') else os.path.join(repository.repository_dir, 'etc')
        if skip_check is False:
            for name in can_skip:
                path = os.path.join(script_dir, name)
                if not os.path.isfile(path):
                    succeed = False
                    stdio.error('No such file: %s . You can use --skip-check to skip this check or --disable to ban this package' % path)

        if repository.version != current_repository.version:
            for name in large_upgrade_need:
                path = os.path.join(script_dir, name)
                if not os.path.isfile(path):
                    cant_use = True
                    succeed = False
                    stdio.error('No such file: %s .' % path)
        if cant_use:
            stdio.error('%s cannot be used for the upgrade. You can use the --disable option to disable the image.' % repository)
        i += 1

    if succeed:
        plugin_context.return_true()
