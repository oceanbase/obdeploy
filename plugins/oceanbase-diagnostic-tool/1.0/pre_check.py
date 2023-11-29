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
import os

import os
from copy import deepcopy
import re
from ssh import LocalClient
from _rpm import Version

import _errno as err
from tool import DirectoryUtil

def pre_check(plugin_context, gather_type=None, obdiag_path='', obdiag_new_version='1.0', utils_work_dir_check=False, version_check=False, *args, **kwargs):
    def utils_work_dir_checker(util_name):
        clients = plugin_context.clients
        cluster_config = plugin_context.cluster_config
        if util_name is None:
            stdio.verbose('util name not provided')
            return False
        for server in cluster_config.servers:
            home_path = cluster_config.get_server_conf(server).get('home_path')
            remote_path = os.path.join(home_path, 'bin')
            software_path = os.path.join(remote_path, util_name)
            client = clients[server]
            stdio.verbose('%s pre check' % (server))
            if not client.execute_command('[ -f %s ]' % software_path):
                stdio.verbose('%s util not exist: %s' % (server, software_path))
                return False
        stdio.stop_loading('succeed')
        return True

    def version_checker():
        client = LocalClient
        check_status = {}
        ret = client.execute_command('cd {} && ./obdiag version'.format(obdiag_path))
        if not ret:
            check_status = {'version_checker_status': False, 'obdiag_version': obdiag_new_version, 'obdiag_found': False}
            return check_status
        version_pattern = r'OceanBase\sDiagnostic\sTool:\s+(\d+\.\d+.\d+)'
        found = re.search(version_pattern, ret.stdout) or re.search(version_pattern, ret.stderr)
        if not found:
            check_status = {'version_checker_status': False, 'obdiag_version': obdiag_new_version, 'obdiag_found': False}
            return check_status
        else:
            major_version = found.group(1)
            if Version(major_version) > Version(obdiag_new_version):
                check_status = {'version_checker_status': True, 'obdiag_version': major_version, 'obdiag_found': True}
                return check_status
            else:
                check_status = {'version_checker_status': False, 'obdiag_version': major_version, 'obdiag_found': True}
                return check_status

    def store_dir_checker_and_handler():
        store_dir_option = getattr(plugin_context.options, 'store_dir', None)
        if (store_dir_option is not None) and (not DirectoryUtil.mkdir(store_dir_option, stdio=stdio)):
            return False
        else:
            return True

    stdio = plugin_context.stdio
    utils_work_dir_check_status = True
    version_check_status = True
    obdiag_version = obdiag_new_version
    obdiag_found = True
    skip = True
    if utils_work_dir_check:
        if gather_type in ['gather_clog', 'gather_slog', 'gather_all']:
            utils_work_dir_check_status = utils_work_dir_checker('ob_admin')
            if gather_type != 'gather_all':
                skip = False
    if version_check:
        res = version_checker()
        version_check_status = res['version_checker_status']
        obdiag_version = res['obdiag_version']
        obdiag_found = res['obdiag_found']
    store_dir_checker_status = store_dir_checker_and_handler()
    status = utils_work_dir_check_status and version_check_status and store_dir_checker_status
    if status:
        return plugin_context.return_true(version_status = version_check_status, utils_status = utils_work_dir_check_status, obdiag_version = obdiag_version, obdiag_found = obdiag_found, skip = skip)
    else:
        return plugin_context.return_false(version_status = version_check_status, utils_status = utils_work_dir_check_status, obdiag_version = obdiag_version, obdiag_found = obdiag_found, skip = skip)

