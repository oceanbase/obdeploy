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
import random


def generate_config(plugin_context, source_option="deploy", upgrade=False, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    deploy_name = plugin_context.deploy_name
    global_config = cluster_config.get_global_conf()
    container_name_prefix = global_config.get('container_name') or (deploy_name + '-' + cluster_config.name)
    if source_option == "redeploy" or upgrade:
        container_name_prefix = container_name_prefix[:container_name_prefix.rfind('-')]
    container_name = container_name_prefix + "-" + str(random.randint(0, 999999)).zfill(6)
    if upgrade:
        plugin_context.set_variable('upgrade_container_name', container_name)
    not upgrade and cluster_config.update_global_conf('container_name', container_name, True)

    data_dir = global_config.get('data_dir')
    model_cache_path = global_config.get('model_cache_path')
    docker_image_path = global_config.get('docker_image_path')
    if not model_cache_path:
        model_cache_path = os.path.join(data_dir, "model_cache_path")
        cluster_config.update_global_conf('model_cache_path', model_cache_path, True)
    if not docker_image_path:
        docker_image_path = os.path.join(data_dir, "docker_image_path")
        cluster_config.update_global_conf('docker_image_path', docker_image_path, True)

    return plugin_context.return_true()

