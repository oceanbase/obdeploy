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

from _types import Capacity
import _errno as err


def generate_scenario(plugin_context, generate_config_mini=False, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    repositories = plugin_context.repositories
    stdio = plugin_context.stdio

    scenarios = ['express_oltp', 'complex_oltp', 'olap', 'htap', 'kv']
    scenario_check = lambda scenario: scenario in scenarios
    global_config = cluster_config.get_original_global_conf()
    scenario = global_config.get('scenario', None)
    default_scenario = cluster_config.get_global_conf_with_default().get('scenario')
    if not scenario:
        if generate_config_mini:
            scenario = 'express_oltp'
        else:
            optzs = {
                '1': 'express_oltp',
                '2': 'complex_oltp',
                '3': 'olap',
                '4': 'htap',
                '5': 'kv',
            }
            if stdio.isatty():
                stdio.print("Scenario not specified, please specify the scenario you want.")
                default_key = '1'
                for k, v in optzs.items():
                    if v == default_scenario:
                        default_key = k
                        stdio.print("%s. %s (default)" % (k, v))
                    else:
                        stdio.print("%s. %s" % (k, v))
                while not scenario:
                    optz = stdio.read('Please input the scenario [default: %s]: ' % default_key, blocked=True).strip().lower()
                    if not optz:
                        scenario = default_scenario
                    elif optz in optzs:
                        scenario = optzs[optz]
                    elif scenario_check(optz):
                        scenario = optz
                    else:
                        stdio.error('Invalid scenario, please input again.')
            else:
                scenario = default_scenario
                stdio.verbose("scenario not specified, use the default scenario: %s." % scenario)

        stdio.verbose('set scenario %s.' % scenario)
        cluster_config.update_global_conf('scenario', scenario, False)
    return plugin_context.return_true()