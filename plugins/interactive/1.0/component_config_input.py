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

from tool import port_check


def component_config_input(plugin_context, client, *args, **kwargs):
    stdio = plugin_context.stdio
    comp_confirm = stdio.confirm('Do you need to install the monitoring components (OBAgent, Prometheus, Grafana)?', default_option=False)
    if not comp_confirm:
        return plugin_context.return_true()
    ports = plugin_context.get_variable('ports')
    while True:
        monagent_http_port = stdio.read('Enter the OBAgent monitoring service port (Default: 8088):', blocked=True).strip() or 8088
        rv, ports = port_check(monagent_http_port, client, ports, stdio)
        if rv:
            break
        else:
            continue
    while True:
        mgragent_http_port = stdio.read('Enter the OBAgent management service port (Default: 8089):', blocked=True).strip() or 8089
        rv, ports = port_check(mgragent_http_port, client, ports, stdio)
        if rv:
            break
        else:
            continue
    while True:
        prometheus_port = stdio.read('Enter the Prometheus port (Default: 9090):', blocked=True).strip() or 9090
        rv, ports = port_check(prometheus_port, client, ports, stdio)
        if rv:
            break
        else:
            continue
    while True:
        grafana_port = stdio.read('Enter the Grafana port (Default: 3000):', blocked=True).strip() or 3000
        rv, ports = port_check(grafana_port, client, ports, stdio)
        if rv:
            break
        else:
            continue

    component_config = {
        "monagent_http_port": monagent_http_port,
        "mgragent_http_port": mgragent_http_port,
        "prometheus_port": prometheus_port,
        "grafana_port": grafana_port
    }

    return plugin_context.return_true(component_config=component_config)