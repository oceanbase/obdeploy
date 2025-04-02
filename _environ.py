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

# obd id
ENV_OBD_ID = "OBD_ID"

# obd dev mode. {0/1}
ENV_DEV_MODE = "OBD_DEV_MODE"

# obd lock mode. 0 - No lock mode, 1 - The deploy lock wiil be downgraded to shared lock, 2 - Default lock mode.
ENV_LOCK_MODE = "OBD_LOCK_MODE"

# base path which will be used by runtime dependencies sync and include config. {absolute path style}
ENV_BASE_DIR = "OBD_DEPLOY_BASE_DIR"

# the installation mode of remote repository. {cp/ln}
ENV_REPO_INSTALL_MODE = "OBD_REPO_INSTALL_MODE"

# disable rsync mode even if the rsync exists. {0/1}
ENV_DISABLE_RSYNC = "OBD_DISABLE_RSYNC"

ENV_DISABLE_PARALLER_EXTRACT = "OBD_DISALBE_PARALLER_EXTRACT"

# telemetry mode. 0 - disable, 1 - enable.
ENV_TELEMETRY_MODE = "TELEMETRY_MODE"

# telemetry log mode. 0 - disable, 1 - enable.
ENV_TELEMETRY_LOG_MODE = "TELEMETRY_LOG_MODE"

# telemetry reporter. {reporter name}
ENV_TELEMETRY_REPORTER = "TELEMETRY_REPORTER"

# ROOT IO DEFAULT CONFIRM. 0 - disable, 1 - enable.
ENV_DEFAULT_CONFIRM = "IO_DEFAULT_CONFIRM"

# Disable ssh ALGORITHMS.  1 - disable algorithms,  0 - enable algorithms.
ENV_DISABLE_RSA_ALGORITHMS = 'OBD_DISABLE_RSA_ALGORITHMS'

# set local connection when using host ip. {0/1} 0 - no local connection. 1 - local connection.
ENV_HOST_IP_MODE = "HOST_IP_MODE"

# obdeploy install pre path. default /
ENV_OBD_INSTALL_PRE = "OBD_INSTALL_PRE"

# obdeploy install path. default /usr/obd/
ENV_OBD_INSTALL_PATH = "OBD_INSTALL_PATH"

# obd web idle minite time before shutdown. default 30
# if you do not want to set idle time, you can set it to "infinity"
ENV_IDLE_TIME_BEFORE_SHUTDOWN_MINITES = "IDLE_TIME_BEFORE_SHUTDOWN_MINITES"

# obdesktop/docker mock cluster id
ENV_CUSTOM_CLUSTER_ID = "CUSTOM_CLUSTER_ID"

# obdeploy web type
ENV_OBD_WEB_TYPE = "OBD_WEB_TYPE"
