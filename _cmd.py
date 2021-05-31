# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.


from __future__ import absolute_import, division, print_function

import os
import sys
import time
import logging
from logging import handlers
from uuid import uuid1 as uuid
from optparse import OptionParser,OptionGroup

from core import ObdHome
from _stdio import IO
from log import Logger
from tool import DirectoryUtil, FileUtil


ROOT_IO = IO(1)
VERSION = '1.0.0'


class BaseCommand(object):

    def __init__(self, name, summary):
        self.name = name
        self.summary = summary
        self.args = []
        self.cmds = []
        self.opts = {}
        self.prev_cmd = ''
        self.is_init = False
        self.parser = OptionParser(add_help_option=False)
        self.parser.add_option('-h', '--help', action='callback', callback=self._show_help, help='show this help message and exit')
        self.parser.add_option('-v', '--verbose', action='callback', callback=self._set_verbose, help='verbose operation')

    def _set_verbose(self, *args, **kwargs):
        ROOT_IO.set_verbose_level(0xfffffff)

    def init(self, cmd, args):
        if self.is_init is False:
            self.prev_cmd = cmd
            self.args = args
            self.is_init = True
            self.parser.prog = self.prev_cmd
            option_list = self.parser.option_list[2:]
            option_list.append(self.parser.option_list[0])
            option_list.append(self.parser.option_list[1])
            self.parser.option_list = option_list
        return self

    def parse_command(self):
        self.opts, self.cmds = self.parser.parse_args(self.args)
        return self.opts

    def do_command(self):
        raise NotImplementedError

    def _show_help(self, *args, **kwargs):
        ROOT_IO.print(self._mk_usage())
        self.parser.exit(1)

    def _mk_usage(self):
        return self.parser.format_help()


class ObdCommand(BaseCommand):

    OBD_PATH = os.path.join(os.environ.get('OBD_HOME', os.getenv('HOME')), '.obd')

    def init_home(self):
        version_path = os.path.join(self.OBD_PATH, 'version')
        need_update = True
        version_fobj = FileUtil.open(version_path, 'a+', stdio=ROOT_IO)
        version_fobj.seek(0)
        version = version_fobj.read()
        if VERSION.split('.') > version.split('.'):
            obd_plugin_path = os.path.join(self.OBD_PATH, 'plugins')
            if DirectoryUtil.mkdir(self.OBD_PATH):
                root_plugin_path = '/usr/obd/plugins'
                if os.path.exists(root_plugin_path):
                    ROOT_IO.verbose('copy %s to %s' % (root_plugin_path, obd_plugin_path))
                    DirectoryUtil.copy(root_plugin_path, obd_plugin_path, ROOT_IO)
            obd_mirror_path = os.path.join(self.OBD_PATH, 'mirror')
            obd_remote_mirror_path = os.path.join(self.OBD_PATH, 'mirror/remote')
            if DirectoryUtil.mkdir(obd_mirror_path):
                root_remote_mirror = '/usr/obd/mirror/remote'
                if os.path.exists(root_remote_mirror):
                    ROOT_IO.verbose('copy %s to %s' % (root_remote_mirror, obd_remote_mirror_path))
                    DirectoryUtil.copy(root_remote_mirror, obd_remote_mirror_path, ROOT_IO)
            version_fobj.seek(0)
            version_fobj.truncate()
            version_fobj.write(VERSION)
            version_fobj.flush()
        version_fobj.close()

    def do_command(self):
        self.parse_command()
        self.init_home()
        try:
            log_dir = os.path.join(self.OBD_PATH, 'log')
            DirectoryUtil.mkdir(log_dir)
            log_path = os.path.join(log_dir, 'obd')
            logger = Logger('obd')
            handler = handlers.TimedRotatingFileHandler(log_path, when='midnight', interval=1, backupCount=30)
            handler.setFormatter(logging.Formatter("[%%(asctime)s] [%s] [%%(levelname)s] %%(message)s" % uuid(), "%Y-%m-%d %H:%M:%S"))
            logger.addHandler(handler)
            ROOT_IO.trace_logger = logger
            obd = ObdHome(self.OBD_PATH, ROOT_IO)
            ROOT_IO.track_limit += 1
            return self._do_command(obd)
        except NotImplementedError:
            ROOT_IO.exception('command \'%s\' is not implemented' % self.prev_cmd)
        except IOError:
            ROOT_IO.exception('obd is running')
        except SystemExit:
            pass
        except:
            ROOT_IO.exception('Run Error')
        return False

    def _do_command(self, obd):
        raise NotImplementedError


class MajorCommand(BaseCommand):

    def __init__(self, name, summary):
        super(MajorCommand, self).__init__(name, summary)
        self.commands = {}

    def _mk_usage(self):
        if self.commands:
            usage = ['%s <command> [options]\n\nAvailable Commands:\n' % self.prev_cmd]
            commands = [x for x in self.commands.values() if not (hasattr(x, 'hidden') and x.hidden)]
            commands.sort(key=lambda x: x.name)
            for command in commands:
                usage.append("%-14s %s\n" % (command.name, command.summary))
            self.parser.set_usage('\n'.join(usage))
        return super(MajorCommand, self)._mk_usage()

    def do_command(self):
        if not self.is_init:
            ROOT_IO.error('%s command not init' % self.prev_cmd)
            raise SystemExit('command not init')
        if len(self.args) < 1:
            ROOT_IO.print('You need to give some command')
            self._show_help()
            return False
        base, args = self.args[0], self.args[1:]
        if base not in self.commands:
            self.parse_command()
            self._show_help()
            return False
        cmd = '%s %s' % (self.prev_cmd, base)
        ROOT_IO.track_limit += 1
        return self.commands[base].init(cmd, args).do_command()
        
    def register_command(self, command):
        self.commands[command.name] = command


class MirrorCloneCommand(ObdCommand):

    def __init__(self):
        super(MirrorCloneCommand, self).__init__('clone', 'clone remote mirror or local rpmfile as mirror.')
        self.parser.add_option('-f', '--force', action='store_true', help="overwrite when mirror exist")

    def init(self, cmd, args):
        super(MirrorCloneCommand, self).init(cmd, args)
        self.parser.set_usage('%s [mirror source] [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if self.cmds:
            for src in self.cmds:
                if not obd.add_mirror(src, self.opts):
                    return False
            return True
        else:
            return self._show_help()


class MirrorCreateCommand(ObdCommand):

    def __init__(self):
        super(MirrorCreateCommand, self).__init__('create', 'create a local mirror by local binary file')
        self.parser.conflict_handler = 'resolve'
        self.parser.add_option('-n', '--name', type='string', help="mirror's name")
        self.parser.add_option('-t', '--tag', type='string', help="mirror's tag, use `,` interval")
        self.parser.add_option('-n', '--name', type='string', help="mirror's name")
        self.parser.add_option('-V', '--version', type='string', help="mirror's version")
        self.parser.add_option('-p','--path', type='string', help="mirror's path", default='./')
        self.parser.add_option('-f', '--force', action='store_true', help="overwrite when mirror exist")
        self.parser.conflict_handler = 'error'

    def _do_command(self, obd):
        return obd.create_repository(self.opts)


class MirrorListCommand(ObdCommand):

    def __init__(self):
        super(MirrorListCommand, self).__init__('list', 'list mirror')

    def show_pkg(self, name, pkgs):
        ROOT_IO.print_list(
            pkgs, 
            ['name', 'version', 'release', 'arch', 'md5'], 
            lambda x: [x.name, x.version, x.release, x.arch, x.md5],
            title='%s Package List' % name
        )

    def _do_command(self, obd):
        if self.cmds:
            name = self.cmds[0]
            if name == 'local':
                pkgs = obd.mirror_manager.local_mirror.get_all_pkg_info()
                self.show_pkg(name, pkgs)
                return True
            else:
                repos = obd.mirror_manager.get_mirrors()
                for repo in repos:
                    if repo.name == name:
                        pkgs = repo.get_all_pkg_info()
                        self.show_pkg(name, pkgs)
                        return True
                ROOT_IO.error('No such mirror repository: %s' % name)
                return False
        else:
            repos = obd.mirror_manager.get_mirrors()
            ROOT_IO.print_list(
                repos, 
                ['name', 'type', 'update time'], 
                lambda x: [x.name, x.mirror_type.value, time.strftime("%Y-%m-%d %H:%M", time.localtime(x.repo_age))],
                title='Mirror Repository List'
            )
        return True


class MirrorUpdateCommand(ObdCommand):

    def __init__(self):
        super(MirrorUpdateCommand, self).__init__('update', 'update remote mirror info')
    
    def _do_command(self, obd):
        success = True
        repos = obd.mirror_manager.get_remote_mirrors()
        for repo in repos:
            try:
                success = repo.update_mirror() and success
            except:
                success = False
                ROOT_IO.stop_loading('fail')
                ROOT_IO.exception('fail to synchronize mirorr (%s)' % repo.name)
        return success


class MirrorMajorCommand(MajorCommand):

    def __init__(self):
        super(MirrorMajorCommand, self).__init__('mirror', 'Manage a component repository for obd.')
        self.register_command(MirrorListCommand())
        self.register_command(MirrorCloneCommand())
        self.register_command(MirrorCreateCommand())
        self.register_command(MirrorUpdateCommand())


class ClusterMirrorCommand(ObdCommand):

    def init(self, cmd, args):
        super(ClusterMirrorCommand, self).init(cmd, args)
        self.parser.set_usage('%s [cluster name] [options]' % self.prev_cmd)
        return self


class ClusterDeployCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterDeployCommand, self).__init__('deploy', 'use current deploy config or an deploy yaml file to deploy a cluster')
        self.parser.add_option('-c', '--config', type='string', help="cluster config yaml path")
        self.parser.add_option('-f', '--force', action='store_true', help="remove all when home_path is not empty", default=False)
        self.parser.add_option('-U', '--unuselibrepo', '--ulp', action='store_true', help="obd will not install libs when library is not found")
        # self.parser.add_option('-F', '--fuzzymatch', action='store_true', help="enable fuzzy match when search package")

    def _do_command(self, obd):
        if self.cmds:
            return obd.deploy_cluster(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterStartCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterStartCommand, self).__init__('start', 'start a cluster had deployed')
        self.parser.add_option('-f', '--force-delete', action='store_true', help="cleanup when cluster had registered")
        self.parser.add_option('-s', '--strict-check', action='store_true', help="prompt for errors instead of warnings when the check fails")

    def _do_command(self, obd):
        if self.cmds:
            return obd.start_cluster(self.cmds[0], self.cmds[1:], self.opts)
        else:
            return self._show_help()


class ClusterStopCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterStopCommand, self).__init__('stop', 'stop a cluster had started')

    def _do_command(self, obd):
        if self.cmds:
            return obd.stop_cluster(self.cmds[0])
        else:
            return self._show_help()


class ClusterDestroyCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterDestroyCommand, self).__init__('destroy', 'start a cluster had deployed')
        self.parser.add_option('-f', '--force-kill', action='store_true', help="force kill when observer is running")

    def _do_command(self, obd):
        if self.cmds:
            return obd.destroy_cluster(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterDisplayCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterDisplayCommand, self).__init__('display', 'display a cluster info')

    def _do_command(self, obd):
        if self.cmds:
            return obd.display_cluster(self.cmds[0])
        else:
            return self._show_help()


class ClusterRestartCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterRestartCommand, self).__init__('restart', 'restart a cluster had started')

    def _do_command(self, obd):
        if self.cmds:
            return obd.restart_cluster(self.cmds[0])
        else:
            return self._show_help()


class ClusterRedeployCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterRedeployCommand, self).__init__('redeploy', 'redeploy a cluster had started')

    def _do_command(self, obd):
        if self.cmds:
            return obd.redeploy_cluster(self.cmds[0])
        else:
            return self._show_help()


class ClusterReloadCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterReloadCommand, self).__init__('reload', 'reload a cluster had started')

    def _do_command(self, obd):
        if self.cmds:
            return obd.reload_cluster(self.cmds[0])
        else:
            return self._show_help()


class ClusterListCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterListCommand, self).__init__('list', 'show all deploy')

    def _do_command(self, obd):
        if self.cmds:
            return self._show_help()
        else:
            return obd.list_deploy()


class ClusterEditConfigCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterEditConfigCommand, self).__init__('edit-config', 'edit a deploy config')

    def _do_command(self, obd):
        if self.cmds:
            return obd.edit_deploy_config(self.cmds[0])
        else:
            return self._show_help()


class ClusterMajorCommand(MajorCommand):

    def __init__(self):
        super(ClusterMajorCommand, self).__init__('cluster', 'deploy and manager cluster')
        self.register_command(ClusterDeployCommand())
        self.register_command(ClusterStartCommand())
        self.register_command(ClusterStopCommand())
        self.register_command(ClusterDestroyCommand())
        self.register_command(ClusterDisplayCommand())
        self.register_command(ClusterListCommand())
        self.register_command(ClusterRestartCommand())
        self.register_command(ClusterRedeployCommand())
        self.register_command(ClusterEditConfigCommand())
        self.register_command(ClusterReloadCommand())


class TestMirrorCommand(ObdCommand):

    def init(self, cmd, args):
        super(TestMirrorCommand, self).init(cmd, args)
        self.parser.set_usage('%s [cluster name] [options]' % self.prev_cmd)
        return self


class MySQLTestCommand(TestMirrorCommand):

    def __init__(self):
        super(MySQLTestCommand, self).__init__('mysqltest', 'run mysqltest for a deploy')
        self.parser.add_option('--component', type='string', help='the component for mysqltest')
        self.parser.add_option('--test-server', type='string', help='the server for mysqltest, default the first root server in the component')
        self.parser.add_option('--user', type='string', help='username for test', default='admin')
        self.parser.add_option('--password', type='string', help='password for test', default='admin')
        self.parser.add_option('--database', type='string', help='database for test', default='test')
        self.parser.add_option('--mysqltest-bin', type='string', help='mysqltest bin path', default='/u01/obclient/bin/mysqltest')
        self.parser.add_option('--obclient-bin', type='string', help='obclient bin path', default='obclient')
        self.parser.add_option('--test-dir', type='string', help='test case file directory', default='./mysql_test/t')
        self.parser.add_option('--result-dir', type='string', help='result case file directory', default='./mysql_test/r')
        self.parser.add_option('--record-dir', type='string', help='the directory of the result file for mysqltest')
        self.parser.add_option('--log-dir', type='string', help='the directory of the log file', default='./log')
        self.parser.add_option('--tmp-dir', type='string', help='tmp dir to use when run mysqltest', default='./tmp')
        self.parser.add_option('--var-dir', type='string', help='var dir to use when run mysqltest', default='./var')
        self.parser.add_option('--test-set', type='string', help='test list, use `,` interval')
        self.parser.add_option('--test-pattern', type='string', help='pattern for test file')
        self.parser.add_option('--suite', type='string', help='suite list, use `,` interval')
        self.parser.add_option('--suite-dir', type='string', help='suite case directory', default='./mysql_test/test_suite')
        self.parser.add_option('--init-sql-dir', type='string', help='init sql directory', default='../')
        self.parser.add_option('--init-sql-files', type='string', help='init sql file list, use `,` interval')
        self.parser.add_option('--need-init', action='store_true', help='exec init sql', default=False)
        self.parser.add_option('--auto-retry', action='store_true', help='auto retry when failed', default=False)
        self.parser.add_option('--all', action='store_true', help='run all suite-dir case', default=False)
        self.parser.add_option('--psmall', action='store_true', help='run psmall case', default=False)
        # self.parser.add_option('--java', action='store_true', help='use java sdk', default=False)

    def _do_command(self, obd):
        if self.cmds:
            return obd.mysqltest(self.cmds[0], self.opts)
        else:
            return self._show_help()


class TestMajorCommand(MajorCommand):

    def __init__(self):
        super(TestMajorCommand, self).__init__('test', 'run test for a running deploy')
        self.register_command(MySQLTestCommand())


class BenchMajorCommand(MajorCommand):

    def __init__(self):
        super(BenchMajorCommand, self).__init__('bench', '')


class MainCommand(MajorCommand):

    def __init__(self):
        super(MainCommand, self).__init__('obd', '')
        self.register_command(MirrorMajorCommand())
        self.register_command(ClusterMajorCommand())
        self.register_command(TestMajorCommand())
        self.parser.version = '''OceanBase Deploy: %s
Copyright (C) 2021 OceanBase
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.''' % (VERSION)
        self.parser._add_version_option()

if __name__ == '__main__':
    defaultencoding = 'utf-8'
    if sys.getdefaultencoding() != defaultencoding:
        try:
            from imp import reload
        except:
            pass
        reload(sys)
        sys.setdefaultencoding(defaultencoding)
    sys.path.append('/usr/obd/lib/site-packages')
    ROOT_IO.track_limit += 2
    if MainCommand().init('obd', sys.argv[1:]).do_command():
        ROOT_IO.exit(0)
    ROOT_IO.exit(1)

