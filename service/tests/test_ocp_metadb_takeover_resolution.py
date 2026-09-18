# coding: utf-8

from __future__ import absolute_import, division, print_function

import unittest
from unittest import mock

import const
from _deploy import DeployStatus, ServerConfig
from service.handler.metadb_handler import MetadbHandler
from service.handler.ocp_handler import OcpHandler
from service.model.database import DatabaseConnection


class FakeDeployInfo(object):

    def __init__(self, status=DeployStatus.STATUS_RUNNING):
        self.status = status


class FakeClusterConfig(object):

    def __init__(self, host='10.0.0.8', port=2881):
        self.servers = [ServerConfig(host)]
        self.port = port

    def get_server_conf_with_default(self, server):
        return {'mysql_port': self.port}


class FakeDeployConfig(object):

    def __init__(self, component=None, cluster_config=None):
        self.components = {}
        if component is not None:
            self.components[component] = cluster_config or FakeClusterConfig()


class FakeDeploy(object):

    def __init__(self, name, component=None, cluster_config=None,
                 status=DeployStatus.STATUS_RUNNING):
        self.name = name
        self.deploy_info = FakeDeployInfo(status)
        self.deploy_config = FakeDeployConfig(component, cluster_config)


class FakeDeployManager(object):

    def __init__(self, deploys):
        self.deploys = {deploy.name: deploy for deploy in deploys}

    def get_deploy_config(self, name, read_only=False):
        return self.deploys.get(name)

    def get_deploy_configs(self, read_only=True):
        return list(self.deploys.values())


class FakeObd(object):

    def __init__(self, deploys):
        self.deploy_manager = FakeDeployManager(deploys)


class FakeCursor(object):

    def __init__(self, cluster_name=None, error=None):
        self.cluster_name = cluster_name
        self.error = error

    def fetchone(self, *args, **kwargs):
        if self.error is not None:
            raise self.error
        return {'cluster_name': self.cluster_name}


class OcpMetadbTakeoverResolutionTest(unittest.TestCase):

    def setUp(self):
        self.handler = object.__new__(OcpHandler.__wrapped__)

    @staticmethod
    def metadb(cluster_name='', host='10.0.0.8', port=2881):
        return DatabaseConnection(
            cluster_name=cluster_name, host=host, port=port)

    def configure(self, deploys, cursor):
        self.handler._obd = FakeObd(deploys)
        self.handler._context = {'metadb_cursor': cursor}

    def test_database_cluster_name_wins_over_ocp_deployment_name(self):
        metadb_deploy = FakeDeploy('metadb-deploy', const.COMP_OB_CE)
        ocp_deploy = FakeDeploy('ocp-deploy', const.COMP_OCP_SERVER)
        self.configure(
            [metadb_deploy, ocp_deploy], FakeCursor('metadb-deploy'))

        result = self.handler._resolve_metadb_cluster_name(
            self.metadb(cluster_name='ocp-deploy'), 'ocp-deploy')

        self.assertEqual('metadb-deploy', result)

    def test_blank_name_falls_back_to_unique_matching_endpoint(self):
        metadb_deploy = FakeDeploy(
            'metadb-deploy', const.COMP_OB_CE,
            FakeClusterConfig('10.0.0.8', 2881))
        self.configure(
            [metadb_deploy], FakeCursor(error=RuntimeError('no privilege')))

        result = self.handler._resolve_metadb_cluster_name(
            self.metadb(), 'ocp-deploy')

        self.assertEqual('metadb-deploy', result)

    def test_valid_explicit_metadb_deployment_is_used_when_query_fails(self):
        metadb_deploy = FakeDeploy('metadb-deploy', const.COMP_OB_CE)
        self.configure(
            [metadb_deploy], FakeCursor(error=RuntimeError('no privilege')))

        result = self.handler._resolve_metadb_cluster_name(
            self.metadb(cluster_name='metadb-deploy'), 'ocp-deploy')

        self.assertEqual('metadb-deploy', result)

    def test_ambiguous_endpoint_is_rejected(self):
        deploys = [
            FakeDeploy('metadb-a', const.COMP_OB_CE),
            FakeDeploy('metadb-b', const.COMP_OB),
        ]
        self.configure(deploys, FakeCursor(error=RuntimeError('no privilege')))

        with self.assertRaisesRegex(Exception, 'multiple running OceanBase'):
            self.handler._resolve_metadb_cluster_name(
                self.metadb(), 'ocp-deploy')

    def test_unknown_endpoint_is_rejected_instead_of_using_ocp_name(self):
        ocp_deploy = FakeDeploy('ocp-deploy', const.COMP_OCP_SERVER)
        self.configure(
            [ocp_deploy], FakeCursor(error=RuntimeError('no privilege')))

        with self.assertRaisesRegex(Exception, 'no running OBD-managed'):
            self.handler._resolve_metadb_cluster_name(
                self.metadb(cluster_name='ocp-deploy'), 'ocp-deploy')

    def test_combined_deployment_without_external_metadb_uses_own_name(self):
        combined = FakeDeploy('combined', const.COMP_OB_CE)
        self.configure([combined], None)

        self.assertEqual(
            'combined',
            self.handler._resolve_metadb_cluster_name(None, 'combined'))

    def test_takeover_exception_marks_task_failed(self):
        self.handler._context = {'deploy_status': {7: ''}}
        with mock.patch.object(
                self.handler, '_take_over_metadb',
                side_effect=RuntimeError('takeover failed')):
            with self.assertRaisesRegex(RuntimeError, 'takeover failed'):
                self.handler._take_over_metadb_for_task(1, 'ocp-deploy', 7)

        self.assertEqual('failed', self.handler._context['deploy_status'][7])


class MetadbConnectionIdentityTest(unittest.TestCase):

    def setUp(self):
        self.handler = object.__new__(MetadbHandler.__wrapped__)
        self.handler._context = {'connection_info': {}}
        self.handler._obd = mock.Mock()

    def test_connection_response_contains_database_cluster_name(self):
        info = DatabaseConnection(
            cluster_name='', host='10.0.0.8', port=2881,
            user='root@sys', password='encrypted')
        cursor = FakeCursor('metadb-deploy')

        rsa_handler = mock.Mock()
        rsa_handler.decrypt_private_key.return_value = 'plain'
        with mock.patch(
                'service.handler.metadb_handler.RSAHandler',
                return_value=rsa_handler), mock.patch(
                    'service.handler.metadb_handler.Cursor', return_value=cursor):
            result = self.handler.create_connection_info(info, sys=True)

        self.assertEqual('metadb-deploy', result.cluster_name)
        self.assertEqual('', result.password)
        self.assertIs(
            self.handler.context['connection_info']['metadb-deploy'], info)

    def test_connection_query_failure_preserves_requested_cluster_name(self):
        info = DatabaseConnection(
            cluster_name='requested-deploy', host='10.0.0.8', port=2881,
            user='root@sys', password='encrypted')
        cursor = FakeCursor(error=RuntimeError('no privilege'))

        rsa_handler = mock.Mock()
        rsa_handler.decrypt_private_key.return_value = 'plain'
        with mock.patch(
                'service.handler.metadb_handler.RSAHandler',
                return_value=rsa_handler), mock.patch(
                    'service.handler.metadb_handler.Cursor', return_value=cursor):
            result = self.handler.create_connection_info(info, sys=True)

        self.assertEqual('requested-deploy', result.cluster_name)
        self.assertIn(
            'requested-deploy', self.handler.context['connection_info'])


if __name__ == '__main__':
    unittest.main()
