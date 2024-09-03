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
import requests
import urllib
from subprocess import Popen, PIPE
from copy import deepcopy
from ssh import LocalClient
from tool import DirectoryUtil
from _stdio import FormatText

inner_dir = os.path.split(__file__)[0]
inner_test_dir = os.path.join(inner_dir, 't')
inner_result_dir = os.path.join(inner_dir, 'r')
inner_suite_dir = os.path.join(inner_dir, 'test_suite')


class Arguments:
    def add(self, k, v=None):
        self.args.update({k: v})

    def __str__(self):
        s = []
        for k, v in self.args.items():
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
        if 'connector' in opt and opt.get('java'):
            self.add('--connector', opt['connector'])
        self.add('--host', opt['host'])
        self.add('--port', opt['port'])
        self.add('--tmpdir', opt['tmp_dir'])
        if not opt.get('log_dir'):
            log_dir = os.path.join(opt['var_dir'], 'log')
        else:
            log_dir = opt['log_dir']
        self.add('--logdir', log_dir)
        DirectoryUtil.mkdir(opt['tmp_dir'])
        DirectoryUtil.mkdir(log_dir)
        self.add('--silent')
        # our mysqltest doesn't support this option
        # self.add('--skip-safemalloc')
        self.add('--user', 'root')
        if opt.get('user'):
            user = opt['user']
            if 'connector' not in opt or opt['connector'] == 'ob':
                user = user + '@' + opt['case_mode']
            self.add('--user', user)
        if opt.get('password'):
            self.add('--password', opt['password'])
        if opt.get('full_user'):
            self.add('--full_username', opt['full_user'].replace('sys', opt['case_mode']))
        if opt.get('tenant'):
            self.add('--user', 'root@' + opt['tenant'])
            self.add('--password', '')
            if opt.get('cluster'):
                self.add('--full_username', 'root@' + opt['tenant'] + '#' + opt['cluster'])
            else:
                self.add('--full_username', 'root@' + opt['tenant'])
        if opt.get('rslist_url'):
            self.add('--rslist_url', opt['rslist_url'])
        if opt.get('database'):
            self.add('--database', opt['database'])
        if opt.get('charsetdsdir'):
            self.add('--character-sets-dir', opt['charsetsdir'])
        if opt.get('basedir'):
            self.add('--basedir', opt['basedir'])
        if opt.get('use_px'):
            self.add('--use-px')
        if opt.get('force_explain_as_px'):
            self.add('--force-explain-as-px')
        if 'force-explain-as-no-px' in opt:
            self.add('--force-explain-as-no-px')
        if opt.get('mark_progress'):
            self.add('--mark-progress')
        if opt.get('ps_protocol'):
            self.add('--ps-protocol')
        if opt.get('sp_protocol'):
            self.add('--sp-protocol')
        if opt.get('view_protocol'):
            self.add('--view-protocol')
        if opt.get('cursor_protocol'):
            self.add('--cursor-protocol')
        if opt.get('special_run'):
            self.add('--disable-explain')
        if opt.get('sp_hint'):
            self.add('--sp-hint', '"%s"' % opt['sp_hint'])
        if opt.get('sort_result'):
            self.add('--sort-result')
        self.add('--timer-file', os.path.join(log_dir, 'timer'))

        if opt.get('compress'):
            self.add('--compress')
        if opt.get('sleep'):
            self.add('--sleep', '%d' % opt['sleep'])
        if opt.get('max_connections'):
            self.add('--max-connections', '%d' % opt['max_connections'])

        if opt.get('test_file'):
            self.add('--test-file', opt['test_file'])

        self.add('--tail-lines', (opt.get('tail_lines')) or 20)
        if opt.get('oblog_diff'):
            self.add('--oblog_diff')

        if opt.get('record') and opt.get('record_file'):
            self.add('--record')
            self.add('--result-file', opt['record_file'])
            DirectoryUtil.mkdir(os.path.dirname(opt['record_file']))
        else:                                    # diff result & file
            self.add('--result-file', opt['result_file'])


def _return(test, cmd, result):
    return {'name': test, 'ret': result.code, 'output': result.stdout, 'cmd': cmd, 'errput': result.stderr}


def slb_request(case_name, exec_id, slb_host, op='lock', stdio=None):
    slb_data = {'eid': exec_id, 'case': case_name}
    slb_msg = {
        'lock': (
            'get lock for case {} successful.',
            'get lock for case {} failed.'),
        'success': (
            'mark successful for case {} successful.',
            'mark successful for case {} failed.')
    }
    assert op in slb_msg
    try:
        url = 'http://{slb_host}/farm/mysqltest/recorder/{op}.php'.format(slb_host=slb_host, op=op)
        stdio.verbose('send request: {}, param: {}'.format(url, slb_data))
        resp = requests.get(url, params=slb_data)
        verbose_msg = 'response code: {}, content: {}'.format(resp.status_code, resp.content)
        stdio.verbose(verbose_msg)
        if resp.status_code == 200:
            stdio.verbose(slb_msg[op][0].format(case_name))
            return True
        elif resp.status_code in (202, 300):
            stdio.verbose(slb_msg[op][1].format(case_name))
            return False
        else:
            stdio.warn(slb_msg[op][1].format(case_name) + verbose_msg)
            return False
    except:
        stdio.warn('send request failed')
        stdio.exception('')
        return False


def run_test(plugin_context, env, *args, **kwargs):

    def return_true(**kw):
        env['run_test_cases'] = run_test_cases
        env['index'] = index
        env['case_results'] = case_results
        env['is_retry'] = is_retry
        env['need_reboot'] = need_reboot
        env['collect_log'] = collect_log
        return plugin_context.return_true(**kw)

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    slb_host = env.get('slb_host')
    exec_id = env.get('exec_id')
    cursor = env.get('cursor')
    run_test_cases = env.get('run_test_cases', [])
    index = env.get('index', 0)
    test_set = env.get('test_set', [])
    case_results = env.get('case_results', [])
    auto_retry = env.get('auto_retry')
    is_retry = env.get('is_retry', False)
    reboot_cases = env.get('reboot_cases', [])
    need_reboot = env.get('need_reboot', False)
    collect_all = env.get('collect_all', False)
    collect_log = False
    total_test_count = len(test_set)
    while index < total_test_count:
        test = test_set[index]
        if test not in run_test_cases:
            if slb_host and exec_id and not slb_request(test, exec_id=exec_id, slb_host=slb_host, stdio=stdio):
                index += 1
                continue
            run_test_cases.append(test)
            if test in reboot_cases:
                stdio.print('Reboot cluster because case "{}" is in the reboot cases list.'.format(test))
                need_reboot = True
        if need_reboot:
            need_reboot = False
            return return_true(reboot=True)
        retry_msg = "in auto retry mode" if is_retry else ""
        label = FormatText.info("[ RUN      ]")
        stdio.start_loading('%sRunning case: %s ( %s / %s ) %s' % (label, test, index+1, total_test_count, retry_msg))
        test_name = test
        opt = {}
        for key in env:
            if key != 'cursor':
                opt[key] = env[key]

        opt['connector'] = 'ob'
        opt['mysql_mode'] = True
        test_file_suffix = opt['test_file_suffix']
        result_file_suffix = opt['result_file_suffix']
        record_file_suffix = opt['record_file_suffix']
        mysqltest_bin = opt.get('mysqltest_bin', 'mysqltest')
        obclient_bin = opt.get('obclient_bin', 'obclient')

        soft = 3600
        buffer = 0
        if opt.get('source_limit'):
            if test_name in opt['source_limit']:
                soft = opt['source_limit'][test_name]
            elif 'g.default' in opt['source_limit']:
                soft = opt['source_limit']['g.default']

            if 'g.buffer' in opt['source_limit']:
                buffer = opt['source_limit']['g.buffer']
        case_timeout = soft + buffer

        if opt.get('case_timeout'):
            case_timeout = opt['case_timeout']

        # support explain select w/o px hit
        # force-explain-xxxx 的结果文件目录为
        # - explain_r/mysql
        # - explain_r/oracle
        # 其余的结果文件目录为
        # - r/mysql
        # - r/oracle
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
        if opt['mode'] == 'mysql' or opt['mode'] == 'oracle':
            opt['case_mode'] = opt['mode']
        if opt['mode'] == 'both':
            if test.endswith('_mysql'):
                opt['case_mode'] = 'mysql'
            if test.endswith('_oracle'):
                opt['case_mode'] = 'oracle'

        get_result_dir = lambda path: os.path.join(path, opt_explain_dir, opt['case_mode'])

        if len(test.split('.')) == 2:
            suite_name, test = test.split('.')
            result_dir = get_result_dir(os.path.join(opt['result_dir'], suite_name, 'r'))
            if os.path.exists(result_dir):
                opt['result_dir'] = result_dir
            else:
                opt['result_dir'] = get_result_dir(os.path.join(opt['suite_dir'], suite_name, 'r'))
            opt['record_dir'] = get_result_dir(os.path.join(opt['record_dir'], suite_name, 'r'))
            opt['test_file'] = os.path.join(opt['suite_dir'], suite_name, 't', test + test_file_suffix)
            if not os.path.isfile(opt['test_file']):
                inner_test_file = os.path.join(inner_suite_dir, suite_name, 't', test + test_file_suffix)
                if os.path.isfile(inner_test_file):
                    opt['test_file'] = inner_test_file
                    opt['result_dir'] = get_result_dir(os.path.join(inner_suite_dir, suite_name, 'r'))

        else:
            opt['test_file'] = os.path.join(opt['test_dir'], test + test_file_suffix)
            opt['record_dir'] = get_result_dir(os.path.join(opt['record_dir']))
            if not os.path.isfile(opt['test_file']):
                inner_test_file = os.path.join(inner_test_dir, test + test_file_suffix)
                if os.path.isfile(inner_test_file):
                    opt['test_file'] = inner_test_file
                    opt['result_dir'] = get_result_dir(inner_result_dir)
            else:
                opt['result_dir'] = get_result_dir(opt['result_dir'])
        # owner
        owner = "anonymous"
        try:
            cmd_t = "grep -E '#\s*owner\s*:' " + opt['test_file'] + " | awk -F':' '{print $2}' | head -n 1"
            p = Popen(cmd_t, stdout=PIPE, stderr=PIPE, shell=True)
            output, errput = p.communicate()
            owner = output.decode("utf-8").strip()
        except:
            stdio.verbose("fail open %s" % (opt['test_file']))

        opt['record_file'] = os.path.join(opt['record_dir'], test + suffix + record_file_suffix)
        opt['result_file'] = os.path.join(opt['result_dir'], test + suffix + result_file_suffix)
        if opt['filter'] == 'slave':
            opt['slave_cmp'] = 1
            result_file = os.path.join(opt['result_dir'], test + suffix + '.slave' + result_file_suffix)
            if os.path.exists(result_file):
                opt['slave_cmp'] = 0
                opt['result_file'] = result_file

        if not opt['is_business']:
            ce_result_file = re.sub(r'\.result$', '.ce.result', opt['result_file'])
            if os.path.exists(ce_result_file):
                opt['result_file'] = ce_result_file

        if 'my_host' in opt or 'oracle_host' in opt:
            # compare mode
            pass

        sys_pwd = cluster_config.get_global_conf().get('root_password', '')
        exec_sql_cmd = "%s -h%s -P%s -uroot %s -A -Doceanbase -e" % (obclient_bin, opt['host'], opt['port'], ("-p'%s'" % sys_pwd) if sys_pwd else '')
        server_engine_cmd = '''%s "select value from __all_virtual_sys_parameter_stat where name like '_enable_static_typing_engine';"''' % exec_sql_cmd
        result = LocalClient.execute_command(server_engine_cmd, timeout=3600, stdio=stdio)
        stdio.verbose('query engine result: {}'.format(result.stdout))
        if not result:
            stdio.error('engine failed, exit code %s. error msg: %s' % (result.code, result.stderr))
        obmysql_ms0_dev = str(opt['host'])
        if ':' in opt['host']:
            # todo: obproxy没有网卡设备选项，可能会遇到问题。如果obproxy支持IPv6后续进行改造
            devname = cluster_config.get_server_conf(opt['test_server']).get('devname')
            if devname:
                obmysql_ms0_dev = '{}%{}'.format(opt['host'], devname)
        update_env = {
            'OBMYSQL_PORT': str(opt['port']),
            'OBMYSQL_MS0': str(opt['host']),
            'OBMYSQL_MS0_DEV': obmysql_ms0_dev,
            'OBMYSQL_PWD': str(opt['password']),
            'OBMYSQL_USR': opt['user'],
            'PATH': os.getenv('PATH'),
            'OBSERVER_DIR': cluster_config.get_server_conf(opt['test_server'])['home_path'],
            'IS_BUSINESS': str(opt['is_business'])
        }
        test_env = deepcopy(os.environ.copy())
        test_env.update(update_env)
        if opt.get('case_mode'):
            test_env['TENANT'] = opt['case_mode']
            if opt.get('user'):
                test_env['OBMYSQL_USR'] = str(opt['user'] + '@' + opt['case_mode'])
            else:
                test_env['OBMYSQL_USR'] = 'root'
        if 'java' in opt:
            opt['connector'] = 'ob'

        if opt['_enable_static_typing_engine'] is not None:
            sql = "select value from oceanbase.__all_virtual_sys_parameter_stat where name like '_enable_static_typing_engine';"
            ret = cursor.fetchone(sql)
            if ret and str(ret.get('value')).lower() != str(opt['_enable_static_typing_engine']).lower():
                LocalClient.execute_command('%s "alter system set _enable_static_typing_engine = %s;select sleep(2);"' % (exec_sql_cmd, opt['_enable_static_typing_engine']), stdio=stdio)

        start_time = time.time()
        cmd = 'timeout %s %s %s' % (case_timeout, mysqltest_bin, str(Arguments(opt)))
        try:
            stdio.verbose('local execute: %s ' % cmd)
            p = Popen(shlex.split(cmd), env=test_env, stdout=PIPE, stderr=PIPE)
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
        cost = time.time() - start_time

        case_info = "%s %s ( %f s )" % (test_name, owner, cost)

        patterns = ['output', 'NAME', 'SORT', 'SCAN', 'LIMIT', 'EXCHANGE', 'GET', 'FUNCTION', 'MERGE', 'JOIN', 'MATERIAL',
                    'DISTINCT', 'SUBPLAN', 'UNION|ALL', 'EXPRESSION', 'SCALAR', 'HASH', 'VALUES', 'DELETE', 'result',
                    'reject', '=====', '-------', 'conds', 'output', 'access', 'GROUP', 'DELETE', 'UPDATE', 'INSERT',
                    'CONNECT', 'nil', 'values', 'COUNT', '^$']
        count = 0
        # 不处理liboblog的结果对比
        if re.search("liboblog_r", errput):
            stdio.verbose("do nothing for liboblog")
        elif (opt['filter'] == 'slave' and opt['slave_cmp'] == 1) or opt['filter'] == 'j' or opt['filter'] == 'jp':
            diff = errput.split('\n')
            for line in diff:
                match = 0
                if re.search(r"^\+", line) or re.search(r"^\-", line):
                    for pattern in patterns:
                        if re.search(pattern, line):
                            match = match + 1
                            continue
                    if match == 0:
                        count = count + 1
                        break
            if count == 0:
                # 处理slave/java 模式下result文件不存在的情况
                if re.search(r"\+", errput):
                    stdio.verbose('ignore explain plan diff')
                    retcode = 0

        result = {"name": test_name, "ret": retcode, "output": output, "cmd": cmd, "errput": errput, 'cost': cost}
        stdio.stop_loading('fail' if retcode else 'succeed')
        stdio.verbose('exited code %s' % retcode)
        if retcode:
            # verbose_msg += ', error output:\n%s' % errput
            stdio.print(errput)
            case_status = FormatText.error("[  FAILED  ]")
        else:
            case_status = FormatText.success('[       OK ]')
        stdio.print("%s%s" % (case_status, case_info))
        if retcode == 0 and slb_host and exec_id:
            slb_request(test_name, exec_id=exec_id, slb_host=slb_host, op='success', stdio=stdio)
        if retcode == 0:
            # success
            case_results.append(result)
            index += 1
            is_retry = False
        elif is_retry or not auto_retry:
            # failed and no chance to retry
            case_results.append(result)
            index += 1
            is_retry = False
            need_reboot = True
            collect_log = collect_all
        else:
            # retry
            is_retry = True
            need_reboot = True
    return return_true(finished=True)