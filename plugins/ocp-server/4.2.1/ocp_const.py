# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.


from __future__ import absolute_import, division, print_function


def ocp_const(plugin_context, start_check_status, **kwargs):
    EXCLUDE_KEYS = [
        "home_path", "cluster_name", "ob_cluster_id", "admin_password", "memory_xms", "memory_xmx", "ocpCPU",
        "root_sys_password", "server_addresses", "system_password", "memory_size", 'jdbc_url', 'jdbc_username',
        'jdbc_password', "ocp_meta_tenant", "ocp_meta_tenant_log_disk_size", "ocp_meta_username", "ocp_meta_password",

    ]

    CONFIG_MAPPER = {
        "port": "server.port",
        "session_timeout": "server.servlet.session.timeout",
        "login_encrypt_enabled": "ocp.login.encryption.enabled",
        "login_encrypt_public_key": "ocp.login.encryption.public-key",
        "login_encrypt_private_key": "ocp.login.encryption.private-key",
        "enable_basic_auth": "ocp.iam.auth.basic.enabled",
        "enable_csrf": "ocp.iam.csrf.enabled",
        "vault_key": "ocp.express.vault.secret-key",
        "druid_name": "spring.datasource.druid.name",
        "druid_init_size": "spring.datasource.druid.initial-size",
        "druid_min_idle": "spring.datasource.druid.min-idle",
        "druid_max_active": "spring.datasource.druid.max-active",
        "druid_test_while_idle": "spring.datasource.druid.test-while-idle",
        "druid_validation_query": "spring.datasource.druid.validation-query",
        "druid_max_wait": "spring.datasource.druid.max-wait",
        "druid_keep_alive": "spring.datasource.druid.keep-alive",
        "logging_pattern_console": "logging.pattern.console",
        "logging_pattern_file": "logging.pattern.file",
        "logging_file_name": "logging.file.name",
        "logging_file_max_size": "logging.file.max-size",
        "logging_file_total_size_cap": "logging.file.total-size-cap",
        "logging_file_clean_when_start": "logging.file.clean-history-on-start",
        "logging_file_max_history": "logging.file.max-history",
        "logging_level_web": "logging.level.web",
        "default_timezone": "ocp.system.default.timezone",
        "default_lang": "ocp.system.default.language",
        "obsdk_sql_query_limit": "ocp.monitor.collect.obsdk.sql-query-row-limit",
        "exporter_inactive_threshold": "ocp.monitor.exporter.inactive.threshold.seconds",
        "monitor_collect_interval": "ocp.metric.collect.interval.second",
        "montior_retention_days": "ocp.monitor.data.retention-days",
        "obsdk_cache_size": "obsdk.connector.holder.capacity",
        "obsdk_max_idle": "obsdk.connector.max-idle.seconds",
        "obsdk_cleanup_period": "obsdk.connector.cleanup.period.seconds",
        "obsdk_print_sql": "obsdk.print.sql",
        "obsdk_slow_query_threshold": "obsdk.slow.query.threshold.millis",
        "obsdk_init_timeout": "obsdk.connector.init.timeout.millis",
        "obsdk_init_core_size": "obsdk.connector.init.executor.thread-count",
        "obsdk_global_timeout": "obsdk.operation.global.timeout.millis",
        "obsdk_connect_timeout": "obsdk.socket.connect.timeout.millis",
        "obsdk_read_timeout": "obsdk.socket.read.timeout.millis"
    }

    plugin_context.set_variable('EXCLUDE_KEYS', EXCLUDE_KEYS)
    plugin_context.set_variable('CONFIG_MAPPER', CONFIG_MAPPER)
    return plugin_context.return_true()