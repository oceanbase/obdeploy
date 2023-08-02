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
import time
from copy import deepcopy
from _types import *

from _stdio import SafeStdio

SQL_FILE = "exec_sql_file"
EXEC_SQL = "exec_sql"
VARIABLES = 'variables'
SYSTEM_CONFIG = 'system_config'


class SqlFile(object):

    def __init__(self, path, entrance, sys=False, **kwargs):
        self.path = path
        self.entrance = entrance
        self.exec_by_sys = sys
        self.extra_kwargs = kwargs
        self.need_restart = False

    def _get_sql(self, **kwargs):
        sql_kwargs = deepcopy(self.entrance.envs)
        sql_kwargs.update(sql_file=self.path, **self.extra_kwargs)
        if self.exec_by_sys:
            sql_kwargs.update(
                tenant=sql_kwargs.get('sys_tenant', 'sys'),
                user=sql_kwargs.get('sys_user', 'root'),
                password=sql_kwargs.get('sys_password', ""),
                database=""
            )
        sql_kwargs.update(kwargs)
        passwd = sql_kwargs.get('password', "")
        database = sql_kwargs.get('database', "")
        sql_kwargs['pass_str'] = '-p{}'.format(passwd) if passwd else ""
        sql_kwargs['db_str'] = '-D{}'.format(database) if database else ""
        return "{obclient_bin} -h{host} -P{port} -u{user}@{tenant} {pass_str} {db_str} -A < {sql_file}".format(
            **sql_kwargs)

    def optimize(self, client, stdio=None, **kwargs):
        ret = client.execute_command(self._get_sql(**kwargs), stdio=stdio)
        if ret:
            return True
        else:
            raise Exception('failed to execute {} {}'.format(self.path, ret.stderr))

    def recover(self, *args, **kwargs):
        return None


class Variable(object):
    TYPES = {
        'DOUBLE': Double,
        'BOOL': Boolean,
        'INT': Integer,
        'STRING': String,
        'MOMENT': Moment,
        'TIME': Time,
        'CAPACITY': Capacity,
        'CAPACITY_MB': CapacityMB,
        'STRING_LIST': StringList
    }

    def __init__(self, value, entrance, name=None, value_type=None, condition="lambda n, o: n != o",
                 optimizer="default", expression=False, query_key='value', **kwargs):
        self.entrance = entrance
        self.name = name
        self._value = value
        self._origin_value = None
        self._value_type = value_type
        self._condition = condition
        self.extra_kwargs = kwargs
        self._optimizer_name = optimizer
        self._optimizer = None
        self.need_restart = False
        self.expression = expression
        self.query_key = query_key

    @property
    def value_type(self):
        if self._value_type in self.TYPES:
            return self.TYPES[self._value_type]

    @property
    def origin_value(self):
        return self._origin_value

    @origin_value.setter
    def origin_value(self, value):
        if not self.value_type and isinstance(value, str) and value.isdigit():
            value = int(value)
        if self.value_type:
            value = self.value_type(value)
        self._origin_value = value

    @property
    def optimizer(self):
        if not self._optimizer:
            self._optimizer = self.entrance.get_optimizer(self._optimizer_name)
        return self._optimizer

    def optimize_arguments(self, **kwargs):
        ret = deepcopy(self.entrance.envs)
        ret.update(name=self.name, value=self.value, **self.extra_kwargs)
        ret.update(kwargs)
        return ret

    def optimize(self, cursor, stdio=None, **kwargs):
        if self.name == 'sleep':
            stdio.verbose('sleep {}'.format(self.value))
            time.sleep(self.value)
            return True
        kwargs = self.optimize_arguments(**kwargs)
        ret = self.optimizer.query(cursor, stdio=stdio, **kwargs)
        if not ret or ret.get(self.query_key) is None:
            stdio.warn('failed to query {}, skip it.'.format(self.name))
            return False
        self.origin_value = ret[self.query_key]
        stdio.verbose('origin_value {}({}) target_value {}({}) condition {}'.format(
            self.origin_value, type(self.origin_value).__name__,
            self.value, type(self.value).__name__, self._condition))
        if self.meet_the_condition(self.value, self.origin_value):
            if not self.optimizer.modify(cursor, stdio=stdio, **kwargs):
                raise Exception('fail to optimize {} to {}'.format(self.name, self.value))
            return True

    def recover(self, cursor, stdio=None, **kwargs):
        if self.name == 'sleep':
            stdio.verbose('sleep {}'.format(self.value))
            time.sleep(self.value)
            return True
        if self.origin_value is None:
            return True
        return self.optimizer.modify(cursor, stdio=stdio, **self.optimize_arguments(value=self.origin_value, **kwargs))

    @property
    def value(self):
        if self.expression:
            value = eval(self._value, {}, self.entrance.envs)
        else:
            value = self._value
        if not self.value_type and isinstance(value, str) and value.isdigit():
            return int(value)
        # self.value_type
        if self.value_type:
            value = self.value_type(value)
        return value

    def meet_the_condition(self, new_value, old_value):
        try:
            envs = deepcopy(self.entrance.envs)
            _condition = eval(self._condition, envs, envs)
            envs.update(
                new_value=new_value,
                old_value=old_value,
                _condition=_condition
            )
            exec("ret = _condition(new_value, old_value)", envs, envs)
            ret = envs.get('ret')
            return ret
        except:
            raise Exception("Invalid condition: {}".format(self._condition))


class ExecSql(Variable):
    OPTIMIZE_TYPE = EXEC_SQL

    def __init__(self, name, entrance, value=None, **kwargs):
        super(ExecSql, self).__init__(name=name, entrance=entrance, value=value, **kwargs)

    def optimize(self, cursor, stdio=None, **kwargs):
        kwargs = self.optimize_arguments(**kwargs)
        if not self.optimizer.modify(cursor, stdio=stdio, **kwargs):
            raise Exception('fail to exec sql {} '.format(self.name))
        return True

    def recover(self, cursor, stdio=None, **kwargs):
        return


class SystemConfig(Variable):
    OPTIMIZE_TYPE = SYSTEM_CONFIG

    def __init__(self, name, entrance, value, need_restart=False, **kwargs):
        super(SystemConfig, self).__init__(name=name, entrance=entrance, value=value, **kwargs)
        self.need_restart = need_restart

    def optimize_arguments(self, **kwargs):
        ret = deepcopy(self.entrance.envs)
        ret.update(name=self.name, value=self.value, **self.extra_kwargs)
        ret['tenant_where'] = 'tenant="{}"'.format(self.entrance.envs.get('tenant'))
        ret.update(kwargs)
        return ret


class OptimizeObjectEntrance(object):
    OPTIMIZE_TYPE = None
    ITEM_CLASS = None

    def __init__(self, kwargs_list):
        """

        :param kwargs_list: [
            {'key1': value1, 'key2': value2}
        ]
        """
        self._optimize_config = None
        self.items = []
        self.items_done = []
        self.optimizer_map = {}
        for kwargs in kwargs_list:
            self.items.append(self.ITEM_CLASS(entrance=self, **kwargs))
        self._need_restart = False

    @property
    def envs(self):
        return self._optimize_config.envs

    def optimize(self, stdio=None, disable_restart=False, *args, **kwargs):
        try:
            for item in self.items:
                if disable_restart and item.need_restart:
                    continue
                ret = item.optimize(*args, stdio=stdio, **kwargs)
                if ret:
                    self.items_done.append(item)
                    if item.need_restart:
                        self._need_restart = True
            return True
        except:
            stdio.exception('Failed to optimize {}'.format(self.OPTIMIZE_TYPE))
            return False

    def recover(self, stdio=None, *args, **kwargs):
        try:
            for item in self.items_done[::-1]:
                item.recover(stdio=stdio, *args, **kwargs)
                if item.need_restart:
                    self._need_restart = True
        except:
            stdio.exception('Failed to recover {}'.format(self.OPTIMIZE_TYPE))

    def mark_relationship(self, optimizers=None, optimize_config=None):
        self.optimizer_map = optimizers
        self._optimize_config = optimize_config

    def get_optimizer(self, name='default'):
        return self.optimizer_map[name]

    @property
    def need_restart(self):
        return self._need_restart


class VariableEntrance(OptimizeObjectEntrance):
    ITEM_CLASS = Variable
    OPTIMIZE_TYPE = VARIABLES


class SystemConfigEntrance(OptimizeObjectEntrance):
    ITEM_CLASS = SystemConfig
    OPTIMIZE_TYPE = SYSTEM_CONFIG


class SqlFileEntrance(OptimizeObjectEntrance):
    ITEM_CLASS = SqlFile
    OPTIMIZE_TYPE = SQL_FILE


class ExecSqlEntrance(OptimizeObjectEntrance):
    ITEM_CLASS = ExecSql
    OPTIMIZE_TYPE = EXEC_SQL


OptimizeObjectMap = {
    VARIABLES: VariableEntrance,
    SYSTEM_CONFIG: SystemConfigEntrance,
    EXEC_SQL: ExecSqlEntrance,
    SQL_FILE: SqlFileEntrance
}


class OptimizeConfig(SafeStdio):

    def __init__(self, config_dict, optimizer_dict):
        """

        :param config_dict: {
            <component>:
                <stage>:
                    <optimize>:
                        OptimizeObject
        }
        :param optimizer_dict: {
            <component>:
                <optimize_type>:
                    <name>: Optimizer
        }
        """
        self.config_dict = config_dict
        self.optimizer_dict = optimizer_dict
        self.envs = {}

    def set_exec_sql(self, component, stage, sql_kwargs_list, stdio=None):
        """

        :param component:
        :param stage:
        :param sql_kwargs_list: [
            {
                "path": "<sql file path>",
                "sys": false # execute sql file in sys tenant
            }
        ]
        :return:
        """
        stdio.verbose(
            'Set the optimization of the component {} in the {} stage to execute the sql file'.format(component, stage))
        self.config_dict[component][stage] = {SQL_FILE: SqlFileEntrance(kwargs_list=sql_kwargs_list)}

    def get_optimize_entrances(self, component, stage):
        optimize_entrance_map = self.config_dict.get(component, {}).get(stage, {})
        optimize_entrances = []
        for optimize_entrance in optimize_entrance_map.values():
            optimize_entrance.mark_relationship(optimize_config=self, optimizers=self._get_optimizer_map(component,
                                                                                                         optimize_entrance.OPTIMIZE_TYPE))
            optimize_entrances.append(optimize_entrance)
        return optimize_entrances

    def _get_optimizer_map(self, component, optimize_type):
        return self.optimizer_dict.get(component, {}).get(optimize_type, {})

    def set_envs(self, envs):
        self.envs = envs


class CursorOptimizer(SafeStdio):

    def __init__(self, query_sql=None, modify_sql=None, *args, **kwargs):
        super(CursorOptimizer, self).__init__(*args, **kwargs)
        self.query_sql = query_sql
        self.origin_modify_sql = modify_sql
        self._modify_sql = None

    def query(self, cursor, stdio=None, *args, **kwargs):
        if not self.query_sql:
            stdio.verbose('no query sql')
            return
        sql = self.query_sql.format(**kwargs)
        return cursor.fetchone(sql)

    @property
    def modify_sql(self):
        if self._modify_sql is None:
            self._modify_sql = self.origin_modify_sql.replace('{value}', '%s')
        return self._modify_sql

    def modify(self, cursor, stdio=None, value=None, *args, **kwargs):
        if not self.modify_sql:
            stdio.verbose('no modify sql')
            return
        sql = self.modify_sql.format(**kwargs)
        cursor_args = None
        if value is not None:
            cursor_args = (value, )
        if cursor.fetchone(sql, cursor_args) is False:
            return False
        return True


class OptimizeParser(SafeStdio):

    def __init__(self):
        self.optimize_config_dict = {}
        self.optimizer_dict = {}
        self._optimize_config = None

    @property
    def optimize_config(self):
        if not self._optimize_config:
            self._optimize_config = OptimizeConfig(self.optimize_config_dict, self.optimizer_dict)
        return self._optimize_config

    def load(self, config, stdio=None):
        try:
            # load optimizer
            optimizer = config.get('optimizer', {})
            for component, type_optimizer_map in optimizer.items():
                self._load_optimizer_by_component(component, type_optimizer_map)
        except:
            stdio.exception('Failed to load optimizer')
            return False
        try:
            # load optimize config
            optimize_config = config.get('optimize_config', {})
            for component, stage_dict in optimize_config.items():
                self._load_config_by_component(component, stage_dict)
        except:
            stdio.exception('Failed to load optimize config')
            return False
        return True

    def _load_config_by_component(self, component, stage_dict):
        # replace
        self.optimize_config_dict[component] = {}
        for stage, optimize_item in stage_dict.items():
            self.optimize_config_dict[component][stage] = {}
            for optimize_type, content in optimize_item.items():
                if optimize_type in OptimizeObjectMap:
                    self.optimize_config_dict[component][stage][optimize_type] = OptimizeObjectMap[optimize_type](
                        content)
                else:
                    raise Exception('Invalid optimize_type {}'.format(optimize_type))

    def _load_optimizer_by_component(self, component, optimizer_dict):
        # override
        self.optimizer_dict[component] = self.optimizer_dict.get(component, {})
        for optimize_type, name_optimizer_map in optimizer_dict.items():
            component_optimizer_map = self.optimizer_dict[component].get(optimize_type, {})
            for name, optimizer_kwargs in name_optimizer_map.items():
                component_optimizer_map[name] = CursorOptimizer(**optimizer_kwargs)
            self.optimizer_dict[component][optimize_type] = component_optimizer_map

    def load_config_by_component(self, component, config, stdio=None):
        try:
            self._load_config_by_component(component, config)
            return True
        except:
            stdio.exception('Failed to load optimize config for component {}'.format(component))
            return False

    def load_optimizer_by_component(self, component, optimizers, stdio=None):
        try:
            self._load_optimizer_by_component(component, optimizers)
            return True
        except:
            stdio.exception('Failed to load optimizer for component {}'.format(component))
            return False
