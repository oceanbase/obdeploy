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

import hashlib
import os


def load_snap(plugin_context, snap_config, env={}, *args, **kwargs):
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config

    snap_hash = env.get('%s.snap_hash' % cluster_config.name)
    if not snap_hash:
        m_sum = hashlib.md5()
        m_sum.update(str(hash(cluster_config)).encode('utf-8'))
        m_sum.update(str(hash(snap_config)).encode('utf-8'))
        if 'init_file_md5' in env:
            m_sum.update(str(env['init_file_md5']).encode('utf-8'))
        snap_hash = m_sum.hexdigest()

    load_cmd_temp = '''sanp_path='{sanp_path}'
tar_path='{tar_path}'
if [ -d $tar_path ]
then
for fn in `ls $tar_path`
do
    path=$tar_path/$fn
    if [ -L $path ]; then
        path=$(readlink $path)
        rm -fr $path
    fi
done
fi
rm -fr $tar_path
cd /
for fn in `ls $sanp_path`
do
    tar -I zstd -xf $sanp_path/$fn
done'''
    concurrent_executor = plugin_context.concurrent_executor
    concurrent_executor.workers = len(cluster_config.servers)
    for server in cluster_config.servers:
        home_path = cluster_config.get_server_conf(server).get('home_path')
        snap_path = os.path.join(home_path, snap_hash)
        client = clients[server]
        stdio.start_loading('%s load snap' % (server))
        for fn in snap_config.clean:
            concurrent_executor.add_task(client, 'rm -fr {path}; mkdir -p {path}'.format(path=os.path.join(home_path, fn)), timeout=-1)
                
        if client.execute_command('[ -d %s ]' % snap_path):
            concurrent_executor.add_task(client, load_cmd_temp.format(sanp_path=snap_path, tar_path=os.path.join(home_path, fn)), timeout=-1)
        else:
            stdio.verbose('%s snap not exist: %s' % (server, snap_path))
        
    stdio.print('%s create snap' % cluster_config.name)
    if concurrent_executor.size():
        stdio.start_loading('%s create snap' % cluster_config.name)
        results = concurrent_executor.submit()
        if not all(results):
            for ret in results:
                if not ret:
                    stdio.error('(%s) %s' % (ret.client, ret.stdout))
            stdio.stop_loading('fail')
            return
        env['load_snap'] = True

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
