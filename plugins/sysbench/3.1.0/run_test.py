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
import os
from time import sleep
try:
    import subprocess32 as subprocess
except:
    import subprocess
from ssh import LocalClient


stdio = None


def exec_cmd(cmd):
    stdio.verbose('execute: %s' % cmd)
    process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while process.poll() is None:
        line = process.stdout.readline()
        line = line.strip()
        if line:
            stdio.print(line.decode("utf8", 'ignore'))
    return process.returncode == 0


def run_test(plugin_context, *args, **kwargs):
    def get_option(key, default=''):
        if key in opt_keys:
            opt_keys.remove(key)
        value = getattr(options, key, default)
        if value is None:
            value = default
        return value
    global stdio
    stdio = plugin_context.stdio
    options = plugin_context.options
    opt_keys = list(vars(options).keys())
    for used_key in ['component', 'test_server', 'skip_cluster_status_check', 'obclient_bin', 'optimization']:
        opt_keys.remove(used_key)

    sys_namespace = kwargs.get("sys_namespace")
    get_db_and_cursor = kwargs.get("get_db_and_cursor")
    db, cursor = get_db_and_cursor(sys_namespace)
    port = db.port if db else 2881


    host = get_option('host', '127.0.0.1')
    mysql_db = get_option('database', 'test')
    user = get_option('user', 'root')
    tenant_name = get_option('tenant', 'test')
    password = get_option('password', '')
    table_size = get_option('table_size', 10000)
    tables = get_option('tables', 32)
    threads = get_option('threads', 150)
    time = get_option('time', 60)
    interval = get_option('interval', 10)
    events = get_option('events', 0)
    rand_type = get_option('rand_type', None)
    skip_trx = get_option('skip_trx', '').lower()
    percentile = get_option('percentile', None)
    script_name = get_option('script_name', 'oltp_point_select.lua')
    sysbench_bin = get_option('sysbench_bin', 'sysbench')
    sysbench_script_dir = get_option('sysbench_script_dir', '/usr/sysbench/share/sysbench')

    def generate_sysbench_cmd(sysbench_cmd):
        if password:
            sysbench_cmd += ' --mysql-password=%s' % password
        if table_size:
            sysbench_cmd += ' --table_size=%s' % table_size
        if tables:
            sysbench_cmd += ' --tables=%s' % tables
        if time:
            sysbench_cmd += ' --time=%s' % time
        if interval:
            sysbench_cmd += ' --report-interval=%s' % interval
        if events:
            sysbench_cmd += ' --events=%s' % events
        if rand_type:
            sysbench_cmd += ' --rand-type=%s' % rand_type
        if skip_trx in ['on', 'off']:
            sysbench_cmd += ' --skip_trx=%s' % skip_trx
        if percentile:
            sysbench_cmd += ' --percentile=%s' % percentile
        for opt_key in opt_keys:
            sysbench_cmd += ' --%s=%s' % (opt_key.replace('_', '-'), getattr(options, opt_key))
        return sysbench_cmd

    try:
        scripts = script_name.split(',')
        user_threads = threads.split(',')
        max_thread = max(user_threads)
        for script in scripts:
            stdio.print("\nStart executing %s" % (script if script.endswith('.lua') else script + '.lua'))
            sysbench_cmd = "cd %s; %s %s --mysql-host=%s --mysql-port=%s --mysql-user=%s@%s --mysql-db=%s" % (sysbench_script_dir, sysbench_bin, script, host, port, user, tenant_name, mysql_db)
            sysbench_cmd = generate_sysbench_cmd(sysbench_cmd)
            base_cmd = f"{sysbench_cmd} --threads={max_thread}"
            if not (exec_cmd('%s cleanup' % base_cmd) and exec_cmd('%s prepare' % base_cmd)):
                return plugin_context.return_false()
            for thread in user_threads:
                sysbench_run_cmd = f"{sysbench_cmd} --threads={thread}"
                if not exec_cmd('%s --db-ps-mode=disable run' % sysbench_run_cmd):
                    return plugin_context.return_false()
        return plugin_context.return_true()
    except KeyboardInterrupt:
        pass
    except:
        stdio.exception('')