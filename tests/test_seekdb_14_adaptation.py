import importlib.util
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEEKDB_14_ROOT = PROJECT_ROOT / 'plugins' / 'seekdb' / '1.4.0'
OBAGENT_13_ROOT = PROJECT_ROOT / 'plugins' / 'obagent' / '1.3.0'


def load_module(path, name):
    plugin_dir = str(path.parent)
    sys.path.insert(0, plugin_dir)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(plugin_dir)


def load_core_or_skip():
    try:
        import core
        return core
    except ImportError as exc:
        pytest.skip('OBD runtime dependencies are unavailable: %s' % exc)


def stub_obshell_modules(monkeypatch):
    monkeypatch.setitem(sys.modules, 'obshell', SimpleNamespace(
        ClientSet=type('ClientSet', (), {}),
        ClientV1=type('ClientV1', (), {}),
    ))
    monkeypatch.setitem(sys.modules, 'obshell.auth', SimpleNamespace(
        PasswordAuth=type('PasswordAuth', (), {}),
    ))
    monkeypatch.setitem(sys.modules, 'obshell.request', SimpleNamespace(
        ProtocolOptions=type('ProtocolOptions', (), {}),
    ))
    monkeypatch.setitem(sys.modules, 'obshell.model', SimpleNamespace())
    monkeypatch.setitem(sys.modules, 'obshell.model.info', SimpleNamespace(
        Agentidentity=SimpleNamespace(
            TAKE_OVER_MASTER='TAKE_OVER_MASTER',
            CLUSTER_AGENT='CLUSTER_AGENT',
        ),
    ))


def make_seekdb_connect_context(servers, server_configs):
    class ClusterConfig:
        name = 'seekdb'

        def __init__(self):
            self.servers = servers

        @staticmethod
        def get_server_conf(server):
            return server_configs[server.name]

    returned = {}
    context = SimpleNamespace(
        cluster_config=ClusterConfig(),
        stdio=SimpleNamespace(
            start_loading=lambda *args, **kwargs: None,
            stop_loading=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            exception=lambda *args, **kwargs: None,
        ),
        get_variable=lambda *args, **kwargs: None,
        set_variable=lambda key, value: returned.__setitem__(key, value),
        return_true=lambda **kwargs: True,
        return_false=lambda **kwargs: False,
    )
    return context, returned


@pytest.mark.parametrize(
    'version, expected',
    [
        ('1.3.0.0', True),
        ('1.4.0.0', True),
        ('1.4.0', False),
        ('latest', False),
        ('', False),
        (None, False),
    ],
)
def test_seekdb_product_version_validation(version, expected):
    core = load_core_or_skip()
    assert core.ObdHome._is_valid_seekdb_product_version(version) is expected


def test_interactive_install_selects_latest_available_version():
    core = load_core_or_skip()
    from _rpm import PackageInfo

    class RepositoryManager:
        def get_repository(self, **kwargs):
            assert kwargs == {'name': 'seekdb'}
            return PackageInfo('seekdb', '1.3.0.0', '10', 'x86_64', 'old', 1)

    class MirrorManager:
        def get_best_pkg(self, **kwargs):
            assert kwargs == {
                'name': 'seekdb', 'version': None, 'md5': None,
                'release': None, 'fuzzy': False, 'only_info': True,
            }
            return PackageInfo('seekdb', '1.4.0.0', '1', 'x86_64', 'new', 1)

    class Plugin:
        version = core.Version('1.4.0')

    class PluginManager:
        def get_best_plugin(self, *args):
            return Plugin()

        def get_best_py_script_plugin(self, *args):
            return Plugin()

    obd = object.__new__(core.ObdHome)
    obd._repository_manager = RepositoryManager()
    obd._mirror_manager = MirrorManager()
    obd._plugin_manager = PluginManager()
    messages = []
    obd._stdio_func = {
        'print': lambda message, *args, **kwargs: messages.append(message),
        'error': lambda message, *args, **kwargs: messages.append(message),
    }

    assert obd._resolve_seekdb_install_version() == '1.4.0.0'
    assert any('Use seekdb version 1.4.0.0' in message for message in messages)


def test_interactive_install_fails_before_workflow_when_no_package_exists():
    core = load_core_or_skip()

    class RepositoryManager:
        def get_repository(self, **kwargs):
            return None

    class MirrorManager:
        def get_best_pkg(self, **kwargs):
            return None

    obd = object.__new__(core.ObdHome)
    obd._repository_manager = RepositoryManager()
    obd._mirror_manager = MirrorManager()
    messages = []
    obd._stdio_func = {'error': lambda message, *args, **kwargs: messages.append(message)}

    assert obd._resolve_seekdb_install_version() is None
    assert any('No available seekdb package' in message for message in messages)


@pytest.mark.parametrize('candidate_version', ['', 'latest', '1.4.0'])
def test_interactive_install_rejects_invalid_selected_version(candidate_version):
    core = load_core_or_skip()
    from _rpm import PackageInfo

    class RepositoryManager:
        def get_repository(self, **kwargs):
            return None

    class MirrorManager:
        def get_best_pkg(self, **kwargs):
            return PackageInfo('seekdb', candidate_version, '1', 'x86_64', 'bad', 1)

    obd = object.__new__(core.ObdHome)
    obd._repository_manager = RepositoryManager()
    obd._mirror_manager = MirrorManager()
    obd._stdio_func = {'error': lambda *args, **kwargs: None}

    assert obd._resolve_seekdb_install_version() is None


def test_generated_interactive_yaml_pins_version_and_preserves_version_fields():
    core = load_core_or_skip()
    config = core.ObdHome._build_seekdb_install_deploy_config(
        '1.4.0.0',
        {
            'IP': '10.0.0.8',
            'User': 'admin',
            'ssh_port': '2222',
            'home_path': '/opt/seekdb',
            'data_dir': '/data/seekdb',
            'redo_dir': '/redo/seekdb',
            'mysql_port': '2881',
            'obshell_port': '2886',
            'memory_budget': '8G',
            'kvcache_memory_limit': '2G',
            'datafile_maxsize': '20G',
            'log_disk_size': '24G',
            'auto_start': 'true',
        },
        {'ssh_port': 22, 'password': 'ssh-secret'},
        'primary',
        'prod',
    )

    seekdb = config['seekdb']
    assert seekdb['version'] == '1.4.0.0'
    assert seekdb['global']['memory_budget'] == '8G'
    assert seekdb['global']['kvcache_memory_limit'] == '2G'
    assert 'memory_limit' not in seekdb['global']
    assert 'memory_hard_limit' not in seekdb['global']
    assert seekdb['global']['enable_rpc_service'] is True
    assert seekdb['global']['enable_auto_start'] is True
    assert config['user'] == {
        'username': 'admin', 'port': 2222, 'password': 'ssh-secret',
    }


class FakeInteractiveContext:
    def __init__(self, install_mode):
        self.stdio = type('Stdio', (), {'error': lambda self, message: None})()
        self.values = {
            ('seekdb', 'resources'): {
                'total_mem': 16 << 30,
                'avail_mem': 12 << 30,
                'free_disk_bytes': 100 << 30,
                'clog_avail_bytes': 100 << 30,
            },
            ('interactive', 'base_info'): {
                'ip': '127.0.0.1',
                'user': 'admin',
                'home_path': '/opt/seekdb',
                'data_dir': '/data/seekdb',
                'redo_dir': '/redo/seekdb',
                'mysql_port': '2881',
                'obshell_port': '2886',
                'auto_start': False,
            },
            ('interactive', 'install_mode'): install_mode,
            ('interactive', 'install_run_mode'): 'dev',
        }

    def get_variable(self, name, spacename=None):
        return self.values.get((spacename or 'seekdb', name))

    def set_variable(self, name, value):
        self.values[('seekdb', name)] = value

    def return_true(self, **kwargs):
        return True

    def return_false(self, **kwargs):
        return False


@pytest.mark.parametrize(
    'install_mode, expected_log_disk',
    [('standalone', '2G'), ('primary', '3G'), ('standby', '3G')],
)
def test_seekdb_14_interactive_config_uses_memory_budget(install_mode, expected_log_disk):
    module = load_module(
        SEEKDB_14_ROOT / 'seekdb_install_compute_config.py',
        'seekdb_14_compute_%s' % install_mode,
    )
    context = FakeInteractiveContext(install_mode)
    expected_obshell_port = '2886'
    if install_mode == 'standby':
        expected_obshell_port = '4886'
        context.values[('interactive', 'base_info')]['obshell_port'] = expected_obshell_port

    assert module.seekdb_install_compute_config(context) is True
    config = dict(context.values[('seekdb', 'config_list')])
    assert config['memory_budget'] == '1G'
    assert config['log_disk_size'] == expected_log_disk
    assert config['obshell_port'] == expected_obshell_port
    assert 'memory_limit' not in config
    assert 'memory_hard_limit' not in config


def test_seekdb_13_interactive_config_keeps_legacy_memory_fields():
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'seekdb_install_compute_config.py',
        'seekdb_13_compute_under_test',
    )
    context = FakeInteractiveContext('standalone')

    assert module.seekdb_install_compute_config(context) is True
    config = dict(context.values[('seekdb', 'config_list')])
    assert config['memory_limit'] == '1G'
    assert config['memory_hard_limit'] == '4G'
    assert 'memory_budget' not in config
    assert '_memory_budget' not in config


def test_seekdb_13_standby_config_keeps_obshell_port():
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'seekdb_install_compute_config.py',
        'seekdb_13_standby_compute_under_test',
    )
    context = FakeInteractiveContext('standby')
    context.values[('interactive', 'base_info')]['obshell_port'] = '4886'

    assert module.seekdb_install_compute_config(context) is True
    config = dict(context.values[('seekdb', 'config_list')])
    assert config['obshell_port'] == '4886'


def test_standby_base_info_prompts_for_obshell_port(monkeypatch):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'interactive' / '1.0' / 'base_info.py',
        'seekdb_standby_base_info_under_test',
    )
    prompts = []

    answers = {
        'Server IP': '192.0.2.20',
        'Username': 'admin',
        'SSH port': '22',
        'Seekdb installation directory': '/opt/seekdb-standby',
        'Data directory (data_dir, optional)': '/data/seekdb-standby',
        'Redo log directory (redo_dir, optional)': '/redo/seekdb-standby',
        'MySQL port': '3881',
        'RPC port': '3882',
        'OBShell port': '4886',
        'Do you want to enable the Seekdb service to start automatically when the system boots up? (y/yes or n/no)': 'no',
    }

    class FakeInteractiveUI:
        @staticmethod
        def prompt(message, default=''):
            prompts.append(message)
            return answers[message]

        @staticmethod
        def prompt_password(message, default=''):
            return 'ssh-secret'

        @staticmethod
        def parse_yes_no(value, default_yes=False):
            return str(value).lower() in ('y', 'yes')

    class FakeSshClient:
        def __init__(self, *args, **kwargs):
            self.closed = False

        @staticmethod
        def connect(stdio=None, exit=False):
            return True

        def close(self, stdio=None):
            self.closed = True

    class Context:
        def __init__(self):
            self.stdio = SimpleNamespace(warn=lambda *args, **kwargs: None,
                                         error=lambda *args, **kwargs: None)
            self.result = None

        @staticmethod
        def get_variable(name, spacename=None):
            if name == 'install_mode':
                return 'standby'
            if name == 'cluster_name':
                return 'seekdb-standby'
            if name == 'primary_log_disk_size':
                return None
            return None

        def set_variable(self, name, value):
            assert name == 'base_info'
            self.result = value

        @staticmethod
        def return_true(**kwargs):
            return True

    monkeypatch.setattr(module, 'InteractiveUI', FakeInteractiveUI)
    monkeypatch.setattr(module.NetUtil, 'get_host_ip', lambda: '192.0.2.10')
    monkeypatch.setattr(module, 'SshClient', FakeSshClient)
    monkeypatch.setattr(module, 'SshConfig', lambda *args, **kwargs: object())
    monkeypatch.setattr(module, '_dir_check', lambda *args, **kwargs: True)
    monkeypatch.setattr(module, '_check_avail_memory', lambda *args, **kwargs: True)
    monkeypatch.setattr(module, 'is_valid_ip', lambda value: True)
    monkeypatch.setattr(module, 'is_port_in_use', lambda *args, **kwargs: False)

    context = Context()
    assert module.base_info(context) is True
    assert 'OBShell port' in prompts
    assert context.result['obshell_port'] == '4886'
    assert context.result['rpc_port'] == '3882'


class FakeSeekdbSwitchoverContext:
    def __init__(self):
        self.stdio = SimpleNamespace(
            start_loading=lambda *args, **kwargs: None,
            stop_loading=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
        )
        self.values = {
            'primary_deploy_name': 'seekdb-primary',
            'standby_deploy_name': 'seekdb-standby',
        }

    def get_variable(self, name, default=None):
        return self.values.get(name, default)

    def set_variable(self, name, value):
        self.values[name] = value

    @staticmethod
    def return_true(**kwargs):
        return True

    @staticmethod
    def return_false(**kwargs):
        return False


class FakeSeekdbClusterConfig:
    def __init__(self, ip, obshell_port, rpc_port, root_password):
        self.server = SimpleNamespace(ip=ip)
        self.servers = [self.server]
        self.config = {
            'obshell_port': obshell_port,
            'rpc_port': rpc_port,
            'root_password': root_password,
        }

    def get_server_conf_with_default(self, server):
        assert server is self.server
        return dict(self.config)

    def get_global_conf(self):
        return dict(self.config)


def test_seekdb_14_switchover_uses_primary_obshell_dag(monkeypatch):
    module = load_module(
        SEEKDB_14_ROOT / 'switchover.py',
        'seekdb_14_switchover_under_test',
    )
    context = FakeSeekdbSwitchoverContext()
    primary = FakeSeekdbClusterConfig('192.0.2.10', 2886, 2882, 'secret')
    standby = FakeSeekdbClusterConfig('192.0.2.20', 4886, 3882, 'secret')

    class Cursor:
        @staticmethod
        def fetchone(sql, raise_exception=False):
            assert sql == 'SELECT ROLE FROM oceanbase.__all_virtual_server_stat'
            return {'ROLE': 'PRIMARY'}

    class ObshellClient:
        def __init__(self):
            self.calls = []

        def switchover_seekdb_standby_sync(self, peer_host, peer_obshell_port):
            self.calls.append((peer_host, peer_obshell_port))

    client = ObshellClient()
    primary_meta = []

    def new_client(meta):
        primary_meta.append(meta)
        return client

    monkeypatch.setattr(module, '_new_obshell_client', new_client)
    assert module.switchover(
        context,
        cursors={'seekdb-primary': Cursor()},
        cluster_configs={
            'seekdb-primary': primary,
            'seekdb-standby': standby,
        },
    ) is True
    assert primary_meta[0]['ip'] == '192.0.2.10'
    assert primary_meta[0]['obshell_port'] == 2886
    assert client.calls == [('192.0.2.20', 4886)]
    assert context.values['switchover_success'] is True


def test_seekdb_14_switchover_workflow_drops_no_ocs_database():
    module = load_module(
        PROJECT_ROOT / 'workflows' / 'seekdb' / '1.4.0' / 'switchover_seekdb.py',
        'seekdb_14_switchover_workflow_under_test',
    )

    class Workflow:
        def __init__(self):
            self.plugins = []

        def add(self, stage, *plugins):
            self.plugins.extend(plugins)

        def add_with_component(self, stage, component, *plugins):
            self.plugins.extend(plugins)

    context = SimpleNamespace(
        options=SimpleNamespace(skip_cluster_status_check=False),
        return_true=lambda **kwargs: True,
    )
    workflow = Workflow()
    module.switchover_seekdb(context, workflow)

    assert 'switchover' in workflow.plugins
    assert 'switchover_relation_clusters' in workflow.plugins
    assert 'drop_seekdb_ocs' not in workflow.plugins


def test_seekdb_14_rejects_legacy_and_removed_parameters():
    module = load_module(
        SEEKDB_14_ROOT / 'seekdb_14_parameters.py',
        'seekdb_14_parameters_under_test',
    )
    legacy, removed = module.get_unsupported_parameters({
        'memory_limit': '8G',
        'memory_hard_limit': '10G',
        'enable_syslog_wf': True,
        '_memory_budget': '8G',
    })
    assert legacy == ['_memory_budget', 'memory_hard_limit', 'memory_limit']
    assert removed == ['enable_syslog_wf']


def test_seekdb_14_reports_legacy_memory_even_when_resource_check_is_skipped():
    load_core_or_skip()
    module = load_module(
        SEEKDB_14_ROOT / 'parameter_check.py',
        'seekdb_14_parameter_check_under_test',
    )

    server = type('Server', (), {'ip': '127.0.0.1'})()

    class ClusterConfig:
        name = 'seekdb'
        servers = [server]

        @staticmethod
        def get_server_conf_with_default(current_server):
            return {'home_path': '/opt/seekdb', 'memory_budget': '8G'}

        @staticmethod
        def get_explicit_server_conf(current_server, format_conf=True):
            return {'memory_limit': '8G'}

    errors = []
    values = {
        'servers_clients': {},
        'servers_memory': {'127.0.0.1': {}},
        'servers_disk': {'127.0.0.1': {}},
        'servers_clog_mount': {'127.0.0.1': {}},
        'servers_net_interface': {'127.0.0.1': {}},
        'parameter_check': False,
        'error': lambda *args, **kwargs: errors.append(args),
    }

    class Context:
        cluster_config = ClusterConfig()
        clients = {server: object()}

        def get_variable(self, name):
            return values.get(name)

        def set_variable(self, name, value):
            values[name] = value

        @staticmethod
        def return_true(**kwargs):
            return True

    assert module.parameter_check(Context()) is True
    assert any('Use `memory_budget` instead' in args[2] for args in errors)


def test_seekdb_14_deploy_config_check_rejects_unsupported_parameters():
    load_core_or_skip()
    module = load_module(
        SEEKDB_14_ROOT / 'deploy_config_check.py',
        'seekdb_14_deploy_config_check_under_test',
    )
    server = type('Server', (), {
        'ip': '127.0.0.1',
        '__str__': lambda self: self.ip,
    })()

    class ClusterConfig:
        servers = [server]

        @staticmethod
        def get_explicit_server_conf(current_server):
            assert current_server is server
            return {
                'memory_limit': '8G',
                'memory_hard_limit': '10G',
                'enable_syslog_wf': True,
            }

    class Context:
        cluster_config = ClusterConfig()

        @staticmethod
        def return_true(**kwargs):
            return kwargs

    result = module.deploy_config_check(Context())
    assert len(result['errors']) == 2
    assert 'memory_hard_limit, memory_limit' in result['errors'][0]
    assert 'Use `memory_budget` instead' in result['errors'][0]
    assert 'enable_syslog_wf' in result['errors'][1]


def test_edit_config_detects_atomic_editor_replacement(tmp_path):
    core = load_core_or_skip()
    config_path = tmp_path / 'config.yaml'
    replacement_path = tmp_path / 'replacement.yaml'
    initial_config = 'seekdb:\n  global:\n    max_syslog_file_count: 1\n'
    changed_config = 'seekdb:\n  global:\n    max_syslog_file_count: 3\n'
    config_path.write_text(initial_config)

    assert not core.ObdHome._deploy_config_text_changed(
        initial_config, str(config_path))

    replacement_path.write_text(changed_config)
    replacement_path.replace(config_path)
    assert core.ObdHome._deploy_config_text_changed(
        initial_config, str(config_path))


def test_seekdb_display_and_dashboard_preserve_encryption_display_semantics(monkeypatch):
    display = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.2.0.0' / 'display.py',
        'seekdb_display_password_under_test',
    )
    monkeypatch.setitem(sys.modules, 'obshell', SimpleNamespace(ClientV1=type('ClientV1', (), {})))
    dashboard = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.3.0' / 'obshell_dashboard.py',
        'seekdb_dashboard_password_under_test',
    )

    for module in (display, dashboard):
        assert module.mask_display_password('plain-secret', None) == 'plain-secret'
        assert module.mask_display_password('plain-secret', '<masked>') == '<masked>'
        assert module.mask_display_password('', None) == ''


def test_seekdb_14_parameter_catalog_invariants():
    parameters = yaml.safe_load((SEEKDB_14_ROOT / 'parameter.yaml').read_text())
    names = {parameter['name'] for parameter in parameters}
    assert len(names) == len(parameters)
    assert len(parameters) == 298
    assert {'memory_budget', 'cpu_count', 'kvcache_memory_limit',
            'memstore_memory_limit', 'vector_memory_limit'}.issubset(names)
    assert not {'_memory_budget', 'memory_hard_limit', 'system_memory', 'memory_limit_percentage',
                'cluster', 'zone', 'cluster_id'}.intersection(names)
    memory_limit = next(parameter for parameter in parameters
                        if parameter['name'] == 'memory_limit')
    assert memory_limit['need_restart'] is True
    parameter_by_name = {parameter['name']: parameter for parameter in parameters}
    assert parameter_by_name['_storage_meta_memory_limit_percentage']['default'] == 13
    assert parameter_by_name['query_memory_limit_percentage']['default'] == 32
    assert '40% of memory_budget' in parameter_by_name['kvcache_memory_limit']['description_en']
    assert '50% of memory_budget' in parameter_by_name['memstore_memory_limit']['description_en']
    assert '50% of memory_budget' in parameter_by_name['vector_memory_limit']['description_en']

def test_seekdb_14_start_parameters_exclude_removed_settings():
    module = load_module(
        SEEKDB_14_ROOT / 'start_pre.py',
        'seekdb_14_start_pre_under_test',
    )
    server_config = {
        'mysql_port': 2881,
        'redo_dir': '/redo/seekdb',
        'memory_budget': '8G',
        '_memory_budget': '7G',
        'memory_limit': '8G',
        'memory_hard_limit': '10G',
        'cluster_id': 1,
        'zone': 'zone1',
        'local_ip': '127.0.0.1',
        'enable_rpc_service': False,
        'rpc_port': 2882,
    }
    command = []

    module.construct_opts(server_config, dict(server_config), command, None)
    rendered = ' '.join(command)

    assert '--port 2881' in rendered
    assert '--redo-dir \'/redo/seekdb\'' in rendered
    assert '--parameter memory_budget=' in rendered
    assert '_memory_budget=' not in rendered
    assert 'memory_limit=' not in rendered
    assert 'memory_hard_limit=' not in rendered
    assert 'cluster_id=' not in rendered
    assert 'zone=' not in rendered
    assert 'local_ip=' not in rendered
    assert 'rpc_port=' not in rendered
    assert 'enable_rpc_tls=' not in rendered


def test_seekdb_14_restart_keeps_effective_rpc_port():
    module = load_module(
        SEEKDB_14_ROOT / 'start_pre.py',
        'seekdb_14_start_pre_rpc_under_test',
    )
    server_config = {
        'mysql_port': 2881,
        'enable_rpc_service': True,
        'rpc_port': 3882,
    }

    changed_only_command = []
    module.construct_opts(
        server_config, {'rpc_port': 3882}, changed_only_command, None)
    assert '--parameter rpc_port=3882' in ' '.join(changed_only_command)

    enable_only_command = []
    module.construct_opts(
        server_config, {'enable_rpc_service': True}, enable_only_command, None)
    rendered = ' '.join(enable_only_command)
    assert '--parameter rpc_port=3882' in rendered
    assert '--parameter enable_rpc_service=True' in rendered


def test_seekdb_14_init_leaves_kernel_owned_redo_layout_empty():
    module = load_module(
        SEEKDB_14_ROOT / 'init_pre.py',
        'seekdb_14_init_pre_under_test',
    )

    class Context:
        def __init__(self):
            self.variables = {}

        def set_variable(self, name, value):
            self.variables[name] = value

        @staticmethod
        def return_true(**kwargs):
            return True

    context = Context()
    assert module.init_pre(context) is True
    assert context.variables['dir_mapping'] == {}
    assert context.variables['clean_dir_keys'] == ['redo']
    assert context.variables['default_redo_dir_subdir'] == 'redo'
    assert context.variables['data_dir_not_same_redo_dir_keys'] == [
        'home_path', 'data_dir', 'redo_dir']


def test_seekdb_plugin_fallback_selects_13_and_14_implementations():
    core = load_core_or_skip()
    manager = core.PluginManager(str(PROJECT_ROOT), dev_mode=True)
    workflow_manager = core.WorkflowManager(str(PROJECT_ROOT), dev_mode=True)

    compute_13 = manager.get_best_py_script_plugin(
        'seekdb_install_compute_config', 'seekdb', '1.3.0.0')
    compute_14 = manager.get_best_py_script_plugin(
        'seekdb_install_compute_config', 'seekdb', '1.4.0.0')
    switchover_13 = manager.get_best_py_script_plugin(
        'switchover', 'seekdb', '1.3.0.0')
    switchover_14 = manager.get_best_py_script_plugin(
        'switchover', 'seekdb', '1.4.0.0')
    freeze_12 = manager.get_best_py_script_plugin('major_freeze', 'seekdb', '1.2.0.0')
    freeze_14 = manager.get_best_py_script_plugin('major_freeze', 'seekdb', '1.4.0.0')
    dump_12 = manager.get_best_py_script_plugin('dump_relation', 'seekdb', '1.2.0.0')
    dump_13 = manager.get_best_py_script_plugin('dump_relation', 'seekdb', '1.3.0.0')
    dump_14 = manager.get_best_py_script_plugin('dump_relation', 'seekdb', '1.4.0.0')
    install_14 = manager.get_best_plugin(core.PluginType.INSTALL, 'seekdb', '1.4.0.0')
    param_13 = manager.get_best_plugin(core.PluginType.PARAM, 'seekdb', '1.3.0.0')
    param_14 = manager.get_best_plugin(core.PluginType.PARAM, 'seekdb', '1.4.0.0')
    workflow_13 = workflow_manager.get_workflow_template(
        'switchover_seekdb', 'seekdb', '1.3.0.0')
    workflow_14 = workflow_manager.get_workflow_template(
        'switchover_seekdb', 'seekdb', '1.4.0.0')
    restart_12 = workflow_manager.get_workflow_template(
        'restart', 'seekdb', '1.2.0.0')
    restart_13 = workflow_manager.get_workflow_template(
        'restart', 'seekdb', '1.3.0.0')
    restart_14 = workflow_manager.get_workflow_template(
        'restart', 'seekdb', '1.4.0.0')

    assert str(compute_13.version) == '1.0.0'
    assert str(compute_14.version) == '1.4.0'
    assert str(switchover_13.version) == '1.2.0.0'
    assert str(switchover_14.version) == '1.4.0'
    assert str(freeze_12.version) == '1.0.0'
    assert str(freeze_14.version) == '1.3.0'
    assert str(dump_12.version) == '1.2.0.0'
    assert str(dump_13.version) == '1.3.0'
    assert str(dump_14.version) == '1.3.0'
    assert str(install_14.version) == '1.0.0'
    assert str(param_13.version) == '1.0.0'
    assert str(param_14.version) == '1.4.0'
    assert str(workflow_13.version) == '1.3.0'
    assert str(workflow_14.version) == '1.4.0'
    assert str(restart_12.version) == '1.2.0.0'
    assert str(restart_13.version) == '1.3.0'
    assert str(restart_14.version) == '1.3.0'
    assert len(param_14.params) == 298

    obd = object.__new__(core.ObdHome)
    obd._plugin_manager = manager
    obd._stdio_func = {'error': lambda *args, **kwargs: None}
    assert obd._seekdb_version_plugins_available(
        '1.4.0.0', require_interactive=True)
    assert not obd._seekdb_version_plugins_available(
        '1.5.0.0', require_interactive=True)


def test_new_plugins_load_through_obd_dynamic_loader():
    core = load_core_or_skip()
    manager = core.PluginManager(str(PROJECT_ROOT), dev_mode=True)
    plugins = [
        manager.get_best_py_script_plugin('deploy_config_check', 'seekdb', '1.4.0.0'),
        manager.get_best_py_script_plugin('parameter_check', 'seekdb', '1.4.0.0'),
        manager.get_best_py_script_plugin('init_pre', 'seekdb', '1.4.0.0'),
        manager.get_best_py_script_plugin('start_pre', 'seekdb', '1.4.0.0'),
        manager.get_best_py_script_plugin('switchover', 'seekdb', '1.4.0.0'),
        manager.get_best_py_script_plugin('start', 'obagent', '4.2.2'),
        manager.get_best_py_script_plugin('reload', 'obagent', '4.2.2'),
    ]

    for plugin in plugins:
        plugin._import()
        try:
            assert plugin.module is not None
        finally:
            plugin._export()


def test_takeover_uses_product_version_and_version_specific_memory_parameters():
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'takeover.py',
        'seekdb_takeover_under_test',
    )

    assert module._parse_seekdb_version(
        '5.7.25-OceanBase seekdb-v1.4.0.0') == '1.4.0.0'
    assert module._parse_seekdb_version('OceanBase 4.3.5.3') is None
    old_names = module._takeover_parameter_names('1.3.0.0')
    new_names = module._takeover_parameter_names('1.4.0.0')
    assert {'memory_limit', 'memory_hard_limit'}.issubset(old_names)
    assert 'memory_budget' not in old_names
    assert '_memory_budget' not in old_names
    assert {'memory_budget', 'kvcache_memory_limit', 'memstore_memory_limit',
            'vector_memory_limit'}.issubset(new_names)
    assert 'memory_limit' not in new_names


def test_takeover_discovers_home_path_from_obshell_info_without_proxy(monkeypatch):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'takeover.py',
        'seekdb_takeover_obshell_info_under_test',
    )
    inventory = (
        '/opt/seekdb/bin/seekdb --port 3881 --base-dir /opt/seekdb\n'
        '/opt/seekdb/bin/obshell server --port 4886 --base-dir /opt/seekdb --seekdb\n'
    )

    class CommandResult:
        stdout = inventory

        def __bool__(self):
            return True

    class Client:
        @staticmethod
        def execute_command(command):
            assert command == 'ps -eo args'
            return CommandResult()

    class Response:
        status_code = 200

        def __init__(self, data):
            self.data = data

        def json(self):
            return {'successful': True, 'data': self.data}

    class Session:
        trust_env = True

        def get(self, url, timeout, verify):
            assert timeout == 3
            assert verify is False
            assert self.trust_env is False
            if url == 'http://127.0.0.1:4886/api/v1/info':
                return Response({'type': 'seekdb', 'homePath': '/opt/seekdb'})
            if url == 'http://127.0.0.1:4886/api/v1/status':
                return Response({'sqlPort': 3881})
            raise AssertionError(url)

    monkeypatch.setattr(module.requests, 'Session', Session)
    home_path, obshell_port, error = module._query_home_path_from_obshell(
        Client(), '127.0.0.1', 3881, None)
    assert error is None
    assert home_path == '/opt/seekdb'
    assert obshell_port == 4886


def test_takeover_obshell_port_candidates_keep_legacy_defaults():
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'takeover.py',
        'seekdb_takeover_obshell_ports_under_test',
    )
    assert module._obshell_port_candidates('', 3881) == [3886, 2886]


def test_takeover_uses_ocs_for_existing_seekdb_versions():
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'takeover.py',
        'seekdb_takeover_ocs_under_test',
    )

    class Cursor:
        @staticmethod
        def fetchone(sql, args=None):
            if sql == "SHOW DATABASES LIKE 'ocs'":
                return {'Database (ocs)': 'ocs'}
            assert sql.startswith('SELECT home_path, port FROM ocs.all_agent')
            assert args == (3881,)
            return {'home_path': '/opt/seekdb', 'port': 4886}

    assert module._query_obshell_from_ocs(Cursor(), '127.0.0.1', 3881) == (
        '/opt/seekdb', 4886, None)


def test_takeover_rejects_single_obshell_when_seekdb_identity_is_not_visible(monkeypatch):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'takeover.py',
        'seekdb_takeover_restricted_ps_under_test',
    )

    class Result:
        stdout = 'COMMAND\n/usr/bin/python worker.py\n'

        def __bool__(self):
            return True

    class Client:
        @staticmethod
        def execute_command(command):
            return Result()

    class Response:
        def __init__(self, status_code):
            self.status_code = status_code

        def json(self):
            return {'data': {
                'type': 'seekdb', 'homePath': '/opt/seekdb', 'sqlPort': 3881,
            }}

    class Session:
        trust_env = True

        def get(self, url, timeout, verify):
            return Response(200 if ':3886/' in url and url.startswith('http://') else 404)

    monkeypatch.setattr(module.requests, 'Session', Session)
    home_path, obshell_port, error = module._query_home_path_from_obshell(
        Client(), '127.0.0.1', 3881, None)
    assert home_path is None
    assert obshell_port is None
    assert 'Could not discover' in error


def test_takeover_accepts_obshell_started_seekdb_without_port_argument(monkeypatch):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'takeover.py',
        'seekdb_takeover_obshell_process_under_test',
    )

    class Result:
        stdout = '/opt/seekdb/bin/seekdb --base-dir /opt/seekdb\n'

        def __bool__(self):
            return True

    class Client:
        @staticmethod
        def execute_command(command):
            return Result()

    class Response:
        status_code = 200

        def __init__(self, data):
            self.data = data

        def json(self):
            return {'data': self.data}

    class Session:
        trust_env = True

        def get(self, url, timeout, verify):
            if url.endswith('/api/v1/info'):
                return Response({'type': 'seekdb', 'homePath': '/opt/seekdb'})
            if url.endswith('/api/v1/status'):
                return Response({'sqlPort': 3881})
            raise AssertionError(url)

    monkeypatch.setattr(module.requests, 'Session', Session)
    assert module._query_home_path_from_obshell(
        Client(), '127.0.0.1', 3881, None) == ('/opt/seekdb', 3886, None)


def test_takeover_allows_unique_home_among_multiple_portless_processes(monkeypatch):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'takeover.py',
        'seekdb_takeover_ambiguous_process_under_test',
    )
    inventory = (
        '/opt/seekdb/bin/seekdb --base-dir /opt/seekdb\n'
        '/srv/seekdb/bin/seekdb --base-dir /srv/seekdb\n'
    )
    assert module._home_matches_seekdb(
        inventory, '/opt/seekdb', 3881) is True

    duplicate_home_inventory = inventory + (
        '/opt/seekdb/current/bin/seekdb --base-dir /opt/seekdb\n')
    assert module._home_matches_seekdb(
        duplicate_home_inventory, '/opt/seekdb', 3881) is False


def test_takeover_skips_wrong_portless_instance_obshell(monkeypatch):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'takeover.py',
        'seekdb_takeover_multi_instance_under_test',
    )
    inventory = (
        '/opt/a/bin/seekdb --base-dir /opt/a\n'
        '/opt/a/bin/obshell server --port 2886 --base-dir /opt/a --seekdb\n'
        '/opt/b/bin/seekdb --base-dir /opt/b\n'
        '/opt/b/bin/obshell server --port 3886 --base-dir /opt/b --seekdb\n'
    )

    class Result:
        stdout = inventory

        def __bool__(self):
            return True

    class Client:
        @staticmethod
        def execute_command(command):
            return Result()

    class Response:
        status_code = 200

        def __init__(self, data):
            self.data = data

        def json(self):
            return {'data': self.data}

    class Session:
        trust_env = True

        def get(self, url, timeout, verify):
            port = 2886 if ':2886/' in url else 3886 if ':3886/' in url else None
            if not port or not url.startswith('http://'):
                return SimpleNamespace(status_code=404)
            if url.endswith('/api/v1/info'):
                return Response({
                    'type': 'seekdb',
                    'homePath': '/opt/a' if port == 2886 else '/opt/b',
                })
            if url.endswith('/api/v1/status'):
                return Response({'sqlPort': 2881 if port == 2886 else 3881})
            return SimpleNamespace(status_code=404)

    monkeypatch.setattr(module.requests, 'Session', Session)
    assert module._query_home_path_from_obshell(
        Client(), '127.0.0.1', 3881, None) == ('/opt/b', 3886, None)


def test_takeover_accepts_custom_obshell_port_for_matching_sql_port(monkeypatch):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'takeover.py',
        'seekdb_takeover_custom_obshell_port_under_test',
    )
    inventory = (
        '/opt/seekdb/bin/seekdb --base-dir /opt/seekdb\n'
        '/opt/seekdb/bin/obshell server --port 4886 '
        '--base-dir /opt/seekdb --seekdb\n'
    )

    class Result:
        stdout = inventory

        def __bool__(self):
            return True

    class Client:
        @staticmethod
        def execute_command(command):
            return Result()

    class Response:
        status_code = 200

        def __init__(self, data):
            self.data = data

        def json(self):
            return {'data': self.data}

    class Session:
        trust_env = True

        def get(self, url, timeout, verify):
            assert ':4886/' in url
            if url.endswith('/api/v1/info'):
                return Response({'type': 'seekdb', 'homePath': '/opt/seekdb'})
            return Response({'sqlPort': 3881})

    monkeypatch.setattr(module.requests, 'Session', Session)
    assert module._query_home_path_from_obshell(
        Client(), '127.0.0.1', 3881, None) == ('/opt/seekdb', 4886, None)


def test_takeover_reads_requested_parameters_in_one_query():
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'takeover.py',
        'seekdb_takeover_query_under_test',
    )

    class Cursor:
        def __init__(self):
            self.calls = []

        def fetchall(self, sql, args, raise_exception=False):
            self.calls.append((sql, args, raise_exception))
            return [
                {'NAME': 'memory_budget', 'VALUE': '8G'},
                {'NAME': 'mysql_port', 'VALUE': '2881'},
            ]

    cursor = Cursor()
    parameters, error = module._query_parameters(
        cursor, ['memory_budget', 'mysql_port'])

    assert error is None
    assert parameters == {'memory_budget': '8G', 'mysql_port': '2881'}
    assert len(cursor.calls) == 1
    assert 'oceanbase.V$OB_PARAMETERS' in cursor.calls[0][0]
    assert cursor.calls[0][1] == ('memory_budget', 'mysql_port')
    assert cursor.calls[0][2] is True


def test_takeover_defaults_redo_under_effective_data_directory():
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'takeover.py',
        'seekdb_takeover_storage_paths_under_test',
    )
    default_config = {}
    module._complete_storage_paths(default_config, '/opt/seekdb', '1.4.0.0')
    assert default_config == {
        'data_dir': '/opt/seekdb/store',
        'redo_dir': '/opt/seekdb/store/redo',
    }

    custom_config = {'data_dir': '/data/seekdb'}
    module._complete_storage_paths(custom_config, '/opt/seekdb', '1.4.0.0')
    assert custom_config['redo_dir'] == '/data/seekdb/redo'

    legacy_config = {'data_dir': '/data/seekdb'}
    module._complete_storage_paths(legacy_config, '/opt/seekdb', '1.3.0.0')
    assert legacy_config['redo_dir'] == '/data/seekdb'


def test_new_and_legacy_obagent_seekdb_mappers():
    module = load_module(
        OBAGENT_13_ROOT / 'seekdb_mapper.py',
        'obagent_seekdb_mapper_under_test',
    )
    new_mapper = {
        'monitor_user': 'monagent.ob.monitor.user',
        'monitor_password': 'monagent.ob.monitor.password',
        'sql_port': 'monagent.ob.sql.port',
        'rpc_port': 'monagent.ob.rpc.port',
        'seekdb_user': 'monagent.seekdb.user',
        'seekdb_password': 'monagent.seekdb.password',
        'seekdb_host': 'monagent.seekdb.host',
        'seekdb_port': 'monagent.seekdb.port',
        'seekdb_monitor_status': 'monagent.pipeline.seekdb.status',
    }
    assert module.configure_seekdb_mapper(new_mapper) is True
    assert 'monitor_user' not in new_mapper
    assert 'sql_port' not in new_mapper
    assert new_mapper['seekdb_host'] == 'monagent.seekdb.host'

    legacy_mapper = {
        'monitor_user': 'monagent.ob.monitor.user',
        'monitor_password': 'monagent.ob.monitor.password',
        'sql_port': 'monagent.ob.sql.port',
    }
    assert module.configure_seekdb_mapper(legacy_mapper) is False
    assert legacy_mapper['monitor_user'] == 'monagent.seekdb.user'
    assert legacy_mapper['monitor_password'] == 'monagent.seekdb.password'
    assert legacy_mapper['seekdb_monitor_status'] == 'monagent.pipeline.seekdb.status'

    legacy_parameters = {
        'monitor_user': 'seekdb_monitor',
        'monitor_password': 'secret',
        'sql_port': 3881,
    }
    assert module.map_seekdb_start_parameters(
        legacy_parameters, True, '10.0.0.8') == {
            'monitor_user': 'seekdb_monitor',
            'monitor_password': 'secret',
            'sql_port': 3881,
            'seekdb_user': 'seekdb_monitor',
            'seekdb_password': 'secret',
            'seekdb_host': '10.0.0.8',
            'seekdb_port': 3881,
        }
    assert module.map_seekdb_start_parameters(
        legacy_parameters, False, '10.0.0.8') == legacy_parameters

    old_config = {
        'seekdb_monitor_user': 'old', 'seekdb_monitor_password': 'old-password',
        'mysql_port': 2881, 'rpc_port': 2882,
    }
    new_config = {
        'seekdb_monitor_user': 'new', 'seekdb_monitor_password': 'new-password',
        'mysql_port': 3881, 'rpc_port': 3882,
    }
    assert module.seekdb_dependency_changes(old_config, new_config, True) == {
        'seekdb_user': 'new', 'seekdb_password': 'new-password', 'seekdb_port': 3881,
    }
    assert module.seekdb_dependency_changes(old_config, new_config, True, '10.0.0.8') == {
        'seekdb_user': 'new', 'seekdb_password': 'new-password',
        'seekdb_host': '10.0.0.8', 'seekdb_port': 3881,
    }
    assert module.seekdb_dependency_changes(old_config, new_config, False) == {
        'monitor_user': 'new', 'monitor_password': 'new-password',
        'sql_port': 3881, 'rpc_port': 3882,
    }
    payload, unmapped = module.build_config_update_payload(
        {'seekdb_user': 'new', 'seekdb_port': 3881}, new_mapper)
    assert payload == [
        {'key': 'monagent.seekdb.user', 'value': 'new'},
        {'key': 'monagent.seekdb.port', 'value': 3881},
    ]
    assert unmapped == []
    payload, unmapped = module.build_config_update_payload(
        {'seekdb_user': 'new', 'unknown': 'value'}, legacy_mapper)
    assert payload == []
    assert unmapped == ['seekdb_user', 'unknown']


@pytest.mark.parametrize(
    'original_config, expected_ob_status, expected_seekdb_status',
    [
        ({}, 'inactive', 'active'),
        ({'ob_monitor_status': 'active', 'seekdb_monitor_status': 'inactive'},
         'active', 'inactive'),
    ],
)
def test_obagent_seekdb_dependency_statuses_override_defaults_only_when_omitted(
        original_config, expected_ob_status, expected_seekdb_status):
    module = load_module(
        OBAGENT_13_ROOT / 'parameter_pre.py',
        'obagent_parameter_pre_status_under_test',
    )
    class Server:
        ip = '127.0.0.1'

    server = Server()

    class ClusterConfig:
        depends = ['seekdb']
        servers = [server]

        @staticmethod
        def get_server_conf_with_default(target):
            assert target is server
            return {
                'ob_monitor_status': 'active',
                'seekdb_monitor_status': 'inactive',
            }

        @staticmethod
        def get_explicit_server_conf(target):
            assert target is server
            return dict(original_config)

        @staticmethod
        def get_depend_config(component, target=None):
            assert component == 'seekdb'
            return {} if target is None else {'mysql_port': 3881}

        @staticmethod
        def get_depend_servers(component):
            assert component == 'seekdb'
            return [server]

    class Context:
        cluster_config = ClusterConfig()

        def __init__(self):
            self.variables = {
                'OBAGNET_CONFIG_MAP': {
                    'ob_monitor_status': 'inactive',
                    'seekdb_monitor_status': 'active',
                },
                'depends_keys': [],
            }

        def get_variable(self, name):
            return self.variables[name]

        def set_variable(self, name, value):
            self.variables[name] = value

        @staticmethod
        def return_true(**kwargs):
            return True

        @staticmethod
        def return_false(**kwargs):
            return False

    context = Context()
    assert module.parameter_pre(context) is True
    start_config = context.variables['start_env'][server]
    assert start_config['ob_monitor_status'] == expected_ob_status
    assert start_config['seekdb_monitor_status'] == expected_seekdb_status


def test_obagent_reload_posts_json_key_values_envelope(monkeypatch):
    module = load_module(
        OBAGENT_13_ROOT / 'connect.py',
        'obagent_connect_reload_under_test',
    )
    calls = []

    class Response:
        status_code = 200
        content = b''

    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return Response()

    class Stdio:
        messages = []

        @classmethod
        def verbose(cls, message, *args, **kwargs):
            cls.messages.append(str(message))

        @staticmethod
        def exception(*args, **kwargs):
            pass

    monkeypatch.setattr(module.requests, 'request', request)
    cursor = module.ObagentAPICursor(
        ip='127.0.0.1', port=8089, username='admin', password='secret')
    changes = [{'key': 'monagent.seekdb.user', 'value': 'seekdb_monitor'}]

    assert cursor.reload(changes, stdio=Stdio()) is True
    assert len(calls) == 1
    method, url, kwargs = calls[0]
    assert method == 'POST'
    assert url == 'http://127.0.0.1:8089/api/v1/module/config/update'
    assert kwargs['json'] == {'configs': changes}
    assert 'data' not in kwargs
    assert kwargs['verify'] is False
    assert 'seekdb_monitor' not in ''.join(Stdio.messages)
    assert 'monagent.seekdb.user' in ''.join(Stdio.messages)


def test_obagent_reload_runs_after_database_reload_stage():
    module = load_module(
        PROJECT_ROOT / 'workflows' / 'obagent' / '0.1' / 'reload.py',
        'obagent_reload_workflow_under_test',
    )

    class Workflow:
        def __init__(self):
            self.calls = []

        def add(self, stage, *plugins):
            self.calls.append((stage, plugins))

    class Context:
        @staticmethod
        def return_true(**kwargs):
            return True

    workflow = Workflow()
    assert module.reload(Context(), workflow) is True
    assert workflow.calls == [
        (module.const.STAGE_FIRST, ('connect',)),
        (module.const.STAGE_THIRD, ('reload',)),
    ]


def test_explicit_server_config_preserves_include_precedence_without_defaults():
    load_core_or_skip()
    from _deploy import ClusterConfig as ObdClusterConfig
    server = object()

    class Config:
        _server_conf = {server: {'shared': 'server', 'server_only': True}}

        @staticmethod
        def _get_include_config(key, default):
            assert key == 'config'
            return {'include_only': True, 'shared': 'include'}

        @staticmethod
        def get_original_global_conf():
            return {'global_only': True, 'shared': 'global'}

        @staticmethod
        def _apply_temp_conf(config):
            return config

    result = ObdClusterConfig.get_explicit_server_conf(Config(), server)
    assert result == {
        'include_only': True,
        'global_only': True,
        'server_only': True,
        'shared': 'server',
    }


def test_obagent_database_dependency_changes_use_agent_keys():
    module = load_module(
        OBAGENT_13_ROOT / 'reload.py',
        'obagent_database_dependency_reload_under_test',
    )
    changes = module.database_dependency_changes(
        {
            'root_password': 'old', 'mysql_port': 2881, 'rpc_port': 2882,
            'appname': 'old-cluster', 'cluster_id': 1, 'zone': 'zone1',
        },
        {
            'root_password': 'new', 'mysql_port': 3881, 'rpc_port': 3882,
            'appname': 'new-cluster', 'cluster_id': 2, 'zone': 'zone2',
        },
    )
    assert changes == {
        'monitor_password': 'new',
        'sql_port': 3881,
        'rpc_port': 3882,
        'cluster_name': 'new-cluster',
        'cluster_id': 2,
        'zone_name': 'zone2',
    }


def test_seekdb_14_auto_memory_budget_matches_server_rule():
    module = load_module(
        SEEKDB_14_ROOT / 'resource_check.py',
        'seekdb_14_auto_memory_budget_under_test',
    )
    gib = 1 << 30
    assert module.automatic_memory_budget(16 * gib) == int(16 * gib * 0.8)
    assert module.automatic_memory_budget(4 * gib) == 3 * gib
    assert module.automatic_memory_budget(2 * gib) == gib
    assert module.automatic_memory_budget(gib // 2) == gib
    memory_stat = {
        'num': 2 * gib,
        'percentage': 10,
        'servers': {
            'auto': {'auto_memory_budget': True},
            'fixed': {'auto_memory_budget': False},
        },
    }
    assert module.total_memory_usage(memory_stat, 4 * gib) == int(5.4 * gib)

    parameters = load_module(
        SEEKDB_14_ROOT / 'seekdb_14_parameters.py',
        'seekdb_14_shared_auto_memory_under_test',
    )
    assert parameters.automatic_memory_budget(4 * gib) == 3 * gib
    core = load_core_or_skip()
    assert core._seekdb_automatic_memory_budget(4 * gib) == 3 * gib


def test_seekdb_effective_memory_total_handles_cgroup_limits():
    from _types import effective_memory_available, effective_memory_total

    gib = 1 << 30
    assert effective_memory_total(128 * gib, 8 * gib) == 8 * gib
    assert effective_memory_total(128 * gib, 'max') == 128 * gib
    assert effective_memory_total(128 * gib, 1 << 62) == 128 * gib
    assert effective_memory_available(
        128 * gib, 64 * gib, 8 * gib, 7 * gib) == 1 * gib

    parameters = load_module(
        SEEKDB_14_ROOT / 'seekdb_14_parameters.py',
        'seekdb_14_effective_memory_under_test',
    )

    class Result:
        def __init__(self, stdout):
            self.stdout = stdout

        def __bool__(self):
            return True

    class Client:
        def __init__(self, limit, usage=None):
            self.limit = limit
            self.usage = usage

        def execute_command(self, command):
            assert 'memory.max' in command
            assert 'memory.limit_in_bytes' in command
            values = [self.limit]
            if self.usage is not None:
                values.append(self.usage)
            return Result('\n'.join(values))

    assert parameters.detect_effective_memory_total(
        Client(str(8 * gib)), 128 * gib) == 8 * gib
    assert parameters.detect_effective_memory_total(
        Client('max'), 128 * gib) == 128 * gib
    assert parameters.detect_effective_memory_stats(
        Client(str(8 * gib), str(7 * gib)), 128 * gib, 64 * gib
    ) == (8 * gib, 1 * gib)


def test_seekdb_primary_memory_uses_cgroup_limit(monkeypatch):
    core = load_core_or_skip()
    gib = 1 << 30

    class Server:
        ip = '127.0.0.1'

    server = Server()

    class Result:
        def __init__(self, stdout):
            self.stdout = stdout

        def __bool__(self):
            return True

    class Client:
        @staticmethod
        def execute_command(command):
            if command == 'cat /proc/meminfo':
                return Result('MemTotal:       134217728 kB\n')
            if 'memory.max' in command:
                return Result(str(8 * gib))
            raise AssertionError(command)

    obd = object.__new__(core.ObdHome)
    monkeypatch.setattr(
        obd, 'get_clients',
        lambda config, repositories: {server: Client()})
    deploy = SimpleNamespace(deploy_config=SimpleNamespace())
    assert obd._seekdb_primary_total_memory(deploy, server) == 8 * gib


def test_seekdb_interactive_resources_use_cgroup_limit(monkeypatch):
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0'
        / 'seekdb_install_get_resources.py',
        'seekdb_install_cgroup_resources_under_test',
    )
    gib = 1 << 30

    class Result:
        def __init__(self, stdout):
            self.stdout = stdout

        def __bool__(self):
            return True

    def execute(command, stdio=None):
        if command == 'cat /proc/meminfo':
            return Result(
                'MemTotal:       134217728 kB\n'
                'MemAvailable:   67108864 kB\n')
        if 'memory.max' in command:
            return Result('%s\n%s' % (8 * gib, 7 * gib))
        if command.startswith('df -Pk'):
            return Result('104857600\n')
        raise AssertionError(command)

    monkeypatch.setattr(module.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(module.NetUtil, 'get_host_ip', lambda: '127.0.0.1')
    monkeypatch.setattr(module.LocalClient, 'execute_command', execute)
    values = {
        ('interactive', 'base_info'): {
            'ip': '127.0.0.1', 'user': 'admin',
            'home_path': '/opt/seekdb', 'data_dir': '/data/seekdb',
            'redo_dir': '/redo/seekdb',
        },
    }

    class Context:
        stdio = SimpleNamespace(error=lambda *args, **kwargs: None)

        @staticmethod
        def get_variable(name, spacename=None):
            return values.get((spacename or 'seekdb', name))

        @staticmethod
        def set_variable(name, value):
            values[('seekdb', name)] = value

        @staticmethod
        def return_true(**kwargs):
            return True

        @staticmethod
        def return_false(**kwargs):
            return False

    assert module.seekdb_install_get_resources(Context()) is True
    resources = values[('seekdb', 'resources')]
    assert resources['total_mem'] == 8 * gib
    assert resources['avail_mem'] == 1 * gib


@pytest.mark.parametrize('encrypted', [False, True])
def test_seekdb_temp_config_update_preserves_encryption_mode(
        monkeypatch, tmp_path, encrypted):
    core = load_core_or_skip()
    from _deploy import ConfigParserManager, DeployConfig, DeployConfigStatus, InnerConfig
    from tool import YamlLoader

    deploy_dir = tmp_path / 'seekdb-primary'
    deploy_dir.mkdir()
    config_path = deploy_dir / 'config.yaml'
    inner_path = deploy_dir / 'inner_config.yaml'
    config_path.write_text(yaml.safe_dump({
        'user': {'username': 'admin', 'password': 'ssh-secret'},
        'seekdb': {
            'servers': ['127.0.0.1'],
            'global': {
                'home_path': '/opt/seekdb',
                'mysql_port': 2881,
                'root_password': 'plain-secret',
            },
        },
    }))

    command_env = dict(core.COMMAND_ENV.show_env())
    command_env[core.const.ENCRYPT_PASSWORD] = '1'
    monkeypatch.setattr(core.COMMAND_ENV, '_cmd_env', command_env)
    loader = YamlLoader()
    parser_manager = ConfigParserManager(str(tmp_path))
    inner = InnerConfig(str(inner_path), loader)
    source = DeployConfig(
        str(config_path), yaml_loader=loader, inner_config=inner,
        config_parser_manager=parser_manager, config_encrypted=False,
        stdio=SimpleNamespace(
            verbose=lambda *args, **kwargs: None,
            exception=lambda *args, **kwargs: None))
    if encrypted:
        source.enable_encrypt_dump()
    else:
        source.disable_encrypt_dump()
    assert source.dump() is True

    class Deploy:
        config_dir = str(deploy_dir)
        deploy_config = source
        deploy_info = SimpleNamespace(config_status=DeployConfigStatus.UNCHNAGE)

        @staticmethod
        def update_deploy_config_status(status):
            Deploy.deploy_info.config_status = status
            return True

    obd = object.__new__(core.ObdHome)
    obd._deploy_manager = SimpleNamespace(config_parser_manager=parser_manager)
    obd.stdio = SimpleNamespace(
        verbose=lambda *args, **kwargs: None,
        exception=lambda *args, **kwargs: None)
    obd._stdio_func = {'error': lambda *args, **kwargs: None}

    def updater(config):
        if encrypted:
            raw_before_update = Path(config.yaml_path).read_text()
            assert 'plain-secret' not in raw_before_update
            assert 'ssh-secret' not in raw_before_update
        return config.components['seekdb'].update_global_conf(
            'enable_rpc_service', True, save=True)

    assert obd._seekdb_write_temp_config_update(
        Deploy(), DeployConfigStatus.NEED_RESTART, updater) is True
    temp_path = deploy_dir / 'tmp_config.yaml'
    raw = temp_path.read_text()
    if encrypted:
        assert 'plain-secret' not in raw
        assert 'ssh-secret' not in raw
    else:
        assert 'plain-secret' in raw
        assert 'ssh-secret' in raw

    loaded = DeployConfig(
        str(temp_path), yaml_loader=loader, inner_config=inner,
        config_parser_manager=parser_manager,
        config_encrypted=encrypted, stdio=obd.stdio)
    conf = loaded.components['seekdb'].get_global_conf()
    assert conf['root_password'] == 'plain-secret'
    assert conf['enable_rpc_service'] is True
    assert loaded.user.password == 'ssh-secret'
    assert bool(inner.get_global_config(core.const.ENCRYPT_PASSWORD)) is encrypted


@pytest.mark.parametrize('failure_point', ['copy', 'status'])
def test_seekdb_temp_config_update_rolls_back_failures(
        monkeypatch, tmp_path, failure_point):
    core = load_core_or_skip()
    from _deploy import ConfigParserManager, DeployConfig, DeployConfigStatus, InnerConfig
    from tool import YamlLoader

    deploy_dir = tmp_path / 'seekdb-primary'
    deploy_dir.mkdir()
    config_path = deploy_dir / 'config.yaml'
    temp_path = deploy_dir / 'tmp_config.yaml'
    inner_path = deploy_dir / 'inner_config.yaml'
    config_path.write_text(yaml.safe_dump({
        'seekdb': {
            'servers': ['127.0.0.1'],
            'global': {'home_path': '/opt/seekdb', 'mysql_port': 2881},
        },
    }))
    temp_path.write_text('previous-temp-config')
    loader = YamlLoader()
    parser_manager = ConfigParserManager(str(tmp_path))
    source = DeployConfig(
        str(config_path), yaml_loader=loader,
        inner_config=InnerConfig(str(inner_path), loader),
        config_parser_manager=parser_manager, config_encrypted=False,
        stdio=SimpleNamespace(
            verbose=lambda *args, **kwargs: None,
            exception=lambda *args, **kwargs: None))
    source.disable_encrypt_dump()

    class Deploy:
        config_dir = str(deploy_dir)
        deploy_config = source
        deploy_info = SimpleNamespace(config_status=DeployConfigStatus.UNCHNAGE)

        @staticmethod
        def update_deploy_config_status(status):
            return failure_point != 'status'

    obd = object.__new__(core.ObdHome)
    obd._deploy_manager = SimpleNamespace(config_parser_manager=parser_manager)
    obd.stdio = source.stdio
    obd._stdio_func = {'error': lambda *args, **kwargs: None}

    original_copy = core.FileUtil.copy
    copy_calls = []

    def partial_copy(src, target, stdio):
        copy_calls.append((src, target))
        if len(copy_calls) == 2:
            Path(target).write_text('partial')
            return False
        return original_copy(src, target, stdio)

    if failure_point == 'copy':
        monkeypatch.setattr(core.FileUtil, 'copy', partial_copy)
    assert obd._seekdb_write_temp_config_update(
        Deploy(), DeployConfigStatus.NEED_RESTART,
        lambda config: config.components['seekdb'].update_global_conf(
            'enable_rpc_service', True, save=True)) is False
    assert temp_path.read_text() == 'previous-temp-config'
    if failure_point == 'copy':
        assert len(copy_calls) == 2
    assert not [
        path for path in deploy_dir.iterdir()
        if path.name not in {'config.yaml', 'tmp_config.yaml', 'inner_config.yaml'}
    ]


def test_seekdb_standby_log_disk_uses_effective_zero_memory_budgets(monkeypatch):
    core = load_core_or_skip()
    from _deploy import DeployConfigStatus, DeployStatus

    gib = 1 << 30
    server = SimpleNamespace(ip='127.0.0.1')

    class ClusterConfig:
        servers = [server]

        @staticmethod
        def get_server_conf_with_default(target):
            assert target is server
            return {'memory_budget': '0M', 'log_disk_size': '4G'}

        @staticmethod
        def get_original_server_conf(target):
            return {}

    deploy_config = SimpleNamespace(components={'seekdb': ClusterConfig()})
    deploy = SimpleNamespace(
        deploy_config=deploy_config,
        deploy_info=SimpleNamespace(
            status=DeployStatus.STATUS_RUNNING,
            config_status=DeployConfigStatus.UNCHNAGE),
        config_dir='/unused',
    )
    obd = object.__new__(core.ObdHome)
    obd._deploy_manager = SimpleNamespace(
        get_deploy_config=lambda name: deploy,
        config_parser_manager=None,
    )
    obd._stdio_func = {
        'print': lambda *args, **kwargs: None,
        'warn': lambda *args, **kwargs: None,
        'error': lambda *args, **kwargs: None,
    }
    obd.deploy = None
    captured = {}

    def write_update(target_deploy, status, updater):
        class UpdatedClusterConfig:
            servers = [server]

            @staticmethod
            def update_global_conf(key, value, save=True):
                captured[key] = value
                return True

        return updater(SimpleNamespace(
            components={'seekdb': UpdatedClusterConfig()}))

    monkeypatch.setattr(obd, '_seekdb_primary_total_memory', lambda *args: 4 * gib)
    monkeypatch.setattr(obd, '_seekdb_write_temp_config_update', write_update)
    monkeypatch.setattr(obd, 'reload_cluster', lambda name: True)

    assert obd._seekdb_ensure_primary_log_disk_for_standby(
        'primary', '0M', standby_total_memory=2 * gib) is True
    # Primary 0M => 3G effective on a 4G host; the log disk must be 3x that.
    assert captured['log_disk_size'] == '9G'


def test_seekdb_pending_log_disk_reload_is_retried(monkeypatch):
    core = load_core_or_skip()
    from _deploy import DeployConfigStatus, DeployStatus

    server = SimpleNamespace(ip='127.0.0.1')

    class ClusterConfig:
        servers = [server]

        @staticmethod
        def get_server_conf_with_default(target):
            return {'memory_budget': '1G', 'log_disk_size': '9G'}

        @staticmethod
        def get_original_server_conf(target):
            return {}

    config = SimpleNamespace(components={'seekdb': ClusterConfig()})
    deploy = SimpleNamespace(
        deploy_config=config,
        temp_deploy_config=config,
        deploy_info=SimpleNamespace(
            status=DeployStatus.STATUS_RUNNING,
            config_status=DeployConfigStatus.NEED_RELOAD),
    )
    obd = object.__new__(core.ObdHome)
    obd._deploy_manager = SimpleNamespace(get_deploy_config=lambda name: deploy)
    obd._stdio_func = {
        'print': lambda *args, **kwargs: None,
        'warn': lambda *args, **kwargs: None,
        'error': lambda *args, **kwargs: None,
    }
    monkeypatch.setattr(obd, 'set_deploy', lambda value: None)
    results = iter([False, True])
    calls = []

    def reload_cluster(name):
        calls.append(name)
        return next(results)

    monkeypatch.setattr(obd, 'reload_cluster', reload_cluster)
    assert obd._seekdb_ensure_primary_log_disk_for_standby(
        'primary', '1G') is False
    assert obd._seekdb_ensure_primary_log_disk_for_standby(
        'primary', '1G') is True
    assert calls == ['primary', 'primary']


def test_seekdb_enable_primary_rpc_preserves_server_override(monkeypatch):
    core = load_core_or_skip()
    from _deploy import DeployConfigStatus

    server = SimpleNamespace(ip='127.0.0.1')
    updates = []

    class ActiveClusterConfig:
        servers = [server]

        @staticmethod
        def get_original_server_conf(target):
            return {'enable_rpc_service': False}

    class UpdatedClusterConfig:
        servers = [server]

        @staticmethod
        def update_server_conf(target, key, value, save=True):
            updates.append(('server', target, key, value, save))
            return True

        @staticmethod
        def update_global_conf(key, value, save=True):
            updates.append(('global', key, value, save))
            return True

    active = SimpleNamespace(components={'seekdb': ActiveClusterConfig()})
    deploy = SimpleNamespace(
        deploy_config=active,
        deploy_info=SimpleNamespace(config_status=DeployConfigStatus.UNCHNAGE),
    )
    obd = object.__new__(core.ObdHome)
    obd._deploy_manager = SimpleNamespace(get_deploy_config=lambda name: deploy)
    obd._stdio_func = {
        'error': lambda *args, **kwargs: None,
        'print': lambda *args, **kwargs: None,
    }

    def write_update(target_deploy, status, updater):
        assert status == DeployConfigStatus.NEED_RESTART
        return updater(SimpleNamespace(
            components={'seekdb': UpdatedClusterConfig()}))

    monkeypatch.setattr(obd, '_seekdb_write_temp_config_update', write_update)
    assert obd._seekdb_enable_primary_rpc_for_standby(
        'primary', 'restart_later') is True
    assert updates == [
        ('server', server, 'enable_rpc_service', True, True),
    ]


def test_seekdb_enable_primary_rpc_rejects_redeploy_state(monkeypatch):
    core = load_core_or_skip()
    from _deploy import DeployConfigStatus

    config = SimpleNamespace(components={'seekdb': object()})
    deploy = SimpleNamespace(
        deploy_config=config,
        deploy_info=SimpleNamespace(config_status=DeployConfigStatus.NEED_REDEPLOY),
    )
    obd = object.__new__(core.ObdHome)
    obd._deploy_manager = SimpleNamespace(get_deploy_config=lambda name: deploy)
    obd._stdio_func = {'error': lambda *args, **kwargs: None}
    called = []
    monkeypatch.setattr(
        obd, '_seekdb_write_temp_config_update',
        lambda *args, **kwargs: called.append(True))
    assert obd._seekdb_enable_primary_rpc_for_standby(
        'primary', 'restart_now') is False
    assert called == []


def test_seekdb_atomic_temp_config_apply_rolls_back_status_failure(tmp_path):
    core = load_core_or_skip()
    from _deploy import DeployConfigStatus

    config_path = tmp_path / 'config.yaml'
    temp_path = tmp_path / 'tmp_config.yaml'
    data_path = tmp_path / '.data'
    config_path.write_text('old-config')
    temp_path.write_text('new-config')
    data_path.write_text('old-status')
    for path in (config_path, temp_path, data_path):
        path.chmod(0o600)

    class Deploy:
        config_dir = str(tmp_path)
        deploy_info = SimpleNamespace(
            config_status=DeployConfigStatus.NEED_RESTART)
        _config = object()

        @staticmethod
        def update_deploy_config_status(status):
            data_path.write_text('partial-status')
            return False

    obd = object.__new__(core.ObdHome)
    obd.stdio = SimpleNamespace(
        verbose=lambda *args, **kwargs: None,
        exception=lambda *args, **kwargs: None)
    obd._stdio_func = {'error': lambda *args, **kwargs: None}

    deploy = Deploy()
    assert obd._seekdb_apply_temp_config_atomically(deploy) is False
    assert config_path.read_text() == 'old-config'
    assert temp_path.read_text() == 'new-config'
    assert data_path.read_text() == 'old-status'
    assert [
        path.stat().st_mode & 0o777
        for path in (config_path, temp_path, data_path)
    ] == [0o600, 0o600, 0o600]
    assert not list(tmp_path.glob('.obd_restore_*'))
    assert Deploy.deploy_info.config_status == DeployConfigStatus.NEED_RESTART
    assert deploy._config is None


def test_seekdb_connect_new_endpoint_accepts_old_password_during_restart(monkeypatch):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'connect.py',
        'seekdb_connect_password_transition_under_test',
    )
    server = SimpleNamespace(ip='127.0.0.1', name='seekdb-1')

    class ClusterConfig:
        name = 'seekdb'
        servers = [server]

        def __init__(self, port, password):
            self.port = port
            self.password = password

        def get_server_conf(self, candidate):
            if candidate is not server and candidate.name != server.name:
                raise KeyError(candidate)
            return {'mysql_port': self.port, 'root_password': self.password}

    old_config = ClusterConfig(2881, 'old-password')
    new_config = ClusterConfig(3881, 'new-password')
    attempts = []

    class Cursor:
        def __init__(self, ip, port, tenant, password, stdio):
            attempts.append((ip, port, password))
            if password == 'new-password':
                raise RuntimeError('authentication failed')
            self.port = port
            self.password = password
            self.db = object()

        def execute(self, *args, **kwargs):
            return self.port == 3881 and self.password == 'old-password'

        def close(self):
            return None

    monkeypatch.setattr(module, 'Cursor', Cursor)
    monkeypatch.setattr(module.time, 'sleep', lambda seconds: None)
    returned = {}
    context = SimpleNamespace(
        cluster_config=new_config,
        stdio=SimpleNamespace(
            start_loading=lambda *args, **kwargs: None,
            stop_loading=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            exception=lambda *args, **kwargs: None),
        get_variable=lambda *args, **kwargs: None,
        set_variable=lambda key, value: returned.__setitem__(key, value),
        return_true=lambda **kwargs: True,
        return_false=lambda **kwargs: False,
    )

    assert module.connect(
        context, retry_times=1, old_cluster_config=old_config) is True
    assert attempts == [
        ('127.0.0.1', 3881, 'new-password'),
        ('127.0.0.1', 3881, 'old-password'),
    ]
    assert returned['server'] is server


def test_seekdb_connect_falls_back_to_empty_password_during_first_start(monkeypatch):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'connect.py',
        'seekdb_connect_empty_password_fallback_under_test',
    )
    server = SimpleNamespace(ip='127.0.0.1', name='seekdb-1')

    class ClusterConfig:
        name = 'seekdb'
        servers = [server]

        @staticmethod
        def get_server_conf(candidate):
            assert candidate is server
            return {
                'mysql_port': 2881,
                'root_password': 'generated-password',
            }

    attempts = []

    class Cursor:
        def __init__(self, ip, port, tenant, password, stdio):
            attempts.append(password)
            if password:
                raise RuntimeError(1045, 'Access denied for user root')
            self.db = object()

        @staticmethod
        def execute(*args, **kwargs):
            return True

    monkeypatch.setattr(module, 'Cursor', Cursor)
    monkeypatch.setattr(module.time, 'sleep', lambda seconds: None)
    returned = {}
    context = SimpleNamespace(
        cluster_config=ClusterConfig(),
        stdio=SimpleNamespace(
            start_loading=lambda *args, **kwargs: None,
            stop_loading=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            exception=lambda *args, **kwargs: None,
        ),
        get_variable=lambda *args, **kwargs: None,
        set_variable=lambda key, value: returned.__setitem__(key, value),
        return_true=lambda **kwargs: True,
        return_false=lambda **kwargs: False,
    )

    assert module.connect(context, retry_times=1) is True
    assert attempts == ['generated-password', '']
    assert returned['server'] is server


@pytest.mark.parametrize('failure_mode', ['constructor', 'query'])
def test_seekdb_connect_does_not_fallback_after_non_auth_failure(
        monkeypatch, failure_mode):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'connect.py',
        'seekdb_connect_non_auth_failure_%s' % failure_mode,
    )
    server = SimpleNamespace(ip='127.0.0.1', name='seekdb-1')
    attempts = []
    closed = []

    class Cursor:
        def __init__(self, ip, port, tenant, password, stdio):
            attempts.append(password)
            if failure_mode == 'constructor':
                raise RuntimeError('connection refused')
            self.db = object()

        @staticmethod
        def execute(*args, **kwargs):
            return False

        def close(self):
            closed.append(True)

    context, _ = make_seekdb_connect_context(
        [server],
        {'seekdb-1': {
            'mysql_port': 2881,
            'root_password': 'configured-password',
        }},
    )
    monkeypatch.setattr(module, 'Cursor', Cursor)
    monkeypatch.setattr(module.time, 'sleep', lambda seconds: None)

    assert module.connect(context, retry_times=1) is None
    assert attempts == ['configured-password']
    assert closed == ([] if failure_mode == 'constructor' else [True])


def test_seekdb_connect_normalizes_none_password_to_single_empty_attempt(monkeypatch):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'connect.py',
        'seekdb_connect_none_password_under_test',
    )
    server = SimpleNamespace(ip='127.0.0.1', name='seekdb-1')
    attempts = []

    class Cursor:
        def __init__(self, ip, port, tenant, password, stdio):
            attempts.append(password)
            self.db = object()

        @staticmethod
        def execute(*args, **kwargs):
            return True

    context, returned = make_seekdb_connect_context(
        [server],
        {'seekdb-1': {'mysql_port': 2881, 'root_password': None}},
    )
    monkeypatch.setattr(module, 'Cursor', Cursor)

    assert module.connect(context, retry_times=1) is True
    assert attempts == ['']
    assert returned['server'] is server


def test_seekdb_connect_all_closes_partial_connections_before_retry(monkeypatch):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'connect.py',
        'seekdb_connect_all_partial_failure_under_test',
    )
    servers = [
        SimpleNamespace(ip='127.0.0.1', name='seekdb-1'),
        SimpleNamespace(ip='127.0.0.2', name='seekdb-2'),
    ]
    successful_cursors = []

    class Cursor:
        def __init__(self, ip, port, tenant, password, stdio):
            if ip == '127.0.0.2':
                raise RuntimeError('connection refused')
            self.db = object()
            self.close_count = 0
            successful_cursors.append(self)

        @staticmethod
        def execute(*args, **kwargs):
            return True

        def close(self):
            self.close_count += 1

    context, _ = make_seekdb_connect_context(
        servers,
        {
            'seekdb-1': {'mysql_port': 2881, 'root_password': ''},
            'seekdb-2': {'mysql_port': 2881, 'root_password': ''},
        },
    )
    monkeypatch.setattr(module, 'Cursor', Cursor)
    monkeypatch.setattr(module.time, 'sleep', lambda seconds: None)

    assert module.connect(context, retry_times=2, connect_all=True) is None
    assert len(successful_cursors) == 2
    assert [cursor.close_count for cursor in successful_cursors] == [1, 1]


def test_seekdb_connect_all_keeps_only_returned_connection_open(monkeypatch):
    load_core_or_skip()
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.0.0' / 'connect.py',
        'seekdb_connect_all_success_under_test',
    )
    servers = [
        SimpleNamespace(ip='127.0.0.1', name='seekdb-1'),
        SimpleNamespace(ip='127.0.0.2', name='seekdb-2'),
    ]
    cursors = []

    class Cursor:
        def __init__(self, ip, port, tenant, password, stdio):
            self.ip = ip
            self.db = object()
            self.close_count = 0
            cursors.append(self)

        @staticmethod
        def execute(*args, **kwargs):
            return True

        def close(self):
            self.close_count += 1

    context, returned = make_seekdb_connect_context(
        servers,
        {
            'seekdb-1': {'mysql_port': 2881, 'root_password': ''},
            'seekdb-2': {'mysql_port': 2881, 'root_password': ''},
        },
    )
    monkeypatch.setattr(module, 'Cursor', Cursor)

    assert module.connect(context, retry_times=1, connect_all=True) is True
    assert [cursor.close_count for cursor in cursors] == [1, 0]
    assert returned['cursor'] is cursors[1]
    assert returned['server'] is servers[1]


def test_seekdb_obshell_sync_retries_pending_relation(monkeypatch):
    stub_obshell_modules(monkeypatch)
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.3.0' / 'sync_cluster_to_obshell.py',
        'seekdb_obshell_sync_retry_under_test',
    )

    class ClusterConfig:
        def __init__(self, primary=None, pending=None):
            self.attrs = {
                '_cluster_primary': primary,
                '_obshell_standby_sync_pending': pending,
            }
            self.servers = [SimpleNamespace(ip='127.0.0.1')]

        def get_component_attr(self, key):
            return self.attrs.get(key)

        def update_component_attr(self, key, value, save=True):
            assert save is True
            self.attrs[key] = value
            return True

        def get_server_conf_with_default(self, server):
            return {'rpc_port': 2882, 'obshell_port': 2886, 'root_password': ''}

        @staticmethod
        def get_global_conf():
            return {}

    primary_config = ClusterConfig()
    standby_config = ClusterConfig('primary', True)

    class DeployManager:
        @staticmethod
        def get_deploy_config(name):
            assert name == 'primary'
            return SimpleNamespace(
                deploy_config=SimpleNamespace(components={'seekdb': primary_config}))

    class Client:
        def __init__(self, token):
            self.token = token

        def set_seekdb_standby_pair(self, **kwargs):
            return True

        def get_seekdb_standby_status(self):
            return {'status': 'ok'}

    clients = iter([(Client('primary-token'), {'token': 'primary-token'}),
                    (Client('standby-token'), {'token': 'standby-token'})])
    monkeypatch.setattr(module, '_new_client_and_token', lambda meta: next(clients))

    stdio = SimpleNamespace(
        verbose=lambda *args, **kwargs: None,
        start_loading=lambda *args, **kwargs: None,
        stop_loading=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
    )

    class Context:
        cluster_config = standby_config

        @staticmethod
        def get_variable(name, spacename=None):
            return None

        @staticmethod
        def return_true(**kwargs):
            return True

        @staticmethod
        def return_false(**kwargs):
            return False

    context = Context()
    context.stdio = stdio
    assert module.sync_cluster_to_obshell(
        context, deploy_manager=DeployManager()) is True
    assert standby_config.attrs['_obshell_standby_sync_pending'] is False


@pytest.mark.parametrize(
    'version, expected',
    [('1.3.0.0', True), ('1.4.0.0', False)],
)
def test_seekdb_obshell_sync_failure_remains_pending(monkeypatch, version, expected):
    stub_obshell_modules(monkeypatch)
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.3.0' / 'sync_cluster_to_obshell.py',
        'seekdb_obshell_sync_failure_under_test',
    )
    config = SimpleNamespace(
        version=version,
        servers=[SimpleNamespace(ip='127.0.0.1')],
        get_component_attr=lambda key: {
            '_cluster_primary': 'primary',
            '_obshell_standby_sync_pending': True,
        }.get(key),
        get_server_conf_with_default=lambda server: {
            'rpc_port': 2882, 'obshell_port': 2886, 'root_password': ''},
        get_global_conf=lambda: {},
    )
    primary = SimpleNamespace(
        servers=config.servers,
        get_server_conf_with_default=config.get_server_conf_with_default,
        get_global_conf=config.get_global_conf,
    )
    deploy_manager = SimpleNamespace(get_deploy_config=lambda name: SimpleNamespace(
        deploy_config=SimpleNamespace(components={'seekdb': primary})))
    monkeypatch.setattr(
        module, '_new_client_and_token',
        lambda meta: (_ for _ in ()).throw(RuntimeError('unavailable')))
    context = SimpleNamespace(
        cluster_config=config,
        stdio=SimpleNamespace(
            verbose=lambda *args, **kwargs: None,
            start_loading=lambda *args, **kwargs: None,
            stop_loading=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            warn=lambda *args, **kwargs: None),
        get_variable=lambda name, spacename=None: None,
        return_true=lambda **kwargs: True,
        return_false=lambda **kwargs: False,
    )
    assert module.sync_cluster_to_obshell(
        context, deploy_manager=deploy_manager) is expected


def test_seekdb_13_restart_retries_pending_obshell_sync():
    module = load_module(
        PROJECT_ROOT / 'workflows' / 'seekdb' / '1.3.0' / 'restart.py',
        'seekdb_13_restart_sync_under_test',
    )
    calls = []

    class Workflow:
        @staticmethod
        def add(stage, *plugins):
            calls.append((plugins, {}))

        @staticmethod
        def add_with_kwargs(stage, kwargs, *plugins):
            calls.append((plugins, kwargs))

        @staticmethod
        def add_with_component_version_kwargs(stage, component, version, kwargs, *plugins):
            calls.append((plugins, kwargs))

    repository = SimpleNamespace(name='seekdb', repository_dir='/repo')
    cluster_config = SimpleNamespace(token='old')
    new_cluster_config = SimpleNamespace(token='new')
    old_clients = {'old': object()}
    new_clients = {'new': object()}
    new_deploy_config = SimpleNamespace(
        components={'seekdb': new_cluster_config})
    context = SimpleNamespace(
        cluster_config=cluster_config,
        get_variable=lambda name: {
            'clients': old_clients,
            'new_clients': new_clients,
            'new_deploy_config': new_deploy_config,
        }.get(name),
        return_true=lambda **kwargs: True,
    )
    assert module.restart(context, Workflow(), repository=repository) is True
    plugin_sequence = [
        plugin for plugins, kwargs in calls for plugin in plugins
    ]
    connect_calls = [
        kwargs for plugins, kwargs in calls if 'connect' in plugins
    ]
    assert len(connect_calls) == 2
    assert connect_calls[0]['cluster_config'] is new_cluster_config
    assert connect_calls[0]['old_cluster_config'] is cluster_config
    assert connect_calls[1]['cluster_config'] is new_cluster_config
    assert 'old_cluster_config' not in connect_calls[1]
    assert plugin_sequence.index('connect') < plugin_sequence.index('reload')
    assert plugin_sequence.index('reload') < plugin_sequence.index(
        'sync_cluster_to_obshell')
    sync_calls = [
        kwargs for plugins, kwargs in calls
        if 'sync_cluster_to_obshell' in plugins
    ]
    assert len(sync_calls) == 1
    assert sync_calls[0]['cluster_config'] is new_cluster_config
    assert sync_calls[0]['clients'] == context.get_variable('new_clients')


def test_dump_relation_persists_retry_marker_before_primary(monkeypatch):
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.3.0' / 'dump_relation.py',
        'seekdb_dump_relation_retry_under_test',
    )

    class Config:
        def __init__(self, deploy_name):
            self.deploy_name = deploy_name
            self.attrs = {}
            self.fail_primary_write = False

        def get_component_attr(self, key):
            return self.attrs.get(key)

        def update_component_attr(self, key, value, save=True):
            if self.fail_primary_write:
                return False
            self.attrs[key] = value
            return True

        def update_component_attrs(self, attrs, save=True):
            self.attrs.update(attrs)
            return True

    primary = Config('primary')
    standby = Config('standby')
    primary.fail_primary_write = True
    deploys = {
        'primary': SimpleNamespace(
            deploy_config=SimpleNamespace(components={'seekdb': primary})),
        'standby': SimpleNamespace(
            deploy_config=SimpleNamespace(components={'seekdb': standby})),
    }
    manager = SimpleNamespace(get_deploy_config=lambda name: deploys.get(name))
    variables = {'primary_deploy_name': 'primary'}
    context = SimpleNamespace(
        cluster_config=standby,
        stdio=SimpleNamespace(
            verbose=lambda *args, **kwargs: None,
            warn=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None),
        get_variable=lambda name: variables.get(name),
        return_true=lambda **kwargs: True,
        return_false=lambda **kwargs: False,
    )
    repository = SimpleNamespace(name='seekdb')

    assert module.dump_relation(
        context, deploy_manager=manager, repository=repository) is False
    assert standby.attrs['_cluster_primary'] == 'primary'
    assert standby.attrs['_obshell_standby_sync_pending'] is True
    assert primary.attrs.get('_cluster_standby_relation') is None

    # The next non-interactive start recovers primary_name from the standby
    # marker and completes the previously partial transaction.
    variables.clear()
    primary.fail_primary_write = False
    assert module.dump_relation(
        context, deploy_manager=manager, repository=repository) is True
    assert primary.attrs['_cluster_standby_relation'] == ['standby']


def test_seekdb_major_freeze_times_out(monkeypatch):
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.3.0' / 'major_freeze.py',
        'seekdb_major_freeze_timeout_under_test',
    )
    timestamps = iter([0, module.MAJOR_FREEZE_TIMEOUT_SECONDS + 1])
    monkeypatch.setattr(module.time, 'time', lambda: next(timestamps))

    class Cursor:
        @staticmethod
        def fetchone(sql):
            return {'FROZEN_SCN': 1, 'LAST_SCN': 0}

        @staticmethod
        def execute(sql):
            return True

    class Stdio:
        messages = []

        @staticmethod
        def start_loading(*args):
            pass

        @staticmethod
        def stop_loading(*args):
            pass

        @classmethod
        def error(cls, message):
            cls.messages.append(message)

    context = SimpleNamespace(
        stdio=Stdio(),
        return_false=lambda **kwargs: False,
        return_true=lambda **kwargs: True,
    )
    assert module.major_freeze(context, Cursor()) is False
    assert Stdio.messages == ['Timed out waiting for the major freeze SCN to advance.']


def test_seekdb_existing_data_start_publishes_obshell_client(monkeypatch):
    stub_obshell_modules(monkeypatch)
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.3.0' / 'obshell_bootstrap.py',
        'seekdb_obshell_bootstrap_existing_data_under_test',
    )

    class Api:
        @staticmethod
        def get_info():
            return SimpleNamespace(identity='CLUSTER_AGENT')

    class ClientSet:
        def __init__(self, ip, port, auth):
            self.ip = ip
            self.port = port
            self.v1 = Api()

    monkeypatch.setattr(module, 'ClientSet', ClientSet)
    monkeypatch.setattr(module, 'PasswordAuth', lambda password: password)

    class Server:
        ip = '192.0.2.10'

    server = Server()
    values = {'scale_out': False, 'seekdb_is_standby': False}
    returned = {}
    context = SimpleNamespace(
        cluster_config=SimpleNamespace(
            servers=[server],
            get_server_conf=lambda current: {
                'obshell_port': 2886,
                'root_password': 'secret',
            },
        ),
        stdio=SimpleNamespace(verbose=lambda *args, **kwargs: None),
        get_variable=lambda name, default=None: values.get(name, default),
        set_variable=lambda name, value: returned.__setitem__(name, value),
        return_true=lambda **kwargs: True,
    )

    assert module.obshell_bootstrap(context, need_bootstrap=False) is True
    assert returned['obshell_client'].ip == '192.0.2.10'
    assert returned['obshell_client'].port == 2886


def test_seekdb_https_obshell_client_survives_bootstrap_poll(monkeypatch):
    stub_obshell_modules(monkeypatch)
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'seekdb' / '1.3.0' / 'obshell_bootstrap.py',
        'seekdb_obshell_bootstrap_https_poll_under_test',
    )

    class HttpApi:
        @staticmethod
        def get_info():
            raise RuntimeError('status code: 400')

    class ClientSet:
        def __init__(self, ip, port, auth):
            self.v1 = HttpApi()

    identities = iter(['INITIALIZING', 'CLUSTER_AGENT'])

    class ClientV1:
        def __init__(self, ip, port, auth, protocol_options):
            self.ip = ip

        @staticmethod
        def get_info():
            return SimpleNamespace(identity=next(identities))

    monkeypatch.setattr(module, 'ClientSet', ClientSet)
    monkeypatch.setattr(module, 'ClientV1', ClientV1)
    monkeypatch.setattr(module, 'PasswordAuth', lambda password: password)
    monkeypatch.setattr(
        module, 'ProtocolOptions',
        SimpleNamespace(https_insecure=lambda: 'https-insecure'))
    monkeypatch.setattr(module.time, 'sleep', lambda seconds: None)
    monkeypatch.setattr(module, 'Agentidentity', SimpleNamespace(
        TAKE_OVER_MASTER=SimpleNamespace(value='TAKE_OVER_MASTER'),
        CLUSTER_AGENT=SimpleNamespace(value='CLUSTER_AGENT'),
    ))

    class Server:
        ip = '192.0.2.10'

    server = Server()
    returned = {}
    context = SimpleNamespace(
        cluster_config=SimpleNamespace(
            servers=[server],
            get_server_conf=lambda current: {
                'obshell_port': 2886,
                'root_password': 'secret',
            },
        ),
        stdio=SimpleNamespace(
            start_loading=lambda *args, **kwargs: None,
            stop_loading=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            exception=lambda *args, **kwargs: None,
        ),
        get_variable=lambda name, default=None: False,
        set_variable=lambda name, value: returned.__setitem__(name, value),
        return_true=lambda **kwargs: True,
        return_false=lambda **kwargs: False,
    )

    assert module.obshell_bootstrap(context, need_bootstrap=True) is True
    assert isinstance(returned['obshell_client'], ClientV1)


class FakePrometheusServer:
    def __init__(self, ip):
        self.ip = ip


class FakePrometheusClusterConfig:
    def __init__(self, servers, config=None):
        self.servers = servers
        self.depends = []
        self.config = config or {
            'home_path': '/opt/prometheus',
            'port': 9090,
            'basic_auth_users': {'admin': 'secret'},
        }

    def get_server_conf(self, server):
        return dict(self.config)


class FakePrometheusStdio:
    def __init__(self):
        self.verbose_messages = []
        self.warn_messages = []

    def verbose(self, message, *args):
        self.verbose_messages.append(message % args if args else message)

    def warn(self, message, *args):
        self.warn_messages.append(message % args if args else message)

    @staticmethod
    def stop_loading(*args, **kwargs):
        pass


def _prometheus_register_context(obshell_client, ips=None, server_config=None):
    servers = [FakePrometheusServer(ip) for ip in (
        ips or ['192.0.2.20'])]
    stdio = FakePrometheusStdio()
    namespace = SimpleNamespace(
        get_variable=lambda name: (
            obshell_client if name == 'obshell_client' else None),
    )
    context = SimpleNamespace(
        cluster_config=FakePrometheusClusterConfig(servers, server_config),
        clients={server: SimpleNamespace(
            execute_command=lambda command: True,
        ) for server in servers},
        namespaces={'seekdb': namespace},
        stdio=stdio,
        return_true=lambda **kwargs: True,
    )
    return context, stdio


class FakeObshellError(Exception):
    def __init__(self, err_code):
        super().__init__(err_code)
        self.err_code = err_code


def test_seekdb_prometheus_registration_retries_after_started_flag():
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'prometheus' / '2.37.1' /
        'register_to_obshell.py',
        'prometheus_register_retry_under_test',
    )

    class Api:
        def __init__(self):
            self.registered = None

        @staticmethod
        def get_info():
            return SimpleNamespace(version='4.3.2.0')

        def get_prometheus_config(self):
            if self.registered is None:
                raise FakeObshellError('Config.NotFound')
            return self.registered

        def set_prometheus_config(self, url, username, password):
            self.registered = {
                'url': url, 'username': username, 'password': password}

    api = Api()
    context, stdio = _prometheus_register_context(
        SimpleNamespace(v1=api))

    assert module.register_to_obshell(context) is True
    assert api.registered == {
        'url': 'http://192.0.2.20:9090/',
        'username': 'admin',
        'password': 'secret',
    }
    assert not stdio.warn_messages
    assert all('secret' not in message for message in stdio.verbose_messages)


def test_seekdb_prometheus_registration_preserves_existing_config():
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'prometheus' / '2.37.1' /
        'register_to_obshell.py',
        'prometheus_register_existing_config_under_test',
    )

    class DirectApi:
        set_calls = []

        @staticmethod
        def get_info():
            return SimpleNamespace(version='4.3.2.0')

        @staticmethod
        def get_prometheus_config():
            return {
                'address': 'http://manual-prometheus:9090/',
                'auth': {'username': 'manual', 'password': 'manual-secret'},
            }

        @classmethod
        def set_prometheus_config(cls, *args):
            cls.set_calls.append(args)

    context, stdio = _prometheus_register_context(DirectApi())

    assert module.register_to_obshell(context) is True
    assert DirectApi.set_calls == []
    assert not stdio.warn_messages
    assert all('manual-secret' not in message
               for message in stdio.verbose_messages)


def test_seekdb_prometheus_registration_does_not_replace_unready_config():
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'prometheus' / '2.37.1' /
        'register_to_obshell.py',
        'prometheus_register_unready_config_under_test',
    )

    class Api:
        set_calls = []

        @staticmethod
        def get_info():
            return SimpleNamespace(version='4.3.2.0')

        @staticmethod
        def get_prometheus_config():
            raise FakeObshellError('External.Component.Not.Ready')

        @classmethod
        def set_prometheus_config(cls, *args):
            cls.set_calls.append(args)

    context, stdio = _prometheus_register_context(SimpleNamespace(v1=Api()))

    assert module.register_to_obshell(context) is True
    assert Api.set_calls == []
    assert any('External.Component.Not.Ready' in message
               for message in stdio.warn_messages)


def test_prometheus_database_context_follows_dependency_graph():
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'prometheus' / '2.37.1' /
        'register_to_obshell.py',
        'prometheus_database_context_under_test',
    )
    oceanbase_namespace = object()
    seekdb_namespace = object()
    seekdb_config = SimpleNamespace(depends=[])
    obagent_config = SimpleNamespace(
        depends=['seekdb'],
        get_depend_cluster_config=lambda name: seekdb_config,
    )
    prometheus_config = SimpleNamespace(
        depends=['obagent'],
        get_depend_cluster_config=lambda name: obagent_config,
    )
    context = SimpleNamespace(
        cluster_config=prometheus_config,
        namespaces={
            'oceanbase': oceanbase_namespace,
            'seekdb': seekdb_namespace,
        },
    )

    assert module._database_context(context) == (
        'seekdb', seekdb_namespace)


def test_prometheus_registration_tries_next_server_after_connection_error():
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'prometheus' / '2.37.1' /
        'register_to_obshell.py',
        'prometheus_register_next_server_under_test',
    )
    attempts = []

    class Api:
        @staticmethod
        def get_info():
            if not attempts:
                attempts.append('connection-error')
                raise module.requests.exceptions.ConnectionError('unavailable')
            return SimpleNamespace(version='4.3.2.0')

        @staticmethod
        def get_prometheus_config():
            raise FakeObshellError('Config.NotFound')

        @staticmethod
        def set_prometheus_config(url, username, password):
            attempts.append(url)

    context, stdio = _prometheus_register_context(
        SimpleNamespace(v1=Api()),
        ips=['192.0.2.20', '192.0.2.21'],
    )

    assert module.register_to_obshell(context) is True
    assert attempts == [
        'connection-error', 'http://192.0.2.21:9090/']
    assert len(stdio.warn_messages) == 1


def test_prometheus_registration_supports_tls_without_authentication(monkeypatch):
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'prometheus' / '2.37.1' /
        'register_to_obshell.py',
        'prometheus_register_tls_no_auth_under_test',
    )
    monkeypatch.setattr(module.NetUtil, 'get_host_ip', lambda: '192.0.2.30')

    class Api:
        registered = None

        @staticmethod
        def get_info():
            return SimpleNamespace(version='4.3.2.0')

        @staticmethod
        def get_prometheus_config():
            raise FakeObshellError('Config.NotFound')

        @classmethod
        def set_prometheus_config(cls, url, username, password):
            cls.registered = (url, username, password)

    context, stdio = _prometheus_register_context(
        SimpleNamespace(v1=Api()),
        ips=['127.0.0.1'],
        server_config={
            'home_path': '/opt/prometheus',
            'port': 9090,
            'basic_auth_users': {},
            'web_config': {
                'tls_server_config': {'cert_file': '/path/to/cert'},
            },
        },
    )

    assert module.register_to_obshell(context) is True
    assert Api.registered == ('https://192.0.2.30:9090/', '', '')
    assert not stdio.warn_messages


def _alertmanager_register_context(obshell_client):
    server = FakePrometheusServer('192.0.2.40')
    stdio = FakePrometheusStdio()
    namespace = SimpleNamespace(
        get_variable=lambda name: (
            obshell_client if name == 'obshell_client' else None),
    )
    context = SimpleNamespace(
        cluster_config=FakePrometheusClusterConfig([server], {
            'home_path': '/opt/alertmanager',
            'port': 9093,
            'basic_auth_users': {'alert': 'alert-secret'},
            'web_config': {
                'tls_server_config': {'cert_file': '/path/to/cert'},
            },
        }),
        clients={server: SimpleNamespace(
            execute_command=lambda command: True,
        )},
        namespaces={'seekdb': namespace},
        stdio=stdio,
        return_true=lambda **kwargs: True,
    )
    return context, stdio


def test_seekdb_alertmanager_registration_accepts_direct_https_client():
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'alertmanager' / '0.28.1' /
        'register_to_obshell.py',
        'alertmanager_register_https_client_under_test',
    )

    class DirectApi:
        registered = None

        @staticmethod
        def get_info():
            return SimpleNamespace(version='4.3.2.0')

        @staticmethod
        def get_alertmanager_config():
            raise FakeObshellError('Config.NotFound')

        @classmethod
        def set_alertmanager_config(cls, url, username, password):
            cls.registered = (url, username, password)

    context, stdio = _alertmanager_register_context(DirectApi())

    assert module.register_to_obshell(context) is True
    assert DirectApi.registered == (
        'https://192.0.2.40:9093', 'alert', 'alert-secret')
    assert not stdio.warn_messages
    assert all('alert-secret' not in message
               for message in stdio.verbose_messages)


def test_seekdb_alertmanager_registration_preserves_unready_config():
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'alertmanager' / '0.28.1' /
        'register_to_obshell.py',
        'alertmanager_register_unready_config_under_test',
    )

    class DirectApi:
        set_calls = []

        @staticmethod
        def get_info():
            return SimpleNamespace(version='4.3.2.0')

        @staticmethod
        def get_alertmanager_config():
            raise FakeObshellError('External.Component.Not.Ready')

        @classmethod
        def set_alertmanager_config(cls, *args):
            cls.set_calls.append(args)

    context, stdio = _alertmanager_register_context(DirectApi())

    assert module.register_to_obshell(context) is True
    assert DirectApi.set_calls == []
    assert any('External.Component.Not.Ready' in message
               for message in stdio.warn_messages)


def test_prometheus_registration_reports_real_error():
    module = load_module(
        PROJECT_ROOT / 'plugins' / 'prometheus' / '2.37.1' /
        'register_to_obshell.py',
        'prometheus_register_error_under_test',
    )
    context, stdio = _prometheus_register_context(None)

    assert module.register_to_obshell(context) is True
    assert len(stdio.warn_messages) == 1
    assert 'OBShell client is unavailable' in stdio.warn_messages[0]
