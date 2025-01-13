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

import os
import time
import tool
import datetime
from ssh import LocalClient
from tool import Exector as BaseExector


class Exector(BaseExector):

    def __init__(self, tmp_prefix, host, port, user, pwd, exector_path, stdio):
        super(Exector, self).__init__(host, port, user, pwd, exector_path, stdio)
        self.tmp_prefix = tmp_prefix

    @property
    def cmd(self):
        if self._cmd is None:
            self._cmd = '%s %%s -h %s -P %s -u %s %s' % (self._exector, self.host, self.port, self.user, '-p %s' % tool.ConfigUtil.passwd_format(self.pwd) if self.pwd else '')
        return self._cmd

    def exec_script(self, name, repository, direct_upgrade=False, can_skip=False):
        script_dir = self.create_temp(repository, direct_upgrade)
        path = os.path.join(script_dir, name)
        self.stdio.verbose('exec %s %s' % (repository, name))
        if os.path.exists(path):
            cmd = self.cmd.replace('%s', path, 1)
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

    def __init__(self, plugin_context, search_py_script_plugin, apply_param_plugin, upgrade_ctx, upgrade_repositories, local_home_path, exector_path, install_repository_to_servers, unuse_lib_repository, get_workflows, run_workflow):
        self._search_py_script_plugin = search_py_script_plugin
        self._run_workflow = run_workflow
        self.get_workflows = get_workflows
        self.apply_param_plugin = apply_param_plugin
        self.plugin_context = plugin_context
        self.components = plugin_context.components
        self.clients = plugin_context.clients
        self.cluster_config = plugin_context.cluster_config
        self.stdio = plugin_context.stdio
        self._connect_plugin = None
        self._display_plugin = None
        self._start_workflows = None
        self._stop_workflows = None
        self.install_repository_to_servers = install_repository_to_servers
        self.unuse_lib_repository = unuse_lib_repository
        self.local_home_path = local_home_path
        self.exector_path = exector_path
        self.exector = None
        self.db = None
        self.cursor = None
        self.repositories = upgrade_repositories
        self.upgrade_ctx = upgrade_ctx
        self.route = upgrade_ctx.get('route')
        self.route_index = upgrade_ctx.get('index')
        self.process_index = upgrade_ctx.get('process_index', 0)
        self.process_route_index = upgrade_ctx.get('process_route_index', self.route_index)
        self.process = [
            self.exec_upgrade_checker,
            self.upgrade_mode_on,
            self.exec_upgrade_pre,
            self.upgrade_zone,
            self.upgrade_virtual_schema,
            self.exec_upgrade_post,
            self.upgrade_mode_off,
            self.root_inspect,
            self.exec_upgrade_post_checker
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

    def run_workflow(self, workflows, repository, cluster_config, **kwargs):
        if not kwargs.get(repository.name):
            kwargs[repository.name] = dict()
        kwargs[repository.name]["cluster_config"] = cluster_config
        return self._run_workflow(workflows, repositories=[repository], **kwargs)

    @property
    def start_workflows(self):
        if self._start_workflows is None:
            self._start_workflows = self.get_workflows('upgrade_start', [self.repositories[self.next_stage]])
        return self._start_workflows

    @property
    def stop_workflows(self):
        if self._stop_workflows is None:
            self._stop_workflows = self.get_workflows('stop', [self.repositories[self.route_index - 1]])
        return self._stop_workflows

    @property
    def connect_plugin(self):
        if self._connect_plugin is None:
            self._connect_plugin = self.search_py_script_plugin(self.route_index - 1, 'connect')
        return self._connect_plugin

    @property
    def display_plugin(self):
        if self._display_plugin is None:
            self._display_plugin = self.search_py_script_plugin(self.route_index - 1, 'display')
        return self._display_plugin

    def _clear_plugin(self):
        self._connect_plugin = None
        self._start_workflows = None
        self._stop_workflows = None
        self._display_plugin = None

    def call_plugin(self, plugin, *args, **kwargs):
        return plugin(self.plugin_context.namespace, self.plugin_context.namespaces, self.plugin_context.deploy_name, self.plugin_context.deploy_status,
                      self.plugin_context.repositories, self.plugin_context.components, self.plugin_context.clients,
                      self.plugin_context.cluster_config, self.plugin_context.cmds, self.plugin_context.options,
                      self.plugin_context.stdio, *args, **kwargs)

    def run(self):
        total = len(self.route)
        self.apply_param_plugin(self.repositories[self.route_index - 1])
        while self.route_index < total:
            setattr(self.plugin_context.options, 'without_parameter', True)
            start_workflows = self.get_workflows('upgrade_start', [self.repositories[self.route_index - 1]])
            self.run_workflow(start_workflows, self.repositories[self.route_index - 1], self.cluster_config, **{self.repositories[self.route_index].name: {"local_home_path": None, "repository_dir": None}})
            self.close()
            if not self.connect():
                return False
            self.stdio.verbose('upgrade %s to %s' % (self.repositories[self.route_index], self.repositories[self.next_stage]))
            while self.process_index < self.process_total:
                try:
                    if not self.process[self.process_index]():
                        return False
                    self.process_index += 1
                    self.process_route_index = self.route_index
                except Exception as e:
                    self.stdio.exception(str(e))
                    return False
                finally:
                    self._dump()
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

    def close(self):
        if self.db:
            self.cursor.close()
            self.cursor = None
            self.db = None
            self.exector = None

    def connect(self, cache=True):
        if self.cursor is None or not cache or self.execute_sql('select version()', error=False) is False:
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
            self.exector = Exector(self.tmp_prefix, host, port, user, pwd if pwd is not None else '', self.exector_path, self.stdio)
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

    def _exec_script_dest_only(self, name, can_skip=True):
        self.stdio.start_loading('Exec %s' % name)
        next_stage = self.next_stage
        repository = self.repositories[next_stage]
        self.stdio.verbose('exec %s %s' % (repository, name))
        if not self.exector.exec_script(name, repository, direct_upgrade=self.route[next_stage].get('direct_upgrade'), can_skip=can_skip):
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

    def upgrade_mode_on(self):
        self.stdio.start_loading('Enable upgrade mode')
        if self.execute_upgrade_sql('alter system begin upgrade') is False:
            self.stdio.stop_loading('fail')
            return False
        time.sleep(2)
        sql = "select value from oceanbase.__all_virtual_sys_parameter_stat where name = 'enable_upgrade_mode' and value = 'False'"
        while True:
            if not self.execute_sql(sql, error=False):
                self.stdio.stop_loading('succeed')
                return True
            time.sleep(2)

    def exec_upgrade_pre(self):
        return self._exec_script_all_repositories('upgrade_pre.py')

    def broken_sql(self, sql, sleep_time=3):
        while True:
            ret = self.execute_sql(sql, error=False)
            if ret is None:
                break
            time.sleep(sleep_time)
            self.connect(cache=False)

    def wait(self):
        if not self.connect():
            return False
        self.stdio.verbose('server cneck')
        self.broken_sql("select * from oceanbase.__all_server where status != 'active' or stop_time > 0 or start_service_time = 0")
        self.broken_sql("select * from oceanbase.__all_virtual_clog_stat where is_in_sync= 0 and is_offline = 0")
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
        check_sql = "select * from oceanbase.__all_zone where name = 'status' and zone = '%s' and info = 'ACTIVE'" % zone
        while True:
            if self.execute_sql(stop_sql, error=False) is None:
                break
            if self.execute_sql(check_sql, error=False):
                break
            time.sleep(3)
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
        if not self.run_workflow(self.stop_workflows, self.repositories[self.route_index - 1], self.cluster_config):
            self.stdio.stop_loading('stop_loading', 'fail')
            return False

        self.apply_param_plugin(repository)
        if not self.run_workflow(self.start_workflows, repository, self.cluster_config, **{repository.name: {"local_home_path": self.local_home_path, "repository_dir": repository_dir}}):
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
            while True:
                for server in zones_servers[zone]:
                    config = self.cluster_config.get_server_conf(server)
                    sql = '''
                    select count(*) as cnt from oceanbase.__all_tenant as a left join (
                        select tenant_id, refreshed_schema_version 
                        from oceanbase.__all_virtual_server_schema_info 
                        where svr_ip = %s and svr_port = %s and refreshed_schema_version > 1
                        ) as b on a.tenant_id = b.tenant_id 
                    where b.tenant_id is null'''
                    if self.execute_sql(sql, args=(server.ip, config['rpc_port'])).get('cnt'):
                        break
                else:
                    break
                time.sleep(3)

            while self.execute_sql("select * from oceanbase.__all_virtual_clog_stat where table_id = 1099511627777 and status != 'ACTIVE'"):
                time.sleep(3)
            
            self.stop_zone(zone)

            self.stdio.print('upgrade zone "%s"' % zone)
            self.install_repository_to_servers(self.components, self.cluster_config, repository, self.clients, self.unuse_lib_repository)


            if pre_zone:
                self.apply_param_plugin(self.repositories[self.route_index - 1])
            if not self.run_workflow(self.stop_workflows, self.repositories[self.route_index - 1], self.cluster_config):
                self.stdio.stop_loading('stop_loading', 'fail')
                return False

            self.apply_param_plugin(repository)
            if not self.run_workflow(self.start_workflows, repository, self.cluster_config, **{repository.name: {"local_home_path": self.local_home_path, "repository_dir": repository_dir}}):
                self.stdio.stop_loading('stop_loading', 'fail')
                return False
            self.close()
            pre_zone = zone
            
        if not self.start_zone(pre_zone):
            self.stdio.stop_loading('stop_loading', 'fail')
            return False
        self.stdio.stop_loading('succeed')
        return True

    def upgrade_virtual_schema(self):
        return self.execute_upgrade_sql('alter system upgrade virtual schema')

    def exec_upgrade_post(self):
        return self._exec_script_all_repositories('upgrade_post.py')

    def upgrade_mode_off(self):
        self.stdio.start_loading('Disable upgrade mode')
        if self.execute_upgrade_sql('alter system end upgrade') is False:
            self.stdio.stop_loading('fail')
            return False
        time.sleep(2)
        sql = "select value from oceanbase.__all_virtual_sys_parameter_stat where name = 'enable_upgrade_mode' and value = 'True'"
        while True:
            if not self.execute_sql(sql, error=False):
                self.stdio.stop_loading('succeed')
                return True
            time.sleep(2)

    def root_inspect(self):
        self.stdio.start_loading('Root inspection')
        if self.execute_sql("alter system run job 'root_inspection'") is False:
            self.stdio.stop_loading('fail')
            return False
        self.stdio.stop_loading('succeed')
        return True

    def exec_upgrade_post_checker(self):
        return self._exec_script_dest_only('upgrade_post_checker.py')


def upgrade(plugin_context, search_py_script_plugin, apply_param_plugin, install_repository_to_servers, unuse_lib_repository, get_workflows, run_workflow, *args, **kwargs):

    upgrade_ctx = kwargs.get('upgrade_ctx')
    local_home_path = kwargs.get('local_home_path')
    upgrade_repositories = kwargs.get('upgrade_repositories')
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
        get_workflows=get_workflows,
        run_workflow=run_workflow
        )
    if upgrader.run():
        if upgrader.route_index >= len(upgrader.route):
            upgrader.call_plugin(upgrader.display_plugin, upgrader.cursor, *args, **kwargs)
        plugin_context.return_true()

