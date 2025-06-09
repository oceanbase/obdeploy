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
import json
from singleton_decorator import singleton
from optparse import Values

import const
from tool import COMMAND_ENV
import _environ as ENV
from service.handler.base_handler import BaseHandler
from service.model.deployments import TelemetryData
from _environ import ENV_TELEMETRY_REPORTER




@singleton
class TelemetryHandler(BaseHandler):
    def __init__(self):
        super().__init__()

    def get_telemetry_data(self, name):
        deploy = self.obd.deploy_manager.get_deploy_config(name)
        if not deploy or not COMMAND_ENV.get(ENV.ENV_TELEMETRY_MODE, default='1') == '1':
            msg = 'get deploy config failed for %s' % name
            return TelemetryData(data={}, msg=msg)
        repositories = self.obd.load_local_repositories(deploy.deploy_info, False)
        repositories = self.obd.sort_repository_by_depend(repositories, deploy.deploy_config)
        if const.COMP_OB_CE not in deploy.deploy_config.components:
            msg = 'get deploy config failed for %s' % name
            return TelemetryData(data={}, msg=msg)
        clients = self.obd.get_clients(deploy.deploy_config, repositories)
        cluster_config = deploy.deploy_config.components[const.COMP_OB_CE]
        data = {}
        for component, _ in self.obd.namespaces.items():
            data[component] = _.get_variable('run_result')
        COMMAND_ENV.set(ENV_TELEMETRY_REPORTER, const.TELEMETRY_COMPONENT_FRONTEND, save=True)
        self.obd.set_options(Values({'data': json.dumps(data)}))
        workflows = self.obd.get_workflows('get_telemetry_data')
        component_kwargs = {}
        for repository in repositories:
            component_kwargs[repository.name] = {'cluster_config': cluster_config, 'clients': clients}
        ret = self.obd.run_workflow(workflows, **component_kwargs)
        if not ret:
            msg = 'run workflow get_telemetry_data failed'
            return TelemetryData(data={}, msg=msg)
        data = self.obd.get_namespace('telemetry').get_return('telemetry_info_collect').kwargs.get('telemetry_post_data', {})
        return TelemetryData(data=data, msg='')
