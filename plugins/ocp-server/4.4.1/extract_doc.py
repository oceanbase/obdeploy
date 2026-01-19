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

def extract_doc(plugin_context, *args, **kwargs):
    start_env = plugin_context.get_variable('start_env')
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    source_option = kwargs.get('source_option')

    if not start_env:
        stdio.verbose('start env is not set')
        return plugin_context.return_false()   

    stdio.start_loading("extract compressed doc")

    extract_doc_result = {}
    for server in cluster_config.servers:
        client = clients[server]
        server_config = start_env[server]
        home_path = server_config['home_path']
        knowledge_path = os.path.join(home_path, 'knowledge')
        compress_file_path = os.path.join(home_path, 'knowledge/ai_assistant_knowledge_base.tar.gz')
        if source_option == 'upgrade':
            delete_cmd = f"rm -rf {knowledge_path}/!(ai_assistant_knowledge_base.tar.gz)"
            if not client.execute_command(delete_cmd):
                stdio.warn("delete ai_assistant_knowledge_base files is failed")


        if not client.execute_command('[ -f {} ]'.format(compress_file_path)):
            stdio.warn('Compressed file not found: {} on server {}'.format(compress_file_path, server))
            extract_doc_result[server] = False
            continue

        find_extract_file_cmd = f'ls {knowledge_path}/KnowledgeBase*'
        if client.execute_command(find_extract_file_cmd).stdout.strip():
            continue
        
        extract_cmd = f'cd {knowledge_path};tar -xzf {compress_file_path}'
        ret = client.execute_command(extract_cmd, timeout=300)
        
        if ret:
            extract_doc_result[server] = True
            stdio.verbose('Successfully extracted {} on server {}'.format(compress_file_path, server))
        else:
            extract_doc_result[server] = False
            stdio.warn('Failed to extract {} on server {}: {}'.format(compress_file_path, server, ret.stderr))
    
    plugin_context.set_variable('extract_doc_result', extract_doc_result)
    
    stdio.stop_loading('succeed')
    return plugin_context.return_true()