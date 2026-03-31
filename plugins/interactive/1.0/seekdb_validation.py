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

"""Shared SeekDB install validation: dir_check, check_avail_memory, client wrapper. Used by base_info and seekdb_confirm_config."""

from __future__ import absolute_import, division, print_function

import os
import platform
import re
import socket

import const
from ssh import SshClient, SshConfig, LocalClient
from tool import GetStdio, get_port_socket_inode

CLOG_MIN_BYTES = 2 * (1024 ** 3)
AVAIL_MEM_MIN_BYTES = 1 << 30


def is_valid_ip(ip):
    """Return True if ip is a valid IPv4, IPv6 address, or 'localhost'."""
    if not ip or not isinstance(ip, str):
        return False
    ip = ip.strip()
    if not ip:
        return False
    if ip.lower() == 'localhost':
        return True
    try:
        socket.inet_pton(socket.AF_INET, ip)
        return True
    except (socket.error, AttributeError):
        try:
            socket.inet_pton(socket.AF_INET6, ip)
            return True
        except (socket.error, AttributeError):
            return False


def is_loopback_ip(ip):
    """Return True if ip is a loopback address (127.x.x.x or localhost). Primary SeekDB should not use loopback."""
    if not ip or not isinstance(ip, str):
        return False
    ip = ip.strip()
    if not ip:
        return False
    if ip.lower() == 'localhost':
        return True
    if ip == '127.0.0.1':
        return True
    if ip.startswith('127.'):
        return True
    return False


def parse_port(port_str):
    """Return (True, port_int) if port_str is a valid port 1-65535, else (False, None)."""
    if port_str is None:
        return False, None
    s = str(port_str).strip()
    if not s:
        return False, None
    try:
        port = int(s)
        if 1 <= port <= 65535:
            return True, port
    except (ValueError, TypeError):
        pass
    return False, None


def is_port_in_use(client, port, stdio=None):
    """Check if the given port is in use on the target host (via client). Uses /proc/net (same as tool.get_port_socket_inode)."""
    if not client or port is None:
        return False
    port = int(port)
    io = stdio if stdio is not None else GetStdio.stdio()
    socket_inodes = get_port_socket_inode(client, port, stdio=io)
    return bool(socket_inodes)


class _LocalClientWrapper(object):
    """Wrapper so LocalClient has the same interface as SshClient (execute_command returning .stdout, .config.username)."""

    def __init__(self, stdio, username):
        self.stdio = stdio
        self.config = type("Config", (), {"username": username})()

    def execute_command(self, cmd, timeout=None, stdio=None):
        return LocalClient.execute_command(cmd, stdio=stdio or self.stdio)


def _dir_check(client, stdio, dir_path, create_dir=False, min_disk_bytes=None):
    """
    Reference oceanbase_config_input dir_check: absolute path, exists and empty and r/w, or parent writable; optionally create and check disk.
    Returns True if valid.
    """
    if not dir_path or not str(dir_path).strip():
        stdio.warn("Directory path cannot be empty.")
        return False
    dir_path = str(dir_path).strip()
    if not os.path.isabs(dir_path):
        stdio.warn("The directory must be an absolute path. Please try again.")
        return False

    dir_exists = client.execute_command("[ -d '%s' ] && echo true || echo false" % dir_path.replace("'", "'\\''")).stdout.strip() == "true"

    if dir_exists:
        is_empty = client.execute_command(
            "[ -z \"$(ls -A '%s' 2>/dev/null)\" ] && echo true || echo false" % dir_path.replace("'", "'\\''")
        ).stdout.strip() == "true"
        if not is_empty:
            stdio.warn("The directory must be empty. Please choose an empty directory.")
            return False
        can_access = client.execute_command(
            "[ -r '%s' ] && [ -w '%s' ] && echo true || echo false" % (dir_path.replace("'", "'\\''"), dir_path.replace("'", "'\\''"))
        ).stdout.strip() == "true"
        if not can_access:
            stdio.warn("The current user does not have read/write permissions for this directory. Please choose a directory with the required access.")
            return False
    else:
        # Walk up with dirname(1) until an existing parent is found; dirname eventually stabilizes at /.
        parent_dir = dir_path
        while True:
            escaped = parent_dir.replace("'", "'\\''")
            parent_dir = client.execute_command("dirname '%s'" % escaped).stdout.strip()
            if not parent_dir:
                stdio.warn("Invalid directory path for parent resolution.")
                return False
            parent_exists = client.execute_command("[ -e '%s' ] && echo true || echo false" % parent_dir.replace("'", "'\\''")).stdout.strip() == "true"
            if parent_exists:
                parent_accessible = client.execute_command(
                    "[ -w '%s' ] && [ -r '%s' ] && echo true || echo false" % (parent_dir.replace("'", "'\\''"), parent_dir.replace("'", "'\\''"))
                ).stdout.strip() == "true"
                if not parent_accessible:
                    stdio.warn("The current user does not have read/write permissions for the parent directory %s." % parent_dir)
                    return False
                break
            if parent_dir == '/':
                stdio.warn("Cannot resolve a valid parent directory for %s." % dir_path)
                return False

    if create_dir:
        result = client.execute_command("mkdir -p '%s' && echo SUCCESS || echo FAILED" % dir_path.replace("'", "'\\''")).stdout
        if "SUCCESS" not in result:
            stdio.warn("Failed to create directory %s." % dir_path)
            return False

    if min_disk_bytes is not None:
        try:
            path_to_query = dir_path.replace("'", "'\\''")
            avail_kb = 0
            while path_to_query:
                df_cmd = "df -Pk '%s' 2>/dev/null | tail -1 | awk '{print $4}'" % path_to_query
                out = client.execute_command(df_cmd).stdout.strip()
                if out and out.isdigit():
                    avail_kb = int(out)
                    break
                parent = client.execute_command("dirname '%s'" % path_to_query).stdout.strip()
                if not parent or parent == path_to_query:
                    break
                path_to_query = parent
            disk_available = avail_kb * 1024
            if disk_available < min_disk_bytes:
                stdio.warn("Insufficient disk space in the directory (need >= %dG, available less). Please choose another directory." % (min_disk_bytes // (1024 ** 3)))
                return False
        except (ValueError, AttributeError) as e:
            stdio.warn("Failed to check disk space: %s" % e)
            return False

    return True


def _check_avail_memory(client, stdio):
    """Check available memory >= 1G. Returns True if ok."""
    is_darwin = platform.system() == const.PLATFORM_DARWIN
    if is_darwin:
        ret = client.execute_command("sysctl -n hw.memsize")
        total_mem = int(ret.stdout.strip()) if ret and ret.stdout else 0
        vm = client.execute_command("vm_stat")
        free_pages = 0
        inactive_pages = 0
        if vm and vm.stdout:
            for line in vm.stdout.split("\n"):
                if "Pages free" in line:
                    m = re.search(r"\d+", line)
                    if m:
                        free_pages = int(m.group())
                elif "Pages inactive" in line:
                    m = re.search(r"\d+", line)
                    if m:
                        inactive_pages = int(m.group())
        page_size = 16384
        avail_mem = (free_pages + inactive_pages) * page_size
    else:
        ret = client.execute_command("cat /proc/meminfo")
        total_mem = 0
        avail_mem = 0
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
    if avail_mem < AVAIL_MEM_MIN_BYTES:
        stdio.warn("Available memory on target machine < 1G (required >= 1G). Please ensure the machine has enough memory and try again.")
        return False
    return True
