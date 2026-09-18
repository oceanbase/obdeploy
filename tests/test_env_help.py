# coding: utf-8

from __future__ import absolute_import, division, print_function

import os
import subprocess
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_help(tmp_path, *args):
    env = os.environ.copy()
    env['OBD_HOME'] = str(tmp_path)
    process = subprocess.Popen(
        [sys.executable, os.path.join(ROOT_DIR, '_cmd.py')] + list(args),
        cwd=ROOT_DIR,
        env=env,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    output, _ = process.communicate()
    return output


def test_env_help_lists_available_commands(tmp_path):
    output = _run_help(tmp_path, 'env', '--help')

    assert 'Available commands:' in output
    assert 'set            Set obd environment variable' in output
    assert 'unset          Unset obd environment variable' in output
    assert 'show           Show obd environment variables' in output
    assert 'clear          Clear obd environment variables' in output


def test_top_level_help_lists_env_command(tmp_path):
    output = _run_help(tmp_path, '--help')

    assert 'env            Environment variables for OBD' in output
