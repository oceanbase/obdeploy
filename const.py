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

# OceanBase official website
OB_OFFICIAL_WEBSITE = 'https://www.oceanbase.com/'

# post telemetry data to OceanBase official
TELEMETRY_WEBSITE = '<TELEMETRY_WEBSITE>'
TELEMETRY_URL = '{}/api/web/oceanbase/report'.format(TELEMETRY_WEBSITE if TELEMETRY_WEBSITE else 'https://openwebapi.oceanbase.com')
TELEMETRY_COMPONENT = 'obd'
TELEMETRY_COMPONENT_OB = "obd_web_ob"
TELEMETRY_COMPONENT_OCP = "obd_web_ocp"
TELEMETRY_SIG = 'dbe97393a695335d67de91dd4049ba'

# obdeploy version
VERSION = '<VERSION>'
# obdeploy build commit
REVISION = '<CID>'
# obdeploy build branch
BUILD_BRANCH = '<B_BRANCH>'
# obdeploy build time
BUILD_TIME = '<B_TIME>'

# obdeploy home path
CONST_OBD_HOME = "OBD_HOME"
# obdeploy forbidden variable
FORBIDDEN_VARS = (CONST_OBD_HOME)

# tool variable
COMP_OBCLIENT = "obclient"
COMP_OCEANBASE_DIAGNOSTIC_TOOL = "oceanbase-diagnostic-tool"
COMP_OBDIAG = "obdiag"
COMP_JRE = 'openjdk-jre'

# ocp
COMP_OCP_EXPRESS = 'ocp-express'
COMP_OCP_SERVER = 'ocp-server'
COMP_OCP_SERVER_CE = 'ocp-server-ce'
COMPS_OCP = [COMP_OCP_SERVER, COMP_OCP_SERVER_CE]

# ob
COMP_OB = "oceanbase"
COMP_OB_CE = "oceanbase-ce"
COMPS_OB = [COMP_OB, COMP_OB_CE]

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