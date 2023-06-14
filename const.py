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
# obdeploy install pre path
CONST_OBD_INSTALL_PRE = "OBD_INSTALL_PRE"
# obdeploy install path
CONST_OBD_INSTALL_PATH = "OBD_INSTALL_PATH"
# obdeploy forbidden variable
FORBIDDEN_VARS = (CONST_OBD_HOME, CONST_OBD_INSTALL_PRE, CONST_OBD_INSTALL_PATH)