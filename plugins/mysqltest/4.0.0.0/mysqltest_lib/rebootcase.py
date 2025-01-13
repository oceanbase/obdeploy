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
reboot_cases=['zz_alter_sys',
              'create2',
 'dump',
 'calc_phy_plan_size',
 'charset_and_collation',
 'kill',
 'killquery',
 'read_config',
 'select_frozen_version',
 'create_index',
 'create_syntax',
 'bigvarchar_trans',
 'bigvarchar_gmt',
 'bigvarchar_1.25M_idx',
 'expire_bug5328455',
 'expire_trx',
 'expire_index_trxdel',
 'binary_protocol',
 'error_msg',
 'index_basic',
 'index_quick',
 'index_01_create_cols',
 'teststricttime',
 'step_merge_num',
 'index_03_create_type',
 'index_32_trx_rowkey_range_in',
 'many_number_pk_large_than_58',
 'virtual_table',
 'merge_delete2',
 'nested_loop_join_cache',
 'nested_loop_join_cache_joinon',
 'alter_table',
 'expire_trx_modifydata',
 'jdbc_ps_all_statement',
 'expire_trx_nop',
 'show',
 'ps_lose_update_tr',
 'join',
 'table_consistent_mode',
 'table_only_have_rowkey',
 'resource_pool',
 'bigvarchar_pri',
 'bigvarchar_1.25M_time',
 'testlimit_index',
 'trx_expire_step_merge_num',
 'trx_expire_alter_drop_add_col',
 'trx_expire_idx_unique_merge_step',
 'update_delete_many_data',
 'bigvarchar_prejoin',
 'zaddlmajor_gt64times',
 'zcreate10000table',
 'zcreateindex1000',
 'sql_audit',
 'trx_expire_more_oper',
 'expire_trx_replace2',
 'expire_trx2',
 'zhuweng_thinking',
 'lower_case_0',
 'lower_case_1',
 'lower_case_2',
  'create_tenant_sys_var_option',
 'show_tables',
 'information_schema',
 'index_11_dml_after_major_freeze',
 'update_delete_limit_merge_idx_part',
 'idx_with_const_expr26to30',
 'idx_unique_many_idx_one_ins',
 'inner_table.inner_table_overall',
 'inner_table.all_virtual_partition_sstable_image_info',
 'inner_table.all_virtual_sql_plan_statistics',
 'inner_table.all_virtual_tenant_memstore_allocator_info',
 'information_schema.information_schema_part',
 'information_schema',
 'information_schema.information_schema_select',
 'information_schema.select_in_sys_and_normal_tenant',
 'information_schema.information_schema_select_one_table',
 'parallel_create_table',
 'inner_table.all_partition_sstable_merge_info',
 'tenant.resource_pool_new',
 'charset.jp_create_db_utf8',
 'information_schema.information_schema_desc',
 'plan_base_line_for_schema',
 'partition.partition_innodb',
 'schema_bugs',
 'schema_bugs2',
 'schema_bug#8767674',
 'schema_bug#8872003',
 'spm.outline_no_hint_check_hit',
 'spm.outline_concurrent',
 'spm.outline_use',
 'default_system_variable',
 'ddl_on_core_table',
 'time_zone.time_zone_variable',
 'ddl_on_core_table_supplement',
 'schema_change_merge',
 'visible_index',
 'progressive_merge',
 'information_schema.information_schema2',
 'rebalance_map',
 'alipay_dns_4ob',
 'replace.re_string_range_set',
 'information_schema_part_oceanbase',
 'ddl_on_inner_table',
 'show_databases_oracle',
 'expr.userenv_func_by_design_oracle'
 'part_mg.alter_tablegroup_timeout',
 'part_mg.alter_tablegroup_timeout1',
 'part_mg.basic',
 'part_mg.basic_partition_mg1',
 'part_mg.tablegroup_split_with_drop_table',
 'zcreate1wpartiton',
 'dcl.create_user_oracle',
 'tenant',
 'tenant2'
 ]

