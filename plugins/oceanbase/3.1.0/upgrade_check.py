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


def upgrade_check(plugin_context, current_repository, repositories, route, cursor, *args, **kwargs):
    def execute_sql(query, args=None, one=True, error=True):
        msg = query % tuple(args) if args is not None else query
        stdio.verbose("query: %s. args: %s" % (query, args))
        try:
            stdio.verbose('execute sql: %s' % msg)
            cursor.execute(query, args)
            result = cursor.fetchone() if one else cursor.fetchall()
            result and stdio.verbose(result)
            return result
        except:
            msg = 'execute sql exception: %s' % msg if error else ''
            stdio.exception(msg)
        return False

    options = plugin_context.options
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config

    skip_check = getattr(options, 'skip_check', False)

    can_skip = ['upgrade_checker.py', 'upgrade_post_checker.py']
    large_upgrade_need = ['upgrade_pre.py', 'upgrade_post.py']
    zones = set()
    for server in cluster_config.servers:
        config = cluster_config.get_server_conf_with_default(server)
        zone = config['zone']
        zones.add(zone)
    
    if len(zones) > 2:
        tenants = execute_sql('select * from oceanbase.gv$tenant', one=False)
        for tenant in tenants:
            zone_list = tenant.get('zone_list', '').split(';')
            if len(zone_list) < 3:
                stdio.error('Tenant %s does not meet rolling upgrade conditions (zone number greater than 2).' % tenant.get('tenant_name'))
                return

    succeed = True
    n, i = len(route), 1
    while i < n:
        cant_use = False
        node = route[i]
        repository = repositories[i]
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
