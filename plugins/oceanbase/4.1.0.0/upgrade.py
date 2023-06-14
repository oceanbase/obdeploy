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

import os
import time
from collections import defaultdict

import tool
from _rpm import Version
from ssh import LocalClient


class Exector(object):

    def __init__(self, tmp_prefix, host, port, user, pwd, exector_path, stdio, script_query_timeout=''):
        self.tmp_prefix = tmp_prefix
        self._host = host
        self._port = port
        self._user = user
        self._pwd = pwd
        self._cmd = None
        self.stdio = stdio
        self._exector = os.path.join(exector_path, 'executer27/bin/executer')
        self.script_query_timeout = script_query_timeout

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def user(self):
        return self._user

    @property
    def pwd(self):
        return self._pwd

    @property
    def exector(self):
        return self._exector

    @property
    def cmd(self):
        if self._cmd is None:
            self._cmd = '%s %%s -h %s -P %s -u %s %s' % (self._exector, self.host, self.port, self.user, "-p '%s'" % self.pwd if self.pwd else '')
        return self._cmd

    @host.setter
    def host(self, value):
        self._host = value
        self._cmd = None

    @port.setter
    def port(self, value):
        self._port = value
        self._cmd = None

    @user.setter
    def user(self, value):
        self._user = value
        self._cmd = None

    @pwd.setter
    def pwd(self, value):
        self._pwd = value
        self._cmd = None

    @pwd.setter
    def exector(self, exector_path):
        self._exector = os.path.join(exector_path, 'bin/executer27')
        self._cmd = None

    def create_temp(self, repository, direct_upgrade=False):
        tmp_path = os.path.join('/tmp', self.tmp_prefix, repository.md5)
        if not os.path.exists(tmp_path):
            relative_dir = 'etc/direct_upgrade' if direct_upgrade else 'etc'
            script_dir = os.path.join(repository.repository_dir, relative_dir)
            LocalClient.put_dir(script_dir, tmp_path)
        return tmp_path

    def clear_temp(self):
        tmp_path = os.path.join('/tmp', self.tmp_prefix)
        tool.DirectoryUtil.rm(tmp_path)

    def exec_script(self, name, repository, direct_upgrade=False, can_skip=False, param=''):
        script_dir = self.create_temp(repository, direct_upgrade)
        path = os.path.join(script_dir, name)
        self.stdio.verbose('exec %s %s' % (repository, name))
        if os.path.exists(path):
            cmd = '{} {} {}'.format(self.cmd.replace('%s', path, 1), param, '-t {}'.format(self.script_query_timeout) if self.script_query_timeout else '')
            self.stdio.start_loading('Exec %s %s' % (repository, name))
            if LocalClient.execute_command(cmd, stdio=self.stdio):
                self.stdio.stop_loading('succeed')
                return True
            else:
                self.stdio.stop_loading('fail')
                return False
        else:
            if can_skip:
                self.stdio.print('skip %s %s' % (repository, name))
                return True
            else:
                self.stdio.error('No such file: %s' % path)
                return False


class Upgrader(object):

    def __init__(self, plugin_context, search_py_script_plugin, apply_param_plugin, upgrade_ctx, upgrade_repositories,
                 local_home_path, exector_path, install_repository_to_servers, unuse_lib_repository, script_query_timeout):
        self._search_py_script_plugin = search_py_script_plugin
        self.apply_param_plugin = apply_param_plugin
        self.plugin_context = plugin_context
        self.components = plugin_context.components
        self.clients = plugin_context.clients
        self.cluster_config = plugin_context.cluster_config
        self.stdio = plugin_context.stdio
        self._connect_plugin = None
        self._start_plugin = None
        self._stop_plugin = None
        self._display_plugin = None
        self.install_repository_to_servers = install_repository_to_servers
        self.unuse_lib_repository = unuse_lib_repository
        self.local_home_path = local_home_path
        self.exector_path = exector_path
        self.components = plugin_context.components
        self.exector = None
        self.db = None
        self.cursor = None
        self.repositories = upgrade_repositories
        self.upgrade_ctx = upgrade_ctx
        self.route = upgrade_ctx.get('route')
        self.route_index = upgrade_ctx.get('index')
        self.process_index = upgrade_ctx.get('process_index', 0)
        self.process_route_index = upgrade_ctx.get('process_route_index', self.route_index)
        self.backup_param = upgrade_ctx.get('backup_param', None)
        self.script_query_timeout = script_query_timeout

        self.process = [
            self.backup_config,
            self.disable_ddl_and_check,
            self.exec_upgrade_checker,
            self.exec_upgrade_pre,
            self.exec_upgrade_health_checker,
            self.upgrade_zone,
            self.exec_upgrade_post,
            self.restore_config
        ]
        self.process_total = len(self.process)
        key = []
        for server in self.cluster_config.servers:
            config = self.cluster_config.get_server_conf_with_default(server)
            port = config.get('rpc_port')
            key.append('%s:%s' % (server.ip, port))
        self.tmp_prefix =  '_'.join(key)

    def search_py_script_plugin(self, index, name):
        repository = self.repositories[index]
        return self._search_py_script_plugin([repository], name)[repository]

    @property
    def connect_plugin(self):
        if self._connect_plugin is None:
            self._connect_plugin = self.search_py_script_plugin(self.route_index - 1, 'connect')
        return self._connect_plugin

    @property
    def start_plugin(self):
        if self._start_plugin is None:
            self._start_plugin = self.search_py_script_plugin(self.next_stage, 'start')
        return self._start_plugin

    @property
    def stop_plugin(self):
        if self._stop_plugin is None:
            self._stop_plugin = self.search_py_script_plugin(self.route_index - 1, 'stop')
        return self._stop_plugin

    @property
    def display_plugin(self):
        if self._display_plugin is None:
            self._display_plugin = self.search_py_script_plugin(self.route_index - 1, 'display')
        return self._display_plugin

    def _clear_plugin(self):
        self._connect_plugin = None
        self._start_plugin = None
        self._stop_plugin = None
        self._display_plugin = None

    def call_plugin(self, plugin, *args, **kwargs):
        return plugin(self.plugin_context.namespace, self.plugin_context.namespaces, self.plugin_context.deploy_name,
                      self.plugin_context.repositories, self.plugin_context.components, self.plugin_context.clients,
                      self.plugin_context.cluster_config, self.plugin_context.cmds, self.plugin_context.options,
                      self.plugin_context.stdio, *args, **kwargs)

    def run(self):
        total = len(self.route)
        self.apply_param_plugin(self.repositories[self.route_index - 1])
        while self.route_index < total:
            self.call_plugin(self.start_plugin, local_home_path=None, repository_dir=None)
            self.close()
            if not self.connect():
                return False
            self.stdio.verbose('upgrade %s to %s' % (self.repositories[self.route_index], self.repositories[self.next_stage]))
            while self.process_index < self.process_total:
                try:
                    if not self.process[self.process_index]():
                        self._dump()
                        return False
                    self.process_index += 1
                    self.process_route_index = self.route_index
                except Exception as e:
                    self._dump()
                    self.stdio.exception(str(e))
                    return False
            self.process_index = 0
            self.route_index = self.next_stage + 1
            self.exector.clear_temp()
            self.stdio.verbose('set route index from %s to %s' % (self.route_index, self.next_stage + 1))
            break
        self._dump()
        return True

    def _dump(self):
        self.upgrade_ctx['route'] = self.route
        self.upgrade_ctx['index'] = self.route_index
        self.upgrade_ctx['process_index'] = self.process_index
        self.upgrade_ctx['process_route_index'] = self.process_route_index
        self.upgrade_ctx['backup_param'] = self.backup_param

    def close(self):
        if self.db:
            self.cursor.close()
            self.cursor = None
            self.db = None
            self.exector = None

    def connect(self):
        if self.cursor is None or self.execute_sql('select version()', error=False) is False:
            ret = self.call_plugin(self.connect_plugin)
            if not ret:
                return False
            if self.cursor:
                self.close()
            self.cursor = ret.get_return('cursor')
            self.db = ret.get_return('connect')
            while self.execute_sql('use oceanbase', error=False) is False:
                time.sleep(2)
            self.execute_sql('set session ob_query_timeout=1000000000')
            server = ret.get_return('server')
            host = server.ip
            port = self.db.port
            user = 'root'
            pwd = self.cluster_config.get_global_conf().get('root_password', '')
            self.exector = Exector(self.tmp_prefix, host, port, user, pwd if pwd is not None else '', self.exector_path, self.stdio,self.script_query_timeout)
        return True

    def execute_sql(self, query, args=None, one=True, error=True):
        exc_level = 'error' if error else 'verbose'
        if one:
            result = self.cursor.fetchone(query, args, exc_level=exc_level)
        else:
            result = self.cursor.fetchall(query, args, exc_level=exc_level)
        result and self.stdio.verbose(result)
        return result

    @property
    def next_stage(self):
        next_stage = self.route_index
        total = len(self.route) - 1
        while next_stage < total:
            node = self.route[next_stage]
            if node.get('require_from_binary'):
                break
            next_stage += 1
        return next_stage

    def _exec_script_dest_only(self, name, can_skip=True, param=''):
        self.stdio.start_loading('Exec %s' % name)
        next_stage = self.next_stage
        repository = self.repositories[next_stage]
        self.stdio.verbose('exec %s %s' % (repository, name))
        if not self.exector.exec_script(name, repository, direct_upgrade=self.route[next_stage].get('direct_upgrade'), can_skip=can_skip, param=param):
            return False
        self.stdio.stop_loading('succeed')
        return True

    def _exec_script_all_repositories(self, name, can_skip=False):
        self.stdio.start_loading('Exec %s' % name)
        next_stage = self.next_stage
        cur_repository = self.repositories[self.route_index - 1]
        while self.process_route_index <= next_stage:
            repository = self.repositories[self.process_route_index]
            if cur_repository.version == repository.version:
                self.stdio.verbose('skip %s %s' % (repository, name))
            else:
                self.stdio.verbose('exec %s %s' % (repository, name))
                if not self.exector.exec_script(name, repository, direct_upgrade=self.route[self.process_route_index].get('direct_upgrade'), can_skip=can_skip):
                    self.stdio.stop_loading('fail')
                    return False
            self.process_route_index += 1
        self.stdio.stop_loading('succeed')
        return True

    def execute_upgrade_sql(self, query, args=None, one=True):
        if self.execute_sql(query, args, one) is False:
            return False
        self.process_route_index = self.route_index
        return True

    def exec_upgrade_checker(self):
        return self._exec_script_dest_only('upgrade_checker.py')

    def exec_upgrade_health_checker(self):
        return self._exec_script_dest_only('upgrade_health_checker.py')

    def exec_upgrade_health_checker_zone(self, zone):
        return self._exec_script_dest_only('upgrade_health_checker.py', param="-z '{}'".format(zone))

    def exec_upgrade_pre(self):
        return self._exec_script_all_repositories('upgrade_pre.py')

    def disable_ddl_and_check(self):
        if self.repositories[self.route_index - 1].version == Version('4.0.0.0'):
            self.stdio.start_loading('Disable DDL')
            while True:
                # check ddl end
                while self.execute_sql("select task_id from __all_virtual_ddl_task_status", error=True):
                    time.sleep(3)
                # close ddl
                if self.execute_sql('alter system set enable_ddl = false') is False:
                    self.stdio.stop_loading('fail')
                    return False
                while self.execute_sql("select * from __all_virtual_sys_parameter_stat where name = 'enable_ddl' and value != 'false'"):
                    time.sleep(3)

                # check ddl end
                if self.execute_sql("select task_id from __all_virtual_ddl_task_status", error=True):
                    if not self.execute_sql('alter system set enable_ddl = true'):
                        self.stdio.stop_loading('fail')
                    continue
                break
                
            # check clog
            self.stdio.verbose('wait clog sync')
            rets = self.execute_sql("select tenant_id, ls_id, max(max_scn) as max_scn from gv$ob_log_stat group by tenant_id, ls_id", one=False, error=True)
            if rets is not None:
                for ret in rets:
                    while self.execute_sql("select unsubmitted_log_scn from __all_virtual_replay_stat where tenant_id = %s and ls_id = %s and role != 'leader' and unsubmitted_log_scn <= %s" % (ret['tenant_id'], ret['ls_id'], ret['max_scn']), error=True):
                        time.sleep(3)

            # major freeze
            # 1. check merge status
            pre_global_broadcast_scn = 0
            while True:
                merge_status = self.execute_sql("select max(global_broadcast_scn) as global_broadcast_scn, max(global_broadcast_scn > last_scn) as is_merging from CDB_OB_MAJOR_COMPACTION")
                if merge_status['is_merging'] == 0:
                    pre_global_broadcast_scn = merge_status['global_broadcast_scn']
                    break
                time.sleep(3)
            # 2. begin merge
            self.execute_sql("alter system major freeze tenant = all", error=False)
            # 3. wait merge start
            while self.execute_sql("select * from CDB_OB_MAJOR_COMPACTION where global_broadcast_scn <= %s", [pre_global_broadcast_scn]):
                time.sleep(3)
            # 4.wait merge finsh
            while self.execute_sql("select * from CDB_OB_MAJOR_COMPACTION where global_broadcast_scn > last_scn"):
                time.sleep(3)

            self.stdio.stop_loading('succeed')

        return True

    def broken_sql(self, sql, sleep_time=3):
        while True:
            ret = self.execute_sql(sql, error=False)
            if ret is None:
                break
            time.sleep(sleep_time)

    def wait(self):
        if not self.connect():
            return False
        self.stdio.verbose('server cneck')
        self.broken_sql("select * from oceanbase.DBA_OB_SERVERS where STATUS != 'ACTIVE' or STOP_TIME is not NULL or START_SERVICE_TIME is NULL")
        self.broken_sql("select * from GV$OB_LOG_STAT where in_sync = 'NO'")
        return True

    def start_zone(self, zone=None):
        if not self.connect():
            return False
        if zone:
            self.stdio.verbose('start zone %s' % zone)
            start_sql = "alter system start zone %s" % zone
            check_sql = "select * from oceanbase.__all_zone where name = 'status' and zone = '%s' and info != 'ACTIVE'" % zone
            while True:
                if self.execute_sql(start_sql, error=False) is None:
                    break
                if self.execute_sql(check_sql, error=False) is None:
                    break
                time.sleep(3)
        self.wait()
        return True

    def stop_zone(self, zone):
        if not self.wait():
            return False

        self.stdio.verbose('stop zone %s' % zone)
        stop_sql = "alter system stop zone %s" % zone

        if self.execute_sql(stop_sql, error=False) is None:
            return True

    def upgrade_zone(self):
        zones_servers = {}
        for server in self.cluster_config.servers:
            config = self.cluster_config.get_server_conf_with_default(server)
            zone = config['zone']
            if zone not in zones_servers:
                zones_servers[zone] = []
            zones_servers[zone].append(server)
        servers = self.cluster_config.servers
        try:
            if len(zones_servers) > 2:
                ret = self.rolling_upgrade(zones_servers)
            else:
                ret = self.un_rolling_upgrade()
            if ret:
                self._clear_plugin()
                return True
            return False
        except Exception as e:
            self.stdio.exception('Run Exception: %s' % e)
            return False
        finally:
            self.cluster_config.servers = servers

    def un_rolling_upgrade(self):
        self.stdio.start_loading('Upgrade')
        repository = self.repositories[self.next_stage]
        repository_dir = repository.repository_dir
        self.install_repository_to_servers(self.components, self.cluster_config, repository, self.clients,
                                           self.unuse_lib_repository)

        if not self.call_plugin(self.stop_plugin):
            self.stdio.stop_loading('stop_loading', 'fail')
            return False

        self.apply_param_plugin(repository)
        if not self.call_plugin(self.start_plugin, local_home_path=self.local_home_path, repository_dir=repository_dir):
            self.stdio.stop_loading('stop_loading', 'fail')
            return False
        self.close()
        self.wait()
        self.stdio.stop_loading('succeed')
        return True

    def rolling_upgrade(self, zones_servers):
        self.stdio.start_loading('Rotation upgrade')
        all_servers = self.cluster_config.servers
        repository = self.repositories[self.next_stage]
        repository_dir = repository.repository_dir
        pre_zone = None
        for zone in zones_servers:
            self.cluster_config.servers = zones_servers[zone]
            if not self.start_zone(pre_zone):
                self.stdio.stop_loading('stop_loading', 'fail')
                return False

            self.stop_zone(zone)

            self.stdio.print('upgrade zone "%s"' % zone)
            self.install_repository_to_servers(self.components, self.cluster_config, repository, self.clients, self.unuse_lib_repository)


            if pre_zone:
                self.apply_param_plugin(self.repositories[self.route_index - 1])
            if not self.call_plugin(self.stop_plugin):
                self.stdio.stop_loading('stop_loading', 'fail')
                return False

            self.apply_param_plugin(repository)
            if not self.call_plugin(self.start_plugin, local_home_path=self.local_home_path, repository_dir=repository_dir):
                self.stdio.stop_loading('stop_loading', 'fail')
                return False
            self.wait()
            if not self.exec_upgrade_health_checker_zone(zone):
                return False
            self.close()
            pre_zone = zone

        if not self.start_zone(pre_zone):
            self.stdio.stop_loading('stop_loading', 'fail')
            return False
        self.stdio.stop_loading('succeed')
        return True

    def exec_upgrade_post(self):
        return self._exec_script_all_repositories('upgrade_post.py')

    def backup_config(self):
        keys = ("server_permanent_offline_time", "enable_rebalance", "enable_rereplication")
        query_sql = 'select SVR_IP,SVR_PORT,NAME,VALUE from oceanbase.GV$OB_PARAMETERS where name in %s '
        ret = self.execute_sql(query_sql, [keys, ], one=False, error=False)
        if ret is not None:
            backup_param = defaultdict(dict)
            for config in ret:
                backup_param['{}:{}'.format(config['SVR_IP'], config['SVR_PORT'])].update({config['NAME']: config['VALUE']})
            self.backup_param = backup_param
        else:
            return False

        return True

    def restore_config(self):
        dict_backup_param = dict(self.backup_param)
        for server_port in dict_backup_param:
            for key in dict_backup_param[server_port]:
                alter_sql = 'alter system set {} = %s server %s'.format(key)
                if self.execute_sql(alter_sql, [dict_backup_param[server_port][key], server_port], error=False) is False:
                    return False
        return True


def upgrade(plugin_context, search_py_script_plugin, apply_param_plugin, install_repository_to_servers, unuse_lib_repository, *args, **kwargs):

    upgrade_ctx = kwargs.get('upgrade_ctx')
    local_home_path = kwargs.get('local_home_path')
    upgrade_repositories = kwargs.get('upgrade_repositories')
    script_query_timeout = kwargs.get('script_query_timeout')
    exector_path = getattr(plugin_context.options, 'executer_path', '/usr/obd/lib/executer')

    upgrader = Upgrader(
        plugin_context=plugin_context,
        search_py_script_plugin=search_py_script_plugin,
        apply_param_plugin=apply_param_plugin,
        upgrade_ctx=upgrade_ctx,
        upgrade_repositories=upgrade_repositories,
        local_home_path=local_home_path,
        exector_path=exector_path,
        install_repository_to_servers=install_repository_to_servers,
        unuse_lib_repository=unuse_lib_repository,
        script_query_timeout=script_query_timeout)
    if upgrader.run():
        if upgrader.route_index >= len(upgrader.route):
            upgrader.call_plugin(upgrader.display_plugin, upgrader.cursor, *args, **kwargs)
        plugin_context.return_true()

