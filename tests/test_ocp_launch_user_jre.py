import importlib.util
from pathlib import Path

from _plugin import InstallPlugin


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'general_install_repo', ROOT / 'plugins/general/0.1/install_repo.py'
)
INSTALL_REPO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALL_REPO)


def load_start_plugin(version):
    spec = importlib.util.spec_from_file_location(
        'ocp_start_{}'.format(version.replace('.', '_')),
        ROOT / 'plugins/ocp-server' / version / 'start.py',
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_jre_is_copied_when_launch_user_differs_from_deploy_user():
    command = INSTALL_REPO.get_install_command(
        InstallPlugin.InstallMethod.ANY, True, 'admin', 'root'
    )

    assert command == 'cp -f'


def test_jre_remains_linked_for_same_user():
    command = INSTALL_REPO.get_install_command(
        InstallPlugin.InstallMethod.ANY, True, 'admin', 'admin'
    )

    assert command == 'ln -fs'


def test_non_jre_dependency_keeps_declared_link_mode():
    command = INSTALL_REPO.get_install_command(
        InstallPlugin.InstallMethod.ANY, False, 'admin', 'root'
    )

    assert command == 'ln -fs'


def test_explicit_copy_mode_is_preserved():
    command = INSTALL_REPO.get_install_command(
        InstallPlugin.InstallMethod.CP, False, '', 'root'
    )

    assert command == 'cp -f'


def test_server_level_launch_user_is_used_for_jre_install():
    class ClusterConfig:
        def get_global_conf(self):
            return {}

        def get_server_conf(self, server):
            assert server == '127.0.0.1'
            return {'launch_user': 'admin'}

    config = ClusterConfig()
    launch_user = INSTALL_REPO.get_server_launch_user(config, '127.0.0.1')
    command = INSTALL_REPO.get_install_command(
        InstallPlugin.InstallMethod.ANY,
        True,
        launch_user,
        'root',
    )

    assert launch_user == 'admin'
    assert command == 'cp -f'


def test_ocp_versions_use_instance_java_for_a_different_launch_user():
    for version in ('4.2.1', '4.4.0'):
        start_plugin = load_start_plugin(version)

        assert start_plugin.resolve_java_bin('java', '/home/admin/ocp', 'admin') == (
            '/home/admin/ocp/jre/bin/java'
        )


def test_custom_java_path_is_preserved():
    for version in ('4.2.1', '4.4.0'):
        start_plugin = load_start_plugin(version)

        assert start_plugin.resolve_java_bin(
            '/usr/local/java/bin/java', '/home/admin/ocp', 'admin'
        ) == '/usr/local/java/bin/java'


def test_ocp_start_output_is_not_discarded():
    for version in ('4.2.1', '4.4.0'):
        source = (ROOT / 'plugins/ocp-server' / version / 'start.py').read_text()

        assert "os.path.join(log_dir, 'ocp-start.log')" in source
        assert '> /dev/null 2>&1 &' not in source


class FakeClient:
    class Config:
        username = 'root'

    config = Config()

    def __init__(self, fail_on=None):
        self.commands = []
        self.env = {}
        self.fail_on = fail_on

    def add_env(self, key, value, *args):
        self.env[key] = value

    def execute_command(self, command):
        self.commands.append(command)
        return not (self.fail_on and self.fail_on in command)


def jre_dir_item():
    return InstallPlugin.FileItem(
        'jre', '', InstallPlugin.FileItemType.DIR,
        InstallPlugin.InstallMethod.ANY, None,
    )


def test_cross_user_jre_install_executes_copy_and_chown():
    client = FakeClient()

    result = INSTALL_REPO.install_repository_files(
        client, [jre_dir_item()], '/root/.obd/repository/jre',
        '/home/admin/ocp/jre', True, 'admin', 'root',
    )

    assert result is True
    assert any('cp -f ${source}/{} ${target}/{}' in cmd for cmd in client.commands)
    assert 'sudo chown -R admin ${_home_path}' in client.commands


def test_same_user_jre_install_keeps_links():
    client = FakeClient()
    client.config.username = 'admin'

    result = INSTALL_REPO.install_repository_files(
        client, [jre_dir_item()], '/home/admin/.obd/repository/jre',
        '/home/admin/ocp/jre', True, 'admin', 'admin',
    )

    assert result is True
    assert any('ln -fs ${source}/{} ${target}/{}' in cmd for cmd in client.commands)


def test_jre_copy_failure_is_propagated():
    client = FakeClient(fail_on='cp -f')

    result = INSTALL_REPO.install_repository_files(
        client, [jre_dir_item()], '/root/.obd/repository/jre',
        '/home/admin/ocp/jre', True, 'admin', 'root',
    )

    assert result is False
