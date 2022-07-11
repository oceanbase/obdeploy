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

import re
import os
import time
import shlex
from subprocess import Popen, PIPE
from copy import deepcopy
from ssh import LocalClient
from tool import DirectoryUtil



inner_dir = os.path.split(__file__)[0]
inner_test_dir = os.path.join(inner_dir, 't')
inner_result_dir = os.path.join(inner_dir, 'r')
inner_suite_dir = os.path.join(inner_dir, 'test_suite')


class Arguments:
    def add(self, k, v=None):
        self.args.update({k:v})

    def __str__(self):
        s = []
        for k,v in self.args.items():
            if v != None:
                if re.match('^--\w', k):
                    s.append(' %s=%s' % (k, v))
                else:
                    s.append(' %s %s' % (k, v))
            else:
                s.append(' %s' % k)
        return ' '.join(s)

    def __init__(self, opt):
        self.args = dict()
        if 'connector' in opt and 'java' in opt and opt['java']:
            self.add('--connector', opt['connector'])
        self.add('--host', opt['host'])
        self.add('--port', opt['port'])
        self.add('--tmpdir', opt['tmp_dir'])
        self.add('--logdir', '%s/log' % opt['var_dir'])
        DirectoryUtil.mkdir(opt['tmp_dir'])
        DirectoryUtil.mkdir('%s/log' % opt['var_dir'])
        self.add('--silent')
        # our mysqltest doesn't support this option
        # self.add('--skip-safemalloc')
        self.add('--user', 'root')
        if 'user' in opt and opt['user']:
            user = opt['user']
            if 'connector' not in opt or opt['connector'] == 'ob':
                user = user + '@' + opt['case_mode']
            self.add('--user', user)
        if 'password' in opt and opt['password']:
            self.add('--password', opt['password'])
        if 'full_user' in opt and opt['full_user']:
            self.add('--full_username', opt['full_user'].replace('sys',opt['case_mode']))
        if 'tenant' in opt and opt['tenant']:
            self.add('--user', 'root@' + opt['tenant'])
            self.add('--password', '')
            if 'cluster' in opt and opt['cluster']:
                self.add('--full_username', 'root@' + opt['tenant'] + '#' + opt['cluster'])
            else:
                self.add('--full_username', 'root@' + opt['tenant'])
        if 'rslist_url' in opt and opt['rslist_url']:
            self.add('--rslist_url', opt['rslist_url'])
        if 'database' in opt and opt['database']:
            self.add('--database', opt['database'])
        if 'charsetdsdir' in opt and opt['charsetdsdir']:
            self.add('--character-sets-dir', opt['charsetsdir'])
        if 'basedir' in opt and opt['basedir']:
            self.add('--basedir', opt['basedir'])
        if 'use_px' in opt and opt['use_px']:
            self.add('--use-px')
        if 'force_explain_as_px' in opt and opt['force_explain_as_px']:
            self.add('--force-explain-as-px')
        if 'force-explain-as-no-px' in opt:
            self.add('--force-explain-as-no-px')
        if 'mark_progress' in opt and opt['mark_progress']:
            self.add('--mark-progress')
        if 'ps_protocol' in opt and opt['ps_protocol']:
            self.add('--ps-protocol')
        if 'sp_protocol' in opt and opt['sp_protocol']:
            self.add('--sp-protocol')
        if 'view_protocol' in opt and opt['view_protocol']:
            self.add('--view-protocol')
        if 'cursor_protocol' in opt and opt['cursor_protocol']:
            self.add('--cursor-protocol')

        self.add('--timer-file', '%s/log/timer' % opt['var_dir'])

        if 'compress' in opt and opt['compress']:
            self.add('--compress')
        if 'sleep' in opt and opt['sleep']:
            self.add('--sleep', '%d' % opt['sleep'])
        if 'max_connections' in opt and opt['max_connections']:
            self.add('--max-connections', '%d' % opt['max_connections'])

        if 'test_file' in opt and opt['test_file']:
            self.add('--test-file', opt['test_file'])

        self.add('--tail-lines', ('tail_lines' in opt and opt['tail_lines']) or 20)
        if 'oblog_diff' in opt and opt['oblog_diff']:
            self.add('--oblog_diff')

        if 'record' in opt and opt['record'] and 'record_file' in opt and opt['record_file']:
            self.add('--record')
            self.add('--result-file', opt['record_file'])
        else:                                    # diff result & file
            self.add('--result-file', opt['result_file'])


def _return(test, cmd, result):
    return {'name' : test, 'ret' : result.code, 'output' : result.stdout, 'cmd' : cmd, 'errput': result.stderr}


def run_test(plugin_context, test, env, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    stdio.start_loading('Runing case: %s' % test)
    test_ori = test
    opt = {}
    for key in env:
        if key != 'cursor':
            opt[key] = env[key]

    opt['connector'] = 'ob'
    opt['mysql_mode'] = True
    mysqltest_bin = opt['mysqltest_bin'] if 'mysqltest_bin' in opt and opt['mysqltest_bin'] else 'mysqltest'
    obclient_bin = opt['obclient_bin'] if 'obclient_bin' in opt and opt['obclient_bin'] else 'obclient'
    
    soft = 3600
    buffer = 0
    if 'source_limit' in opt and opt['source_limit']:
        if test_ori in opt['source_limit']:
            soft = opt['source_limit'][test_ori]
        elif 'g.default' in opt['source_limit']:
            soft = opt['source_limit']['g.default']

        if 'g.buffer' in opt['source_limit']:
            buffer = opt['source_limit']['g.buffer']
    case_timeout = soft + buffer


    opt['filter'] = 'c'
    if 'profile' in args:
        opt['profile'] = True
        opt['record'] = True
    if 'ps' in args:
        opt['filter'] = opt['filter'] + 'p'

    if 'cluster-mode' in opt and opt['cluster-mode'] in ['slave', 'proxy']:
        opt['filter'] = opt['cluster-mode']

    # support explain select w/o px hit
    # force-explain-xxxx 的结果文件目录为
    # - explain_r/mysql
    # 其余的结果文件目录为
    # - r/mysql
    suffix = ''
    opt_explain_dir = ''
    if 'force-explain-as-px' in opt:
        suffix = '.use_px'
        opt_explain_dir = 'explain_r/'
    elif 'force-explain-as-no-px' in opt:
        suffix = '.no_use_px'
        opt_explain_dir = 'explain_r/'

    opt['case_mode'] = 'mysql'
    if 'mode' not in opt:
        opt['mode'] = 'both'
    if opt['mode'] == 'mysql':
        opt['case_mode'] = opt['mode']
    if opt['mode'] == 'both':
        if test.endswith('_mysql'):
            opt['case_mode'] = 'mysql'

    get_result_dir = lambda path: os.path.join(path, opt_explain_dir, opt['case_mode'])
    opt['result_dir'] = get_result_dir(opt['result_dir'])
    if opt['filter'] == 'slave':
        opt['slave_cmp'] = 1
        result_file = os.path.join(opt['result_dir'], test + suffix + '.slave.result')
        if os.path.exists(result_file):
            opt['slave_cmp'] = 0
            opt['result_file'] = result_file
    
    if len(test.split('.')) == 2:
        suite_name, test= test.split('.')
        opt['result_dir'] = get_result_dir(os.path.join(opt['suite_dir'], suite_name, 'r'))
        opt['test_file'] = os.path.join(opt['suite_dir'], suite_name, 't', test + '.test')
        if not os.path.isfile(opt['test_file']):
            inner_test_file = os.path.join(inner_suite_dir, suite_name, 't', test + '.test')
            if os.path.isfile(inner_test_file):
                opt['test_file'] = inner_test_file
                opt['result_dir'] = get_result_dir(os.path.join(inner_suite_dir, suite_name, 'r'))
    else:
        opt['test_file'] = os.path.join(opt['test_dir'], test + '.test')
        if not os.path.isfile(opt['test_file']):
            inner_test_file = os.path.join(inner_test_dir, test + '.test')
            if os.path.isfile(inner_test_file):
                opt['test_file'] = inner_test_file
                opt['result_dir'] = get_result_dir(inner_result_dir)

    opt['record_file'] = os.path.join(opt['result_dir'], test + suffix + '.record')
    opt['result_file'] = os.path.join(opt['result_dir'], test + suffix + '.result')

    if 'my_host' in opt or 'oracle_host' in opt:
        # compare mode
        pass

    
    sys_pwd = cluster_config.get_global_conf().get('root_password', '')
    exec_sql_cmd = "%s -h%s -P%s -uroot %s -A -Doceanbase -e" % (obclient_bin, opt['host'], opt['port'], ("-p'%s'" % sys_pwd) if sys_pwd else '')
    server_engine_cmd = '''%s "select value from __all_virtual_sys_parameter_stat where name like '_enable_static_typing_engine';"''' % exec_sql_cmd
    result = LocalClient.execute_command(server_engine_cmd, timeout=3600, stdio=stdio)
    if not result:
        stdio.error('engine failed, exit code %s. error msg: %s' % (result.code, result.stderr))

    env = {
        'OBMYSQL_PORT': str(opt['port']),
        'OBMYSQL_MS0': str(opt['host']),
        'OBMYSQL_PWD': str(opt['password']),
        'OBMYSQL_USR': opt['user'],
        'PATH': os.getenv('PATH')
    }
    if 'case_mode' in opt and opt['case_mode']:
        env['TENANT'] = opt['case_mode']
        if 'user' in opt and opt['user']:
            env['OBMYSQL_USR'] = str(opt['user'] + '@' + opt['case_mode'])
        else:
            env['OBMYSQL_USR'] = 'root'
    if 'java' in opt:
        opt['connector'] = 'ob'

    LocalClient.execute_command('%s "alter system set _enable_static_typing_engine = True;select sleep(2);"' % (exec_sql_cmd), stdio=stdio)

    start_time = time.time()
    cmd = 'timeout %s %s %s' % (case_timeout, mysqltest_bin, str(Arguments(opt)))
    try:
        stdio.verbose('local execute: %s ' % cmd, end='')
        p = Popen(shlex.split(cmd), env=env, stdout=PIPE, stderr=PIPE)
        output, errput = p.communicate()
        retcode = p.returncode
        if retcode == 124:
            output = ''
            if 'source_limit' in opt and 'g.buffer' in opt['source_limit']:
                errput = "%s secs out of soft limit (%s secs), sql may be hung, please check" % (opt['source_limit']['g.buffer'], case_timeout)
            else:
                errput = "%s seconds timeout, sql may be hung, please check" % case_timeout
        elif isinstance(errput, bytes):
            errput = errput.decode(errors='replace')
    except Exception as e:
        errput = str(e)
        output = ''
        retcode = 255
    verbose_msg = 'exited code %s' % retcode
    if retcode:
        verbose_msg += ', error output:\n%s' % errput
    stdio.verbose(verbose_msg)
    cost = time.time() - start_time

    LocalClient.execute_command('%s "alter system set _enable_static_typing_engine = False;select sleep(2);"' % (exec_sql_cmd), stdio=stdio)
    result = {"name" : test_ori, "ret" : retcode, "output" : output, "cmd" : cmd, "errput" : errput, 'cost': cost}
    stdio.stop_loading('fail' if retcode else 'succeed')
    return plugin_context.return_true(result=result)
