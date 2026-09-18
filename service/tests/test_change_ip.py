# coding: utf-8

from __future__ import absolute_import, division, print_function

import glob
import os
import tempfile
import unittest
from io import StringIO
from unittest import mock

import const
from _change_ip import ChangeIpError, DeploymentAddressChanger
from _lock import LockMode
from _stdio import IO
from core import ObdHome
from tool import YamlLoader


class DeploymentAddressChangerTest(unittest.TestCase):

    def test_build_plan_preserves_server_names_for_default_and_cluster_styles(self):
        source = {
            'oceanbase-standalone': {
                'servers': ['10.0.0.8'],
                'global': {'home_path': '/opt/oceanbase'},
            },
            'obagent': {
                'servers': [{'name': 'observer-host', 'ip': '10.0.0.8'}],
            },
            'oceanbase-ce': {
                'style': 'cluster',
                'zones': {
                    'zone1': {
                        'servers': [{'name': 'zone-server', 'ip': '10.0.0.8'}],
                    },
                },
            },
        }
        plan = DeploymentAddressChanger.build_plan(
            source,
            ['oceanbase-standalone', 'obagent', 'oceanbase-ce'],
            '10.0.0.8',
            '10.0.0.9'
        )

        self.assertEqual(3, plan.replacement_count)
        self.assertEqual(
            {'name': '10.0.0.8', 'ip': '10.0.0.9'},
            dict(plan.data['oceanbase-standalone']['servers'][0])
        )
        self.assertEqual(
            {'name': 'observer-host', 'ip': '10.0.0.9'},
            dict(plan.data['obagent']['servers'][0])
        )
        self.assertEqual(
            {'name': 'zone-server', 'ip': '10.0.0.9'},
            dict(plan.data['oceanbase-ce']['zones']['zone1']['servers'][0])
        )
        self.assertEqual('10.0.0.8', source['oceanbase-standalone']['servers'][0])

    def test_build_plan_rejects_existing_target_and_missing_source(self):
        source = {
            'oceanbase-standalone': {
                'servers': ['10.0.0.8', '10.0.0.9'],
            },
        }
        with self.assertRaises(ChangeIpError):
            DeploymentAddressChanger.build_plan(
                source, ['oceanbase-standalone'], '10.0.0.8', '10.0.0.9')
        with self.assertRaises(ChangeIpError):
            DeploymentAddressChanger.build_plan(
                source, ['oceanbase-standalone'], '10.0.0.7', '10.0.0.10')

    def test_commit_restores_original_when_directory_sync_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, 'config.yaml')
            with open(config_path, 'w') as f:
                f.write('value: old\n')
            candidate_path = DeploymentAddressChanger.stage(
                config_path, {'value': 'new'})
            sync_calls = []

            def fail_first_sync(path):
                sync_calls.append(path)
                if len(sync_calls) == 1:
                    raise OSError('simulated fsync failure')

            with mock.patch.object(
                    DeploymentAddressChanger, '_fsync_directory', side_effect=fail_first_sync):
                with self.assertRaises(ChangeIpError):
                    DeploymentAddressChanger.commit(config_path, candidate_path)

            with open(config_path, 'r') as f:
                self.assertEqual('value: old\n', f.read())


class ChangeClusterIpTest(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.home = self.temp_dir.name
        self.deploy_name = 'standalone-test'
        self.deploy_dir = os.path.join(self.home, 'cluster', self.deploy_name)
        os.makedirs(self.deploy_dir)
        self.yaml = YamlLoader()
        self.config_path = os.path.join(self.deploy_dir, 'config.yaml')
        self.inner_config_path = os.path.join(self.deploy_dir, 'inner_config.yaml')
        self.data_path = os.path.join(self.deploy_dir, '.data')
        self._dump(self.config_path, {
            'user': {
                'username': 'root',
                'password': 'test-password',
            },
            const.COMP_OB_STANDALONE: {
                'version': '4.4.2.3',
                'servers': ['10.0.0.8'],
                'global': {
                    'home_path': '/opt/oceanbase',
                    'mysql_port': 2881,
                    'rpc_port': 2882,
                },
            },
            'obagent': {
                'version': '4.2.2',
                'servers': [{'name': 'observer-host', 'ip': '10.0.0.8'}],
                'global': {
                    'home_path': '/opt/obagent',
                },
            },
        })
        self._dump(self.inner_config_path, {
            const.COMP_OB_STANDALONE: {
                '$_component_global_attrs': {
                    '$_%s' % const.OBSERVER_IDENTITY_IP: const.OBSERVER_LOOPBACK_IP,
                    '$_%s' % const.OBSERVER_IDENTITY_STATE: const.OBSERVER_IDENTITY_VERIFIED,
                    '$_%s' % const.OBSERVER_IDENTITY_SOURCE: const.OBSERVER_IDENTITY_FRESH_BOOTSTRAP,
                },
            },
        })
        self._dump(self.data_path, {
            'name': self.deploy_name,
            'status': 'STATUS_RUNNING',
            'config_status': 'UNCHNAGE',
            'components': {
                const.COMP_OB_STANDALONE: {
                    'version': '4.4.2.3',
                    'hash': 'standalone-hash',
                },
                'obagent': {
                    'version': '4.2.2',
                    'hash': 'obagent-hash',
                },
            },
            'create_date': None,
        })
        self.output = StringIO()
        self.stdio = IO(1, input_stream=StringIO(), output_stream=self.output)
        self.obd = ObdHome(
            home_path=self.home,
            lock_mode=LockMode.NO_LOCK,
            stdio=self.stdio
        )
        self.verify_database = DeploymentAddressChanger.verify_database
        self.verify_ssh_patcher = mock.patch.object(
            DeploymentAddressChanger, 'verify_ssh', return_value=True)
        self.verify_database_patcher = mock.patch.object(
            DeploymentAddressChanger, 'verify_database', return_value=True)
        self.verify_ssh_patcher.start()
        self.verify_database_patcher.start()

    def tearDown(self):
        self.verify_database_patcher.stop()
        self.verify_ssh_patcher.stop()
        self.temp_dir.cleanup()

    def _dump(self, path, data):
        with open(path, 'w') as f:
            self.yaml.dump(data, f)

    def _load(self, path):
        with open(path, 'rb') as f:
            return self.yaml.load(f)

    @staticmethod
    def _read_bytes(path):
        with open(path, 'rb') as f:
            return f.read()

    def test_change_cluster_ip_commits_config_and_keeps_inner_config(self):
        original_inner = self._read_bytes(self.inner_config_path)

        result = self.obd.change_cluster_ip(
            self.deploy_name,
            '10.0.0.8',
            '10.0.0.9',
            need_confirm=False
        )

        self.assertTrue(result)
        config = self._load(self.config_path)
        self.assertEqual(
            {'name': '10.0.0.8', 'ip': '10.0.0.9'},
            dict(config[const.COMP_OB_STANDALONE]['servers'][0])
        )
        self.assertEqual(
            {'name': 'observer-host', 'ip': '10.0.0.9'},
            dict(config['obagent']['servers'][0])
        )
        self.assertEqual(original_inner, self._read_bytes(self.inner_config_path))
        self.assertEqual(1, len(glob.glob(self.config_path + '.change-ip.*.bak')))
        self.assertEqual('UNCHNAGE', self._load(self.data_path)['config_status'])

    def test_change_cluster_ip_dry_run_does_not_write_files(self):
        original_config = self._read_bytes(self.config_path)

        result = self.obd.change_cluster_ip(
            self.deploy_name,
            '10.0.0.8',
            '10.0.0.9',
            dry_run=True,
            need_confirm=False
        )

        self.assertTrue(result)
        self.assertEqual(original_config, self._read_bytes(self.config_path))
        self.assertEqual([], glob.glob(self.config_path + '.change-ip.*.bak'))

    def test_change_cluster_ip_allows_primary_standby_metadata_with_action_required(self):
        inner_config = self._load(self.inner_config_path)
        inner_config[const.COMP_OB_STANDALONE]['$_component_global_attrs']['$_primary_tenant'] = {
            'standby': [['primary-deploy', 'primary']],
        }
        self._dump(self.inner_config_path, inner_config)

        result = self.obd.change_cluster_ip(
            self.deploy_name,
            '10.0.0.8',
            '10.0.0.9',
            need_confirm=False
        )

        self.assertTrue(result)
        self.assertEqual(1, len(glob.glob(self.config_path + '.change-ip.*.bak')))
        self.assertIn(
            'Maintain the primary/standby endpoints manually',
            self.output.getvalue()
        )

    def test_change_cluster_ip_allows_standby_relation_metadata_with_action_required(self):
        inner_config = self._load(self.inner_config_path)
        inner_config[const.COMP_OB_STANDALONE]['$_component_global_attrs']['$_standby_relation'] = {
            'primary': [['standby-deploy', 'standby']],
        }
        self._dump(self.inner_config_path, inner_config)

        result = self.obd.change_cluster_ip(
            self.deploy_name,
            '10.0.0.8',
            '10.0.0.9',
            need_confirm=False
        )

        self.assertTrue(result)
        self.assertEqual(1, len(glob.glob(self.config_path + '.change-ip.*.bak')))
        self.assertIn(
            'Maintain the primary/standby endpoints manually',
            self.output.getvalue()
        )

    def test_verify_change_ip_database_checks_loopback_identity(self):
        class FakeCursor(object):

            def __init__(self, rows):
                self.rows = rows
                self.closed = False

            def fetchall(self, *args, **kwargs):
                return self.rows

            def close(self):
                self.closed = True

        deploy = self.obd.deploy_manager.get_deploy_config(self.deploy_name)
        cursor = FakeCursor([{
            'svr_ip': const.OBSERVER_LOOPBACK_IP,
            'svr_port': 2882,
            'inner_port': 2881,
        }])
        with mock.patch('_change_ip.Cursor', return_value=cursor):
            self.assertTrue(self.verify_database(
                deploy.deploy_config, '10.0.0.9', self.stdio))
        self.assertTrue(cursor.closed)


if __name__ == '__main__':
    unittest.main()
