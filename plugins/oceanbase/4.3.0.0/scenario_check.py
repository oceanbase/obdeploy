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


def scenario_check(plugin_context, scenario='', *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio

    scenarios = ['express_oltp', 'complex_oltp', 'olap', 'htap', 'kv']
    scenario_check = lambda scenario: scenario in scenarios
    scenario = getattr(plugin_context.options, 'optimize', scenario)
    global_config = cluster_config.get_global_conf_with_default()
    default_scenario = global_config.get('scenario')
    if not scenario:
        optzs = {
            '1': 'express_oltp',
            '2': 'complex_oltp',
            '3': 'olap',
            '4': 'htap',
            '5': 'kv',
        }
        if not getattr(plugin_context.options, 'yes', False) and stdio.isatty():
            stdio.print("Tenant optimization scenario not specified, please specify the scenario you want to optimize.")
            default_key = '1'
            for k, v in optzs.items():
                if v == default_scenario:
                    default_key = k
                    stdio.print("%s. %s (default, follow cluster)" % (k, v))
                else:
                    stdio.print("%s. %s" % (k, v))
            while not scenario:
                optz = stdio.read('Please input the scenario you want to optimize [default: %s]: ' % default_key, blocked=True).strip().lower()
                if not optz:
                    scenario = default_scenario
                elif optz in optzs:
                    scenario = optzs[optz]
                elif scenario_check(optz):
                    scenario = optz
                else:
                    stdio.error('Invalid input, please input again.')
        else:
            stdio.verbose("Tenant optimization scenario not specified, use the cluster scenario: %s." % default_scenario)
            scenario = default_scenario
    else:
        if not scenario_check(scenario):
            stdio.error('This scenario is not supported: %s. scenarios: %s' % (scenario, ', '.join(scenarios)))
            return plugin_context.return_false()
    
    stdio.verbose('set scenario %s.' % scenario)
    plugin_context.set_variable('scenario', scenario)
    return plugin_context.return_true()
