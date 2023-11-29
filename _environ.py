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


from __future__ import absolute_import, division, print_function

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
TELEMETRY_MODE = "TELEMETRY_MODE"

# telemetry log mode. 0 - disable, 1 - enable.
TELEMETRY_LOG_MODE = "TELEMETRY_LOG_MODE"

# ROOT IO DEFAULT CONFIRM. 0 - disable, 1 - enable.
ENV_DEFAULT_CONFIRM = "IO_DEFAULT_CONFIRM"

# Disable ssh ALGORITHMS.  1 - disable algorithms,  0 - enable algorithms.
ENV_DISABLE_RSA_ALGORITHMS = 'OBD_DISABLE_RSA_ALGORITHMS'

# set local connection when using host ip. {0/1} 0 - no local connection. 1 - local connection.
ENV_HOST_IP_MODE = "HOST_IP_MODE"