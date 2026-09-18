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
import json
import os
import tempfile

from _rpm import Version
from tool import OrderedDict
from _errno import EC_CONFIG_CONFLICT_DIR, EC_FAIL_TO_INIT_PATH, InitDirFailedErrorMessage, EC_COMPONENT_DIR_NOT_EMPTY
from const import COMP_OB_SEEKDB


SEEKDB_DASHBOARD_FILTER_MIN_VERSION = Version('1.4.0')
SEEKDB_REMOVED_METRICS = (
    'seekdb_sysstat',
    'seekdb_waitevent_wait_seconds_total',
    'seekdb_waitevent_wait_total',
)
GRAFANA_DASHBOARD_WIDTH = 24

stdio = None
force = False
global_ret = True


def should_filter_seekdb_dashboard(repositories):
    for repository in repositories or []:
        if repository.name == COMP_OB_SEEKDB:
            return repository.version >= SEEKDB_DASHBOARD_FILTER_MIN_VERSION
    return False


def _safe_unlink(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _target_uses_removed_seekdb_metric(target):
    expression = target.get('expr', '')
    return any(metric in expression for metric in SEEKDB_REMOVED_METRICS)


def _layout_dashboard_section(row, panels, start_y):
    if row:
        row_grid = row.setdefault('gridPos', {})
        row_grid.update({'x': 0, 'y': start_y, 'w': GRAFANA_DASHBOARD_WIDTH})
        start_y += row_grid.get('h', 1)

    if len(panels) == 1:
        panel_grid = panels[0].setdefault('gridPos', {})
        panel_grid.update({'x': 0, 'y': start_y, 'w': GRAFANA_DASHBOARD_WIDTH})
        return start_y + panel_grid.get('h', 1)

    current_x = 0
    current_row_height = 0
    for panel in panels:
        panel_grid = panel.setdefault('gridPos', {})
        panel_width = min(panel_grid.get('w', 12), GRAFANA_DASHBOARD_WIDTH)
        panel_height = panel_grid.get('h', 1)
        if current_x and current_x + panel_width > GRAFANA_DASHBOARD_WIDTH:
            start_y += current_row_height
            current_x = 0
            current_row_height = 0
        panel_grid.update({'x': current_x, 'y': start_y, 'w': panel_width})
        current_x += panel_width
        current_row_height = max(current_row_height, panel_height)
    return start_y + current_row_height


def filter_seekdb_dashboard(dashboard):
    sections = []
    current_row = None
    current_panels = []

    def flush_section():
        if current_panels:
            sections.append((current_row, current_panels[:]))

    for panel in dashboard.get('panels', []):
        if panel.get('type') == 'row':
            flush_section()
            current_row = panel
            current_panels = []
            continue

        targets = panel.get('targets', [])
        if targets:
            supported_targets = [
                target for target in targets
                if not _target_uses_removed_seekdb_metric(target)
            ]
            if not supported_targets:
                continue
            panel['targets'] = supported_targets
        current_panels.append(panel)
    flush_section()

    filtered_panels = []
    next_y = 0
    for row, panels in sections:
        if row:
            filtered_panels.append(row)
        filtered_panels.extend(panels)
        next_y = _layout_dashboard_section(row, panels, next_y)

    dashboard['panels'] = filtered_panels
    dashboard['version'] = dashboard.get('version', 0) + 1
    return dashboard


def create_filtered_seekdb_dashboard(dashboard_path):
    fd, filtered_path = tempfile.mkstemp(prefix='obd-seekdb-dashboard-', suffix='.json')
    os.close(fd)
    try:
        with open(dashboard_path, 'r') as dashboard_file:
            dashboard = json.load(dashboard_file, object_pairs_hook=OrderedDict)
        filter_seekdb_dashboard(dashboard)
        with open(filtered_path, 'w') as dashboard_file:
            json.dump(dashboard, dashboard_file, ensure_ascii=False, indent=2)
            dashboard_file.write('\n')
        return filtered_path
    except Exception:
        _safe_unlink(filtered_path)
        raise


def critical(*arg, **kwargs):
    global global_ret
    global_ret = False
    stdio.error(*arg, **kwargs)


def init(plugin_context, source_option=None, *args, **kwargs):
    global stdio, force
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    deploy_name = plugin_context.deploy_name
    servers_dirs = {}
    force = getattr(plugin_context.options, 'force', False)
    clean = getattr(plugin_context.options, 'clean', False)
    stdio.start_loading('Initializes grafana work home')

    path_list = ['data_dir','logs_dir', 'plugins_dir', 'provisioning_dir']
    all_path_list = ['home_path'] + path_list
    for server in cluster_config.servers:
        ip = server.ip
        if ip not in servers_dirs:
            servers_dirs[ip] = {}
        dirs = servers_dirs[ip]
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']

        for key in all_path_list:
            if server_config.get(key):
                path = server_config[key]
                if path in dirs:
                    critical(EC_CONFIG_CONFLICT_DIR.format(server1=server, path=path, server2=dirs[path]['server'], key=dirs[path]['key']))
                    continue
                dirs[path] = {
                    'server': server,
                    'key': key,
                }

        stdio.verbose('%s init grafana work home', server)
        need_clean = force
        if clean and not force:
            if client.execute_command('bash -c \'if [[ "$(ls -d {0} 2>/dev/null)" != "" && ! -O {0} ]]; then exit 0; else exit 1; fi\''.format(home_path)):
                owner = client.execute_command("ls -ld %s | awk '{print $3}'" % home_path).stdout.strip()
                err_msg = ' {} is not empty, and the owner is {}'.format(home_path, owner)
                critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err_msg))
                continue
            need_clean = True
        
        bin_path = '%s/bin/grafana-server' % home_path
        grafana_pid_path = '%s/run/grafana.pid' % home_path
        ini_path = '%s/conf/obd-grafana.ini' % home_path
        pid_cmd = '%s --homepath=%s --config=%s --pidfile=%s' % (bin_path, home_path, ini_path, grafana_pid_path)
        if need_clean:
            clean_ret = True
            client.execute_command(
                "pkill -9 -u `whoami` -f '%s'" % (pid_cmd))
            for key in all_path_list:
                if server_config.get(key):
                    ret = client.execute_command('rm -fr %s/*' % server_config[key], timeout=-1)
                    if not ret:
                        clean_ret = False
                        critical(EC_FAIL_TO_INIT_PATH.format(server=server, key=server_config[key], msg=ret.stderr))
            if not clean_ret:
                continue
        
        ret = client.execute_command('bash -c "mkdir -p %s/{run,conf}"' % home_path)
        if ret:
            link_path_map = OrderedDict({
                'data_dir': 'data',
                'logs_dir': 'data/log',
                'plugins_dir': 'data/plugins',
                'provisioning_dir': 'conf/provisioning'
            })
            mkdir_ret = True
            for k in path_list:
                link_path = os.path.join(home_path, link_path_map[k]) 
                target_path = server_config.get(k, link_path)
                if client.execute_command('mkdir -p %s' % target_path):
                    ret = client.execute_command('ls %s' % target_path)
                    if not ret or ret.stdout.strip():
                        critical(EC_FAIL_TO_INIT_PATH.format(server=server, key=k, msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=target_path)))
                        source_option == "deploy" and critical(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                        mkdir_ret = False
                        continue
                    client.execute_command("if [ ! '%s' -ef '%s' ]; then ln -sf %s %s; fi" % (target_path, link_path, target_path, link_path))
            if not mkdir_ret:
                continue

        dashboard_template_path = os.path.join(home_path, 'conf/provisioning/dashboards/templates')
        if client.execute_command('bash -c "mkdir -p %s"' % dashboard_template_path):
            deploy_components = cluster_config._deploy_config.components if getattr(cluster_config, '_deploy_config', None) else {}
            is_seekdb_deploy = COMP_OB_SEEKDB in deploy_components
            file_name = 'seekdb-metrics_rev1.json' if is_seekdb_deploy else 'oceanbase-metrics_rev1.json'
            dashboard = os.path.join(os.path.split(__file__)[0], file_name)
            filtered_dashboard = None
            try:
                if is_seekdb_deploy and should_filter_seekdb_dashboard(plugin_context.repositories):
                    filtered_dashboard = create_filtered_seekdb_dashboard(dashboard)
                    dashboard = filtered_dashboard
                client.put_file(dashboard, os.path.join(dashboard_template_path, file_name))
            finally:
                if filtered_dashboard:
                    _safe_unlink(filtered_dashboard)
        else:
            critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='conf/provisioning/dashboards/templates', msg=InitDirFailedErrorMessage.CREATE_FAILED.format(path=dashboard_template_path)))
            continue
        
        link_path = os.path.join(home_path, 'log')
        target_path = os.path.join(home_path, 'data/log')
        client.execute_command("ln -s %s %s" % (target_path, link_path))

    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
