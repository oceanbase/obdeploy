# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2023 OceanBase
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

import os
import re
import time
import json
import requests
from _rpm import Version
from copy import deepcopy
from requests.auth import HTTPBasicAuth

from tool import Cursor, FileUtil, YamlLoader
from _errno import EC_OBSERVER_CAN_NOT_MIGRATE_IN


def takeover_precheck(plugin_context, cursors=None, *args, **kwargs):
    try:
        # init variables, include get obcluster info from deploy config
        cluster_config = plugin_context.cluster_config
        clients = plugin_context.clients
        options = plugin_context.options
        stdio = plugin_context.stdio
        stdio.verbose(vars(cluster_config))
        cursors = plugin_context.get_return('connect').get_return('cursor') if not cursors else cursors
        cursor = cursors[cluster_config.servers[0]]
        ocp_info = cursor.info(stdio=stdio)
        stdio.verbose("get ocp info %s", ocp_info)
        ocp_version = Version(ocp_info['buildVersion'].split("_")[0])
        if ocp_version < Version("4.2.0"):
            stdio.error("unable to export obcluster to ocp, ocp version must be at least 4.2.0")
            return plugin_context.return_false(ocp_version=ocp_version)
        server = cluster_config.servers[0]
        mysql_port = cluster_config.get_global_conf().get("mysql_port")
        root_password = cluster_config.get_global_conf().get("root_password")
        if root_password is None or root_password == "":
            stdio.error("unable to export obcluster to ocp, root password is empty")
            return plugin_context.return_false(ocp_version=ocp_version)
        precheck_data = {"connectionMode": "direct", "address": server.ip, "port": mysql_port,
                         "rootSysPassword": root_password}
        proxyro_password = cluster_config.get_global_conf().get("proxyro_password")
        if proxyro_password is not None and proxyro_password != "":
            precheck_data.update({"proxyroPassword": proxyro_password})
        precheck_result = cursor.take_over_precheck(precheck_data, stdio=stdio)
        stdio.verbose("precheck result %s" % precheck_result)
        return plugin_context.return_true(ocp_version=ocp_version)
    except Exception as ex:
        stdio.error("do takeover precheck got exception:%s", ex)
        return plugin_context.return_false()