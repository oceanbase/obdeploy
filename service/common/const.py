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

CE = "ce"
BUSINESS = "business"

OBPROXY_CE = 'obproxy-ce'
OBPROXY = 'obproxy'

OCP_EXPRESS = 'ocpexpress'
OCP_SERVER_CE = 'ocp-server-ce'
OCP_SERVER = 'ocp-server'
OBAGENT = 'obagent'
OB_CONFIGSERVER = 'obconfigserver'

no_generate_comps = ['ob-configserver']

DESTROY_PLUGIN = "destroy"
INIT_PLUGINS = ("init",)
START_PLUGINS = ("start_check", "start", "connect", "bootstrap", "display")
DEL_COMPONENT_PLUGINS = ("stop", "destroy")
CHANGED_COMPONENTS = ('obproxy-ce', 'obagent', 'ocp-express', 'ob-configserver', 'prometheus', 'grafana')
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

