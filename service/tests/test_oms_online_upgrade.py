# coding: utf-8

from __future__ import absolute_import, division, print_function

import importlib.util
import os
import subprocess
import types
import unittest
from unittest import mock


class CommandResult(object):

    def __init__(self, stdout='', success=True, stderr=''):
        self.stdout = stdout
        self.stderr = stderr
        self.success = success

    def __bool__(self):
        return self.success

    __nonzero__ = __bool__


class FakeServer(object):

    def __init__(self, ip='10.0.0.8'):
        self.ip = ip

    def __str__(self):
        return self.ip


class FakeClient(object):

    def __init__(self, fail_hot_upgrade=False, fail_copy_to_container=False,
                 fail_rollback=False, health_failures=0,
                 backup_complete=False, fail_health=False):
        self.config = types.SimpleNamespace(username='root')
        self.commands = []
        self.command_calls = []
        self.fail_hot_upgrade = fail_hot_upgrade
        self.fail_copy_to_container = fail_copy_to_container
        self.fail_rollback = fail_rollback
        self.health_failures = health_failures
        self.backup_complete = backup_complete
        self.fail_health = fail_health

    def execute_command(self, command, **kwargs):
        self.commands.append(command)
        self.command_calls.append((command, kwargs))
        if command.startswith('ls /tmp/oms-upgrade'):
            return CommandResult(success=False)
        if command.startswith('df -BG '):
            return CommandResult(stdout='30G')
        if command == 'command -v docker':
            return CommandResult(stdout='/usr/bin/docker\n')
        if ('timeout --signal=TERM' in command and
                'docker_copy_dumpfile_to_container.sh ' in command and
                self.fail_copy_to_container):
            return CommandResult(stderr='copy failed', success=False)
        if ('timeout --signal=TERM' in command and
                'docker_copy_dumpfile_rollback.sh ' in command and
                self.fail_rollback):
            return CommandResult(stderr='rollback failed', success=False)
        if ('docker exec ' in command and
                'test -f ' in command and
                '.obd_backup_complete' in command):
            return CommandResult(success=self.backup_complete)
        if 'docker_hot_update_init.sh' in command and self.fail_hot_upgrade:
            return CommandResult(stdout='init failed!', success=False)
        if 'curl ' in command and '/oms/health' in command:
            if self.fail_health:
                return CommandResult(stderr='health failed', success=False)
            if self.health_failures:
                self.health_failures -= 1
                return CommandResult(stderr='health failed', success=False)
        return CommandResult()

    def remote_client_get_tpy(self):
        return None


class FakeClusterConfig(object):

    def __init__(self, server):
        self.servers = [server]
        self.image_name = 'example/oms-ce'
        self._server = server

    def get_global_conf(self):
        return {'container_name': 'oms-test'}

    def get_server_conf(self, server):
        return {'mount_path': '/tmp/oms'}


class FakeStdio(object):

    def __init__(self):
        self.errors = []

    def start_loading(self, *args, **kwargs):
        return None

    def stop_loading(self, *args, **kwargs):
        return None

    def print(self, *args, **kwargs):
        return None

    def error(self, message):
        self.errors.append(message)


class FakePluginContext(object):

    def __init__(self, client):
        server = FakeServer()
        self.cluster_config = FakeClusterConfig(server)
        self.clients = {server: client}
        self.stdio = FakeStdio()

    def return_true(self):
        return True

    def return_false(self):
        return False


def load_online_upgrade_plugin():
    repository_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    path = os.path.join(repository_root, 'plugins', 'oms', '1.0.0', 'online_upgrade.py')
    spec = importlib.util.spec_from_file_location('oms_online_upgrade_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_upgrade_workflow():
    repository_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    path = os.path.join(repository_root, 'workflows', 'oms', '1.0.0', 'upgrade.py')
    spec = importlib.util.spec_from_file_location('oms_upgrade_workflow_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OmsOnlineUpgradeTest(unittest.TestCase):

    def setUp(self):
        self.plugin = load_online_upgrade_plugin()
        self.repository = types.SimpleNamespace(version='4.2.14')

    def run_upgrade(self, client, sudo_client=None, health_timeout=None,
                    external_health_fail=False):
        context = FakePluginContext(client)
        sudo_client = sudo_client or client
        external_health_response = types.SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {'data': {'healthy': True}},
        )
        if external_health_fail:
            external_health_patch = mock.patch.object(
                self.plugin.requests,
                'get',
                side_effect=self.plugin.requests.ConnectionError(
                    'external health failed'),
            )
        else:
            external_health_patch = mock.patch.object(
                self.plugin.requests,
                'get',
                return_value=external_health_response,
            )
        with mock.patch.object(self.plugin, 'get_root_permission_client', return_value=sudo_client), \
                mock.patch.object(self.plugin, 'get_sudo_prefix', return_value=''), \
                external_health_patch:
            if health_timeout is None:
                result = self.plugin.online_upgrade(
                    context,
                    self.repository,
                    default_oms_files_path='/tmp/oms-upgrade',
                )
            else:
                with mock.patch.object(
                        self.plugin, 'HEALTH_TIMEOUT_SECONDS', health_timeout):
                    result = self.plugin.online_upgrade(
                        context,
                        self.repository,
                        default_oms_files_path='/tmp/oms-upgrade',
                    )
        return result, context, sudo_client

    def test_online_upgrade_initializes_once_and_checks_fresh_marker(self):
        client = FakeClient()
        sudo_client = FakeClient()

        result, context, sudo_client = self.run_upgrade(client, sudo_client)

        self.assertTrue(result, context.stdio.errors)
        hot_upgrade_commands = [
            command for command in sudo_client.commands
            if 'docker_hot_update_init.sh' in command
        ]
        self.assertEqual(1, len(hot_upgrade_commands))
        command = hot_upgrade_commands[0]
        self.assertIn('rm -f /root/init_flag.txt', command)
        self.assertIn('test -s /root/init_flag.txt', command)
        self.assertFalse(any(
            'docker_hot_update_init.sh' in command for command in client.commands
        ))
        self.assertFalse(any(
            '/root/docker_init.sh' in command
            for command in client.commands + sudo_client.commands
        ))
        self.assertTrue(any(
            'docker run -d' in command and
            command.count('docker rm -f oms-config-tool') == 2
            for command in sudo_client.commands
        ))
        self.assertFalse(any(
            'docker run -d' in command for command in client.commands
        ))
        self.assertTrue(any(
            'curl ' in command and '/oms/health' in command
            for command in sudo_client.commands
        ))
        self.assertTrue(any(
            '.obd_backup_complete' in command and 'sed -i' in command and
            'sync_usr_local_runtime_from_dump' in command and
            '# update \\/root' in command
            for command in sudo_client.commands
        ))
        self.assertTrue(any(
            '.obd_runtime_backup' in command and 'original_paths.tar' in command
            for command in sudo_client.commands
        ))
        self.assertTrue(any(
            'tee /root/oms_script/.obd_bin/docker' in command and
            'OBD_OMS_UPGRADE_DEADLINE_EPOCH' in command
            for command in sudo_client.commands
        ))
        self.assertTrue(any(
            'curl ' in command and '/oms/health' in command and
            kwargs.get('timeout') == 10
            for command, kwargs in sudo_client.command_calls
        ))
        copy_calls = [
            (command, kwargs)
            for command, kwargs in sudo_client.command_calls
            if 'timeout --signal=TERM' in command and
            'docker_copy_dumpfile_to_container.sh' in command
        ]
        self.assertEqual(1, len(copy_calls))
        self.assertIn('timeout --signal=TERM --kill-after=30s 900s', copy_calls[0][0])
        self.assertIn('OBD_OMS_UPGRADE_DEADLINE_EPOCH', copy_calls[0][0])
        self.assertIn(' + 840 ', copy_calls[0][0])
        self.assertIn('PATH=/root/oms_script/.obd_bin:$PATH', copy_calls[0][0])
        self.assertEqual(960, copy_calls[0][1].get('timeout'))
        self.assertIn(
            'timeout --signal=TERM --kill-after=30s 840s',
            hot_upgrade_commands[0],
        )
        self.assertIn(
            'timeout --signal=TERM --kill-after=30s 900s',
            hot_upgrade_commands[0],
        )
        hot_upgrade_call = next(
            kwargs for command, kwargs in sudo_client.command_calls
            if 'docker_hot_update_init.sh' in command
        )
        self.assertEqual(960, hot_upgrade_call.get('timeout'))

    def test_online_upgrade_fails_when_init_marker_is_not_recreated(self):
        client = FakeClient()
        sudo_client = FakeClient(fail_hot_upgrade=True)

        result, context, sudo_client = self.run_upgrade(client, sudo_client)

        self.assertFalse(result)
        self.assertEqual(1, len(context.stdio.errors))
        self.assertIn('Hot update oms failed', context.stdio.errors[0])
        self.assertIn('container initialization log', context.stdio.errors[0])
        self.assertTrue(any(
            'timeout --signal=TERM' in command and
            'docker_copy_dumpfile_rollback.sh' in command
            for command in sudo_client.commands
        ))
        self.assertTrue(any(
            'supervisorctl start' in command for command in sudo_client.commands
        ))
        self.assertTrue(any(
            '.obd_runtime_backup' in command and
            'tar -xpf' in command
            for command in sudo_client.commands
        ))
        runtime_restore_call = next(
            (command, kwargs)
            for command, kwargs in sudo_client.command_calls
            if '.obd_runtime_backup' in command and 'tar -xpf' in command
        )
        self.assertIn(
            'timeout --signal=TERM --kill-after=30s 240s',
            runtime_restore_call[0],
        )
        self.assertIn(
            'timeout --signal=TERM --kill-after=30s 300s',
            runtime_restore_call[0],
        )
        self.assertEqual(360, runtime_restore_call[1].get('timeout'))

    def test_copy_failure_without_complete_backup_recovers_services_without_destructive_rollback(self):
        client = FakeClient()
        sudo_client = FakeClient(fail_copy_to_container=True)

        result, context, sudo_client = self.run_upgrade(client, sudo_client)

        self.assertFalse(result)
        self.assertTrue(any(
            'supervisorctl start' in command for command in sudo_client.commands
        ))
        self.assertFalse(any(
            'timeout --signal=TERM' in command and
            'docker_copy_dumpfile_rollback.sh' in command
            for command in sudo_client.commands
        ))

    def test_copy_failure_after_backup_completion_rolls_back_current_server(self):
        client = FakeClient()
        sudo_client = FakeClient(
            fail_copy_to_container=True,
            backup_complete=True,
        )

        result, context, sudo_client = self.run_upgrade(client, sudo_client)

        self.assertFalse(result)
        self.assertTrue(any(
            'test -f ' in command and '.obd_backup_complete' in command
            for command in sudo_client.commands
        ))
        self.assertTrue(any(
            'timeout --signal=TERM' in command and
            'docker_copy_dumpfile_rollback.sh' in command
            for command in sudo_client.commands
        ))
        self.assertTrue(any(
            'supervisorctl start' in command for command in sudo_client.commands
        ))

    def test_rollback_failure_still_attempts_service_recovery(self):
        client = FakeClient()
        sudo_client = FakeClient(fail_hot_upgrade=True, fail_rollback=True)

        result, context, sudo_client = self.run_upgrade(client, sudo_client)

        self.assertFalse(result)
        self.assertTrue(any(
            'timeout --signal=TERM' in command and
            'docker_copy_dumpfile_rollback.sh' in command
            for command in sudo_client.commands
        ))
        self.assertTrue(any(
            'supervisorctl start' in command for command in sudo_client.commands
        ))
        self.assertTrue(any(
            'Rollback failed servers' in error for error in context.stdio.errors
        ))

    def test_final_health_failure_rolls_back_modified_servers(self):
        client = FakeClient()
        sudo_client = FakeClient(fail_health=True)

        result, context, sudo_client = self.run_upgrade(
            client, sudo_client, health_timeout=0.01)

        self.assertFalse(result)
        self.assertTrue(any(
            'health check failed after online upgrade' in error
            for error in context.stdio.errors
        ))
        self.assertTrue(any(
            'timeout --signal=TERM' in command and
            'docker_copy_dumpfile_rollback.sh' in command
            for command in sudo_client.commands
        ))
        self.assertTrue(any(
            'supervisorctl start' in command for command in sudo_client.commands
        ))

    def test_external_health_failure_rolls_back_modified_servers(self):
        client = FakeClient()
        sudo_client = FakeClient()

        result, context, sudo_client = self.run_upgrade(
            client,
            sudo_client,
            health_timeout=0.01,
            external_health_fail=True,
        )

        self.assertFalse(result)
        self.assertTrue(any(
            'health check failed after online upgrade' in error
            for error in context.stdio.errors
        ))
        self.assertTrue(any(
            'timeout --signal=TERM' in command and
            'docker_copy_dumpfile_rollback.sh' in command
            for command in sudo_client.commands
        ))

    def test_hot_upgrade_command_rejects_script_false_success_and_removes_stale_marker(self):
        with self.subTest('marker removal failure stops before hot script'):
            with self._temporary_hot_upgrade_files() as paths:
                marker_path, hot_script_path = paths
                os.mkdir(marker_path)
                hot_script_sentinel = '%s.executed' % hot_script_path
                with open(hot_script_path, 'w') as script_file:
                    script_file.write('#!/usr/bin/env bash\n')
                    script_file.write("touch '%s'\n" % hot_script_sentinel)
                    script_file.write('exit 0\n')
                command = self.plugin.build_hot_upgrade_inner_command(
                    marker_path, hot_script_path)

                result = subprocess.run(
                    ['bash', '-c', command],
                    check=False,
                    env=dict(os.environ, LC_ALL='C'),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                self.assertNotEqual(0, result.returncode)
                self.assertFalse(os.path.exists(hot_script_sentinel))

        with self.subTest('hot script exits zero without recreating marker'):
            with self._temporary_hot_upgrade_files() as paths:
                marker_path, hot_script_path = paths
                with open(marker_path, 'w') as marker_file:
                    marker_file.write('stale success marker')
                command = self.plugin.build_hot_upgrade_inner_command(
                    marker_path, hot_script_path)

                result = subprocess.run(
                    ['bash', '-c', command],
                    check=False,
                    env=dict(os.environ, LC_ALL='C'),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                self.assertNotEqual(0, result.returncode)
                self.assertFalse(os.path.exists(marker_path))

        with self.subTest('hot script recreates a non-empty marker'):
            with self._temporary_hot_upgrade_files(write_marker=True) as paths:
                marker_path, hot_script_path = paths
                command = self.plugin.build_hot_upgrade_inner_command(
                    marker_path, hot_script_path)

                result = subprocess.run(
                    ['bash', '-c', command],
                    check=False,
                    env=dict(os.environ, LC_ALL='C'),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                self.assertEqual(0, result.returncode)

    def test_server_timeout_finishes_before_transport_timeout(self):
        command = self.plugin.build_server_timeout_command(
            'echo upgrade',
            timeout_seconds=12,
            termination_grace_seconds=3,
            sudo_prefix='sudo ',
        )

        self.assertEqual(
            "sudo timeout --signal=TERM --kill-after=3s 12s "
            "bash -c 'echo upgrade'",
            command,
        )
        self.assertEqual(
            45,
            self.plugin.command_transport_timeout(
                timeout_seconds=12,
                termination_grace_seconds=3,
            ),
        )

    def test_container_timeout_finishes_before_host_timeout(self):
        command = self.plugin.build_timed_container_command(
            'oms-test',
            'sleep 60',
            sudo_prefix='sudo ',
            timeout_seconds=300,
        )

        self.assertIn(
            'timeout --signal=TERM --kill-after=30s 240s', command)
        self.assertIn(
            'sudo timeout --signal=TERM --kill-after=30s 300s', command)
        self.assertEqual(240, self.plugin.container_command_timeout(300))

    def test_docker_wrapper_injects_container_side_timeout(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_path = os.path.join(temp_dir, 'docker')
            fake_docker_path = os.path.join(temp_dir, 'real-docker')
            args_path = os.path.join(temp_dir, 'args')
            with open(wrapper_path, 'w') as wrapper_file:
                wrapper_file.write(
                    self.plugin.build_docker_exec_timeout_wrapper())
            with open(fake_docker_path, 'w') as fake_docker_file:
                fake_docker_file.write(
                    '#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$ARGS_FILE"\n')
            os.chmod(wrapper_path, 0o755)
            os.chmod(fake_docker_path, 0o755)
            env = dict(os.environ)
            env.update({
                'ARGS_FILE': args_path,
                'OBD_REAL_DOCKER_BINARY': fake_docker_path,
                'OBD_OMS_UPGRADE_DEADLINE_EPOCH': '9999999999',
                'OBD_OMS_COMMAND_TERMINATION_GRACE_SECONDS': '3',
            })

            result = subprocess.run(
                [wrapper_path, 'exec', '-it', 'oms-test', 'sleep', '60'],
                check=False,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(0, result.returncode, result.stderr.decode())
            with open(args_path) as args_file:
                args = args_file.read().splitlines()
            self.assertEqual(['exec', 'oms-test'], args[:2])
            self.assertEqual('timeout', args[2])
            self.assertEqual('--signal=TERM', args[3])
            self.assertEqual('--kill-after=3s', args[4])
            self.assertTrue(args[5].endswith('s'))
            self.assertEqual(['sleep', '60'], args[6:])

    def test_docker_wrapper_removes_all_tty_flags(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_path = os.path.join(temp_dir, 'docker')
            fake_docker_path = os.path.join(temp_dir, 'real-docker')
            args_path = os.path.join(temp_dir, 'args')
            with open(wrapper_path, 'w') as wrapper_file:
                wrapper_file.write(
                    self.plugin.build_docker_exec_timeout_wrapper())
            with open(fake_docker_path, 'w') as fake_docker_file:
                fake_docker_file.write(
                    '#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$ARGS_FILE"\n')
            os.chmod(wrapper_path, 0o755)
            os.chmod(fake_docker_path, 0o755)
            env = dict(os.environ)
            env.update({
                'ARGS_FILE': args_path,
                'OBD_REAL_DOCKER_BINARY': fake_docker_path,
                'OBD_OMS_UPGRADE_DEADLINE_EPOCH': '9999999999',
            })

            result = subprocess.run(
                [wrapper_path, 'exec', '-dit', '--interactive', '-i=true',
                 '--interactive=false', '--tty', '-t=true', '--tty=false',
                 '--detach-keys', 'ctrl-x', 'oms-test', 'true'],
                check=False,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(0, result.returncode, result.stderr.decode())
            with open(args_path) as args_file:
                args = args_file.read().splitlines()
            self.assertEqual(
                ['exec', '-d', '--detach-keys', 'ctrl-x', 'oms-test'],
                args[:5],
            )
            self.assertNotIn('-i', args)
            self.assertNotIn('--interactive', args)
            self.assertNotIn('-i=true', args)
            self.assertNotIn('--interactive=false', args)
            self.assertNotIn('-t', args)
            self.assertNotIn('--tty', args)
            self.assertNotIn('-t=true', args)
            self.assertNotIn('--tty=false', args)

            short_option_cases = (
                (['-itw', '/root'], ['-w', '/root']),
                (['-itw/root'], ['-w/root']),
                (['-ituroot'], ['-uroot']),
                (['-ite', 'FOO=bar'], ['-e', 'FOO=bar']),
                (['-dit=true'], ['-d']),
                (['-dit=false'], ['-d']),
                (['-itd=false'], ['-d=false']),
                (['-it=1'], []),
                (['-dit=F'], ['-d']),
                (['-itd=T'], ['-d']),
                (['-dd=false'], ['-d', '-d=false']),
                (['-did=false'], ['-d', '-d=false']),
                (['-d', '-d=false'], ['-d', '-d=false']),
                (['--detach', '-d=false'], ['--detach', '-d=false']),
            )
            for original_options, rewritten_options in short_option_cases:
                with self.subTest(options=original_options):
                    result = subprocess.run(
                        [wrapper_path, 'exec'] + original_options +
                        ['oms-test', 'true'],
                        check=False,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    self.assertEqual(
                        0, result.returncode, result.stderr.decode())
                    with open(args_path) as args_file:
                        args = args_file.read().splitlines()
                    expected_prefix = (
                        ['exec'] + rewritten_options + ['oms-test'])
                    self.assertEqual(
                        expected_prefix, args[:len(expected_prefix)])

    def test_outer_upgrade_workflow_does_not_repeat_health_check(self):
        workflow_module = load_upgrade_workflow()
        calls = []
        workflow = types.SimpleNamespace(
            add=lambda *args: calls.append(args),
        )
        context = types.SimpleNamespace(return_true=lambda: True)

        result = workflow_module.upgrade(context, workflow)

        self.assertTrue(result)
        self.assertEqual([
            (
                workflow_module.STAGE_FIRST,
                'meta_backup',
                'generate_oms_config',
                'upgrade_pre',
            ),
        ], calls)

    class _temporary_hot_upgrade_files(object):

        def __init__(self, write_marker=False):
            import tempfile
            self.temp_dir = tempfile.TemporaryDirectory()
            self.write_marker = write_marker

        def __enter__(self):
            marker_path = os.path.join(self.temp_dir.name, 'init_flag.txt')
            hot_script_path = os.path.join(self.temp_dir.name, 'hot_upgrade.sh')
            with open(hot_script_path, 'w') as script_file:
                script_file.write('#!/usr/bin/env bash\n')
                if self.write_marker:
                    script_file.write("echo success > '%s'\n" % marker_path)
                script_file.write('exit 0\n')
            os.chmod(hot_script_path, 0o755)
            return marker_path, hot_script_path

        def __exit__(self, exc_type, exc_value, traceback):
            self.temp_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
