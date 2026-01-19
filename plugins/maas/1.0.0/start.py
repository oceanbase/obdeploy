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

import glob
import json
import os
import time

from _arch import getBaseArch
from tool import docker_run_sudo_prefix


def start(plugin_context, upgrade=False, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    for repository in plugin_context.repositories:
        if repository.name == cluster_config.name:
            break
    stdio.start_loading('Start maas')

    global_config = cluster_config.get_global_conf()
    container_name = plugin_context.get_variable('upgrade_container_name') if upgrade else global_config.get('container_name')
    
    for server in cluster_config.servers:
        client = clients[server]
        prefix = docker_run_sudo_prefix(client)
        ret = client.execute_command('%sdocker ps -a --filter "name=%s" --format "{{json .}}" | head -1' % (prefix, container_name)).stdout.strip()
        if ret:
            container_info = json.loads(ret)
            if container_info.get('State') == 'running':
                stdio.verbose('%s is running, skip' % server)
                continue
            elif container_info.get('State') == 'exited':
                stdio.verbose('%s is exited, start %s' % (server, container_name))
                if not client.execute_command('%sdocker start %s' % (prefix, container_name)):
                    stdio.error('start %s failed' % container_name)
                    return plugin_context.return_false()
        else:
            server_config = cluster_config.get_server_conf(server)
            extra_docker_args = []
            basearch = getBaseArch()
            if 'x86_64' in basearch:
                stdio.verbose('Detected x86_64 architecture. Configuring for NVIDIA GPU.')
                if server_config.get('all_gpus'):
                    extra_docker_args = ["--gpus", "all"]
            elif 'aarch64' in basearch:
                stdio.verbose('Detected aarch64 architecture. Configuring for Huawei NPU (Ascend).')
                # Find NPU devices
                npu_device_patterns = [
                    "/dev/davinci*",
                    "/dev/devmm_svm",
                    "/dev/hisi_hdc",
                    "/dev/davinci_manager"
                ]
                npu_devices = []
                for pattern in npu_device_patterns:
                    npu_devices.extend(glob.glob(pattern))

                for device in npu_devices:
                    extra_docker_args.extend(["--device", device])

                extra_docker_args.extend([
                    "-v", "/usr/local/bin/:/usr/local/bin/",
                    "-v", "/usr/local/sbin/:/usr/local/sbin/",
                    "-v", "/usr/local/sbin/npu-smi:/usr/local/sbin/npu-smi",
                    "-v", "/usr/local/dcmi:/usr/local/dcmi",
                    "-v", "/usr/local/Ascend/driver/:/usr/local/Ascend/driver/",
                    "-v", "/etc/ascend_install.info:/etc/ascend_install.info",
                ])

            model_cache_path = server_config.get('model_cache_path')
            docker_image_path = server_config.get('docker_image_path')
            port = server_config.get('port', 8001)
            prometheus_host_port = server_config.get('prometheus_host_port', 9090)
            data_dir = server_config.get('data_dir')
            extra_docker_args.extend([
                "-v", f"{data_dir}:{data_dir}",
                "-v", "/var/run/docker.sock:/var/run/docker.sock",
                "-v", "/usr/bin/docker:/usr/bin/docker",
                "-v", "/usr/share/zoneinfo:/usr/share/zoneinfo:ro",
                "-v", f"{model_cache_path}:{model_cache_path}",
                "-v", f"{docker_image_path}:{docker_image_path}",
                "-e", f"MODEL_CACHE_PATH={model_cache_path}",
                "-e", f"DOCKER_IMAGE_PATH={docker_image_path}",
            ])

            image_name = cluster_config.image_name + ':' + repository.version

            cmd = f"{prefix}docker run -d --name {container_name} -e PROMETHEUS_LOCAL_PORT={prometheus_host_port} -e MAAS_SERVICE_LOCAL_PORT={port} -e TZ=Asia/Shanghai --network host "
            cmd += ' '.join(extra_docker_args)
            cmd += f" {image_name}"
            
            if not client.execute_command(cmd):
                stdio.stop_loading('fail')
                stdio.error('%s: start %s failed' % (server, container_name))
                return plugin_context.return_false()
        time.sleep(5)

    if upgrade:
        cluster_config.update_global_conf('container_name', container_name, True)

    stdio.stop_loading('succeed')
    return plugin_context.return_true()

