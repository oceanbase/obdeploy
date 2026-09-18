import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = (
    PROJECT_ROOT / 'plugins' / 'seekdb' / '1.2.0.0' /
    'delete_relation_clusters.py'
)


def load_plugin():
    spec = importlib.util.spec_from_file_location(
        'seekdb_delete_relation_clusters_under_test', PLUGIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClusterConfig:
    def __init__(self, deploy_name, attrs=None, ip='192.0.2.10', rpc_port=2882):
        self.deploy_name = deploy_name
        self.attrs = dict(attrs or {})
        self.server = SimpleNamespace(ip=ip)
        self.servers = [self.server]
        self.rpc_port = rpc_port

    def get_component_attr(self, name):
        return self.attrs.get(name)

    def update_component_attr(self, name, value, save=False):
        assert save is True
        self.attrs[name] = value

    def get_server_conf_with_default(self, server):
        assert server is self.server
        return {'rpc_port': self.rpc_port}


class FakeStdio:
    def __init__(self):
        self.errors = []
        self.loading_results = []

    def start_loading(self, *args, **kwargs):
        pass

    def verbose(self, *args, **kwargs):
        pass

    def error(self, message):
        self.errors.append(message)

    def stop_loading(self, result):
        self.loading_results.append(result)


def make_context(log_restore_source):
    primary = FakeClusterConfig(
        'primary', {'_cluster_standby_relation': ['standby']})
    standby = FakeClusterConfig(
        'standby', {'_cluster_primary': 'primary'}, ip='192.0.2.20')
    stdio = FakeStdio()

    class Cursor:
        @staticmethod
        def fetchone(sql, stdio=None):
            assert sql == (
                'select log_restore_source from '
                'oceanbase.__all_virtual_server_stat'
            )
            return {'log_restore_source': log_restore_source}

    context = SimpleNamespace(
        cluster_config=standby,
        stdio=stdio,
        return_true=lambda **kwargs: True,
        return_false=lambda **kwargs: False,
    )
    return context, Cursor(), primary, standby, stdio


@pytest.mark.parametrize('option_type', ['failover', 'decouple'])
def test_relation_cleanup_accepts_original_restore_source(option_type):
    module = load_plugin()
    context, cursor, primary, standby, stdio = make_context(
        '192.0.2.10:2882')

    assert module.delete_relation_clusters(
        context,
        cursors={'standby': cursor},
        cluster_configs={'primary': primary, 'standby': standby},
        option_type=option_type,
    ) is True

    assert stdio.errors == []
    assert stdio.loading_results == ['succeed']
    assert primary.attrs['_cluster_standby_relation'] == {}
    assert standby.attrs['_cluster_primary'] is None


@pytest.mark.parametrize('option_type', ['failover', 'decouple'])
@pytest.mark.parametrize('log_restore_source', ['', '192.0.2.99:2882'])
def test_relation_cleanup_rejects_empty_or_unrelated_restore_source(
        option_type, log_restore_source):
    module = load_plugin()
    context, cursor, primary, standby, stdio = make_context(log_restore_source)

    assert module.delete_relation_clusters(
        context,
        cursors={'standby': cursor},
        cluster_configs={'primary': primary, 'standby': standby},
        option_type=option_type,
    ) is False

    assert stdio.errors == [
        'log_restore_source mismatch when decoupling/failover: '
        "expected '192.0.2.10:2882', got %r." % log_restore_source
    ]
    assert stdio.loading_results == ['fail']
    assert primary.attrs['_cluster_standby_relation'] == ['standby']
    assert standby.attrs['_cluster_primary'] == 'primary'


@pytest.mark.parametrize('option_type', ['failover', 'decouple'])
def test_relation_cleanup_rejects_missing_primary_config(option_type):
    module = load_plugin()
    context, cursor, primary, standby, stdio = make_context('')

    assert module.delete_relation_clusters(
        context,
        cursors={'standby': cursor},
        cluster_configs={'standby': standby},
        option_type=option_type,
    ) is False

    assert stdio.errors == [
        'Primary cluster primary not found; cannot verify '
        'log_restore_source before decoupling/failover.'
    ]
    assert stdio.loading_results == ['fail']
    assert primary.attrs['_cluster_standby_relation'] == ['standby']
    assert standby.attrs['_cluster_primary'] == 'primary'
