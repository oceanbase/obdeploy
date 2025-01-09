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
import re

import _errno as err


def get_port_socket_inode(client, port, stdio=None):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp*,udp*}' | awk -F' ' '{if($4==\"0A\") print $2,$4,$10}' | grep ':%s' | awk -F' ' '{print $3}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    stdio.verbose(res.stdout)
    return res.stdout.strip().split('\n')


def has_obshell(repository):
    repository_dir = repository.repository_dir
    obshell_path = os.path.join(repository_dir, 'bin', 'obshell')
    return os.path.exists(obshell_path)


def scenario_start_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    critical = plugin_context.get_variable('critical')
    need_bootstrap = plugin_context.get_variable('need_bootstrap')

    if need_bootstrap:
        scenarios = ['express_oltp', 'complex_oltp', 'olap', 'htap', 'kv']
        scenario_check = lambda scenario: scenario in scenarios
        global_config = cluster_config.get_global_conf_with_default()
        scenario = global_config['scenario']
        if not scenario_check(scenario):
            critical(cluster_config.servers[0], 'scenario', err.EC_OBSERVER_UNKONE_SCENARIO.format(scenario=scenario), [err.SUB_OBSERVER_UNKONE_SCENARIO.format(scenarios=scenarios)])
            return plugin_context.return_false()
    return plugin_context.return_true()

