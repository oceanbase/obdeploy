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

import time

from _deploy import ObserverIdentity, ObserverIdentityError


VERIFY_OBSERVER_IDENTITY_TIMEOUT = 900


def verify_observer_identity(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    try:
        marker = ObserverIdentity.marker(cluster_config)
    except ObserverIdentityError as e:
        stdio.error(str(e))
        return plugin_context.return_false()
    if not marker:
        return plugin_context.return_true()

    connect_ret = plugin_context.get_return('connect')
    cursor = connect_ret.get_return('cursor') if connect_ret else None
    if not cursor:
        stdio.error('missing observer connection while verifying standalone observer identity')
        return plugin_context.return_false()

    stdio.start_loading('Verify observer identity')
    deadline = time.time() + VERIFY_OBSERVER_IDENTITY_TIMEOUT
    while True:
        servers = cursor.fetchall(
            'select * from oceanbase.__all_server',
            raise_exception=False, exc_level='verbose')
        if servers and all([server.get('status') for server in servers]):
            break
        if time.time() >= deadline:
            stdio.stop_loading('fail')
            stdio.error('timed out after %s seconds while verifying standalone observer identity' %
                        VERIFY_OBSERVER_IDENTITY_TIMEOUT)
            return plugin_context.return_false()
        time.sleep(1)
    try:
        ObserverIdentity.verify(cluster_config, servers)
    except ObserverIdentityError as e:
        stdio.stop_loading('fail')
        stdio.error(str(e))
        return plugin_context.return_false()
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
