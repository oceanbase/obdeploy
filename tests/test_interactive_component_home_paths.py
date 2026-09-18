import importlib.util
import os
from pathlib import Path

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIRM_CONFIG_FILE = (
    PROJECT_ROOT / 'plugins' / 'interactive' / '1.0' / 'confirm_config.py'
)


def load_confirm_config_module():
    spec = importlib.util.spec_from_file_location(
        'interactive_confirm_config', CONFIRM_CONFIG_FILE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_oceanbase_always_uses_its_own_directory():
    module = load_confirm_config_module()

    assert module.get_oceanbase_home_path('/home/admin/test') == (
        '/home/admin/test/oceanbase'
    )


def test_oceanbase_path_handles_trailing_slash():
    module = load_confirm_config_module()

    assert module.get_oceanbase_home_path('/home/admin/test/') == (
        '/home/admin/test/oceanbase'
    )


@pytest.mark.parametrize('with_components', [False, True])
def test_generated_config_reserves_oceanbase_directory(
    monkeypatch, with_components
):
    module = load_confirm_config_module()

    oceanbase_config = {
        'name': 'oceanbase-standalone',
        'version': '4.3.5.0',
        'release': 1,
        'mysql_port': 2881,
        'rpc_port': 2882,
        'obshell_port': 2886,
        'cpu_count': 4,
        'memory_limit': 8 << 30,
        'home_path': '/home/admin/test',
        'data_dir': '/data/ob',
        'log_dir': '/redo/ob',
        'datafile_maxsize': 20 << 30,
        'log_disk_size': 20 << 30,
        'root_password': 'password',
        'scenario': 'express_oltp',
    }
    component_config = (
        {
            'monagent_http_port': 8088,
            'mgragent_http_port': 8089,
            'prometheus_port': 9090,
            'grafana_port': 3000,
        }
        if with_components
        else None
    )

    class ResultGroup:
        def __init__(self, values):
            self.values = values

        def get_return(self, name):
            return self.values[name]

    class Stdio:
        def print(self, *args, **kwargs):
            pass

        def confirm(self, *args, **kwargs):
            return True

    class PluginContext:
        stdio = Stdio()

        def get_return(self, name):
            return {
                'oceanbase_config_input': ResultGroup(
                    {'oceanbase_config': oceanbase_config}
                ),
                'tenant_config_input': ResultGroup({'tenant_config': None}),
                'component_config_input': ResultGroup(
                    {'component_config': component_config}
                ),
            }[name]

        def return_true(self, **kwargs):
            return kwargs

    class ClientConfig:
        host = '127.0.0.1'
        username = 'admin'
        password = 'password'

    class Client:
        config = ClientConfig()

    class CommandEnv:
        def set(self, *args, **kwargs):
            pass

    monkeypatch.setattr(module, 'COMMAND_ENV', CommandEnv())
    result = module.confirm_config(PluginContext(), Client(), 'test')
    config_path = result['cluster_config_yaml_path']
    try:
        generated = yaml.safe_load(Path(config_path).read_text())
    finally:
        os.unlink(config_path)

    assert generated['oceanbase-standalone']['global']['home_path'] == (
        '/home/admin/test/oceanbase'
    )
    if with_components:
        assert generated['obagent']['global']['home_path'] == (
            '/home/admin/test/obagent'
        )
        assert generated['prometheus']['global']['home_path'] == (
            '/home/admin/test/prometheus'
        )
        assert generated['grafana']['global']['home_path'] == (
            '/home/admin/test/grafana'
        )
    else:
        assert 'obagent' not in generated
        assert 'prometheus' not in generated
        assert 'grafana' not in generated
