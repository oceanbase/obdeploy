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