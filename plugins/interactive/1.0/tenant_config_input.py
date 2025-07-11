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

import re
from getpass import getpass
from optparse import Values

import const
from _stdio import FormatText
from _types import Capacity
from tool import get_sys_cpu, get_sys_log_disk_size, get_system_memory, input_int_value, byte_to_GB


def tenant_config_input(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    tenant_confirm = stdio.confirm('Do you want to create tenant for your business workload?', default_option=True)
    if not tenant_confirm:
        return plugin_context.return_true()
    oceanbase_config = plugin_context.get_variable('oceanbase_config')
    cpu_count = oceanbase_config['cpu_count']
    scenario = oceanbase_config['scenario']
    memory_limit = oceanbase_config['memory_limit']
    log_disk_size = oceanbase_config['log_disk_size']
    oceanbase_name = oceanbase_config['name']
    system_memory = get_system_memory(memory_limit)

    sys_cpu = get_sys_cpu(cpu_count)
    sys_log_disk_size = get_sys_log_disk_size(memory_limit)
    if not (oceanbase_name == const.COMP_OB_STANDALONE and memory_limit < 128 << 30):
        sys_log_disk_size = sys_log_disk_size + (1 << 30)
    sys_memory_size = 1 << 30 if oceanbase_name == const.COMP_OB_STANDALONE and memory_limit < 128 << 30 else 2 << 30
    stdio.print(FormatText.success(f'Tenant: sys conifguration: {sys_cpu}C/{Capacity(sys_memory_size)}/{Capacity(sys_log_disk_size)}(CPU/Memory/Log disk)'))
    stdio.print(FormatText.success(f'system_memory configuration(Unit: G): {Capacity(system_memory)}'))

    while True:
        tenant_name = stdio.read('Enter the tenant name (Default: test; allowed characters: letters, numbers, and underscores): ', blocked=True).strip() or 'test'
        if not re.match(r'^[a-zA-Z0-9_]+$', tenant_name):
            stdio.print(FormatText.error('The tenant name is invalid. Only letters, numbers, and underscores are allowed.'))
            continue
        break
    while True:
        if oceanbase_name == const.COMP_OB_CE:
            tenant_mode = 'mysql'
            break
        stdio.print(FormatText.warning('    Please select the tenant mode (enter the corresponding number): '))
        stdio.print('    1) MySQL')
        stdio.print('    2) Oracle')
        tenant_mode = stdio.read('Please enter your choice [1/2] [default 1]: ', blocked=True).strip() or '1'
        if tenant_mode == '1':
            tenant_mode = 'mysql'
            break
        elif tenant_mode == '2':
            tenant_mode = 'oracle'
            break
        else:
            stdio.print(FormatText.error("The tenant mode is invalid. Only '1' and '2' are allowed."))
            continue
    while True:
        tenant_password_first = getpass('Enter the tenant password: ').strip()
        tenant_password_second = getpass('Confirm the tenant password: ').strip()
        if tenant_password_first != tenant_password_second:
            stdio.print(FormatText.error('The two passwords do not match. Please try again.'))
            continue
        break

    # tenant cpu
    max_tenant_cpu = cpu_count - sys_cpu
    tenant_cpu = input_int_value('tenant cpu', 1, max_tenant_cpu, unit='', default_value=max_tenant_cpu, stdio=stdio)

    # tenant memory
    MIN_TENANT_MEMORY = 2
    default_tenant_memory = memory_limit - sys_memory_size - system_memory
    tenant_memory = Capacity(str(input_int_value('tenant memory', MIN_TENANT_MEMORY, byte_to_GB(default_tenant_memory), default_value=byte_to_GB(default_tenant_memory), stdio=stdio)) + 'G').bytes

    # tenant log disk
    tenant_log_disk_size_avariable = log_disk_size - sys_log_disk_size
    if default_tenant_memory == tenant_memory:
        tenant_default_log_disk_size = tenant_log_disk_size_avariable
    else:
        tenant_default_log_disk_size = (log_disk_size / memory_limit) * tenant_memory
    tenant_log_disk_size = Capacity(str(input_int_value('tenant log disk size', byte_to_GB(tenant_default_log_disk_size), byte_to_GB(tenant_log_disk_size_avariable), default_value=byte_to_GB(tenant_default_log_disk_size), stdio=stdio)) + 'G').bytes

    while True:
        if tenant_mode == 'mysql':
            character_set = ['utf8mb4', 'utf16', 'gbk', 'gb18030', 'binary']
        else:
            character_set = ['utf8mb4', 'gbk', 'gb18030']
        character_dict = dict()
        index = 0
        for character in character_set:
            index += 1
            character_dict[str(index)] = character
        print_str = ''
        for k, v in character_dict.items():
            print_str += f'    {k}) {v}\n'
        stdio.print(FormatText.warning('    Please select the character (enter the corresponding number): '))
        stdio.print(print_str[:-1])
        tenant_character_num = stdio.read(f'Enter the tenant charset (Default: 1): ', blocked=True).strip() or '1'
        if not character_dict.get(tenant_character_num):
            stdio.print(FormatText.error('The tenant charset set is invalid. Please try again.'))
            continue
        tenant_character_set = character_dict.get(tenant_character_num)
        break
    while True:
        tenant_character_collate_dict = {
            "utf8mb4": {
                '1': 'utf8mb4_general_ci',
                '2': 'utf8mb4_bin',
                '3': 'utf8mb4_unicode_ci',
                '4': 'utf8mb4_unicode_520_ci',
                '5': 'utf8mb4_croatian_ci',
                '6': 'utf8mb4_czech_ci',
                '7': 'utf8mb4_0900_ai_ci',
            },
            "utf16": {
                '1': 'utf16_general_ci',
                '2': 'utf16_bin',
                '3': 'utf16_unicode_ci'
            },
            "gbk": {
                '1': 'gbk_chinese_ci',
                '2': 'gbk_bin'
            },
            "gb18030": {
                '1': 'gb18030_chinese_ci',
                '2': 'gb18030_bin'
            },
            "binary": {
                '1': 'binary'
            }
        }
        collate_dict = tenant_character_collate_dict[tenant_character_set]
        if len(collate_dict) == 1:
            tenant_collate = list(collate_dict.values())[0]
            break

        print_str = ''
        for k, v in collate_dict.items():
            print_str += f'    {k}) {v}\n'
        stdio.print(FormatText.warning('    Please select the tenant collation (enter the corresponding number): '))
        stdio.print(print_str[:-1])
        tenant_collate_num = stdio.read(f'Enter the tenant collation (Default: 1): ', blocked=True).strip() or '1'
        if not collate_dict.get(tenant_collate_num):
            stdio.print(FormatText.error('The tenant collation is invalid. Please try again.'))
            continue
        tenant_collate = collate_dict[tenant_collate_num]
        break

    while True:
        time_zone = {
            '1': '-12:00(International Date Line West)',
            '2': '-11:00(Samoa Standard Time)',
            '3': '-10:00(Hawaii-Aleutian Standard Time)',
            '4': '-09:00(Alaska Standard Time)',
            '5': '-08:00(Pacific Standard Time)',
            '6': '-07:00(Mountain Standard Time)',
            '7': '-06:00(Central Standard Time)',
            '8': '-05:00(Eastern Standard Time)',
            '9': '-04:00(Atlantic Standard Time)',
            '10': '-03:00(Brasilia Standard Time)',
            '11': '-02:00(Mid-Atlantic Standard Time)',
            '12': '-01:00(Azores Standard Time)',
            '13': '+00:00(Greenwich Mean Time)',
            '14': '+01:00(Central European Time)',
            '15': '+02:00(Eastern European Time)',
            '16': '+03:00(Moscow Standard Time)',
            '17': '+04:00(Gulf Standard Time)',
            '18': '+05:00(Pakistan Standard Time)',
            '19': '+06:00(Bangladesh Standard Time)',
            '20': '+07:00(Indochina Time)',
            '21': '+08:00(China Standard Time)',
            '22': '+09:00(Japan Standard Time)',
            '23': '+10:00(Australian Eastern Standard Time)',
            '24': '+11:00(Solomon Islands Time)',
            '25': '+12:00(New Zealand Standard Time)',
            '26': '+13:00(Tonga Standard Time)',
            '27': '+14:00(Line Islands Time)'
        }
        print_str = ''
        for k, v in time_zone.items():
            print_str += f'    {k}) {v}\n'
        stdio.print(FormatText.warning('    Please select the tenant time zone (enter the corresponding number): '))
        stdio.print(print_str[:-1])
        tenant_time_zone = stdio.read(f'Enter the tenant time zone (Default: 21): ', blocked=True).strip() or '21'
        if not time_zone.get(tenant_time_zone):
            stdio.print(FormatText.error('The tenant time zone is invalid. Please try again.'))
            continue
        tenant_time_zone = time_zone[tenant_time_zone].split('(')[0]
        break
    variables = "ob_tcp_invited_nodes='%'"
    while True:
        if tenant_mode == 'mysql':
            stdio.print(FormatText.warning('    Please select case sensitivity for table names: '))
            stdio.print('    0) Table names are stored as specified and compared case-sensitively')
            stdio.print('    1) Table names are stored in lowercase and compared case-insensitively')
            stdio.print('    2) Table names are stored as specified but compared case-insensitively')
            case_sensitive = stdio.read('Please enter your choice [0/1/2] [default 1]: ', blocked=True).strip() or '1'
            if case_sensitive not in ['0', '1', '2']:
                stdio.print(FormatText.error('The case sensitivity is invalid. Please try again.'))
                continue
            variables += ', lower_case_table_names=' + case_sensitive
            break
        else:
            break

    tenant_config = {
        "memory_size": tenant_memory,
        "tenant_name": tenant_name,
        "max_cpu": tenant_cpu,
        "min_cpu": tenant_cpu,
        "log_disk_size": tenant_log_disk_size,
        tenant_name + '_root_password': tenant_password_second,
        "mode": tenant_mode,
        "time_zone": tenant_time_zone,
        "charset": tenant_character_set,
        "collate": tenant_collate,
        "optimize": scenario,
        "variables": variables
    }
    opt = Values()
    setattr(opt, "memory_size", str(Capacity(tenant_memory)))
    setattr(opt, "tenant_name", tenant_name)
    setattr(opt, "max_cpu", tenant_cpu)
    setattr(opt, "min_cpu", tenant_cpu)
    setattr(opt, "log_disk_size", str(Capacity(tenant_log_disk_size)))
    setattr(opt, tenant_name + '_root_password', tenant_password_second)
    setattr(opt, "mode", tenant_mode)
    setattr(opt, "time_zone", tenant_time_zone)
    setattr(opt, "charset", tenant_character_set)
    setattr(opt, "collate", tenant_collate)
    setattr(opt, "optimize", scenario)
    setattr(opt, "variables", variables)

    return plugin_context.return_true(tenant_config=tenant_config, tenant_opt=opt)
