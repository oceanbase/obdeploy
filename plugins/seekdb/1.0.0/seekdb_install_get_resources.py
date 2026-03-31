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

"""SeekDB install: get resources (memory, disk) on target host from base_info; store resources via set_variable.
Resource validation (redo >= 2G, avail_mem >= 1G) is done in base_info; this plugin only fetches and stores values."""

from __future__ import absolute_import, division, print_function

import re
import platform

import const
from tool import NetUtil
from ssh import SshClient, SshConfig, LocalClient


def _df_avail_kb(run_cmd, path):
    """
    Get available KB for the filesystem containing path. If path does not exist or df gives no output,
    walk up to parent directories until we get a valid value.
    """
    path_to_query = path.replace("'", "'\\''")
    while path_to_query:
        cmd = "df -Pk '%s' 2>/dev/null | tail -1 | awk '{print $4}'" % path_to_query
        ret = run_cmd(cmd)
        out = (ret.stdout or "").strip() if ret else ""
        if out and out.isdigit():
            return int(out)
        parent_ret = run_cmd("dirname '%s'" % path_to_query)
        parent = (parent_ret.stdout or "").strip() if parent_ret else ""
        if not parent or parent == path_to_query:
            return 0
        path_to_query = parent
    return 0


def seekdb_install_get_resources(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    base = plugin_context.get_variable("base_info", spacename="interactive")
    if not base:
        stdio.error("base_info not in namespace. Run base_info first.")
        return plugin_context.return_false()
    ip = base["ip"]
    user = base["user"]
    password = base.get("password") or ""
    data_dir = base.get("data_dir") or ""
    redo_dir = base.get("redo_dir") or ""
    home_path = base.get("home_path") or "."
    path_for_disk = data_dir or home_path
    path_for_clog = redo_dir or home_path
    is_local = ip in ("127.0.0.1", "localhost") or ip == NetUtil.get_host_ip()
    ssh_port = 22
    try:
        ssh_port = int(base.get("ssh_port") or 22)
    except (ValueError, TypeError):
        ssh_port = 22
    if not (1 <= ssh_port <= 65535):
        ssh_port = 22
    if is_local:
        def run_cmd(cmd):
            return LocalClient.execute_command(cmd, stdio=stdio)
    else:
        ssh_client = SshClient(SshConfig(ip, user, password or None, port=ssh_port), stdio)
        if not ssh_client.connect(stdio=stdio, exit=False):
            stdio.error("Failed to connect to %s" % ip)
            return plugin_context.return_false()

        def run_cmd(cmd):
            return ssh_client.execute_command(cmd, stdio=stdio)

    avail_kb = _df_avail_kb(run_cmd, path_for_clog)
    clog_avail_bytes = avail_kb * 1024

    total_mem = 0
    avail_mem = 0
    is_darwin = platform.system() == const.PLATFORM_DARWIN
    if is_darwin:
        ret = run_cmd("sysctl -n hw.memsize")
        total_mem = int(ret.stdout.strip()) if ret and ret.stdout else 0
        vm = run_cmd("vm_stat")
        free_pages = 0
        inactive_pages = 0
        if vm and vm.stdout:
            for line in vm.stdout.split("\n"):
                if "Pages free" in line:
                    free_pages = int(re.search(r"\d+", line).group())
                elif "Pages inactive" in line:
                    inactive_pages = int(re.search(r"\d+", line).group())
        page_size = 16384
        avail_mem = (free_pages + inactive_pages) * page_size
    else:
        ret = run_cmd("cat /proc/meminfo")
        if ret and ret.stdout:
            for line in ret.stdout.split("\n"):
                if line.startswith("MemTotal:"):
                    total_mem = int(line.split()[1]) * 1024
                elif line.startswith("MemAvailable:"):
                    avail_mem = int(line.split()[1]) * 1024
            if not avail_mem:
                for line in ret.stdout.split("\n"):
                    if line.startswith("MemFree:"):
                        avail_mem = int(line.split()[1]) * 1024
                        break

    free_disk_kb = _df_avail_kb(run_cmd, path_for_disk)
    free_disk_bytes = free_disk_kb * 1024

    plugin_context.set_variable("resources", {
        "clog_avail_bytes": clog_avail_bytes,
        "total_mem": total_mem,
        "avail_mem": avail_mem,
        "free_disk_bytes": free_disk_bytes,
    })
    return plugin_context.return_true()
