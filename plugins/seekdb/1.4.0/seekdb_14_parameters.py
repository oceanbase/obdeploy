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

"""SeekDB 1.4 parameter compatibility boundaries shared by OBD plugins."""

from _types import effective_memory_available, effective_memory_total

MIN_AUTO_MEMORY_BUDGET_BYTES = 1 << 30


def automatic_memory_budget(total_memory):
    """Mirror SeekDB's effective sizing rule for memory_budget=0M."""
    eighty_percent = int(total_memory * 80 / 100)
    reserve_one_gib = total_memory - MIN_AUTO_MEMORY_BUDGET_BYTES
    return max(MIN_AUTO_MEMORY_BUDGET_BYTES, min(eighty_percent, reserve_one_gib))


def _read_cgroup_memory(client):
    try:
        ret = client.execute_command(
            'if [ -r /sys/fs/cgroup/memory.max ]; then '
            'cat /sys/fs/cgroup/memory.max; cat /sys/fs/cgroup/memory.current; '
            'elif [ -r /sys/fs/cgroup/memory/memory.limit_in_bytes ]; then '
            'cat /sys/fs/cgroup/memory/memory.limit_in_bytes; '
            'cat /sys/fs/cgroup/memory/memory.usage_in_bytes; fi')
        values = str(ret.stdout).splitlines() if ret and ret.stdout else []
    except Exception:
        values = []
    return (
        values[0].strip() if values else None,
        values[1].strip() if len(values) > 1 else None,
    )


def detect_effective_memory_total(client, physical_total):
    """Apply the host's cgroup v2/v1 limit to a physical memory value."""
    cgroup_limit, _ = _read_cgroup_memory(client)
    return effective_memory_total(physical_total, cgroup_limit)


def detect_effective_memory_stats(client, physical_total, host_available):
    """Return effective total and currently available container memory."""
    cgroup_limit, cgroup_usage = _read_cgroup_memory(client)
    return (
        effective_memory_total(physical_total, cgroup_limit),
        effective_memory_available(
            physical_total, host_available, cgroup_limit, cgroup_usage),
    )

LEGACY_MEMORY_PARAMETERS = {
    '_memory_budget', 'memory_limit', 'memory_hard_limit', 'system_memory',
    'memory_limit_percentage',
}

# Parameters exposed by the legacy SeekDB OBD plugin but absent from the 1.4
# server parameter catalog. This list was checked against the 1.4 RC
# V$OB_PARAMETERS catalog and ob_parameter_seed.ipp.
REMOVED_SERVER_PARAMETERS = {
    '__min_full_resource_pool_memory', 'autoinc_cache_refresh_interval',
    'backup_data_file_size', 'bf_cache_priority',
    'data_storage_error_tolerance_time', 'default_compress',
    'enable_ob_ratelimit', 'enable_sql_audit', 'enable_syslog_recycle',
    'enable_syslog_wf', 'enable_upgrade_mode', 'fuse_row_cache_priority',
    'high_priority_net_thread_count', 'ignore_replay_checksum_error',
    'index_block_cache_priority', 'large_query_threshold',
    'large_query_worker_percentage', 'leak_mod_to_check',
    'location_cache_refresh_min_interval', 'log_archive_concurrency',
    'log_dir', 'ls_meta_table_check_interval', 'memory_reserved',
    'memstore_limit_percentage', 'ob_ratelimit_stat_period',
    'opt_tab_stat_cache_priority', 'rdma_io_thread_count',
    'redundancy_level', 'resource_hard_limit', 'resource_soft_limit',
    'sql_login_thread_count', 'ssl_external_kms_info',
    'sys_bkgd_migration_change_member_list_timeout',
    'sys_bkgd_migration_retry_num', 'sys_cpu_limit_trigger',
    'tablet_ls_cache_priority', 'tenant_task_queue_size',
    'trx_2pc_retry_interval', 'use_large_pages',
    'user_block_cache_priority', 'user_row_cache_priority',
    'user_tab_col_stat_cache_priority',
    'virtual_table_location_cache_expire_time',
}

UNSUPPORTED_CONFIGURATION_PARAMETERS = (
    LEGACY_MEMORY_PARAMETERS | REMOVED_SERVER_PARAMETERS
)


def get_unsupported_parameters(user_config):
    user_keys = set((user_config or {}).keys())
    return (
        sorted(LEGACY_MEMORY_PARAMETERS.intersection(user_keys)),
        sorted(REMOVED_SERVER_PARAMETERS.intersection(user_keys)),
    )
