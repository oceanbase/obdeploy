# coding: utf-8

from __future__ import absolute_import, division, print_function

import errno
import importlib.util
import os
import socket
import tempfile
import types
import unittest
from unittest import mock

import const
import tool
from _deploy import ClusterConfig, ComponentInnerConfig, DeployConfig, DeployStatus, InnerConfig, ObserverIdentity, ObserverIdentityError, ServerConfig
from tool import YamlLoader


class FakeClusterConfig(object):

    def __init__(self, name=const.COMP_OB_STANDALONE, version='4.4.2.3', local_ip=None,
                 server_ip='10.0.0.8'):
        self.name = name
        self.version = version
        self.server = ServerConfig(server_ip, 'observer-1')
        self.servers = [self.server]
        self.original_servers = list(self.servers)
        self.added_servers = []
        self.attrs = {}
        self.config = {
            'home_path': '/opt/oceanbase',
            'mysql_port': 2881,
            'rpc_port': 2882,
            'zone': 'zone1',
        }
        if local_ip is not None:
            self.config['local_ip'] = local_ip

    def get_component_attr(self, key):
        return self.attrs.get(key)

    def update_component_attr(self, key, value, save=True):
        self.attrs[key] = value
        return True

    def update_component_attrs(self, attrs, save=True):
        self.attrs.update(attrs)
        return True

    def get_server_conf(self, server):
        return self.config

    def get_global_conf_with_default(self):
        return {'scenario': 'express_oltp'}

    def get_global_conf(self):
        return {}


class FakePluginContext(object):

    def __init__(self, cluster_config, status=DeployStatus.STATUS_DEPLOYED):
        self.cluster_config = cluster_config
        self.deploy_status = status
        self.variables = {'cfg_url': 'http://configserver.invalid', 'clog_sub_dir': 'clog'}
        self.options = types.SimpleNamespace(with_parameter=False)
        self.repositories = []
        self.clients = {cluster_config.server: FakeClient()}
        self.stdio = FakeStdio()

    def get_variable(self, key, default=None):
        return self.variables.get(key, default)

    def set_variable(self, key, value):
        self.variables[key] = value

    def return_true(self, **kwargs):
        return True

    def return_false(self, **kwargs):
        return False


class FakeStdio(object):

    def __init__(self):
        self.errors = []

    def error(self, message):
        self.errors.append(message)

    def verbose(self, *args, **kwargs):
        pass

    def print(self, *args, **kwargs):
        pass


class CommandResult(object):

    def __init__(self, stdout='', success=True, code=None, stderr=''):
        self.stdout = stdout
        self.success = success
        self.code = (0 if success else 1) if code is None else code
        self.stderr = stderr

    def __bool__(self):
        return self.success

    __nonzero__ = __bool__


class FakeClient(object):

    def execute_command(self, command):
        if command.startswith('test -e ') or command.startswith('test -d '):
            return CommandResult('', success=False)
        if '/clog/' in command:
            return CommandResult('existing clog')
        if 'observer.pid' in command:
            return CommandResult('')
        if 'observer.config.bin' in command:
            return CommandResult('observer.config.bin')
        return CommandResult('')


class InitializedClient(FakeClient):

    def execute_command(self, command):
        if command.startswith('test -e ') and command.endswith('observer.config.bin'):
            return CommandResult('')
        return super(InitializedClient, self).execute_command(command)


class FailedInspectionClient(FakeClient):

    def execute_command(self, command):
        if command.startswith('test -e '):
            return CommandResult('', success=False, code=255, stderr='ssh connection failed')
        return super(FailedInspectionClient, self).execute_command(command)


def load_start_pre_plugin(version='4.2.5.0'):
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'plugins', 'oceanbase', version, 'start_pre.py')
    spec = importlib.util.spec_from_file_location('standalone_start_pre_%s_under_test' % version.replace('.', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_verify_observer_identity_plugin():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'plugins', 'oceanbase', '3.1.0', 'verify_observer_identity.py')
    spec = importlib.util.spec_from_file_location('verify_observer_identity_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_upgrade_start_workflow():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'workflows', 'oceanbase', '3.1.0', 'upgrade_start.py')
    spec = importlib.util.spec_from_file_location('upgrade_start_workflow_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_obshell_start_plugin():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'plugins', 'oceanbase', '4.2.1.4', 'obshell_start.py')
    spec = importlib.util.spec_from_file_location('standalone_obshell_start_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_obshell_dashboard_plugin():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'plugins', 'oceanbase', '4.4.2.1', 'obshell_dashboard.py')
    obshell_module = types.ModuleType('obshell')

    class FakeClientV1(object):

        def get_info(self):
            return types.SimpleNamespace(version='4.3.0.0')

    obshell_module.ClientV1 = FakeClientV1
    spec = importlib.util.spec_from_file_location('standalone_obshell_dashboard_under_test', path)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict('sys.modules', {'obshell': obshell_module}):
        spec.loader.exec_module(module)
    return module


def load_tenant_ha_plugin(filename, version='4.4.2.1'):
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'plugins', 'oceanbase', version, filename)
    spec = importlib.util.spec_from_file_location(
        'standalone_tenant_ha_%s_%s_under_test' % (
            version.replace('.', '_'), filename.replace('.', '_')), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeObshellClient(object):

    def __init__(self):
        self.commands = []
        self.pid_reads = 0
        self._is_local = False

    def add_env(self, *args, **kwargs):
        pass

    def execute_command(self, command):
        self.commands.append(command)
        if command.startswith('cat ') and command.endswith('/run/obshell.pid'):
            self.pid_reads += 1
            return CommandResult('' if self.pid_reads == 1 else '12345')
        return CommandResult('')


class FakeSocket(object):

    def close(self):
        pass


class FailingCloseSocket(object):

    def close(self):
        raise OSError('close failed')


class FakeTenantAccessPointCursor(object):

    def __init__(self, ip_list):
        self.ip_list = ip_list

    def fetchone(self, *args, **kwargs):
        return {'ip_list': self.ip_list}


class CapturingStdio(object):

    def __init__(self):
        self.messages = []

    def verbose(self, message):
        self.messages.append(str(message))

    def error(self, message):
        self.messages.append(str(message))

    def exception(self, message):
        self.messages.append(str(message))


class FakeDatabaseCursor(object):

    def execute(self, *args, **kwargs):
        return True


class CapturingDatabaseCursor(object):

    def __init__(self):
        self.calls = []

    def execute(self, sql, args=None, **kwargs):
        self.calls.append((sql, args, kwargs))
        return True


class FakeDatabase(object):

    def cursor(self, *args, **kwargs):
        return FakeDatabaseCursor()


class SecretFailingDatabaseCursor(object):

    def __init__(self, secret):
        self.secret = secret

    def execute(self, *args, **kwargs):
        raise RuntimeError('database echoed secret: %s' % self.secret)


class SecretFailingDatabase(object):

    def __init__(self, secret):
        self.secret = secret

    def cursor(self, *args, **kwargs):
        return SecretFailingDatabaseCursor(self.secret)


class RaisingTenantCursor(object):

    def execute(self, sql, args=None, raise_exception=False, **kwargs):
        if raise_exception:
            raise RuntimeError('sql failed')
        return False


class FakeTenantParentCursor(object):

    def fetchall(self, *args, **kwargs):
        return [{'SVR_IP': '10.0.0.8', 'SQL_PORT': 2881}]

    def new_cursor(self, *args, **kwargs):
        return RaisingTenantCursor()


class FakeObserverIdentityCursor(object):

    def __init__(self, servers):
        self.servers = servers
        self.queries = []

    def fetchall(self, sql, **kwargs):
        self.queries.append((sql, kwargs))
        return self.servers


class FakePluginReturn(object):

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_return(self, key, default=None):
        return self.kwargs.get(key, default)


class FakeObserverIdentityContext(FakePluginContext):

    def __init__(self, cluster_config, cursor=None):
        super(FakeObserverIdentityContext, self).__init__(cluster_config)
        self.cursor = cursor
        self.stdio.start_loading = lambda *args, **kwargs: None
        self.stdio.stop_loading = lambda *args, **kwargs: None

    def get_return(self, plugin_name):
        if plugin_name == 'connect' and self.cursor:
            return FakePluginReturn(cursor=self.cursor)
        return None


class FakeWorkflow(object):

    def __init__(self):
        self.calls = []

    def add(self, stage, *plugins):
        self.calls.append((stage, plugins))


class ObserverIdentityTest(unittest.TestCase):

    def _obshell_dashboard_url(self, cluster):
        plugin = load_obshell_dashboard_plugin()
        cluster.config['obshell_port'] = 2886
        context = FakePluginContext(cluster)
        context.stdio.start_loading = lambda *args, **kwargs: None
        context.stdio.stop_loading = lambda *args, **kwargs: None
        context.stdio.print_list = lambda *args, **kwargs: None
        context.return_true = lambda **kwargs: kwargs
        with mock.patch.object(plugin.NetUtil, 'get_host_ip', return_value='192.0.2.10'):
            result = plugin.obshell_dashboard(
                context, {cluster.server.ip: plugin.ClientV1()}, True)
        return result['obshell_dashboard']

    def test_obshell_dashboard_preserves_all_standalone_loopback_contracts(self):
        fresh = FakeClusterConfig(server_ip=const.OBSERVER_LOOPBACK_IP)
        ObserverIdentity.prepare(FakePluginContext(fresh), fresh)
        markerless_legacy = FakeClusterConfig(
            version='4.2.5.3', local_ip=const.OBSERVER_LOOPBACK_IP,
            server_ip=const.OBSERVER_LOOPBACK_IP)

        self.assertEqual(
            'http://127.0.0.1:2886', self._obshell_dashboard_url(fresh))
        self.assertIsNone(ObserverIdentity.marker(markerless_legacy))
        self.assertTrue(ObserverIdentity.is_loopback(markerless_legacy))
        self.assertEqual(
            'http://127.0.0.1:2886',
            self._obshell_dashboard_url(markerless_legacy))

    def test_obshell_dashboard_keeps_markerless_fallback_compatibility(self):
        markerless = FakeClusterConfig(server_ip=const.OBSERVER_LOOPBACK_IP)
        community = FakeClusterConfig(
            name=const.COMP_OB_CE, server_ip=const.OBSERVER_LOOPBACK_IP)

        self.assertEqual(
            'http://192.0.2.10:2886',
            self._obshell_dashboard_url(markerless))
        self.assertEqual(
            'http://192.0.2.10:2886',
            self._obshell_dashboard_url(community))

    def test_inner_config_dump_failure_is_propagated(self):
        deploy_config = DeployConfig.__new__(DeployConfig)
        deploy_config.components = {}
        deploy_config._inner_config = types.SimpleNamespace(dump=lambda: False)
        self.assertFalse(deploy_config._dump_inner_config())

        cluster_config = ClusterConfig.__new__(ClusterConfig)
        cluster_config._inner_config = ComponentInnerConfig(const.COMP_OB_STANDALONE, {})
        cluster_config._deploy_config = types.SimpleNamespace(dump_inner_config=lambda: False)
        self.assertFalse(cluster_config.update_component_attr('test_key', 'test_value'))
        self.assertIsNone(cluster_config.get_component_attr('test_key'))

    def test_inner_config_atomic_round_trip_and_corruption_detection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, 'inner_config.yaml')
            inner_config = InnerConfig(path, YamlLoader())
            component_config = ComponentInnerConfig(const.COMP_OB_STANDALONE, {})
            component_config.update_attr(const.OBSERVER_IDENTITY_IP, const.OBSERVER_LOOPBACK_IP)
            inner_config.config[const.COMP_OB_STANDALONE] = component_config
            self.assertTrue(inner_config.dump())
            loaded = InnerConfig(path, YamlLoader())
            self.assertIsNone(loaded.load_error)
            self.assertEqual(const.OBSERVER_LOOPBACK_IP,
                             loaded.get_component_config(const.COMP_OB_STANDALONE).get_attr(const.OBSERVER_IDENTITY_IP))
            with open(path, 'w') as f:
                f.write('invalid: [yaml')
            corrupt = InnerConfig(path, YamlLoader())
            self.assertIsNotNone(corrupt.load_error)

    def test_fresh_supported_standalone_persists_planned_marker(self):
        cluster = FakeClusterConfig(version='4.4.2.3')
        marker = ObserverIdentity.prepare(FakePluginContext(cluster), cluster)
        self.assertEqual(const.OBSERVER_LOOPBACK_IP, marker['ip'])
        self.assertEqual(const.OBSERVER_IDENTITY_PLANNED, marker['state'])
        self.assertEqual(const.OBSERVER_IDENTITY_FRESH_BOOTSTRAP, marker['source'])
        self.assertEqual('10.0.0.8', ObserverIdentity.management_ip(cluster))
        self.assertEqual(const.OBSERVER_LOOPBACK_IP, ObserverIdentity.identity_ip(cluster))

    def test_community_component_and_historical_cluster_are_unchanged(self):
        community = FakeClusterConfig(name=const.COMP_OB_CE, version='4.6.0.0')
        self.assertIsNone(ObserverIdentity.prepare(FakePluginContext(community), community))
        historical = FakeClusterConfig(version='4.6.0.0')
        context = FakePluginContext(historical, status=DeployStatus.STATUS_RUNNING)
        self.assertIsNone(ObserverIdentity.prepare(context, historical))
        self.assertEqual('10.0.0.8', ObserverIdentity.identity_ip(historical))

        partial_historical = FakeClusterConfig(version='4.4.2.3')
        context = FakePluginContext(partial_historical, status=DeployStatus.STATUS_DEPLOYED)
        context.clients[partial_historical.server] = InitializedClient()
        self.assertIsNone(ObserverIdentity.prepare(context, partial_historical))
        self.assertEqual('10.0.0.8', ObserverIdentity.identity_ip(partial_historical))

        inspection_failure = FakeClusterConfig(version='4.4.2.3')
        context = FakePluginContext(inspection_failure, status=DeployStatus.STATUS_DEPLOYED)
        context.clients[inspection_failure.server] = FailedInspectionClient()
        with self.assertRaises(ObserverIdentityError):
            ObserverIdentity.prepare(context, inspection_failure)

    def test_version_before_bp3_is_unchanged_unless_legacy_loopback_is_explicit(self):
        old = FakeClusterConfig(version='4.4.2.2')
        self.assertIsNone(ObserverIdentity.prepare(FakePluginContext(old), old))
        legacy = FakeClusterConfig(version='4.2.5.3', local_ip=const.OBSERVER_LOOPBACK_IP)
        legacy_context = FakePluginContext(legacy, DeployStatus.STATUS_RUNNING)
        legacy_context.clients[legacy.server] = InitializedClient()
        marker = ObserverIdentity.prepare(legacy_context, legacy)
        self.assertEqual(const.OBSERVER_IDENTITY_LEGACY_MANUAL, marker['source'])
        self.assertEqual(const.OBSERVER_IDENTITY_PLANNED, marker['state'])

        markerless_legacy = FakeClusterConfig(version='4.2.5.3', local_ip=const.OBSERVER_LOOPBACK_IP)
        self.assertTrue(ObserverIdentity.is_loopback(markerless_legacy))
        self.assertEqual(const.OBSERVER_LOOPBACK_IP, ObserverIdentity.identity_ip(markerless_legacy))
        self.assertEqual('10.0.0.8',
                         ObserverIdentity.externalize_ip(markerless_legacy, const.OBSERVER_LOOPBACK_IP))
        with self.assertRaises(ObserverIdentityError):
            ObserverIdentity.reject_loopback_capability(markerless_legacy, 'tenant switchover')

    def test_verify_and_externalize_only_verified_identity(self):
        cluster = FakeClusterConfig()
        ObserverIdentity.prepare(FakePluginContext(cluster), cluster)
        self.assertEqual(const.OBSERVER_LOOPBACK_IP,
                         ObserverIdentity.externalize_ip(cluster, const.OBSERVER_LOOPBACK_IP))
        ObserverIdentity.verify(cluster, [{'svr_ip': const.OBSERVER_LOOPBACK_IP}])
        self.assertEqual(const.OBSERVER_IDENTITY_VERIFIED,
                         cluster.attrs[const.OBSERVER_IDENTITY_STATE])
        self.assertEqual('10.0.0.8',
                         ObserverIdentity.externalize_ip(cluster, const.OBSERVER_LOOPBACK_IP))
        with self.assertRaises(ObserverIdentityError):
            ObserverIdentity.verify(cluster, [{'svr_ip': '10.0.0.8'}])
        with self.assertRaises(ObserverIdentityError):
            ObserverIdentity.verify(cluster, [
                {'svr_ip': const.OBSERVER_LOOPBACK_IP},
                {'svr_ip': const.OBSERVER_LOOPBACK_IP},
            ])

        # P0 management-IP replacement only changes config.yaml; the verified
        # observer identity remains loopback and externalizes to the new IP.
        cluster.server.ip = '10.0.0.9'
        self.assertEqual('10.0.0.9',
                         ObserverIdentity.externalize_ip(cluster, const.OBSERVER_LOOPBACK_IP))

    def test_identity_verification_is_independent_from_upgrade_bootstrap(self):
        cluster = FakeClusterConfig()
        ObserverIdentity.prepare(FakePluginContext(cluster), cluster)
        cursor = FakeObserverIdentityCursor([{
            'svr_ip': const.OBSERVER_LOOPBACK_IP,
            'svr_port': 2882,
            'inner_port': 2881,
            'status': 'ACTIVE',
        }])
        context = FakeObserverIdentityContext(cluster, cursor)
        plugin = load_verify_observer_identity_plugin()

        self.assertTrue(plugin.verify_observer_identity(context))
        self.assertEqual(const.OBSERVER_IDENTITY_VERIFIED,
                         cluster.attrs[const.OBSERVER_IDENTITY_STATE])
        self.assertEqual('select * from oceanbase.__all_server', cursor.queries[0][0])

        workflow = FakeWorkflow()
        load_upgrade_start_workflow().upgrade_start(context, workflow)
        self.assertEqual(1, len(workflow.calls))
        self.assertIn('verify_observer_identity', workflow.calls[0][1])
        self.assertNotIn('bootstrap', workflow.calls[0][1])

    def test_identity_verification_fails_closed_on_live_mismatch(self):
        cluster = FakeClusterConfig()
        ObserverIdentity.prepare(FakePluginContext(cluster), cluster)
        cursor = FakeObserverIdentityCursor([{
            'svr_ip': '10.0.0.8',
            'svr_port': 2882,
            'inner_port': 2881,
            'status': 'ACTIVE',
        }])
        context = FakeObserverIdentityContext(cluster, cursor)

        self.assertFalse(load_verify_observer_identity_plugin().verify_observer_identity(context))
        self.assertEqual(const.OBSERVER_IDENTITY_PLANNED,
                         cluster.attrs[const.OBSERVER_IDENTITY_STATE])
        self.assertTrue(any('observer identity mismatch' in message
                            for message in context.stdio.errors))

    def test_identity_verification_is_noop_without_identity_marker(self):
        cluster = FakeClusterConfig(name=const.COMP_OB_CE, version='4.6.0.0')
        context = FakeObserverIdentityContext(cluster)
        self.assertTrue(load_verify_observer_identity_plugin().verify_observer_identity(context))

    def test_identity_verification_times_out_after_900_seconds(self):
        cluster = FakeClusterConfig()
        ObserverIdentity.prepare(FakePluginContext(cluster), cluster)
        cursor = FakeObserverIdentityCursor([])
        context = FakeObserverIdentityContext(cluster, cursor)
        plugin = load_verify_observer_identity_plugin()

        with mock.patch.object(plugin.time, 'time', side_effect=[100, 1000]), \
                mock.patch.object(plugin.time, 'sleep') as sleep:
            self.assertFalse(plugin.verify_observer_identity(context))
        sleep.assert_not_called()
        self.assertEqual(1, len(cursor.queries))
        self.assertTrue(any('timed out after 900 seconds' in message
                            for message in context.stdio.errors))

    def test_explicit_conflict_and_corrupt_inner_config_fail_closed(self):
        conflict = FakeClusterConfig(local_ip='10.0.0.8')
        with self.assertRaises(ObserverIdentityError):
            ObserverIdentity.prepare(FakePluginContext(conflict), conflict)

        corrupt = FakeClusterConfig()
        corrupt._deploy_config = types.SimpleNamespace(
            inner_config=types.SimpleNamespace(load_error=ValueError('invalid yaml')))
        with self.assertRaises(ObserverIdentityError):
            ObserverIdentity.marker(corrupt)

        retry_conflict = FakeClusterConfig()
        context = FakePluginContext(retry_conflict)
        ObserverIdentity.prepare(context, retry_conflict)
        retry_conflict.config['devname'] = 'eth0'
        with self.assertRaises(ObserverIdentityError):
            ObserverIdentity.prepare(context, retry_conflict)

    def test_planned_retry_forces_loopback_full_start_parameters(self):
        for version in ('4.2.5.0', '4.6.0.0'):
            with self.subTest(version=version):
                cluster = FakeClusterConfig()
                ObserverIdentity.prepare(FakePluginContext(cluster), cluster)
                context = FakePluginContext(cluster)
                context.clients[cluster.server] = FakeClient()
                plugin = load_start_pre_plugin(version)
                self.assertTrue(plugin.start_pre(context))
                command = context.variables['clusters_cmd'][cluster.server]
                self.assertIn("-r '127.0.0.1:2882:2881'", command)
                self.assertIn("-I '127.0.0.1'", command)
                self.assertNotIn('configserver.invalid', command)
                self.assertTrue(context.variables['need_bootstrap'])
                self.assertNotIn('local_ip', cluster.config)

    def test_obshell_identity_uses_loopback_but_management_clients_stay_external(self):
        cluster = FakeClusterConfig(version='4.2.5.6', local_ip=const.OBSERVER_LOOPBACK_IP)
        cluster.config.update({'root_password': 'secret', 'obshell_port': 2886})
        context = FakePluginContext(cluster, DeployStatus.STATUS_RUNNING)
        context.variables.update({'need_bootstrap': True, 'start_obshell': True, 'scale_out': False})
        client = FakeObshellClient()
        context.clients[cluster.server] = client
        context.stdio.start_loading = lambda *args, **kwargs: None
        context.stdio.stop_loading = lambda *args, **kwargs: None
        context.stdio.warn = lambda *args, **kwargs: None

        self.assertTrue(load_obshell_start_plugin().obshell_start(context))
        command = next(command for command in client.commands if 'obshell admin start' in command)
        self.assertIn('--ip 127.0.0.1 --port 2886', command)
        self.assertIn('OBSHELL_STANDALONE_MODE=true', command)
        self.assertNotIn('--standalone', command)
        self.assertNotIn('--ip 10.0.0.8', command)

    def test_obshell_standalone_env_is_not_added_for_community_component(self):
        cluster = FakeClusterConfig(name=const.COMP_OB_CE)
        cluster.config.update({'root_password': 'secret', 'obshell_port': 2886})
        context = FakePluginContext(cluster, DeployStatus.STATUS_RUNNING)
        context.variables.update({'need_bootstrap': True, 'start_obshell': True, 'scale_out': False})
        client = FakeObshellClient()
        context.clients[cluster.server] = client
        context.stdio.start_loading = lambda *args, **kwargs: None
        context.stdio.stop_loading = lambda *args, **kwargs: None
        context.stdio.warn = lambda *args, **kwargs: None

        self.assertTrue(load_obshell_start_plugin().obshell_start(context))
        command = next(command for command in client.commands if 'obshell admin start' in command)
        self.assertIn('--ip 10.0.0.8 --port 2886', command)
        self.assertNotIn('OBSHELL_STANDALONE_MODE', command)

    def test_network_dr_capabilities_fail_closed(self):
        cluster = FakeClusterConfig()
        ObserverIdentity.prepare(FakePluginContext(cluster), cluster)
        with self.assertRaises(ObserverIdentityError):
            ObserverIdentity.reject_loopback_capability({'standalone': cluster}, 'tenant switchover')

    def test_failover_probe_distinguishes_unreachable_from_unverified(self):
        plugin = load_tenant_ha_plugin('failover_decouple_tenant_pre.py')
        self.assertEqual(
            ['10.0.0.8:2881+2882', '10.0.0.9:2881'],
            plugin.normalize_primary_endpoints(
                '10.0.0.8:2881+2882;10.0.0.8:2881+3882;'
                '10.0.0.9:2881'))
        with self.assertRaises(ObserverIdentityError):
            plugin.normalize_primary_endpoints('10.0.0.8:not-a-port')

        multi_endpoints = ['10.0.0.8:2881', '10.0.0.9:2881']
        self.assertTrue(plugin.allow_unverified_primary_probe(
            const.COMP_OB_CE, 'mysql', False, None, multi_endpoints))
        for args in (
                (const.COMP_OB, 'mysql', False, None, multi_endpoints),
                (const.COMP_OB_CE, 'oracle', False, None, multi_endpoints),
                (const.COMP_OB_STANDALONE, 'mysql', False, None,
                 multi_endpoints),
                (const.COMP_OB_AI, 'mysql', False, None, multi_endpoints),
                (const.COMP_OB_CE, 'mysql', True, None, multi_endpoints),
                (const.COMP_OB_CE, 'mysql', False, object(),
                 multi_endpoints),
                (const.COMP_OB_CE, 'mysql', False, None,
                 ['10.0.0.8:2881'])):
            with self.subTest(args=args):
                self.assertFalse(plugin.allow_unverified_primary_probe(*args))

        with mock.patch.object(
                plugin.socket, 'create_connection',
                side_effect=OSError(errno.ECONNREFUSED, 'unreachable')):
            self.assertFalse(plugin.probe_primary_endpoint(
                '10.0.0.8', 2881, lambda: self.fail('probe must not run')))
        with mock.patch.object(
                plugin.socket, 'create_connection',
                side_effect=OSError(errno.EMFILE, 'local fd exhaustion')):
            with self.assertRaises(ObserverIdentityError):
                plugin.probe_primary_endpoint(
                    '10.0.0.8', 2881, lambda: self.fail('probe must not run'))
        with mock.patch.object(
                plugin.socket, 'create_connection',
                side_effect=OSError(errno.ECONNRESET, 'peer reset')):
            with self.assertRaises(ObserverIdentityError):
                plugin.probe_primary_endpoint(
                    '10.0.0.8', 2881, lambda: self.fail('probe must not run'))

        with mock.patch.object(plugin.socket, 'create_connection', return_value=FakeSocket()):
            self.assertTrue(plugin.probe_primary_endpoint(
                '10.0.0.8', 2881, lambda: True))
            with self.assertRaises(ObserverIdentityError):
                plugin.probe_primary_endpoint('10.0.0.8', 2881, lambda: False)
            self.assertIsNone(plugin.probe_primary_endpoint(
                '10.0.0.8', 2881, lambda: False, fail_closed=False))
            with self.assertRaises(ObserverIdentityError):
                plugin.probe_primary_endpoint(
                    '10.0.0.8', 2881,
                    lambda: (_ for _ in ()).throw(RuntimeError('authentication failed')))
            with self.assertRaises(ObserverIdentityError):
                plugin.probe_primary_endpoint(
                    '10.0.0.8', 2881,
                    lambda: (_ for _ in ()).throw(RuntimeError('authentication failed')),
                    fail_closed=False)
        with mock.patch.object(
                plugin.socket, 'create_connection', return_value=FailingCloseSocket()):
            self.assertTrue(plugin.probe_primary_endpoint(
                '10.0.0.8', 2881, lambda: True))
        self.assertTrue(plugin.is_primary_probe_timeout_error(
            RuntimeError(4012, 'tenant unavailable')))
        self.assertFalse(plugin.is_primary_probe_timeout_error(
            RuntimeError(1045, 'access denied')))

    def test_failover_allows_unavailable_tenant_on_reachable_minority(self):
        plugin = load_tenant_ha_plugin('failover_decouple_tenant_pre.py')

        class StandbyConfig(object):
            name = const.COMP_OB_CE
            deploy_name = 'standby'

            def __init__(self):
                self.attrs = {
                    'primary_tenant': {
                        'standby_tenant': [
                            ('primary', 'primary_tenant')]
                    }
                }

            def get_component_attr(self, key):
                return self.attrs.get(key)

        class Context(object):

            def __init__(self):
                self.cluster_config = StandbyConfig()
                self.cmds = ['standby', 'standby_tenant', 'failover']
                self.options = types.SimpleNamespace(
                    tenant_name='standby_tenant', tenant_root_password='')
                self.stdio = mock.Mock()
                self.variables = {
                    'relation_tenants': [
                        ('primary', 'primary_tenant')]
                }

            def get_variable(self, key, default=None):
                return self.variables.get(key, default)

            def set_variable(self, key, value):
                self.variables[key] = value

            @staticmethod
            def return_true(**kwargs):
                return True

            @staticmethod
            def return_false(**kwargs):
                return False

        class StandbyCursor(object):

            def __init__(self, primary_ip_list=None):
                self.sqls = []
                self.primary_ip_list = primary_ip_list or (
                    '10.0.0.1:2881;10.0.0.2:2881;10.0.0.3:2881')

            def fetchone(self, sql, args=None, **kwargs):
                self.sqls.append(sql)
                if 'TENANT_ROLE' in sql:
                    return {
                        'TENANT_ID': 1002,
                        'TENANT_ROLE': 'STANDBY',
                        'TENANT_TYPE': 'USER',
                        'STATUS': 'NORMAL',
                        'COMPATIBILITY_MODE': 'MYSQL',
                    }
                if 'SELECT TYPE' in sql:
                    return {'TYPE': const.SERVICE_MODE}
                if 'log_restore_source as a' in sql:
                    return {
                        'VALUE': (
                            'IP_LIST={},USER=standbyro@primary_tenant,'
                            'PASSWORD=test-secret'.format(
                                self.primary_ip_list))
                    }
                if 'COUNT(1)' in sql:
                    return {'count': 0}
                raise AssertionError(sql)

        direct_endpoints = []
        probe_results = []

        class TenantProbeCursor(object):

            def __init__(self, **kwargs):
                direct_endpoints.append((kwargs['ip'], int(kwargs['port'])))

            @staticmethod
            def execute(sql, **kwargs):
                assert sql == 'show databases like "oceanbase"'
                assert kwargs['raise_exception'] is True
                result = probe_results.pop(0)
                if isinstance(result, Exception):
                    raise result
                return result

            @staticmethod
            def close():
                pass

        context = Context()
        standby_cursor = StandbyCursor()
        probe_results[:] = [RuntimeError(4012, 'tenant unavailable')]
        connect_results = [
            OSError(errno.ECONNREFUSED, 'refused'),
            socket.timeout('timed out'),
            FakeSocket(),
        ]
        with mock.patch.object(
                plugin.socket, 'create_connection',
                side_effect=connect_results) as connect, \
                mock.patch.object(plugin, 'Cursor', TenantProbeCursor):
            result = plugin.failover_decouple_tenant_pre(
                context,
                cursors={'standby': standby_cursor},
                cluster_configs={'primary': object()})

        self.assertTrue(result)
        self.assertEqual(3, connect.call_count)
        self.assertEqual([('10.0.0.3', 2881)], direct_endpoints)
        self.assertTrue(any('COUNT(1)' in sql for sql in standby_cursor.sqls))
        context.stdio.error.assert_not_called()

        context = Context()
        standby_cursor = StandbyCursor()
        direct_endpoints[:] = []
        probe_results[:] = []
        with mock.patch.object(
                plugin.socket, 'create_connection',
                side_effect=[
                    OSError(errno.ECONNREFUSED, 'refused'),
                    socket.timeout('timed out'),
                    OSError(errno.EHOSTUNREACH, 'unreachable'),
                ]) as connect, \
                mock.patch.object(plugin, 'Cursor', TenantProbeCursor):
            result = plugin.failover_decouple_tenant_pre(
                context,
                cursors={'standby': standby_cursor},
                cluster_configs={'primary': object()})

        self.assertTrue(result)
        self.assertEqual(3, connect.call_count)
        self.assertEqual([], direct_endpoints)
        self.assertTrue(any('COUNT(1)' in sql for sql in standby_cursor.sqls))
        context.stdio.error.assert_not_called()

        for reachable_count, connect_results in (
                (2, [
                    FakeSocket(), FakeSocket(),
                    OSError(errno.EHOSTUNREACH, 'unreachable')]),
                (3, [FakeSocket(), FakeSocket(), FakeSocket()])):
            with self.subTest(reachable_count=reachable_count):
                context = Context()
                standby_cursor = StandbyCursor()
                direct_endpoints[:] = []
                probe_results[:] = [
                    RuntimeError(4012, 'tenant unavailable')
                    for _ in range(reachable_count)]
                with mock.patch.object(
                        plugin.socket, 'create_connection',
                        side_effect=connect_results) as connect, \
                        mock.patch.object(plugin, 'Cursor', TenantProbeCursor):
                    result = plugin.failover_decouple_tenant_pre(
                        context,
                        cursors={'standby': standby_cursor},
                        cluster_configs={'primary': object()})

                self.assertIsNone(result)
                self.assertEqual(3, connect.call_count)
                self.assertEqual(
                    [('10.0.0.{}'.format(index), 2881)
                     for index in range(1, reachable_count + 1)],
                    direct_endpoints)
                self.assertFalse(any(
                    'COUNT(1)' in sql for sql in standby_cursor.sqls))
                context.stdio.error.assert_called_once_with(
                    'A majority of primary endpoints is reachable but the '
                    'tenant probes could not be verified; refusing failover.')

        context = Context()
        standby_cursor = StandbyCursor()
        direct_endpoints[:] = []
        probe_results[:] = [
            RuntimeError(4012, 'tenant unavailable'), True]
        with mock.patch.object(
                plugin.socket, 'create_connection',
                side_effect=[FakeSocket(), FakeSocket()]) as connect, \
                mock.patch.object(plugin, 'Cursor', TenantProbeCursor):
            result = plugin.failover_decouple_tenant_pre(
                context,
                cursors={'standby': standby_cursor},
                cluster_configs={'primary': object()})

        self.assertIsNone(result)
        self.assertEqual(2, connect.call_count)
        self.assertEqual(
            [('10.0.0.1', 2881), ('10.0.0.2', 2881)],
            direct_endpoints)
        self.assertFalse(any(
            'COUNT(1)' in sql for sql in standby_cursor.sqls))
        context.stdio.error.assert_called_once_with(
            'Primary tenant status is alive, not support failover.')

        context = Context()
        standby_cursor = StandbyCursor()
        direct_endpoints[:] = []
        probe_results[:] = [
            RuntimeError(4012, 'tenant unavailable'),
            RuntimeError(1045, 'authentication failed')]
        with mock.patch.object(
                plugin.socket, 'create_connection',
                side_effect=[FakeSocket(), FakeSocket()]) as connect, \
                mock.patch.object(plugin, 'Cursor', TenantProbeCursor):
            result = plugin.failover_decouple_tenant_pre(
                context,
                cursors={'standby': standby_cursor},
                cluster_configs={'primary': object()})

        self.assertIsNone(result)
        self.assertEqual(2, connect.call_count)
        self.assertEqual(
            [('10.0.0.1', 2881), ('10.0.0.2', 2881)],
            direct_endpoints)
        self.assertFalse(any(
            'COUNT(1)' in sql for sql in standby_cursor.sqls))
        context.stdio.error.assert_called_once_with(
            'Primary endpoint 10.0.0.2:2881 is reachable but the tenant '
            'probe failed; refusing failover.')

        context = Context()
        standby_cursor = StandbyCursor(
            '10.0.0.8:2881+2882;10.0.0.8:2881+3882')
        direct_endpoints[:] = []
        probe_results[:] = [RuntimeError(4012, 'tenant unavailable')]
        with mock.patch.object(
                plugin.socket, 'create_connection',
                return_value=FakeSocket()) as connect, \
                mock.patch.object(plugin, 'Cursor', TenantProbeCursor):
            result = plugin.failover_decouple_tenant_pre(
                context,
                cursors={'standby': standby_cursor},
                cluster_configs={'primary': object()})

        self.assertIsNone(result)
        self.assertEqual(1, connect.call_count)
        self.assertEqual([('10.0.0.8', 2881)], direct_endpoints)
        self.assertFalse(any(
            'COUNT(1)' in sql for sql in standby_cursor.sqls))
        context.stdio.error.assert_called_once_with(
            'Primary endpoint 10.0.0.8:2881 is reachable but the tenant '
            'probe could not be verified; refusing failover.')

    def test_strong_standby_resolution_uses_unique_endpoint_not_tenant_name(self):
        plugin = load_tenant_ha_plugin('switchover_tenant.py')
        target = FakeClusterConfig()
        other = FakeClusterConfig()
        other.server.ip = '10.0.0.9'
        cursors = {
            'target': FakeTenantAccessPointCursor('10.0.0.8:2881'),
            'other': FakeTenantAccessPointCursor('10.0.0.9:2881'),
        }
        configs = {'target': target, 'other': other}
        self.assertEqual(
            'other',
            plugin.resolve_strong_standby_deploy(
                'same_name', ['10.0.0.9:2881'], 'target', 'same_name',
                [['other', 'same_name']], cursors, configs))
        with self.assertRaises(ObserverIdentityError):
            plugin.resolve_strong_standby_deploy(
                'same_name', ['127.0.0.1:2881'], 'target', 'same_name',
                [['other', 'same_name']], cursors, configs)

        target.attrs.update({
            const.OBSERVER_IDENTITY_IP: const.OBSERVER_LOOPBACK_IP,
            const.OBSERVER_IDENTITY_STATE: const.OBSERVER_IDENTITY_VERIFIED,
            const.OBSERVER_IDENTITY_SOURCE: const.OBSERVER_IDENTITY_FRESH_BOOTSTRAP,
        })
        self.assertEqual(
            'target',
            plugin.resolve_strong_standby_deploy(
                'same_name', ['127.0.0.1:2881+2882'], 'target', 'same_name',
                [], {'target': cursors['target']}, {'target': target}))
        with self.assertRaises(ObserverIdentityError):
            plugin.resolve_strong_standby_deploy(
                'same_name', ['127.0.0.1:2881+9999'], 'target', 'same_name',
                [], {'target': cursors['target']}, {'target': target})
        with self.assertRaises(ObserverIdentityError):
            plugin.resolve_strong_standby_deploy(
                'same_name', [], 'target', 'same_name',
                [], {'target': cursors['target']}, {'target': target})

    def test_protected_mode_metadata_requires_user_and_endpoint(self):
        plugin = load_tenant_ha_plugin('switchover_tenant.py')
        for value in ('', 'USER=standbyro@tenant', 'SERVICE=10.0.0.8:2881'):
            with self.subTest(value=value):
                with self.assertRaises(ObserverIdentityError):
                    plugin.parse_tenant_endpoint_metadata(value, 'Strong standby')
        self.assertEqual(
            ('tenant', ['127.0.0.1:2881+2882']),
            plugin.parse_tenant_endpoint_metadata(
                'SERVICE=127.0.0.1:2881+2882,USER=standbyro@tenant',
                'Strong standby'))

    def test_protection_mode_lookup_fails_closed(self):
        plugin = load_tenant_ha_plugin('switchover_tenant.py')
        cursor = mock.Mock()
        cursor.fetchone.return_value = None
        with self.assertRaises(ObserverIdentityError):
            plugin.get_tenant_protection_mode(cursor, 'tenant')
        cursor.fetchone.return_value = {
            'PROTECTION_MODE': 'MAXIMUM PERFORMANCE'}
        self.assertEqual(
            'MAXIMUM PERFORMANCE',
            plugin.get_tenant_protection_mode(cursor, 'tenant'))
        cursor.fetchone.assert_called_with(
            mock.ANY, ('tenant',), raise_exception=True,
            exc_level='verbose')

    def test_loopback_failover_mapping_must_be_unique_and_match_source(self):
        plugin = load_tenant_ha_plugin('failover_decouple_tenant_pre.py')
        primary = FakeClusterConfig()
        primary.attrs.update({
            const.OBSERVER_IDENTITY_IP: const.OBSERVER_LOOPBACK_IP,
            const.OBSERVER_IDENTITY_STATE: const.OBSERVER_IDENTITY_VERIFIED,
            const.OBSERVER_IDENTITY_SOURCE: const.OBSERVER_IDENTITY_FRESH_BOOTSTRAP,
        })
        standby = FakeClusterConfig()
        standby.config.update({'mysql_port': 3881, 'rpc_port': 3882})
        standby.attrs.update({
            const.OBSERVER_IDENTITY_IP: const.OBSERVER_LOOPBACK_IP,
            const.OBSERVER_IDENTITY_STATE: const.OBSERVER_IDENTITY_VERIFIED,
            const.OBSERVER_IDENTITY_SOURCE: const.OBSERVER_IDENTITY_FRESH_BOOTSTRAP,
        })
        relations = [('primary', 'same_name'), ('standby', 'same_name')]
        configs = {'primary': primary, 'standby': standby}
        self.assertEqual(
            ('primary', 'same_name'),
            plugin.resolve_loopback_primary_mapping(
                ('primary', 'same_name'), 'standbyro@same_name',
                ['127.0.0.1:2881+2882'], relations, configs))
        with self.assertRaises(ObserverIdentityError):
            plugin.resolve_loopback_primary_mapping(
                ('standby', 'same_name'), 'standbyro@same_name',
                ['127.0.0.1:2881+2882'], relations, configs)

        standby.config.update({'mysql_port': 2881, 'rpc_port': 2882})
        with self.assertRaises(ObserverIdentityError):
            plugin.resolve_loopback_primary_mapping(
                ('primary', 'same_name'), 'standbyro@same_name',
                ['127.0.0.1:2881+2882'], relations, configs)

    def test_service_metadata_preserves_password_punctuation(self):
        plugin = load_tenant_ha_plugin('failover_decouple_tenant_pre.py')
        secret = "Ab=c,d$E'fg"
        metadata = plugin.parse_service_metadata(
            'IP_LIST=10.0.0.8:2881,USER=standbyro@tenant,PASSWORD=%s,'
            'TENANT_ID=1002,CLUSTER_ID=1,COMPATIBILITY_MODE=MYSQL,'
            'IS_ENCRYPTED=false' % secret)
        self.assertEqual('10.0.0.8:2881', metadata['IP_LIST'])
        self.assertEqual('standbyro@tenant', metadata['USER'])
        self.assertEqual(secret, metadata['PASSWORD'])
        self.assertEqual('1002', metadata['TENANT_ID'])
        self.assertEqual('false', metadata['IS_ENCRYPTED'])

        get_standbys = load_tenant_ha_plugin(
            'get_standbys.py', version='4.2.0.0')
        self.assertIs(get_standbys.parse_service_metadata,
                      tool.parse_service_metadata)
        self.assertEqual(secret, get_standbys.parse_service_metadata(
            'SERVICE=10.0.0.8:2881+2882,USER=standbyro@tenant,'
            'PASSWORD=%s,TENANT_ID=1002' % secret)['PASSWORD'])

    def test_log_restore_source_binding_matches_tenant_mode(self):
        for filename in (
                'switchover_tenant.py',
                'switchover_relation_tenants.py'):
            with self.subTest(filename=filename):
                plugin = load_tenant_ha_plugin(filename)
                restore_source = (
                    "SERVICE=10.0.0.8:2881 USER=standbyro@tenant "
                    "PASSWORD=Ab'cd")
                mysql_sql, mysql_args = (
                    plugin.get_log_restore_source_statement(
                        'mysql', restore_source))
                self.assertEqual(
                    'ALTER SYSTEM SET LOG_RESTORE_SOURCE = %s', mysql_sql)
                self.assertEqual((restore_source,), mysql_args)
                oracle_sql, oracle_args = (
                    plugin.get_log_restore_source_statement(
                        'oracle', restore_source))
                self.assertEqual(
                    "ALTER SYSTEM SET LOG_RESTORE_SOURCE = "
                    "'SERVICE=10.0.0.8:2881 USER=standbyro@tenant "
                    "PASSWORD=Ab''cd'", oracle_sql)
                self.assertIsNone(oracle_args)

    def test_tenant_alter_helpers_propagate_execution_failures(self):
        cluster = FakeClusterConfig()
        for version, filename in (
                ('4.4.2.1', 'switchover_tenant.py'),
                ('4.2.0.0', 'failover_decouple_tenant.py')):
            with self.subTest(version=version, filename=filename):
                plugin = load_tenant_ha_plugin(filename, version=version)
                with self.assertRaises(RuntimeError):
                    plugin.exec_sql_in_tenant(
                        'ALTER SYSTEM TEST', FakeTenantParentCursor(), 'tenant',
                        'mysql', raise_exception=True, retries=0,
                        cluster_config=cluster)

    def test_strong_sync_destination_uses_bound_credentials(self):
        plugin = load_tenant_ha_plugin('switchover_relation_tenants.py')
        cursor = CapturingDatabaseCursor()
        secret = "Ab c$D'ef\\ghi"
        destination = (
            'SERVICE=10.0.0.8:2881 USER=standbyro@tenant PASSWORD=%s' %
            secret)
        self.assertTrue(plugin.set_sync_standby_dest(
            cursor, 'tenant', destination))
        self.assertEqual(1, len(cursor.calls))
        sql, args, kwargs = cursor.calls[0]
        self.assertNotIn(secret, sql)
        self.assertEqual((destination, 'tenant'), args)
        self.assertTrue(kwargs['raise_exception'])

    def test_cursor_never_logs_raw_password_or_sensitive_sql(self):
        secret = "Ab c$D'ef"
        stdio = CapturingStdio()
        with mock.patch.object(tool.mysql, 'connect', return_value=FakeDatabase()):
            cursor = tool.Cursor(
                ip='10.0.0.8', port=2881, user='root', tenant='sys',
                password=secret, stdio=stdio)
        cursor.execute(
            "ALTER SYSTEM SET LOG_RESTORE_SOURCE = 'PASSWORD={}'".format(secret),
            args=(secret,), stdio=stdio)
        output = '\n'.join(stdio.messages)
        self.assertNotIn(secret, output)
        self.assertIn('-p******', output)
        self.assertIn('<sensitive SQL omitted>', output)
        self.assertIn('args: <provided>', output)

    def test_sensitive_sql_failure_hides_driver_exception(self):
        secret = "Ab c$D'ef"
        stdio = CapturingStdio()
        with mock.patch.object(
                tool.mysql, 'connect',
                return_value=SecretFailingDatabase(secret)):
            cursor = tool.Cursor(
                ip='10.0.0.8', port=2881, user='root', tenant='sys',
                password=secret, stdio=stdio)
        with self.assertRaisesRegex(
                RuntimeError, 'Sensitive SQL execution failed') as raised:
            cursor.execute(
                'ALTER SYSTEM SET LOG_RESTORE_SOURCE = %s',
                args=('SERVICE=10.0.0.8:2881 PASSWORD=%s' % secret,),
                raise_exception=True, stdio=stdio)
        output = '\n'.join(stdio.messages) + str(raised.exception)
        self.assertNotIn(secret, output)
        self.assertIn('<sensitive SQL omitted>', output)


if __name__ == '__main__':
    unittest.main()
