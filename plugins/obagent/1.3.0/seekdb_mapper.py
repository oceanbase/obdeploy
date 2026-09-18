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

"""Compatibility helpers for old and new OBAgent SeekDB mappers."""

SEMANTIC_SEEKDB_KEYS = {
    'seekdb_user', 'seekdb_password', 'seekdb_host', 'seekdb_port',
}


def configure_seekdb_mapper(config_mapper):
    """Prefer dedicated SeekDB keys, falling back to legacy monitor fields."""
    if SEMANTIC_SEEKDB_KEYS.issubset(config_mapper):
        for key in ('monitor_user', 'monitor_password', 'sql_port', 'rpc_port'):
            config_mapper.pop(key, None)
        return True
    for key in SEMANTIC_SEEKDB_KEYS:
        config_mapper.pop(key, None)
    config_mapper['monitor_password'] = 'monagent.seekdb.password'
    config_mapper['monitor_user'] = 'monagent.seekdb.user'
    if 'seekdb_monitor_status' not in config_mapper:
        config_mapper['seekdb_monitor_status'] = 'monagent.pipeline.seekdb.status'
    return False


def has_semantic_seekdb_mapper(config_mapper):
    return SEMANTIC_SEEKDB_KEYS.issubset(config_mapper)


def build_config_update_payload(changes, config_mapper):
    """Translate OBD parameter names to OBAgent SDK property names."""
    payload = []
    unmapped = []
    for key, value in changes.items():
        mapped_key = config_mapper.get(key)
        if mapped_key is None:
            unmapped.append(key)
            continue
        payload.append({'key': mapped_key, 'value': value})
    return payload, unmapped


def map_seekdb_start_parameters(parameters, semantic_mapper, host=None):
    """Populate dedicated SeekDB parameters from the legacy OBAgent fields."""
    mapped = dict(parameters)
    if not semantic_mapper:
        return mapped
    aliases = {
        'seekdb_user': 'monitor_user',
        'seekdb_password': 'monitor_password',
        'seekdb_port': 'sql_port',
    }
    for seekdb_key, legacy_key in aliases.items():
        if seekdb_key not in mapped and legacy_key in mapped:
            mapped[seekdb_key] = mapped[legacy_key]
    if 'seekdb_host' not in mapped and host is not None:
        mapped['seekdb_host'] = host
    return mapped


def seekdb_dependency_changes(old_config, new_config, semantic_mapper, host=None):
    """Translate changed SeekDB dependency values to OBAgent configuration keys."""
    old_config = old_config or {}
    new_config = new_config or {}
    if semantic_mapper:
        mapping = {
            'seekdb_user': 'seekdb_monitor_user',
            'seekdb_password': 'seekdb_monitor_password',
            'seekdb_port': 'mysql_port',
        }
    else:
        mapping = {
            'monitor_user': 'seekdb_monitor_user',
            'monitor_password': 'seekdb_monitor_password',
            'sql_port': 'mysql_port',
            'rpc_port': 'rpc_port',
        }
    changes = {}
    for agent_key, seekdb_key in mapping.items():
        if old_config.get(seekdb_key) != new_config.get(seekdb_key):
            changes[agent_key] = new_config.get(seekdb_key)
    if semantic_mapper and host is not None:
        changes['seekdb_host'] = host
    return changes
