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

"""Pure interactive: show config list from namespace, confirm or edit; validate after each edit; store confirmed_config."""

from __future__ import absolute_import, division, print_function

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
    parse_port,
    is_port_in_use,
)


def _paths_must_differ(stdio, config_dict):
    """Check non-empty home_path, data_dir, redo_dir are pairwise different. Return (True, None) or (False, msg)."""
    paths = []
    for k in ("home_path", "data_dir", "redo_dir"):
        v = (config_dict.get(k) or "").strip()
        if v:
            paths.append(os.path.normpath(v))
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            if paths[i] == paths[j]:
                return False, "home_path, data_dir and redo_dir must be different."
    return True, None


def _get_client(stdio, config_dict, base_info):
    """Build client (local wrapper or SSH) from config and base_info for validation."""
    ip = config_dict.get("IP") or config_dict.get("ip") or (base_info or {}).get("ip", "")
    user = config_dict.get("User") or config_dict.get("user") or (base_info or {}).get("user", "")
    password = (base_info or {}).get("password") or ""
    ssh_port_raw = config_dict.get("ssh_port") or (base_info or {}).get("ssh_port") or "22"
    ok_sp, ssh_port_val = parse_port(ssh_port_raw)
    if not ok_sp:
        ssh_port_val = 22
    if not ip or not user:
        return None
    is_local = ip in ("127.0.0.1", "localhost") or ip == NetUtil.get_host_ip()
    if is_local:
        return _LocalClientWrapper(stdio, user)
    ssh_client = SshClient(SshConfig(ip, user, password or None, port=ssh_port_val), stdio)
    if not ssh_client.connect(stdio=stdio, exit=False):
        stdio.warn("Failed to connect to %s for validation. Check password in base_info." % ip)
        return None
    return ssh_client


def _validate_field(key, new_val, config_after_edit, client, stdio):
    """
    Validate a single field value. config_after_edit is the full config dict with this key already set to new_val.
    Returns (True, None) if valid, (False, error_message) if invalid.
    """
    if key in ("IP", "User", "auto_start"):
        if key == "auto_start":
            s = (new_val or "").strip().lower()
            if not s or s in InteractiveUI.YES_VALUES or s in InteractiveUI.NO_VALUES:
                return True, None
            return False, "Must be y/yes/n/no or true/false."
        if key == "IP":
            if not (new_val or "").strip():
                return False, "IP cannot be empty."
            if not is_valid_ip(new_val):
                return False, "Invalid IP format. Enter a valid IPv4, IPv6 address, or 'localhost'."
            return True, None
        if not (new_val or "").strip():
            return False, "Value cannot be empty."
        return True, None

    if key == "home_path":
        if not client:
            return False, "Cannot validate home_path without client (check IP/User/password)."
        if not (new_val or "").strip():
            return False, "home_path is required."
        if not _dir_check(client, stdio, new_val.strip(), create_dir=False):
            return False, "home_path validation failed."
        ok, err = _paths_must_differ(stdio, config_after_edit)
        if not ok:
            return False, err
        return True, None

    if key == "data_dir":
        val = (new_val or "").strip()
        if not val:
            ok, err = _paths_must_differ(stdio, config_after_edit)
            return (False, err) if not ok else (True, None)
        if not client:
            return False, "Cannot validate data_dir without client (check IP/User/password)."
        if not _dir_check(client, stdio, val, create_dir=False):
            return False, "data_dir validation failed."
        ok, err = _paths_must_differ(stdio, config_after_edit)
        if not ok:
            return False, err
        return True, None

    if key == "redo_dir":
        val = (new_val or "").strip()
        if not val:
            ok, err = _paths_must_differ(stdio, config_after_edit)
            return (False, err) if not ok else (True, None)
        if not client:
            return False, "Cannot validate redo_dir without client."
        if not _dir_check(client, stdio, val, create_dir=False, min_disk_bytes=CLOG_MIN_BYTES):
            return False, "redo_dir validation failed (path or disk >= 2G)."
        ok, err = _paths_must_differ(stdio, config_after_edit)
        if not ok:
            return False, err
        if not _check_avail_memory(client, stdio):
            return False, "Available memory on target < 1G."
        return True, None

    if key in ("memory_limit", "memory_hard_limit"):
        new_val = InteractiveUI.normalize_size_input(new_val) or new_val
        try:
            cap = Capacity(new_val)
            if cap.bytes <= 0:
                return False, "Must be a positive size (e.g. 1G, 4G)."
        except Exception as e:
            return False, "Invalid size: %s" % e
        if key == "memory_limit":
            hard_raw = (config_after_edit.get("memory_hard_limit") or "").strip()
            hard_str = InteractiveUI.normalize_size_input(hard_raw) or hard_raw
            if not hard_str:
                return False, "memory_hard_limit is empty. Set memory_hard_limit first, then adjust memory_limit."
            try:
                hard_cap = Capacity(hard_str)
                if hard_cap.bytes <= 0:
                    return False, "memory_hard_limit must be positive."
            except Exception as e:
                return False, "Cannot parse memory_hard_limit (%s): %s. Fix memory_hard_limit first." % (hard_raw, e)
            if cap.bytes > hard_cap.bytes:
                return (
                    False,
                    "memory_limit (%s) is greater than memory_hard_limit (%s). memory_limit must be less than or equal to memory_hard_limit."
                    % (new_val, hard_str),
                )
        if key == "memory_hard_limit":
            soft_raw = (config_after_edit.get("memory_limit") or "").strip() or "0"
            soft_str = InteractiveUI.normalize_size_input(soft_raw) or soft_raw
            try:
                soft_cap = Capacity(soft_str)
                if cap.bytes < soft_cap.bytes:
                    return False, "memory_hard_limit must be >= memory_limit (%s)." % soft_str
            except Exception as e:
                return False, "Cannot parse memory_limit (%s): %s." % (soft_raw, e)
        return True, None

    if key in ("datafile_maxsize", "log_disk_size"):
        new_val = InteractiveUI.normalize_size_input(new_val) or new_val
        try:
            cap = Capacity(new_val)
            if cap.bytes <= 0:
                return False, "Must be a positive size."
        except Exception as e:
            return False, "Invalid size: %s" % e
        return True, None

    if key == "max_syslog_file_count":
        try:
            n = int(new_val)
            if n < 1:
                return False, "Must be >= 1."
        except (ValueError, TypeError):
            return False, "Must be an integer."
        return True, None

    if key == "ssh_port":
        ok, port_val = parse_port(new_val)
        if not ok:
            return False, "SSH port must be a number between 1 and 65535."
        return True, None

    if key in ("mysql_port", "rpc_port", "obshell_port"):
        ok, port_val = parse_port(new_val)
        if not ok:
            return False, "Port must be a number between 1 and 65535."
        try:
            mp = int((config_after_edit.get("mysql_port") or "0").strip() or 0)
            op = int((config_after_edit.get("obshell_port") or "2886").strip() or 2886)
            rp = config_after_edit.get("rpc_port")
            rp = int(rp) if rp not in (None, "") else None
        except (ValueError, TypeError):
            mp, op, rp = 0, 2886, None
        if key == "mysql_port":
            if port_val == op:
                return False, "MySQL port must differ from OBShell port (%s)." % op
            if rp is not None and port_val == rp:
                return False, "MySQL port must differ from RPC port (%s)." % rp
        elif key == "rpc_port":
            if port_val == mp:
                return False, "RPC port must differ from MySQL port (%s)." % mp
            if port_val == op:
                return False, "RPC port must differ from OBShell port (%s)." % op
        else:
            if port_val == mp:
                return False, "OBShell port must differ from MySQL port (%s)." % mp
            if rp is not None and port_val == rp:
                return False, "OBShell port must differ from RPC port (%s)." % rp
        if client and key == "obshell_port" and is_port_in_use(client, port_val, stdio):
            return False, "Port %s is already in use on the target." % port_val
        return True, None

    return True, None


def _fmt_cap_bytes(b):
    """Format byte size as human string for config (e.g. 3G)."""
    if b >= 1024 ** 4:
        return "%dT" % (b // (1024 ** 4))
    if b >= 1024 ** 3:
        return "%dG" % (b // (1024 ** 3))
    if b >= 1024 ** 2:
        return "%dM" % (b // (1024 ** 2))
    return "%d" % b


def seekdb_confirm_config(plugin_context, *args, **kwargs):
    config_list = plugin_context.get_variable("config_list", spacename="seekdb")
    if not config_list:
        plugin_context.stdio.error("config_list not in namespace. Run compute_config first.")
        return plugin_context.return_false()
    stdio = plugin_context.stdio
    base_info = plugin_context.get_variable("base_info", spacename="interactive")
    config_list = list(config_list)
    client = None

    while True:
        stdio.print("--- Config summary ---")
        for i, (k, v) in enumerate(config_list):
            stdio.print("  %d. %s = %s" % (i + 1, k, v))
        install_mode = plugin_context.get_variable("install_mode", spacename="interactive") or "standalone"
        if install_mode in ["primary", "standby"]:
            mem_str = dict(config_list).get("memory_limit") or ""
            mem_bytes = Capacity(InteractiveUI.normalize_size_input(mem_str) or mem_str).bytes
            if mem_bytes < 6 * (1024 ** 3):
                stdio.warn(
                    "memory_limit is below 6G. For a primary cluster this is small; standby sync may be slow. Consider 6G or more if you plan heavy replication."
                )

        confirm_ans = InteractiveUI.prompt("Confirm config? (y/yes or n/no to modify)", "yes")
        if confirm_ans is None:
            return plugin_context.return_false()
        if InteractiveUI.parse_yes_no(confirm_ans, default_yes=True):
            break
        edit_options = [k for k, _ in config_list]
        idx_edit = InteractiveUI.single_choice("Select item to edit", edit_options, default_index=0, hint="↑↓ move   Enter confirm   q back")
        if idx_edit is None or idx_edit < 0:
            continue
        key_edit, cur_val = config_list[idx_edit]
        new_val = InteractiveUI.prompt("New value (current: %s)" % cur_val, (str(cur_val)[:-1] + ', unit: G') if str(cur_val)[-1] == "G" else cur_val)
        if new_val == "":
            continue
        if key_edit in ("memory_limit", "memory_hard_limit", "datafile_maxsize", "log_disk_size"):
            new_val = InteractiveUI.normalize_size_input(new_val) or new_val
        config_dict = dict(config_list)
        config_dict[key_edit] = new_val
        if key_edit == "ssh_port":
            client = None
        if client is None and key_edit in ("home_path", "data_dir", "redo_dir", "mysql_port", "rpc_port", "obshell_port", "ssh_port"):
            client = _get_client(stdio, config_dict, base_info)
        ok, err = _validate_field(key_edit, new_val, config_dict, client, stdio)
        if not ok:
            stdio.warn("Validation failed: %s" % (err or "invalid"))
            continue
        if key_edit in ("mysql_port", "rpc_port", "obshell_port", "ssh_port"):
            _, port_val = parse_port(new_val)
            new_val = str(port_val)
        config_list[idx_edit] = (key_edit, new_val)
        stdio.print("  Updated %s = %s" % (key_edit, new_val))
        install_mode = plugin_context.get_variable("install_mode", spacename="interactive") or "standalone"
        run_mode = plugin_context.get_variable("install_run_mode", spacename="interactive") or "dev"
        if key_edit == "memory_limit" and install_mode in ("primary", "standby"):
            mem_bytes = Capacity(new_val).bytes
            log_disk_str = _fmt_cap_bytes(mem_bytes * 3)
            for i, (k, _) in enumerate(config_list):
                if k == "log_disk_size":
                    config_list[i] = ("log_disk_size", log_disk_str)
                    break
        elif (key_edit == ("memory_limit") and install_mode == "standalone"):
            d = dict(config_list)
            soft_raw = (d.get("memory_limit") or "").strip()
            soft_norm = InteractiveUI.normalize_size_input(soft_raw) or soft_raw
            soft_b = Capacity(soft_norm).bytes
            log_b = max(CLOG_MIN_BYTES, soft_b // 2)
            log_disk_str = _fmt_cap_bytes(log_b)
            for i, (k, _) in enumerate(config_list):
                if k == "log_disk_size":
                    config_list[i] = ("log_disk_size", log_disk_str)
                    break

    plugin_context.set_variable("confirmed_config", dict(config_list))
    return plugin_context.return_true()
