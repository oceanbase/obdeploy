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

import errno
import socket
import time
from collections import defaultdict

from const import COMP_OB, COMP_OB_CE, COMPS_OB, COMP_OB_STANDALONE, SERVICE_MODE, COMP_OB_AI
from tool import Cursor, parse_service_metadata
from _deploy import ObserverIdentity, ObserverIdentityError

# Same pattern as switchover_tenant.py: cache tenant cursors on the sys-level Cursor.
tenant_cursor_cache = defaultdict(dict)
PRIMARY_TENANT_PROBE_TIMEOUT_ERRNOS = frozenset([4012])


def is_primary_probe_timeout_error(error):
    """Return whether OceanBase timed out the primary tenant probe."""
    return bool(error.args) and error.args[0] in PRIMARY_TENANT_PROBE_TIMEOUT_ERRNOS


def normalize_primary_endpoints(primary_ip_value):
    """Validate and deduplicate advertised SQL endpoints."""
    primary_ip_list = []
    primary_endpoint_keys = set()
    for endpoint in primary_ip_value.split(';'):
        endpoint = endpoint.strip()
        address = endpoint.split('+', 1)[0]
        ip, separator, port = address.rpartition(':')
        if not separator or not ip or not port.isdigit():
            raise ObserverIdentityError(
                'Invalid primary tenant endpoint: {}'.format(endpoint))
        endpoint_key = (ip, int(port))
        if endpoint_key not in primary_endpoint_keys:
            primary_endpoint_keys.add(endpoint_key)
            primary_ip_list.append(endpoint)
    return primary_ip_list


def allow_unverified_primary_probe(comp_name, mode, source_is_loopback,
                                   primary_cursor, primary_ip_list):
    """Tolerate an unavailable query only for multi-node CE MySQL sources."""
    return (
        comp_name == COMP_OB_CE and
        mode == 'mysql' and
        not source_is_loopback and
        primary_cursor is None and
        len(primary_ip_list) > 1)


def probe_primary_endpoint(ip, port, probe, timeout=3, fail_closed=True):
    """Probe one primary endpoint.

    True means that the primary tenant was verified alive, False means that
    the endpoint is unreachable, and None means that a reachable endpoint's
    tenant probe was unverified and the caller opted to aggregate that result.
    """
    try:
        probe_socket = socket.create_connection((ip, int(port)), timeout=timeout)
    except socket.timeout:
        return False
    except (OSError, socket.error) as e:
        unreachable_errnos = set(filter(None, [
            getattr(errno, 'ECONNREFUSED', None),
            getattr(errno, 'ETIMEDOUT', None),
            getattr(errno, 'EHOSTUNREACH', None),
            getattr(errno, 'ENETUNREACH', None),
            getattr(errno, 'EHOSTDOWN', None),
            getattr(errno, 'ENETDOWN', None),
        ]))
        if getattr(e, 'errno', None) in unreachable_errnos:
            return False
        raise ObserverIdentityError(
            'Primary endpoint {}:{} reachability check failed locally; refusing '
            'failover.'.format(ip, port))
    try:
        probe_socket.close()
    except Exception:
        # The connection was already established. A cleanup error must never
        # reclassify a reachable primary endpoint as unreachable.
        pass
    try:
        if probe():
            return True
    except Exception:
        raise ObserverIdentityError(
            'Primary endpoint {}:{} is reachable but the tenant probe failed; '
            'refusing failover.'.format(ip, port))
    if not fail_closed:
        return None
    raise ObserverIdentityError(
        'Primary endpoint {}:{} is reachable but the tenant probe could not be '
        'verified; refusing failover.'.format(ip, port))


def resolve_loopback_primary_mapping(mapped_primary, source_user, source_endpoints,
                                     relation_tenants, cluster_configs):
    """Validate that one relation uniquely owns a loopback recovery source."""
    if not mapped_primary:
        raise ObserverIdentityError(
            'Missing primary cluster mapping for loopback tenant; cannot safely '
            'probe the primary tenant.')
    if not source_user or '@' not in source_user:
        raise ObserverIdentityError(
            'Loopback LOG_RESTORE_SOURCE does not identify its source tenant.')
    source_tenant = source_user.split('@', 1)[1]
    candidates = []
    for candidate in relation_tenants:
        candidate = (candidate[0], candidate[1])
        if candidate[1] != source_tenant or candidate[0] not in cluster_configs:
            continue
        candidate_config = cluster_configs[candidate[0]]
        try:
            for endpoint in source_endpoints:
                ObserverIdentity.externalize_sql_endpoint(candidate_config, endpoint)
        except ObserverIdentityError:
            continue
        candidates.append(candidate)
    if len(candidates) != 1:
        raise ObserverIdentityError(
            'Expected exactly one primary mapping for the loopback LOG_RESTORE_SOURCE, '
            'found {}.'.format(len(candidates)))
    if candidates[0] != mapped_primary:
        raise ObserverIdentityError(
            'The persisted primary_tenant mapping does not match the loopback '
            'LOG_RESTORE_SOURCE.')
    return candidates[0]


def exec_sql_in_tenant(sql, cursor, tenant, mode, user='', password='', raise_exception=False, retries=20,
                       cluster_config=None):
    if not user:
        user = 'SYS' if mode == 'oracle' else 'root'
    tenant_cursor = None
    if cursor in tenant_cursor_cache and tenant in tenant_cursor_cache[cursor] and user in tenant_cursor_cache[cursor][tenant]:
        tenant_cursor = tenant_cursor_cache[cursor][tenant][user]
    else:
        query_sql = (
            "select a.SVR_IP as SVR_IP, c.SQL_PORT as SQL_PORT from oceanbase.DBA_OB_UNITS as a, "
            "oceanbase.DBA_OB_TENANTS as b, oceanbase.DBA_OB_SERVERS as c  "
            "where a.TENANT_ID=b.TENANT_ID and a.SVR_IP=c.SVR_IP and a.svr_port=c.SVR_PORT and TENANT_NAME=%s"
        )
        tenant_server_ports = cursor.fetchall(query_sql, (tenant, ), raise_exception=False, exc_level='verbose')
        for tenant_server_port in tenant_server_ports:
            tenant_ip = ObserverIdentity.externalize_ip(cluster_config, tenant_server_port['SVR_IP'])
            tenant_port = tenant_server_port['SQL_PORT']
            tenant_cursor = cursor.new_cursor(
                tenant=tenant, user=user, password=password, ip=tenant_ip, port=tenant_port, mode=mode, print_exception=raise_exception
            )
            if tenant_cursor:
                if tenant not in tenant_cursor_cache[cursor]:
                    tenant_cursor_cache[cursor][tenant] = {}
                tenant_cursor_cache[cursor][tenant][user] = tenant_cursor
                break
    if not tenant_cursor and retries:
        time.sleep(1)
        return exec_sql_in_tenant(
            sql, cursor, tenant, mode, user, password, raise_exception=raise_exception,
            retries=retries - 1, cluster_config=cluster_config)
    return tenant_cursor.execute(sql, raise_exception=False, exc_level='verbose') if tenant_cursor else False


def failover_decouple_tenant_pre(plugin_context, cursors={}, cluster_configs={}, *args, **kwargs):
    stdio = plugin_context.stdio
    standby_deploy_name = plugin_context.cluster_config.deploy_name
    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    cmds = plugin_context.cmds
    option_type = cmds[2]
    standby_tenant = getattr(options, 'tenant_name', '')
    if not standby_tenant:
        stdio.error('Standby tenant name is empty.')
        return False
    standby_cursor = cursors.get(standby_deploy_name)
    if not standby_cursor:
        stdio.error('standby deploy: {} connect check fail.'.format(standby_deploy_name))
        return False
    # role check
    stdio.start_loading('Check tenant')
    sql = "select TENANT_ID, TENANT_ROLE, TENANT_TYPE, STATUS, COMPATIBILITY_MODE from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
    standby_info_res = standby_cursor.fetchone(sql, (standby_tenant, ), raise_exception=True)
    if not standby_info_res:
        stdio.error("Tenant:{} not exists in deployment:{}".format(standby_tenant, standby_deploy_name))
        stdio.stop_loading('fail')
        return
    
    plugin_context.set_variable('tenant_mode', standby_info_res['COMPATIBILITY_MODE'])

    if standby_info_res['TENANT_ROLE'] != 'STANDBY':
        stdio.error("Standby tenant {}:{}'s role is invalid, Expect: USER , Current:{}.".format(standby_deploy_name, standby_tenant, standby_info_res['TENANT_ROLE']))
        stdio.stop_loading('fail')
        return

    primary_dict = cluster_config.get_component_attr('primary_tenant')
    primary_info = primary_dict.get(standby_tenant, []) if primary_dict else []
    primary_cluster = primary_info[0][0] if primary_info else None
    primary_tenant = primary_info[0][1] if primary_info else None
    mapped_primary = (primary_cluster, primary_tenant) if primary_cluster and primary_tenant else None
    primary_cursor = cursors.get(primary_cluster) if primary_cluster else None
    primary_cluster_config = cluster_configs.get(primary_cluster) if primary_cluster else None
    relation_tenants = plugin_context.get_variable('relation_tenants') or []

    # query primary tenant connect info
    if option_type == 'failover':
        source_ret = standby_cursor.fetchone("SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE where TENANT_ID=%s", (standby_info_res['TENANT_ID'], ), raise_exception=False)
        if not source_ret:
            stdio.error("in {} tenant {} find log restore source is failed".format(standby_deploy_name, standby_tenant))
            return
        if source_ret['TYPE'] == SERVICE_MODE:
            res = standby_cursor.fetchone('select a.VALUE as `VALUE` from oceanbase.cdb_ob_log_restore_source as a, oceanbase.DBA_OB_TENANTS as b where a.TENANT_ID=b.TENANT_ID and b.TENANT_NAME = %s', (standby_tenant, ), raise_exception=False)
            if not res:
                stdio.error("Query tenant {}:{}'s primary tenant info fail, place confirm current tenant is have the primary tenant.".format(standby_deploy_name, standby_tenant))
                stdio.stop_loading('fail')
                return
            primary_info_dict = parse_service_metadata(res['VALUE'])
            user = primary_info_dict.get('USER')
            source_password = primary_info_dict.get('PASSWORD')
            primary_ip_value = (
                primary_info_dict.get('IP_LIST') or
                primary_info_dict.get('SERVICE'))
            if not user or not primary_ip_value:
                stdio.error(
                    "Tenant {}:{} log restore source must contain USER and "
                    "IP_LIST/SERVICE.".format(
                        standby_deploy_name, standby_tenant))
                stdio.stop_loading('fail')
                return
            
            comp_name = cluster_config.name
            if comp_name in (COMP_OB, COMP_OB_STANDALONE, COMP_OB_AI):
                standbyro_password_dict = cluster_config.get_component_attr('standbyro_password')
                tenant_standbyro_password = standbyro_password_dict.get(standby_tenant, '') if standbyro_password_dict else ''
            else:
                tenant_standbyro_password = source_password
            
            tenant_root_password = getattr(options, 'tenant_root_password', '') or ''
            
            if comp_name not in COMPS_OB:
                stdio.error('Unsupported component {} for primary tenant probe.'.format(comp_name))
                stdio.stop_loading('fail')
                return
            is_ce_ob = comp_name == COMP_OB_CE
            is_enterprise_ob = not is_ce_ob
            if is_ce_ob and source_password is None:
                stdio.error(
                    "Tenant {}:{} log restore source must contain PASSWORD.".format(
                        standby_deploy_name, standby_tenant))
                stdio.stop_loading('fail')
                return
                    
            try:
                primary_ip_list = normalize_primary_endpoints(primary_ip_value)
            except ObserverIdentityError as e:
                stdio.error(str(e))
                stdio.stop_loading('fail')
                return
            tenant_mode = standby_info_res['COMPATIBILITY_MODE'].lower()

            source_is_loopback = any(
                endpoint.split('+', 1)[0].rpartition(':')[0] == '127.0.0.1'
                for endpoint in primary_ip_list)
            if source_is_loopback:
                try:
                    resolve_loopback_primary_mapping(
                        mapped_primary, user, primary_ip_list,
                        relation_tenants, cluster_configs)
                except ObserverIdentityError as e:
                    stdio.error(str(e))
                    stdio.stop_loading('fail')
                    return

            tenant_name = standby_tenant
            connect_user = user or 'standbyro'
            if user and '@' in user:
                connect_user, tenant_name = user.split('@', 1)
            normalized_user = (connect_user or '').lower()
            password = ''
            if is_ce_ob:
                password = source_password or ''
                if not password:
                    stdio.error('Missing PASSWORD in LOG_RESTORE_SOURCE for CE deployment; cannot probe primary tenant.')
                    stdio.stop_loading('fail')
                    return
            elif is_enterprise_ob:
                if normalized_user == 'standbyro':
                    password = tenant_standbyro_password
                    if not password:
                        stdio.error('Missing standbyro password in inner_config for tenant {}; cannot probe primary tenant.'.format(standby_tenant))
                        stdio.stop_loading('fail')
                        return
                elif normalized_user in ('sys', 'root'):
                    password = tenant_root_password
                    if not password:
                        stdio.error('Missing tenant root password; please retry with --tenant-root-password=xxxxxx to probe primary tenant.')
                        stdio.stop_loading('fail')
                        return
                else:
                    stdio.error('Unsupported LOG_RESTORE_SOURCE user {} for enterprise deployment; cannot obtain password.'.format(connect_user))
                    stdio.stop_loading('fail')
                    return
            mode = tenant_mode
            probe_sql = 'show databases like "oceanbase"' if mode == 'mysql' else "SELECT username FROM all_users WHERE username = 'SYS'"
            sql_user = connect_user
            if mode == 'oracle' and sql_user and sql_user.upper() == 'SYS':
                sql_user = 'SYS'

            # A surviving minority OBServer can accept a MySQL connection while
            # the primary tenant is unavailable. Preserve the historical
            # multi-node CE SERVICE behavior without weakening loopback,
            # enterprise, standalone, Oracle, or single-endpoint checks.
            allow_unverified_multi_endpoint = allow_unverified_primary_probe(
                comp_name, mode, source_is_loopback,
                primary_cursor, primary_ip_list)
            unverified_primary_count = 0

            if source_is_loopback and primary_cursor:
                primary_alive = exec_sql_in_tenant(
                    probe_sql, primary_cursor, tenant_name, mode, user=sql_user,
                    password=password, raise_exception=False, retries=3,
                    cluster_config=primary_cluster_config)
                if primary_alive:
                    stdio.error('Primary tenant status is alive, not support failover.')
                else:
                    stdio.error(
                        'Primary deployment is connected but the primary tenant probe '
                        'could not be verified; refusing failover.')
                stdio.stop_loading('fail')
                return

            for endpoint in primary_ip_list:
                if source_is_loopback:
                    try:
                        endpoint = ObserverIdentity.externalize_sql_endpoint(primary_cluster_config, endpoint)
                    except ObserverIdentityError as e:
                        stdio.error(str(e))
                        stdio.stop_loading('fail')
                        return
                address = endpoint.split('+', 1)[0]
                ip, separator, port = address.rpartition(':')
                if not separator or not ip or not port.isdigit():
                    stdio.error('Invalid primary tenant endpoint: {}'.format(endpoint))
                    stdio.stop_loading('fail')
                    return
                stdio.verbose('connect primary tenant server: %s -P%s -u%s' % (ip, port, user))
                def execute_probe():
                    direct_cursor = Cursor(
                        ip=ip, port=port, user=sql_user, tenant=tenant_name,
                        password=password, mode=mode, stdio=stdio)
                    try:
                        try:
                            return direct_cursor.execute(
                                probe_sql, raise_exception=True,
                                exc_level='verbose')
                        except Exception as e:
                            if is_primary_probe_timeout_error(e):
                                return False
                            raise
                    finally:
                        direct_cursor.close()

                try:
                    primary_alive = probe_primary_endpoint(
                        ip, port, execute_probe,
                        fail_closed=not allow_unverified_multi_endpoint)
                except ObserverIdentityError as e:
                    stdio.error(str(e))
                    stdio.stop_loading('fail')
                    return
                if primary_alive is None:
                    unverified_primary_count += 1
                if primary_alive:
                    stdio.error('Primary tenant status is alive, not support failover.')
                    stdio.stop_loading('fail')
                    return
                # Check every advertised endpoint: a later successful probe must
                # still reject failover after an earlier unavailable query.
            if (allow_unverified_multi_endpoint and
                    unverified_primary_count >= len(primary_ip_list) // 2 + 1):
                stdio.error(
                    'A majority of primary endpoints is reachable but the tenant '
                    'probes could not be verified; refusing failover.')
                stdio.stop_loading('fail')
                return
        else:
            if primary_cursor and primary_tenant:
                sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME='%s'" % primary_tenant
                res = primary_cursor.fetchone(sql)
                if res:
                    stdio.error('Primary tenant status is alive, not support failover.')
                    stdio.stop_loading('fail')
                    return
    # check tenant type
    if standby_info_res['TENANT_TYPE'] != 'USER':
        stdio.error("Standby tenant {}:{}'s type is invalid, Expect: USER , Current:{}".format(standby_deploy_name, standby_tenant, standby_info_res['TENANT_TYPE']))
        stdio.stop_loading('fail')
        return

    # check tenant status
    if standby_info_res['STATUS'] != 'NORMAL':
        stdio.error("Standby tenant {}:{}'s status is invalid, Expect: NORMAL , Current:{}".format(standby_deploy_name, standby_tenant, standby_info_res['STATUS']))
        stdio.stop_loading('fail')
        return

    # check log stream has no leader
    sql = " SELECT COUNT(1) as `count` FROM oceanbase.CDB_OB_LS A LEFT JOIN oceanbase.GV$OB_LOG_STAT B ON A.LS_ID = B.LS_ID AND A.TENANT_ID = B.TENANT_ID  AND B.ROLE='LEADER' WHERE B.LS_ID IS NULL AND A.STATUS NOT IN ('CREATING', 'CREATED', 'TENANT_DROPPING', 'CREATE_ABORT', 'PRE_TENANT_DROPPING') AND A.TENANT_ID IN (%s,%s)"
    no_leader_log_stream = standby_cursor.fetchone(sql, (standby_info_res['TENANT_ID'], int(standby_info_res['TENANT_ID']) - 1), raise_exception=True)
    if no_leader_log_stream['count'] != 0:
        stdio.error("Standby tenant {}:{} has log stream no leader".format(standby_deploy_name, standby_tenant))
        stdio.stop_loading('fail')
        return

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
