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


def upgrade_file_check(plugin_context, route, *args, **kwargs):
    current_repository = kwargs.get('repository')
    repositories = plugin_context.repositories
    options = plugin_context.options
    stdio = plugin_context.stdio

    skip_check = getattr(options, 'skip_check', False)

    can_skip = ['upgrade_checker.py', 'upgrade_post_checker.py']
    large_upgrade_need = ['upgrade_pre.py', 'upgrade_post.py']
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