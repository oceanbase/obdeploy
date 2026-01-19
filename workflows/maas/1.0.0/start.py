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

import os.path

from const import STAGE_FIRST


def start(plugin_context, workflow, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    if getattr(options, 'skip_cluster_status_check', False):
        image_name = cluster_config.image_name + ':' + cluster_config.tag
        runtime_image_name = image_name.replace('ob-maas-backend', 'ob-maas-runtime')
        global_config = cluster_config.get_original_global_conf()
        workflow.add_with_component_version_kwargs(STAGE_FIRST, 'general', '0.1', {'save_dir': global_config['docker_image_path'], 'image_name': runtime_image_name}, 'save_image')
    workflow.add(STAGE_FIRST, 'start_check_pre', 'start')
    return plugin_context.return_true()

