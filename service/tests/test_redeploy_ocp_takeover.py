# coding: utf-8

from __future__ import absolute_import, division, print_function

import unittest
from optparse import Values
from unittest import mock

import const
from _deploy import ClusterConfig, DeployConfigStatus, DeployStatus, ServerConfig
from core import ObdHome


class FakeServer(object):

    def __init__(self, ip='10.0.0.8'):
        self.ip = ip


class FakeOcpConfig(object):

    def __init__(self, server_conf, depends):
        self.servers = [FakeServer()]
        self.depends = depends
        self.server_conf = server_conf
        self.server_conf_calls = 0

    def get_server_conf_with_default(self, server):
        self.server_conf_calls += 1
        return dict(self.server_conf)

    # These represent the incomplete views used before the regression fix.
    def get_original_global_conf(self):
        return {}

    def get_global_conf_with_default(self):
        return {'port': 8080, 'admin_password': 'global-password'}


class FakeDeployConfig(object):

    def __init__(self, ocp_config, events, dump_results=None):
        self.components = {
            const.COMP_OCP_SERVER_CE: ocp_config,
            const.COMP_OB_CE: object(),
        }
        self.events = events
        self.encrypt_dump_enabled = True
        self.last_dump_encrypted = None
        self.dump_results = list(dump_results or [True])

    def disable_encrypt_dump(self):
        self.encrypt_dump_enabled = False
        self.events.append('disable-encrypt-dump')

    def enable_encrypt_dump(self):
        self.encrypt_dump_enabled = True
        self.events.append('enable-encrypt-dump')

    def change_deploy_config_password(self, *args, **kwargs):
        return True

    def dump(self):
        self.last_dump_encrypted = self.encrypt_dump_enabled
        self.events.append(
            'dump-encrypted' if self.encrypt_dump_enabled else 'dump-plaintext')
        return self.dump_results.pop(0) if self.dump_results else True


class IncludeDeployConfig(object):

    def get_base_dir(self):
        return ''

    def load_include_file(self, path):
        return {
            'config': {
                'jdbc_url': 'jdbc:oceanbase://external-metadb:2881/ocp',
                'port': 8280,
                'admin_password': 'include-password',
            }
        }


class FakeDeployInfo(object):
    status = DeployStatus.STATUS_DEPLOYED
    config_status = DeployConfigStatus.UNCHNAGE


class FakeDeploy(object):

    def __init__(self, deploy_config):
        self.name = 'ocp-test'
        self.deploy_config = deploy_config
        self.deploy_info = FakeDeployInfo()


class FakeDeployManager(object):

    def __init__(self, deploy):
        self.deploy = deploy

    def get_deploy_config(self, name):
        return self.deploy


class RedeployOcpTakeoverTest(unittest.TestCase):

    def build_obd(self, server_conf, depends, start_success=True,
                  export_success=True, start_exception=None,
                  export_exception=None, dump_results=None,
                  enable_encrypt=True):
        events = []
        ocp_config = FakeOcpConfig(server_conf, depends)
        deploy_config = FakeDeployConfig(
            ocp_config, events, dump_results=dump_results)
        deploy = FakeDeploy(deploy_config)
        obd = ObdHome.__new__(ObdHome)
        obd._deploy_manager = FakeDeployManager(deploy)
        obd._enable_encrypt = enable_encrypt
        obd.options = Values()
        obd._call_stdio = mock.Mock()
        obd.set_deploy = mock.Mock()
        obd.load_local_repositories = mock.Mock(return_value=[object()])
        obd.set_repositories = mock.Mock()
        obd.get_workflows = mock.Mock(return_value=object())
        obd.run_workflow = mock.Mock(return_value=True)
        obd.search_param_plugin_and_apply = mock.Mock()
        obd._destroy_cluster = mock.Mock(return_value=True)
        obd._deploy_cluster = mock.Mock(return_value=True)

        def start_cluster(*args, **kwargs):
            events.append('start')
            if start_exception is not None:
                raise start_exception
            # _start_cluster persists the deployment status through this dump.
            # Its current implementation does not propagate a failed dump.
            if start_success:
                deploy_config.dump()
            return start_success

        def export_to_ocp(*args, **kwargs):
            events.append(
                'export-encrypted' if deploy_config.last_dump_encrypted
                else 'export-plaintext')
            if export_exception is not None:
                raise export_exception
            return export_success

        obd._start_cluster = mock.Mock(side_effect=start_cluster)
        obd.export_to_ocp = mock.Mock(side_effect=export_to_ocp)
        return obd, deploy_config, ocp_config, events

    def test_takeover_failure_keeps_persisted_config_encrypted(self):
        obd, deploy_config, _, events = self.build_obd(
            {'port': 8180, 'admin_password': 'server-password'},
            [const.COMP_OB_CE],
            export_success=False)

        self.assertFalse(obd.redeploy_cluster('ocp-test', search_repo=False))

        self.assertTrue(deploy_config.encrypt_dump_enabled)
        self.assertTrue(deploy_config.last_dump_encrypted)
        self.assertLess(events.index('dump-encrypted'), events.index('export-encrypted'))
        self.assertNotIn('export-plaintext', events)
        self.assertEqual('http://10.0.0.8:8180', obd.options.address)
        self.assertEqual('server-password', obd.options.password)

    def test_start_failure_still_restores_encrypted_dump(self):
        obd, deploy_config, _, events = self.build_obd(
            {'port': 8180, 'admin_password': 'server-password'},
            [const.COMP_OB_CE],
            start_success=False)

        self.assertFalse(obd.redeploy_cluster('ocp-test', search_repo=False))

        self.assertTrue(deploy_config.encrypt_dump_enabled)
        self.assertIsNone(deploy_config.last_dump_encrypted)
        self.assertNotIn('dump-plaintext', events)
        obd.export_to_ocp.assert_not_called()

    def test_start_exception_restores_encrypted_dump_state(self):
        obd, deploy_config, _, events = self.build_obd(
            {'port': 8180, 'admin_password': 'server-password'},
            [const.COMP_OB_CE],
            start_exception=RuntimeError('start failed'))

        with self.assertRaises(RuntimeError):
            obd.redeploy_cluster('ocp-test', search_repo=False)

        self.assertTrue(deploy_config.encrypt_dump_enabled)
        self.assertNotIn('dump-plaintext', events)
        obd.export_to_ocp.assert_not_called()

    def test_start_dump_failure_never_leaves_plaintext(self):
        obd, deploy_config, _, events = self.build_obd(
            {'port': 8180, 'admin_password': 'server-password'},
            [const.COMP_OB_CE],
            dump_results=[False, False])

        self.assertFalse(obd.redeploy_cluster('ocp-test', search_repo=False))

        self.assertTrue(deploy_config.encrypt_dump_enabled)
        self.assertTrue(deploy_config.last_dump_encrypted)
        self.assertNotIn('dump-plaintext', events)
        obd.export_to_ocp.assert_not_called()

    def test_export_exception_happens_after_encrypted_dump(self):
        obd, deploy_config, _, events = self.build_obd(
            {'port': 8180, 'admin_password': 'server-password'},
            [const.COMP_OB_CE],
            export_exception=RuntimeError('takeover failed'))

        with self.assertRaises(RuntimeError):
            obd.redeploy_cluster('ocp-test', search_repo=False)

        self.assertTrue(deploy_config.encrypt_dump_enabled)
        self.assertTrue(deploy_config.last_dump_encrypted)
        self.assertLess(events.index('dump-encrypted'), events.index('export-encrypted'))
        self.assertNotIn('dump-plaintext', events)

    def test_server_level_external_metadb_skips_takeover(self):
        obd, _, ocp_config, _ = self.build_obd(
            {
                'jdbc_url': 'jdbc:oceanbase://external-metadb:2881/ocp',
                'port': 8180,
                'admin_password': 'server-password',
            },
            [const.COMP_OB_CE])

        self.assertTrue(obd.redeploy_cluster('ocp-test', search_repo=False))

        self.assertEqual(1, ocp_config.server_conf_calls)
        obd.export_to_ocp.assert_not_called()

    def test_ocp_without_oceanbase_dependency_skips_takeover(self):
        obd, _, ocp_config, _ = self.build_obd(
            {'port': 8180, 'admin_password': 'server-password'},
            [])

        self.assertTrue(obd.redeploy_cluster('ocp-test', search_repo=False))

        self.assertEqual(0, ocp_config.server_conf_calls)
        obd.export_to_ocp.assert_not_called()

    def test_unencrypted_deploy_keeps_plaintext_dump_policy(self):
        obd, deploy_config, _, events = self.build_obd(
            {'port': 8180, 'admin_password': 'server-password'},
            [const.COMP_OB_CE],
            enable_encrypt=False)

        self.assertTrue(obd.redeploy_cluster('ocp-test', search_repo=False))

        self.assertFalse(deploy_config.encrypt_dump_enabled)
        self.assertFalse(deploy_config.last_dump_encrypted)
        self.assertIn('dump-plaintext', events)
        self.assertIn('export-plaintext', events)

    def test_effective_server_config_merges_include_and_server_override(self):
        server = ServerConfig('10.0.0.8', 'ocp-1')
        ocp_config = ClusterConfig(
            [server], const.COMP_OCP_SERVER_CE, '4.2.1', '', '', '', '', '')
        ocp_config.set_deploy_config(IncludeDeployConfig())
        ocp_config.set_include_file('ocp-include.yaml')
        ocp_config.set_global_conf({'admin_password': 'global-password'})
        ocp_config.add_server_conf(server, {'port': 8380})

        effective = ocp_config.get_server_conf_with_default(server)

        self.assertEqual(
            'jdbc:oceanbase://external-metadb:2881/ocp', effective['jdbc_url'])
        self.assertEqual(8380, effective['port'])
        self.assertEqual('global-password', effective['admin_password'])


if __name__ == '__main__':
    unittest.main()
