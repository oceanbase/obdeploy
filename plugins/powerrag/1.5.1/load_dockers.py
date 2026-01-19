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

import const
from tool import DirectoryUtil, FileUtil, COMMAND_ENV
from ssh import LocalClient


def load_dockers(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    global_config = cluster_config.get_global_conf_with_default()

    stdio.start_loading('install repository for powerrag')
    pkgs_path = global_config.get('pkgs_path') or COMMAND_ENV.get(const.POWERRAG_PKG_HOME)
    if not pkgs_path:
        stdio.stop_loading('fail')
        stdio.error('pkgs_path is not set. please set pkgs_path in global config')
        return plugin_context.return_false()

    repository = kwargs.get('repository')
    repository_dir = repository.repository_dir

    try:
        for item in os.listdir(pkgs_path):
            src_path = os.path.join(pkgs_path, item)
            dst_path = os.path.join(repository_dir, item)

            if item == 'images':
                continue
                
            if os.path.isdir(src_path):
                DirectoryUtil.copy(src_path, dst_path, stdio=stdio)
            else:
                FileUtil.copy(src_path, dst_path, stdio=stdio)
    except Exception as e:
        stdio.stop_loading('fail')
        stdio.error('Failed to copy files: {}'.format(str(e)))
        if str(repository_dir).startswith(str(os.getenv('HOME'))):
            LocalClient.execute_command('rm -rf {}/*'.format(repository_dir), stdio=stdio)
        return plugin_context.return_false()

    stdio.stop_loading('succeed')

    image_files = []
    images_path = os.path.join(pkgs_path, 'images')
    if os.path.exists(images_path) and os.path.isdir(images_path):
        for root, dirs, files in os.walk(images_path):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, images_path)
                image_files.append(relative_path)

    return plugin_context.return_true(image_files=image_files)





