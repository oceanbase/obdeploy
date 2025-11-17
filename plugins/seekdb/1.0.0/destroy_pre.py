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

from ssh import get_root_permission_client, is_root_user
from _errno import EC_OBSERVER_DISABLE_AUTOSTART

def destroy_pre(plugin_context, *args, **kwargs):
    plugin_context.set_variable("clean_dirs", ['data_dir', 'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir'])
    return plugin_context.return_true()