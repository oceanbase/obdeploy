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

"""Pure interactive: prompt for IP, user, SSH port (remote, default 22), password, home_path, data_dir, redo_dir, auto_start; validate per-field and that the three paths differ; store in namespace."""

from __future__ import absolute_import, division, print_function

import getpass
import os

from _types import Capacity
from tool import InteractiveUI, NetUtil
from ssh import SshClient, SshConfig, LocalClient

from seekdb_validation import (
    CLOG_MIN_BYTES,
    _LocalClientWrapper,
    _dir_check,
    _check_avail_memory,
    is_valid_ip,
    is_loopback_ip,
    parse_port,
    is_port_in_use,
)


def _resolve_path(path, base):
    """If path is not absolute, join with base; then normalize."""
    if not path or not path.strip():
        return path
    path = path.strip()
    if not os.path.isabs(path):
        path = os.path.join(base, path)
    return os.path.normpath(path)


def _paths_must_differ(stdio, home_path, data_dir, redo_dir):
    """Return True if all non-empty paths are pairwise different; else warn and return False."""
    paths = []
    for p in (home_path, data_dir, redo_dir):
        if p and (p if isinstance(p, str) else "").strip():
            paths.append(os.path.normpath((p if isinstance(p, str) else "").strip()))
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            if paths[i] == paths[j]:
                stdio.error("home_path, data_dir and redo_dir must be different. Current: home_path=%s, data_dir=%s, redo_dir=%s" % (home_path, data_dir, redo_dir))
                return False
    return True


def base_info(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    default_ip = NetUtil.get_host_ip()
    default_user = getpass.getuser()
    ip = ""
    while True:
        ip = InteractiveUI.prompt("Server IP", ip or default_ip) or (ip or default_ip)
        if not ip or not ip.strip():
            stdio.warn("IP cannot be empty.")
            continue
        ip = ip.strip()
        if not is_valid_ip(ip):
            stdio.warn("Invalid IP format. Enter a valid IPv4 (e.g. 192.168.1.1), IPv6 address, or 'localhost'.")
            continue
        install_mode = plugin_context.get_variable("install_mode", spacename="interactive") or "standalone"
        if install_mode == "primary" and is_loopback_ip(ip):
            stdio.warn("Primary cluster cannot use loopback IP (127.x.x.x or localhost). Please enter another IP.")
            continue
        break
    user = InteractiveUI.prompt("Username", default_user) or default_user

    is_local = ip in ("127.0.0.1", "localhost") or ip == NetUtil.get_host_ip()
    password = ""
    client = None
    ssh_port_str = "22"
    while True:
        ssh_port_str = InteractiveUI.prompt("SSH port", ssh_port_str or "22").strip() or "22"
        ok_sp, ssh_port_val = parse_port(ssh_port_str)
        if not ok_sp:
            stdio.warn("Invalid SSH port. Enter a number between 1 and 65535.")
            continue
        ssh_port_str = str(ssh_port_val)
        break

    while True:
        password = InteractiveUI.prompt_password("Password (default empty)", password or "")
        ssh_client = SshClient(SshConfig(ip, user, password or None, port=int(ssh_port_str)), stdio)
        if ssh_client.connect(stdio=stdio, exit=False):
            client = ssh_client
            break
        stdio.warn("Failed to connect to %s (port %s). Please re-enter password or check SSH port." % (ip, ssh_port_str))

    cluster_name = plugin_context.get_variable('cluster_name', spacename='seekdb')
    if user == 'root':
        default_home = f'/{user}/{cluster_name}'
    else:
        default_home = f'/home/{user}/{cluster_name}'
    home_path = ""
    while True:
        home_path = InteractiveUI.prompt("Seekdb installation directory", home_path or default_home).strip() or default_home
        if not home_path:
            stdio.warn("home_path is required.")
            continue
        if not _dir_check(client, stdio, home_path, create_dir=False):
            continue
        break

    data_dir = ""
    while True:
        data_dir = InteractiveUI.prompt("Data directory (data_dir, optional)", data_dir if data_dir else "/data/1/seekdb").strip() or ""
        data_dir_abs = _resolve_path(data_dir, home_path) if data_dir else ""
        if data_dir_abs and not _dir_check(client, stdio, data_dir_abs, create_dir=False):
            continue
        if data_dir_abs and not _paths_must_differ(stdio, home_path, data_dir_abs, ""):
            data_dir += '/data1'
            continue
        data_dir = data_dir_abs
        break

    redo_dir = ""
    install_mode_for_redo = plugin_context.get_variable("install_mode", spacename="interactive") or "standalone"
    primary_log_disk_size = plugin_context.get_variable("primary_log_disk_size", spacename="seekdb") if install_mode_for_redo == "standby" else None
    min_clog_bytes = CLOG_MIN_BYTES
    if primary_log_disk_size and install_mode_for_redo == "standby":
        try:
            min_clog_bytes = Capacity(primary_log_disk_size).bytes
        except Exception:
            min_clog_bytes = CLOG_MIN_BYTES
    while True:
        redo_dir = InteractiveUI.prompt("Redo log directory (redo_dir, optional)", redo_dir if redo_dir else "/data/log1/seekdb").strip() or ""
        redo_dir_abs = _resolve_path(redo_dir, home_path) if redo_dir else ""
        if redo_dir_abs and not _dir_check(client, stdio, redo_dir_abs, create_dir=False, min_disk_bytes=min_clog_bytes):
            continue
        if redo_dir_abs and not _paths_must_differ(stdio, home_path, data_dir, redo_dir_abs):
            redo_dir += '/log1'
            continue
        if redo_dir_abs and not _check_avail_memory(client, stdio):
            continue
        redo_dir = redo_dir_abs
        break

    mysql_port = ""
    while True:
        mysql_port = InteractiveUI.prompt("MySQL port", mysql_port or "2881").strip() or "2881"
        ok, port_val = parse_port(mysql_port)
        if not ok:
            stdio.warn("Invalid port. Enter a number between 1 and 65535.")
            continue
        if is_port_in_use(client, port_val, stdio):
            stdio.warn("Port %s is already in use on the target. Please choose another port." % port_val)
            continue
        mysql_port = str(port_val)
        break

    install_mode = plugin_context.get_variable("install_mode", spacename="interactive") or "standalone"
    rpc_port = ""
    if install_mode in ("primary", "standby"):
        while True:
            rpc_port = InteractiveUI.prompt("RPC port", rpc_port or "2882").strip() or "2882"
            ok, port_val = parse_port(rpc_port)
            if not ok:
                stdio.warn("Invalid port. Enter a number between 1 and 65535.")
                continue
            if port_val == int(mysql_port):
                stdio.warn("RPC port must be different from MySQL port (%s)." % mysql_port)
                continue
            if is_port_in_use(client, port_val, stdio):
                stdio.warn("Port %s is already in use on the target. Please choose another port." % port_val)
                continue
            rpc_port = str(port_val)
            break

    obshell_port = "2886"
    if install_mode != "standby":
        while True:
            obshell_port = InteractiveUI.prompt("OBShell port", obshell_port or "2886").strip() or "2886"
            ok, port_val = parse_port(obshell_port)
            if not ok:
                stdio.warn("Invalid port. Enter a number between 1 and 65535.")
                continue
            if port_val == int(mysql_port):
                stdio.warn("OBShell port must be different from MySQL port (%s)." % mysql_port)
                continue
            if install_mode in ("primary", "standby") and rpc_port and port_val == int(rpc_port):
                stdio.warn("OBShell port must be different from RPC port (%s)." % rpc_port)
                continue
            if is_port_in_use(client, port_val, stdio):
                stdio.warn("Port %s is already in use on the target. Please choose another port." % port_val)
                continue
            obshell_port = str(port_val)
            break

    auto_start_s = InteractiveUI.prompt("Do you want to enable the Seekdb service to start automatically when the system boots up? (y/yes or n/no)", "no")
    auto_start = InteractiveUI.parse_yes_no(auto_start_s, default_yes=False)

    if not is_local and client:
        client.close(stdio=stdio)

    base_info_dict = {
        "ip": ip,
        "user": user,
        "password": password,
        "ssh_port": ssh_port_str,
        "home_path": home_path,
        "data_dir": data_dir,
        "redo_dir": redo_dir,
        "mysql_port": mysql_port,
        "obshell_port": obshell_port,
        "auto_start": auto_start,
    }
    if install_mode in ("primary", "standby"):
        base_info_dict["rpc_port"] = rpc_port
    plugin_context.set_variable("base_info", base_info_dict)
    return plugin_context.return_true()
