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
import shutil


def clean_ca(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    deploy_name = plugin_context.cluster_config.deploy_name
    work_dir = '/tmp/.seekdb_ca'
    
    cluster_work_dir = os.path.join(work_dir, deploy_name)
    
    if os.path.exists(cluster_work_dir):
        try:
            shutil.rmtree(cluster_work_dir)
            stdio.verbose('Successfully removed CA directory for cluster {}: {}'.format(deploy_name, cluster_work_dir))
                
        except Exception as e:
            stdio.warn('Failed to remove CA directory: {}. Error: {}'.format(cluster_work_dir, str(e)))
    else:
        stdio.verbose('CA directory {} does not exist, skip cleaning.'.format(cluster_work_dir))

    return plugin_context.return_true()
