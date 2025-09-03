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
# OceanBase official website
OB_OFFICIAL_WEBSITE = 'https://www.oceanbase.com/'

# post telemetry data to OceanBase official
TELEMETRY_WEBSITE = '<TELEMETRY_WEBSITE>'
TELEMETRY_URL = '{}/api/web/oceanbase/report'.format(TELEMETRY_WEBSITE if TELEMETRY_WEBSITE else 'https://openwebapi.oceanbase.com')
TELEMETRY_COMPONENT = 'obd'
TELEMETRY_COMPONENT_OB = "obd_web_ob"
TELEMETRY_COMPONENT_OCP = "obd_web_ocp"
TELEMETRY_COMPONENT_FRONTEND = "obd_web_frontend"
TELEMETRY_SIG = 'dbe97393a695335d67de91dd4049ba'

# obdeploy version
VERSION = '<VERSION>'
# obdeploy build commit
REVISION = '<CID>'
# obdeploy build branch
BUILD_BRANCH = '<B_BRANCH>'
# obdeploy build time
BUILD_TIME = '<B_TIME>'
# obdeploy build plugin list
BUILD_PLUGIN_LIST = '<B_PLUGIN_LIST>'

#encrypt password
ENCRYPT_PASSWORD = 'ENCRYPT_PASSWORD'

#encrypt passkey
ENCRYPT_PASSKEY = 'ENCRYPT_PASSKEY'

# obdeploy home path
CONST_OBD_HOME = "OBD_HOME"
# obdeploy forbidden variable
FORBIDDEN_VARS = (CONST_OBD_HOME, ENCRYPT_PASSWORD, ENCRYPT_PASSKEY)

# tool variable
COMP_OBCLIENT = "obclient"
COMP_OCEANBASE_DIAGNOSTIC_TOOL = "oceanbase-diagnostic-tool"
COMP_OBDIAG = "obdiag"
COMP_JRE = 'openjdk-jre'

TPCC_PATH = "/usr/ob-benchmarksql/OB-BenchmarkSQL-5.0.jar"
TPCH_PATH = "/usr/tpc-h-tools/tpc-h-tools/bin/dbgen"

# ocp
COMP_OCP_EXPRESS = 'ocp-express'
COMP_OCP_SERVER = 'ocp-server'
COMP_OCP_SERVER_CE = 'ocp-server-ce'
COMPS_OCP = [COMP_OCP_SERVER, COMP_OCP_SERVER_CE]
COMPS_OCP_CE_AND_EXPRESS = [COMP_OCP_SERVER_CE, COMP_OCP_EXPRESS]

# ob
COMP_OB = "oceanbase"
COMP_OB_CE = "oceanbase-ce"
COMP_OB_STANDALONE = "oceanbase-standalone"
COMPS_OB = [COMP_OB, COMP_OB_CE, COMP_OB_STANDALONE]

# obproxy
COMP_ODP = "obproxy"
COMP_ODP_CE = "obproxy-ce"
COMPS_ODP = [COMP_ODP, COMP_ODP_CE]

# ob-configserver
COMP_OB_CONFIGSERVER = "ob-configserver"

# obagent
COMP_OBAGENT = 'obagent'

# oblogproxy
COMP_OBLOGPROXY = 'oblogproxy'

# obbinlog
COMP_OBBINLOG_CE = 'obbinlog-ce'
BINLOG_INSTANCE_OPERATORS = ['start', 'stop', 'drop']
BINLOG_INSTANCE_STATUS_OPERATORS_MAP = {
    'start': 'Running',
    'stop': 'Stop',
}

#prometheus
COMP_PROMETHEUS = 'prometheus'

COMP_ALERTMANAGER = 'alertmanager'

# service docs url
DISABLE_SWAGGER = '<DISABLE_SWAGGER>'

# component files type
PKG_RPM_FILE = 'rpm'
PKG_REPO_FILE = 'repository'

RSA_KEY_SIZE = 512

# test tool
TOOL_TPCH = 'obtpch'
TOOL_TPCC = 'obtpcc'
TOOL_SYSBENCH = 'ob-sysbench'
TEST_TOOLS = {
    TOOL_TPCH: 'tpch',
    TOOL_TPCC: 'tpcc',
    TOOL_SYSBENCH: 'sysbench',
}
TOOL_TPCC_BENCHMARKSQL = 'OB-BenchmarkSQL-5.0.jar'

#workflow stages
STAGE_FIRST = 10
STAGE_SECOND = 20
STAGE_THIRD = 30
STAGE_FOURTH = 40
STAGE_FIFTH = 50
STAGE_SIXTH = 60
STAGE_SEVENTH = 70
STAGE_EIGHTH = 80
STAGE_NINTH = 90
STAGE_TENTH = 100

IDLE_TIME_BEFORE_SHUTDOWN_MINITES = 120

#obshell task type
TENANT_BACKUP = 'backup'
TENANT_RESTORE = 'restore'

#standalone
INTERACTIVE_INSTALL = 'INTERACTIVE_INSTALL'

SERVICE_MODE = 'SERVICE'
LOCATION_MODE = 'LOCATION'

ALERTMANAGER_DEFAULT_RECEIVER = {
    "receivers": ["mock_webhook"]
}
ALERTMANAGER_DEFAULT_RECEIVER_CONF = {
    "mock_webhook":{
        "receiver_type": "webhook",
        "url": 'http://127.0.0.1:5001/',
    }
}
