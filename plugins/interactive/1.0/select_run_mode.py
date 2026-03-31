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

"""Pure interactive: select Dev/Prod mode and optional Prod memory params; store in namespace."""

from __future__ import absolute_import, division, print_function

from tool import InteractiveUI
from _types import Capacity


def select_run_mode(plugin_context, *args, **kwargs):
    resources = plugin_context.get_variable("resources", spacename="seekdb")
    if not resources:
        plugin_context.stdio.error("Resources not in namespace. Run get_resources first.")
        return plugin_context.return_false()
    total_mem = resources.get("total_mem", 0)
    free_disk_bytes = resources.get("free_disk_bytes", 0)
    prod_disabled = total_mem < 5 * (1024 ** 3)
    options_mode = ["Dev (development)", "Prod (production)"]
    disabled = {1} if prod_disabled else set()
    idx = InteractiveUI.single_choice("Select mode", options_mode, default_index=0, disabled_indices=disabled,
        hint="↑↓ move   Enter confirm   q quit")
    if idx is None:
        plugin_context.stdio.error("Not a TTY. Run in interactive terminal.")
        return plugin_context.return_false()
    if idx < 0:
        return plugin_context.return_false()
    is_dev = idx == 0
    plugin_context.set_variable("install_run_mode", "dev" if is_dev else "prod")
    if not is_dev:
        base_mem_default = int(total_mem * 0.9)
        total_g = max(1, int(total_mem / (1024 ** 3)))
        base_g = max(1, int(base_mem_default / (1024 ** 3)))
        base_default_g = "%d" % base_g if base_g > 5 else "5"
        while True:
            base_input = InteractiveUI.prompt("SeekDB Max Memory (Configurable Range[5, %s], unit: G)" % total_g, base_default_g)
            if int(base_input) <= total_g:
                break
            else:
                plugin_context.stdio.error("SeekDB Max Memory must be less than %dG" % total_g)
        base_input = InteractiveUI.normalize_size_input(base_input) or base_default_g
        try:
            base_mem = int(Capacity(base_input).bytes) if base_input else base_mem_default
        except Exception:
            base_mem = base_mem_default
        strategies = ["Balanced (Reduce memory usage when possible)", "Performance (Use more memory to enhance performance)"]
        sidx = InteractiveUI.single_choice("Memory strategy", strategies, default_index=0, hint="↑↓ move   Enter confirm   q quit")
        if sidx is None or sidx < 0:
            return plugin_context.return_false()
        hard_mem = base_mem
        plugin_context.set_variable("prod_memory_base", base_mem)
        plugin_context.set_variable("prod_memory_strategy", sidx)
        plugin_context.set_variable("prod_hard_limit", hard_mem)
    return plugin_context.return_true()
