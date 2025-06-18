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
from collections import defaultdict

MINIMAL_CONFIG = '''
{0}:
  global:
    home_path: /root/oceanbase/oceanbase
'''

PKG_ESTIMATED_SIZE = defaultdict(lambda:0)
PKG_ESTIMATED_SIZE.update({"oceanbase-ce": 347142720, "oceanbase": 358142928, "obproxy-ce": 45424640, "obproxy": 56428687, "obagent": 76124864, "ocp-express": 95924680, "ocp-server-ce": 622854144})


OCEANBASE_CE = 'oceanbase-ce'
OCEANBASE = 'oceanbase'
OCEANBASE_STANDALONE = 'oceanbase-standalone'

CE = "ce"
BUSINESS = "business"
STANDALONE = "standalone"

OBPROXY_CE = 'obproxy-ce'
OBPROXY = 'obproxy'

OCP_EXPRESS = 'ocpexpress'
OCP_SERVER_CE = 'ocp-server-ce'
OCP_SERVER = 'ocp-server'
OBAGENT = 'obagent'
OB_CONFIGSERVER = 'obconfigserver'
PROMETHEUS = 'prometheus'
GRAFANA = 'grafana'

no_generate_comps = ['ob-configserver']

DESTROY_PLUGIN = "destroy"
INIT_PLUGINS = ("init",)
START_PLUGINS = ("start_check_pre", "start", "connect", "health_check", "display")
STOP_PLUGINS = ("stop",)
DEL_COMPONENT_PLUGINS = ("stop", "destroy")
CHANGED_COMPONENTS = ('obproxy-ce', 'obagent', 'ob-configserver', 'prometheus', 'grafana')
UPGRADE_PLUGINS = ("upgrade")
# filter component of oceanbase and obproxy version above 4.0
VERSION_FILTER = {
    OCEANBASE: "4.0.0.0",
    OCEANBASE_CE: "4.0.0.0",
    OBPROXY: "4.0.0",
    OBPROXY_CE: "4.0.0"
}

RUNNING = 'running'
FINISHED = 'finished'

GRACEFUL_TIMEOUT = 5

TASK_TYPE_INSTALL = 'install'
TASK_TYPE_START = 'start'
TASK_TYPE_STOP = 'stop'