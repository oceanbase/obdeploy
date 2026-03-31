# coding: utf-8
# Copyright (c) 2025 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Detect SeekDB standby cluster and set seekdb_is_standby on plugin_context for downstream plugins (obshell_*).

Must run after connect when SQL role check is needed; config-only checks work without cursor.
"""

from __future__ import absolute_import, division, print_function


def seekdb_standby_detect(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    is_standby = False
    try:
        if cluster_config.get_component_attr('_cluster_primary'):
            is_standby = True
    except Exception:
        pass
    if not is_standby and plugin_context.get_variable('primary_rpc_info'):
        is_standby = True
    if not is_standby:
        cursor = plugin_context.get_variable('cursor')
        if cursor:

            res = cursor.fetchone(
                'SELECT ROLE FROM oceanbase.__all_virtual_server_stat',
                raise_exception=False,
            )
            role = (res or {}).get('ROLE') or (res or {}).get('role')
            if role and str(role).upper() == 'STANDBY':
                is_standby = True

    plugin_context.set_variable('seekdb_is_standby', is_standby)
    plugin_context.stdio.verbose('seekdb_is_standby: %s' % is_standby)
    return plugin_context.return_true()
