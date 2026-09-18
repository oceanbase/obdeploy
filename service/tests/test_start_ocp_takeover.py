# coding: utf-8

from __future__ import absolute_import, division, print_function

import unittest
import importlib.util
import os
import shutil
import tempfile
from optparse import Values
from types import SimpleNamespace
from unittest import mock

import const
from _deploy import ClusterConfig, DeployConfigStatus, DeployStatus, ServerConfig
from core import ObdHome


class FakeServer(object):

    def __init__(self, ip='10.0.0.8'):
        self.ip = ip
        self.name = ip


class FakeOcpConfig(object):

    def __init__(self, server_config, depends):
        self.servers = [FakeServer()]
        self.depends = depends
        self.server_config = server_config
        self.server_config_calls = 0

    def get_server_conf_with_default(self, server):
        self.server_config_calls += 1
        return dict(self.server_config)


class FakeDeployConfig(object):

    def __init__(self, ocp_config=None, ob_component=const.COMP_OB_CE,
                 extra_ob_components=None):
        self.components = {}
        if ob_component:
            self.components[ob_component] = object()
        for component in extra_ob_components or []:
            self.components[component] = object()
        if ocp_config:
            self.components[const.COMP_OCP_SERVER_CE] = ocp_config


class FakeDeployInfo(object):

    def __init__(self, status, components):
        self.status = status
        self.config_status = DeployConfigStatus.UNCHNAGE
        self.components = components


class FakeDeploy(object):

    def __init__(self, deploy_config, status=DeployStatus.STATUS_DEPLOYED):
        self.name = 'ocp-test'
        self.deploy_config = deploy_config
        self.deploy_info = FakeDeployInfo(status, deploy_config.components)
        self.config_dir = tempfile.mkdtemp(prefix='obd-ocp-takeover-')


class FakeDeployManager(object):

    def __init__(self, deploy):
        self.deploy = deploy

    def get_deploy_config(self, name):
        return self.deploy


class IncludeDeployConfig(object):

    def __init__(self, config=None):
        self.config = config or {
            'jdbc_url': 'jdbc:oceanbase://external-metadb:2881/ocp',
            'port': 8280,
            'admin_password': 'include-password',
        }

    def get_base_dir(self):
        return ''

    def load_include_file(self, path):
        return {'config': self.config}


class StartOcpTakeoverTest(unittest.TestCase):

    def build_obd(self, server_config=None, depends=None,
                  status=DeployStatus.STATUS_DEPLOYED, options=None,
                  ob_component=const.COMP_OB_CE, extra_ob_components=None):
        if server_config is None:
            server_config = {
                'port': 8180,
                'admin_password': 'server-password',
            }
        if depends is None:
            depends = [ob_component]
        ocp_config = FakeOcpConfig(server_config, depends)
        deploy_config = FakeDeployConfig(
            ocp_config, ob_component, extra_ob_components=extra_ob_components)
        deploy = FakeDeploy(deploy_config, status)
        self.addCleanup(shutil.rmtree, deploy.config_dir)

        obd = ObdHome.__new__(ObdHome)
        obd._deploy_manager = FakeDeployManager(deploy)
        obd.options = Values(options or {})
        obd.deploy = None
        obd.repositories = []
        obd._call_stdio = mock.Mock()
        obd._require_seekdb_check = mock.Mock(return_value=True)
        obd.load_local_repositories = mock.Mock(return_value=[object()])
        obd._start_cluster = mock.Mock(return_value=True)
        obd.export_to_ocp = mock.Mock(return_value=None)
        obd.set_deploy = mock.Mock(side_effect=lambda value: setattr(obd, 'deploy', value))
        obd.set_repositories = mock.Mock(
            side_effect=lambda value: setattr(obd, 'repositories', value))
        return obd, deploy, ocp_config

    def test_first_full_start_takes_over_internal_metadb(self):
        obd, deploy, ocp_config = self.build_obd()
        takeover_options = {}

        def export_to_ocp(name, component_name=None):
            takeover_options.update({
                'name': name,
                'component_name': component_name,
                'address': obd.options.address,
                'user': obd.options.user,
                'password': obd.options.password,
            })

        obd.export_to_ocp.side_effect = export_to_ocp

        self.assertTrue(obd.start_cluster(deploy.name))

        self.assertEqual(2, ocp_config.server_config_calls)
        self.assertEqual({
            'name': deploy.name,
            'component_name': const.COMP_OB_CE,
            'address': 'http://10.0.0.8:8180',
            'user': 'admin',
            'password': 'server-password',
        }, takeover_options)
        self.assertFalse(hasattr(obd.options, 'address'))
        self.assertFalse(hasattr(obd.options, 'user'))
        self.assertFalse(hasattr(obd.options, 'password'))
        self.assertIs(deploy, obd.deploy)
        self.assertFalse(os.path.exists(obd._ocp_takeover_pending_path(deploy)))

    def test_takeover_failure_fails_start_result_and_restores_options(self):
        original_options = {
            'address': 'http://old-ocp:8080',
            'user': 'old-user',
            'password': 'old-password',
        }
        obd, deploy, _ = self.build_obd(options=original_options)
        obd.export_to_ocp.return_value = False

        self.assertFalse(obd.start_cluster(deploy.name))

        for key, value in original_options.items():
            self.assertEqual(value, getattr(obd.options, key))
        self.assertIs(deploy, obd.deploy)
        self.assertTrue(os.path.exists(obd._ocp_takeover_pending_path(deploy)))

    def test_takeover_failure_is_retried_after_cluster_becomes_running(self):
        obd, deploy, _ = self.build_obd()

        def start_cluster(*args, **kwargs):
            deploy.deploy_info.status = DeployStatus.STATUS_RUNNING
            return True

        obd._start_cluster.side_effect = start_cluster
        obd.export_to_ocp.side_effect = [False, None]

        self.assertFalse(obd.start_cluster(deploy.name))
        self.assertTrue(obd.start_cluster(deploy.name))

        self.assertEqual(2, obd.export_to_ocp.call_count)
        self.assertFalse(os.path.exists(obd._ocp_takeover_pending_path(deploy)))

    def test_pending_marker_is_kept_until_takeover_succeeds(self):
        obd, deploy, _ = self.build_obd()
        self.assertTrue(obd._set_ocp_takeover_pending(deploy, True))
        marker_seen_during_takeover = []

        def export_to_ocp(name, component_name=None):
            marker_seen_during_takeover.append(
                os.path.exists(obd._ocp_takeover_pending_path(deploy)))
            obd._set_ocp_takeover_pending(deploy, False)

        obd.export_to_ocp.side_effect = export_to_ocp

        self.assertTrue(obd.start_cluster(deploy.name))

        self.assertEqual([True], marker_seen_during_takeover)
        self.assertFalse(os.path.exists(obd._ocp_takeover_pending_path(deploy)))

    def test_marker_exists_before_component_start(self):
        obd, deploy, _ = self.build_obd()

        def start_cluster(*args, **kwargs):
            self.assertTrue(os.path.exists(
                obd._ocp_takeover_pending_path(deploy)))
            return True

        obd._start_cluster.side_effect = start_cluster

        self.assertTrue(obd.start_cluster(deploy.name))

    def test_interrupt_during_component_start_keeps_marker(self):
        obd, deploy, _ = self.build_obd()
        obd._start_cluster.side_effect = KeyboardInterrupt()

        with self.assertRaises(KeyboardInterrupt):
            obd.start_cluster(deploy.name)

        self.assertTrue(os.path.exists(
            obd._ocp_takeover_pending_path(deploy)))
        obd.export_to_ocp.assert_not_called()

    def test_keyboard_interrupt_keeps_marker_for_next_start(self):
        obd, deploy, _ = self.build_obd()

        def start_cluster(*args, **kwargs):
            deploy.deploy_info.status = DeployStatus.STATUS_RUNNING
            return True

        obd._start_cluster.side_effect = start_cluster
        obd.export_to_ocp.side_effect = [KeyboardInterrupt(), None]

        with self.assertRaises(KeyboardInterrupt):
            obd.start_cluster(deploy.name)
        self.assertTrue(os.path.exists(
            obd._ocp_takeover_pending_path(deploy)))

        self.assertTrue(obd.start_cluster(deploy.name))
        self.assertEqual(2, obd.export_to_ocp.call_count)

    def test_password_is_captured_before_start_encrypts_config(self):
        obd, deploy, ocp_config = self.build_obd()
        takeover_passwords = []

        def encrypt_during_start(*args, **kwargs):
            ocp_config.server_config['admin_password'] = 'encrypted-password'
            return True

        def export_to_ocp(name, component_name=None):
            takeover_passwords.append(obd.options.password)

        obd._start_cluster.side_effect = encrypt_during_start
        obd.export_to_ocp.side_effect = export_to_ocp

        self.assertTrue(obd.start_cluster(deploy.name))

        self.assertEqual(['server-password'], takeover_passwords)

    def test_default_port_applied_during_start_is_used_for_takeover(self):
        obd, deploy, ocp_config = self.build_obd(server_config={
            'admin_password': 'server-password',
        })
        takeover_addresses = []

        def apply_defaults_during_start(*args, **kwargs):
            ocp_config.server_config['port'] = 8080
            return True

        def export_to_ocp(name, component_name=None):
            takeover_addresses.append(obd.options.address)

        obd._start_cluster.side_effect = apply_defaults_during_start
        obd.export_to_ocp.side_effect = export_to_ocp

        self.assertTrue(obd.start_cluster(deploy.name))

        self.assertEqual(['http://10.0.0.8:8080'], takeover_addresses)

    def test_dependent_ob_component_is_used_in_mixed_deployment(self):
        obd, deploy, _ = self.build_obd(
            ob_component=const.COMP_OB_CE,
            extra_ob_components=[const.COMP_OB])

        self.assertTrue(obd.start_cluster(deploy.name))

        obd.export_to_ocp.assert_called_once_with(
            deploy.name, component_name=const.COMP_OB_CE)

    def test_external_metadb_does_not_trigger_takeover(self):
        obd, deploy, ocp_config = self.build_obd(server_config={
            'jdbc_url': 'jdbc:oceanbase://external-metadb:2881/ocp',
            'port': 8180,
            'admin_password': 'server-password',
        })

        self.assertTrue(obd.start_cluster(deploy.name))

        self.assertEqual(1, ocp_config.server_config_calls)
        obd.export_to_ocp.assert_not_called()

    def test_include_and_server_overrides_are_used_to_detect_external_metadb(self):
        server = ServerConfig('10.0.0.8', 'ocp-1')
        ocp_config = ClusterConfig(
            [server], const.COMP_OCP_SERVER_CE, '4.2.1', '', '', '', '', '')
        ocp_config.set_deploy_config(IncludeDeployConfig())
        ocp_config.set_include_file('ocp-include.yaml')
        ocp_config.set_global_conf({'admin_password': 'global-password'})
        ocp_config.add_server_conf(server, {'port': 8380})
        ocp_config._depends[const.COMP_OB_CE] = object()
        deploy = FakeDeploy(FakeDeployConfig(None))
        deploy.deploy_config.components[const.COMP_OCP_SERVER_CE] = ocp_config
        deploy.deploy_info.components = deploy.deploy_config.components
        self.addCleanup(shutil.rmtree, deploy.config_dir)

        obd, _, _ = self.build_obd()
        obd._deploy_manager = FakeDeployManager(deploy)

        self.assertTrue(obd.start_cluster(deploy.name))

        obd.export_to_ocp.assert_not_called()

    def test_include_and_server_overrides_supply_internal_ocp_context(self):
        server = ServerConfig('10.0.0.8', 'ocp-1')
        ocp_config = ClusterConfig(
            [server], const.COMP_OCP_SERVER_CE, '4.2.1', '', '', '', '', '')
        ocp_config.set_deploy_config(IncludeDeployConfig({
            'port': 8280,
            'admin_password': 'include-password',
        }))
        ocp_config.set_include_file('ocp-include.yaml')
        ocp_config.set_global_conf({})
        ocp_config.add_server_conf(server, {'port': 8380})
        ocp_config._depends[const.COMP_OB_CE] = object()
        deploy = FakeDeploy(FakeDeployConfig(None))
        deploy.deploy_config.components[const.COMP_OCP_SERVER_CE] = ocp_config
        deploy.deploy_info.components = deploy.deploy_config.components
        self.addCleanup(shutil.rmtree, deploy.config_dir)

        obd, _, _ = self.build_obd()
        obd._deploy_manager = FakeDeployManager(deploy)
        takeover_options = {}

        def export_to_ocp(name, component_name=None):
            takeover_options.update({
                'address': obd.options.address,
                'password': obd.options.password,
            })

        obd.export_to_ocp.side_effect = export_to_ocp

        self.assertTrue(obd.start_cluster(deploy.name))

        self.assertEqual({
            'address': 'http://10.0.0.8:8380',
            'password': 'include-password',
        }, takeover_options)

    def test_ocp_without_managed_oceanbase_dependency_skips_takeover(self):
        obd, deploy, ocp_config = self.build_obd(depends=[])

        self.assertTrue(obd.start_cluster(deploy.name))

        self.assertEqual(0, ocp_config.server_config_calls)
        obd.export_to_ocp.assert_not_called()

    def test_restart_does_not_repeat_takeover(self):
        obd, deploy, _ = self.build_obd(status=DeployStatus.STATUS_STOPPED)

        self.assertTrue(obd.start_cluster(deploy.name))

        obd.export_to_ocp.assert_not_called()

    def test_partial_first_start_does_not_trigger_takeover(self):
        obd, deploy, _ = self.build_obd(options={'components': const.COMP_OB_CE})

        self.assertTrue(obd.start_cluster(deploy.name))

        obd.export_to_ocp.assert_not_called()

    def test_explicit_all_components_and_servers_triggers_takeover(self):
        components = ','.join([const.COMP_OB_CE, const.COMP_OCP_SERVER_CE])
        obd, deploy, _ = self.build_obd(options={
            'components': components,
            'servers': '10.0.0.8',
        })

        self.assertTrue(obd.start_cluster(deploy.name))

        obd.export_to_ocp.assert_called_once_with(
            deploy.name, component_name=const.COMP_OB_CE)

    def test_failed_component_start_does_not_trigger_takeover(self):
        obd, deploy, _ = self.build_obd()
        obd._start_cluster.return_value = False

        self.assertFalse(obd.start_cluster(deploy.name))

        obd.export_to_ocp.assert_not_called()

    def test_export_to_ocp_uses_requested_ob_component(self):
        enterprise_config = object()
        ce_config = object()
        deploy_config = SimpleNamespace(components={
            const.COMP_OB: enterprise_config,
            const.COMP_OB_CE: ce_config,
            const.COMP_OCP_SERVER: object(),
        })
        deploy = FakeDeploy(deploy_config, DeployStatus.STATUS_RUNNING)
        self.addCleanup(shutil.rmtree, deploy.config_dir)

        obd = ObdHome.__new__(ObdHome)
        obd.options = Values({
            'address': 'http://ocp:8080',
            'user': 'admin',
            'password': 'password',
        })
        obd._deploy_manager = FakeDeployManager(deploy)
        obd.deploy = None
        obd.repositories = []
        obd._call_stdio = mock.Mock()
        obd.load_local_repositories = mock.Mock(return_value=[])
        obd.get_clients = mock.Mock(return_value={})
        obd.get_workflows = mock.Mock(return_value=object())
        obd.run_workflow = mock.Mock(return_value=True)
        obd.set_deploy = mock.Mock(side_effect=lambda value: setattr(obd, 'deploy', value))
        obd.set_repositories = mock.Mock(
            side_effect=lambda value: setattr(obd, 'repositories', value))

        self.assertTrue(obd._set_ocp_takeover_pending(deploy, True))

        self.assertTrue(obd.export_to_ocp(
            deploy.name, component_name=const.COMP_OB_CE))

        workflow_kwargs = obd.run_workflow.call_args[1]
        self.assertIs(
            ce_config,
            workflow_kwargs[const.COMP_OCP_SERVER]['cluster_config'])
        self.assertFalse(os.path.exists(obd._ocp_takeover_pending_path(deploy)))

    def test_manual_export_failure_restores_pending_marker(self):
        enterprise_config = object()
        deploy_config = SimpleNamespace(components={
            const.COMP_OB: enterprise_config,
            const.COMP_OCP_SERVER: object(),
        })
        deploy = FakeDeploy(deploy_config, DeployStatus.STATUS_RUNNING)
        self.addCleanup(shutil.rmtree, deploy.config_dir)

        obd = ObdHome.__new__(ObdHome)
        obd.options = Values({
            'address': 'http://ocp:8080',
            'user': 'admin',
            'password': 'password',
        })
        obd._deploy_manager = FakeDeployManager(deploy)
        obd.deploy = None
        obd.repositories = []
        obd._call_stdio = mock.Mock()
        obd.load_local_repositories = mock.Mock(return_value=[])
        obd.get_clients = mock.Mock(return_value={})
        obd.get_workflows = mock.Mock(return_value=object())
        obd.run_workflow = mock.Mock(return_value=False)
        obd.set_deploy = mock.Mock(side_effect=lambda value: setattr(obd, 'deploy', value))
        obd.set_repositories = mock.Mock(
            side_effect=lambda value: setattr(obd, 'repositories', value))
        self.assertTrue(obd._set_ocp_takeover_pending(deploy, True))

        self.assertFalse(obd.export_to_ocp(deploy.name))

        self.assertTrue(os.path.exists(obd._ocp_takeover_pending_path(deploy)))


class OcpTakeoverRequestMaskingTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        plugin_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'plugins', 'ocp-server', '4.2.1')
        plugin_path = os.path.join(plugin_dir, 'takeover_connect.py')
        spec = importlib.util.spec_from_file_location(
            'ocp_takeover_connect_for_test', plugin_path)
        cls.takeover_connect = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.takeover_connect)
        takeover_path = os.path.join(plugin_dir, 'takeover.py')
        spec = importlib.util.spec_from_file_location(
            'ocp_takeover_for_test', takeover_path)
        cls.takeover = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.takeover)
        takeover_precheck_path = os.path.join(
            plugin_dir, 'takeover_precheck.py')
        spec = importlib.util.spec_from_file_location(
            'ocp_takeover_precheck_for_test', takeover_precheck_path)
        cls.takeover_precheck = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.takeover_precheck)

    def test_request_log_masks_nested_passwords_and_private_keys(self):
        stdio = mock.Mock()
        cursor = self.takeover_connect.OcpCursor(
            ip='127.0.0.1', port=8080, component_name='ocp-server-ce',
            stdio=stdio)
        response = mock.Mock(status_code=200, content=b'{}')
        request_data = {
            'rootSysPassword': 'root-secret',
            'hostInfo': {
                'passphrase': 'private-key-secret',
                'credentialId': 1,
            },
            'safe': 'visible-value',
        }

        with mock.patch.object(
                self.takeover_connect.requests, 'request',
                return_value=response) as request:
            cursor._request('POST', '/api/test', data=request_data,
                            retry=0, stdio=stdio)

        log_message = stdio.verbose.call_args_list[-1][0][0]
        self.assertNotIn('root-secret', log_message)
        self.assertNotIn('private-key-secret', log_message)
        self.assertIn('******', log_message)
        self.assertIn('visible-value', log_message)
        sent_data = request.call_args[1]['data']
        self.assertIn('root-secret', sent_data)
        self.assertIn('private-key-secret', sent_data)

    def test_request_retry_does_not_double_encode_json(self):
        stdio = mock.Mock()
        cursor = self.takeover_connect.OcpCursor(
            ip='127.0.0.1', port=8080, component_name='ocp-server-ce',
            stdio=stdio)
        response = mock.Mock(status_code=200, content=b'{}')
        request_data = {'safe': 'value'}

        with mock.patch.object(
                self.takeover_connect.requests, 'request',
                side_effect=[RuntimeError('retry'), response]) as request:
            cursor._request('POST', '/api/test', data=request_data,
                            retry=1, stdio=stdio)

        self.assertEqual(2, request.call_count)
        self.assertEqual(
            request.call_args_list[0][1]['data'],
            request.call_args_list[1][1]['data'])

    def test_precheck_identifies_cluster_already_taken_over(self):
        stdio = mock.Mock()
        cursor = self.takeover_connect.OcpCursor(
            ip='127.0.0.1', port=8080, component_name='ocp-server-ce',
            stdio=stdio)
        response = cursor.Response(400, {
            'error': {
                'code': 'OBE13034',
                'message': 'Cluster demo:1 to be taken over already exists.',
            }
        })

        with mock.patch.object(cursor, '_request', return_value=response):
            result = cursor.take_over_precheck({}, stdio=stdio)

        self.assertEqual({'already_taken_over': True}, result)

    def test_precheck_does_not_hide_unrelated_ocp_error(self):
        stdio = mock.Mock()
        cursor = self.takeover_connect.OcpCursor(
            ip='127.0.0.1', port=8080, component_name='ocp-server-ce',
            stdio=stdio)
        response = cursor.Response(400, {
            'error': {
                'code': 'OBE13034',
                'message': 'Another OCP validation error.',
            }
        })

        with mock.patch.object(cursor, '_request', return_value=response):
            result = cursor.take_over_precheck({}, stdio=stdio)

        self.assertIsNone(result)

    def test_precheck_handles_missing_error_message(self):
        stdio = mock.Mock()
        cursor = self.takeover_connect.OcpCursor(
            ip='127.0.0.1', port=8080, component_name='ocp-server-ce',
            stdio=stdio)
        response = cursor.Response(400, {
            'error': {'code': 'OBE13034', 'message': None}
        })

        with mock.patch.object(cursor, '_request', return_value=response):
            result = cursor.take_over_precheck({}, stdio=stdio)

        self.assertIsNone(result)

    def test_takeover_skips_submission_when_precheck_reports_existing(self):
        stdio = mock.Mock()
        precheck_result = mock.Mock()
        precheck_result.get_return.return_value = True
        plugin_context = mock.Mock()
        plugin_context.stdio = stdio
        plugin_context.get_return.return_value = precheck_result
        plugin_context.return_true.return_value = True

        self.assertTrue(self.takeover.takeover(plugin_context))

        plugin_context.return_true.assert_called_once_with(
            already_taken_over=True)
        stdio.print.assert_called_once()

    def test_precheck_uses_effective_first_server_connection_config(self):
        server = FakeServer()
        cluster_config = mock.Mock()
        cluster_config.servers = [server]
        cluster_config.get_server_conf_with_default.return_value = {
            'mysql_port': 3881,
            'root_password': 'server-root-password',
            'proxyro_password': 'server-proxy-password',
        }
        cursor = mock.Mock()
        cursor.info.return_value = {'buildVersion': '4.4.2'}
        cursor.take_over_precheck.return_value = {}
        plugin_context = mock.Mock()
        plugin_context.cluster_config = cluster_config
        plugin_context.stdio = mock.Mock()
        plugin_context.return_true.return_value = True

        self.assertTrue(self.takeover_precheck.takeover_precheck(
            plugin_context, cursors={server: cursor}))

        cursor.take_over_precheck.assert_called_once_with({
            'connectionMode': 'direct',
            'address': server.ip,
            'port': 3881,
            'rootSysPassword': 'server-root-password',
            'proxyroPassword': 'server-proxy-password',
        }, stdio=plugin_context.stdio)
        cluster_config.get_global_conf.assert_not_called()

    def test_takeover_uses_effective_first_server_connection_config(self):
        server = FakeServer()
        cluster_config = mock.Mock()
        cluster_config.servers = [server]
        cluster_config.get_server_conf_with_default.return_value = {
            'mysql_port': 3881,
            'root_password': 'server-root-password',
            'proxyro_password': 'server-proxy-password',
        }
        ssh_config = SimpleNamespace(
            password='ssh-password', key_filename=None,
            username='root', port=22)
        ssh_client = SimpleNamespace(config=ssh_config)
        cursor = mock.Mock()
        cursor.get_host_types.return_value = {
            'data': {'contents': [{'id': 1}]}}
        cursor.create_credential.return_value = {'data': {'id': 2}}
        cursor.take_over.return_value = {
            'data': {'id': 3, 'clusterId': 4}}
        precheck_result = mock.Mock()
        precheck_result.get_return.return_value = False
        plugin_context = mock.Mock()
        plugin_context.cluster_config = cluster_config
        plugin_context.clients = {server: ssh_client}
        plugin_context.options = SimpleNamespace(
            host_type='', credential_name='', address='http://ocp:8080')
        plugin_context.stdio = mock.Mock()
        plugin_context.get_return.return_value = precheck_result
        plugin_context.return_true.return_value = True

        self.assertTrue(self.takeover.takeover(
            plugin_context, cursors={server: cursor}))

        takeover_data = cursor.take_over.call_args[0][0]
        self.assertEqual(3881, takeover_data['port'])
        self.assertEqual(
            'server-root-password', takeover_data['rootSysPassword'])
        self.assertEqual(
            'server-proxy-password', takeover_data['proxyroPassword'])
        cluster_config.get_global_conf.assert_not_called()


if __name__ == '__main__':
    unittest.main()
