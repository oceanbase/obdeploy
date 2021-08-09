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
VERSION = '1.1.0'
REVISION = '<CID>'
BUILD_BRANCH = '<B_BRANCH>'
BUILD_TIME = '<B_TIME>'


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
        self.parser.add_option('-h', '--help', action='callback', callback=self._show_help, help='Show help and exit.')
        self.parser.add_option('-v', '--verbose', action='callback', callback=self._set_verbose, help='Activate verbose output.')

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
        if VERSION != version:
            obd_plugin_path = os.path.join(self.OBD_PATH, 'plugins')
            if DirectoryUtil.mkdir(self.OBD_PATH):
                root_plugin_path = '/usr/obd/plugins'
                if os.path.exists(root_plugin_path):
                    DirectoryUtil.copy(root_plugin_path, obd_plugin_path, ROOT_IO)
            obd_mirror_path = os.path.join(self.OBD_PATH, 'mirror')
            obd_remote_mirror_path = os.path.join(self.OBD_PATH, 'mirror/remote')
            if DirectoryUtil.mkdir(obd_mirror_path):
                root_remote_mirror = '/usr/obd/mirror/remote'
                if os.path.exists(root_remote_mirror):
                    DirectoryUtil.copy(root_remote_mirror, obd_remote_mirror_path, ROOT_IO)
            version_fobj.seek(0)
            version_fobj.truncate()
            version_fobj.write(VERSION)
            version_fobj.flush()
        version_fobj.close()

    def do_command(self):
        self.parse_command()
        self.init_home()
        trace_id = uuid()
        ret = False
        try:
            log_dir = os.path.join(self.OBD_PATH, 'log')
            DirectoryUtil.mkdir(log_dir)
            log_path = os.path.join(log_dir, 'obd')
            logger = Logger('obd')
            handler = handlers.TimedRotatingFileHandler(log_path, when='midnight', interval=1, backupCount=30)
            handler.setFormatter(logging.Formatter("[%%(asctime)s] [%s] [%%(levelname)s] %%(message)s" % trace_id, "%Y-%m-%d %H:%M:%S"))
            logger.addHandler(handler)
            ROOT_IO.trace_logger = logger
            obd = ObdHome(self.OBD_PATH, ROOT_IO)
            ROOT_IO.track_limit += 1
            ret = self._do_command(obd)
        except NotImplementedError:
            ROOT_IO.exception('command \'%s\' is not implemented' % self.prev_cmd)
        except IOError:
            ROOT_IO.exception('OBD is running')
        except SystemExit:
            pass
        except:
            ROOT_IO.exception('Running Error.')
        # if not ret:
        #     ROOT_IO.print('Trace ID: %s' % trace_id)
        return ret

    def _do_command(self, obd):
        raise NotImplementedError


class MajorCommand(BaseCommand):

    def __init__(self, name, summary):
        super(MajorCommand, self).__init__(name, summary)
        self.commands = {}

    def _mk_usage(self):
        if self.commands:
            usage = ['%s <command> [options]\n\nAvailable commands:\n' % self.prev_cmd]
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
            ROOT_IO.print('You need to give some commands.\n\nTry `obd --help` for more information.')
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
        super(MirrorCloneCommand, self).__init__('clone', 'Clone a RPM package to the local mirror repository.')
        self.parser.add_option('-f', '--force', action='store_true', help="Force clone, overwrite the mirror.")

    def init(self, cmd, args):
        super(MirrorCloneCommand, self).init(cmd, args)
        self.parser.set_usage('%s [mirror path] [options]' % self.prev_cmd)
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
        super(MirrorCreateCommand, self).__init__('create', 'Create a local mirror by using the local binary file.')
        self.parser.conflict_handler = 'resolve'
        self.parser.add_option('-n', '--name', type='string', help="Mirror name.")
        self.parser.add_option('-t', '--tag', type='string', help="Mirror tags. Multiple tags are separated with commas.")
        self.parser.add_option('-V', '--version', type='string', help="Mirror version.")
        self.parser.add_option('-p','--path', type='string', help="Mirror path. [./]", default='./')
        self.parser.add_option('-f', '--force', action='store_true', help="Force create, overwrite the mirror.")
        self.parser.conflict_handler = 'error'

    def _do_command(self, obd):
        return obd.create_repository(self.opts)


class MirrorListCommand(ObdCommand):

    def __init__(self):
        super(MirrorListCommand, self).__init__('list', 'List mirrors.')

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
                ['Name', 'Type', 'Update Time'], 
                lambda x: [x.name, x.mirror_type.value, time.strftime("%Y-%m-%d %H:%M", time.localtime(x.repo_age))],
                title='Mirror Repository List'
            )
        return True


class MirrorUpdateCommand(ObdCommand):

    def __init__(self):
        super(MirrorUpdateCommand, self).__init__('update', 'Update remote mirror information.')
    
    def _do_command(self, obd):
        success = True
        repos = obd.mirror_manager.get_remote_mirrors()
        for repo in repos:
            try:
                success = repo.update_mirror() and success
            except:
                success = False
                ROOT_IO.stop_loading('fail')
                ROOT_IO.exception('Fail to synchronize mirorr (%s)' % repo.name)
        return success


class MirrorMajorCommand(MajorCommand):

    def __init__(self):
        super(MirrorMajorCommand, self).__init__('mirror', 'Manage a component repository for OBD.')
        self.register_command(MirrorListCommand())
        self.register_command(MirrorCloneCommand())
        self.register_command(MirrorCreateCommand())
        self.register_command(MirrorUpdateCommand())


class RepositoryListCommand(ObdCommand):

    def __init__(self):
        super(RepositoryListCommand, self).__init__('list', 'List local repository.')

    def show_repo(self, repos, name=None):
        ROOT_IO.print_list(
            repos,
            ['name', 'version', 'release', 'arch', 'md5', 'tags'], 
            lambda x: [x.name, x.version, x.release, x.arch, x.md5, ', '.join(x.tags)],
            title='%s Local Repository List' % name if name else ''
        )

    def _do_command(self, obd):
        name = self.cmds[0] if self.cmds else None
        repos = obd.repository_manager.get_repositories_view(name)
        self.show_repo(repos, name)
        return True


class RepositoryMajorCommand(MajorCommand):

    def __init__(self):
        super(RepositoryMajorCommand, self).__init__('repo', 'Manage local repository for OBD.')
        self.register_command(RepositoryListCommand())


class ClusterMirrorCommand(ObdCommand):

    def init(self, cmd, args):
        super(ClusterMirrorCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> [options]' % self.prev_cmd)
        return self


class ClusterAutoDeployCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterAutoDeployCommand, self).__init__('autodeploy', 'Deploy a cluster automatically by using a simple configuration file.')
        self.parser.add_option('-c', '--config', type='string', help="Path to the configuration file.")
        self.parser.add_option('-f', '--force', action='store_true', help="Force autodeploy, overwrite the home_path.")
        self.parser.add_option('-U', '--unuselibrepo', '--ulp', action='store_true', help="Disable OBD from installing the libs mirror automatically.")
        self.parser.add_option('-A', '--auto-create-tenant', '--act', action='store_true', help="Disable OBD from creating a tenant named `test` by using all the available resource of the cluster.")
        self.parser.add_option('--force-delete', action='store_true', help="Force delete, delete the registered cluster.")
        self.parser.add_option('-s', '--strict-check', action='store_true', help="Throw errors instead of warnings when check fails.")

    def _do_command(self, obd):
        if self.cmds:
            name = self.cmds[0]
            if obd.genconfig(name, self.opts):
                self.opts.config = ''
                return obd.deploy_cluster(name, self.opts) and obd.start_cluster(name, self.cmds[1:], self.opts)
            return False        
        else:
            return self._show_help()


class ClusterDeployCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterDeployCommand, self).__init__('deploy', 'Deploy a cluster by using the current deploy configuration or a deploy yaml file.')
        self.parser.add_option('-c', '--config', type='string', help="Path to the configuration yaml file.")
        self.parser.add_option('-f', '--force', action='store_true', help="Force deploy, overwrite the home_path.", default=False)
        self.parser.add_option('-U', '--unuselibrepo', '--ulp', action='store_true', help="Disable OBD from installing the libs mirror automatically.")
        self.parser.add_option('-A', '--auto-create-tenant', '--act', action='store_false', help="Disable OBD from creating a tenant named `test` by using all the available resource of the cluster.")
        # self.parser.add_option('-F', '--fuzzymatch', action='store_true', help="enable fuzzy match when search package")

    def _do_command(self, obd):
        if self.cmds:
            return obd.deploy_cluster(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterStartCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterStartCommand, self).__init__('start', 'Start a deployed cluster.')
        self.parser.add_option('-s', '--servers', type='string', help="List the started servers. Multiple servers are separated with commas.")
        self.parser.add_option('-c', '--components', type='string', help="List the started components. Multiple components are separated with commas.")
        self.parser.add_option('-f', '--force-delete', action='store_true', help="Force delete, delete the registered cluster.")
        self.parser.add_option('-S', '--strict-check', action='store_true', help="Throw errors instead of warnings when check fails.")

    def _do_command(self, obd):
        if self.cmds:
            return obd.start_cluster(self.cmds[0], self.cmds[1:], self.opts)
        else:
            return self._show_help()


class ClusterStopCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterStopCommand, self).__init__('stop', 'Stop a started cluster.')
        self.parser.add_option('-s', '--servers', type='string', help="List the started servers. Multiple servers are separated with commas.")
        self.parser.add_option('-c', '--components', type='string', help="List the started components. Multiple components are separated with commas.")

    def _do_command(self, obd):
        if self.cmds:
            return obd.stop_cluster(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterDestroyCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterDestroyCommand, self).__init__('destroy', 'Destroy a started cluster.')
        self.parser.add_option('-f', '--force-kill', action='store_true', help="Force kill the running observer process in the working directory.")

    def _do_command(self, obd):
        if self.cmds:
            return obd.destroy_cluster(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterDisplayCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterDisplayCommand, self).__init__('display', 'Display the information for a cluster.')

    def _do_command(self, obd):
        if self.cmds:
            return obd.display_cluster(self.cmds[0])
        else:
            return self._show_help()


class ClusterRestartCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterRestartCommand, self).__init__('restart', 'Restart a started cluster.')
        self.parser.add_option('-s', '--servers', type='string', help="List the started servers. Multiple servers are separated with commas.")
        self.parser.add_option('-c', '--components', type='string', help="List the started components. Multiple components are separated with commas.")

    def _do_command(self, obd):
        if self.cmds:
            return obd.restart_cluster(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterRedeployCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterRedeployCommand, self).__init__('redeploy', 'Redeploy a started cluster.')
        self.parser.add_option('-f', '--force-kill', action='store_true', help="Force kill the running observer process in the working directory.")

    def _do_command(self, obd):
        if self.cmds:
            return obd.redeploy_cluster(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterReloadCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterReloadCommand, self).__init__('reload', 'Reload a started cluster.')

    def _do_command(self, obd):
        if self.cmds:
            return obd.reload_cluster(self.cmds[0])
        else:
            return self._show_help()


class ClusterListCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterListCommand, self).__init__('list', 'List all the deployments.')

    def _do_command(self, obd):
        if self.cmds:
            return self._show_help()
        else:
            return obd.list_deploy()


class ClusterEditConfigCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterEditConfigCommand, self).__init__('edit-config', 'Edit a deploy configuration file.')

    def _do_command(self, obd):
        if self.cmds:
            return obd.edit_deploy_config(self.cmds[0])
        else:
            return self._show_help()


class CLusterUpgradeCommand(ClusterMirrorCommand):

    def __init__(self):
        super(CLusterUpgradeCommand, self).__init__('upgrade', 'Upgrade a cluster.')
        self.parser.add_option('-f', '--force', action='store_true', help="Force upgrade.")
        self.parser.add_option('-c', '--components', type='string', help="List the updated components. Multiple components are separated with commas.")

    def _do_command(self, obd):
        if self.cmds:
            return obd.upgrade_cluster(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterTenantCreateCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantCreateCommand, self).__init__('create', 'Create a tenant.')
        self.parser.add_option('-n', '--tenant-name', type='string', help="The tenant name.")
        self.parser.add_option('--max-cpu', type='float', help="Unit max CPU number.")
        self.parser.add_option('--min-cpu', type='float', help="Unit min CPU number.")
        self.parser.add_option('--max-memory', type='int', help="Unit max memory size.")
        self.parser.add_option('--min-memory', type='int', help="Unit min memory size.")
        self.parser.add_option('--max-disk-size', type='int', help="Unit max disk size.")
        self.parser.add_option('--max-iops', type='int', help="Unit max iops number. [128]", default=128)
        self.parser.add_option('--min-iops', type='int', help="Unit min iops number.")
        self.parser.add_option('--max-session-num', type='int', help="Unit max session number. [64]", default=64)
        self.parser.add_option('--unit-num', type='int', help="Pool unit number.")
        self.parser.add_option('-z', '--zone-list', type='string', help="Tenant zone list.")
        self.parser.add_option('--charset', type='string', help="Tenant charset.")
        self.parser.add_option('--collate', type='string', help="Tenant COLLATE.")
        self.parser.add_option('--replica-num', type='int', help="tenant replica num")
        self.parser.add_option('--logonly-replica-num', type='int', help="Tenant logonly replica number.")
        self.parser.add_option('--tablegroup', type='string', help="Tenant tablegroup.")
        self.parser.add_option('--primary-zone', type='string', help="Tenant primary zone. [RANDOM]", default='RANDOM')
        self.parser.add_option('--locality', type='string', help="Tenant locality.")
        self.parser.add_option('-s', '--variables', type='string', help="Set the variables for the system tenant. [ob_tcp_invited_nodes='%']", default="ob_tcp_invited_nodes='%'")

    def _do_command(self, obd):
        if self.cmds:
            return obd.create_tenant(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterTenantDropCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantDropCommand, self).__init__('drop', 'Drop a tenant.')
        self.parser.add_option('-n', '--tenant-name', type='string', help="Tenant name.")

    def _do_command(self, obd):
        if self.cmds:
            return obd.drop_tenant(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterTenantCommand(MajorCommand):

    def __init__(self):
        super(ClusterTenantCommand, self).__init__('tenant', 'Create or drop a tenant.')
        self.register_command(ClusterTenantCreateCommand())
        self.register_command(ClusterTenantDropCommand())


class ClusterMajorCommand(MajorCommand):

    def __init__(self):
        super(ClusterMajorCommand, self).__init__('cluster', 'Deploy and manage a cluster.')
        self.register_command(ClusterAutoDeployCommand())
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
        self.register_command(CLusterUpgradeCommand())
        self.register_command(ClusterTenantCommand())


class TestMirrorCommand(ObdCommand):

    def init(self, cmd, args):
        super(TestMirrorCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> [options]' % self.prev_cmd)
        return self


class MySQLTestCommand(TestMirrorCommand):

    def __init__(self):
        super(MySQLTestCommand, self).__init__('mysqltest', 'Run mysqltest for a deployment.')
        self.parser.add_option('--component', type='string', help='The component for mysqltest.')
        self.parser.add_option('--test-server', type='string', help='The server for mysqltest. By default, the first root server in the component is the mysqltest server.')
        self.parser.add_option('--user', type='string', help='Username for a test. [admin]', default='admin')
        self.parser.add_option('--password', type='string', help='Password for a test. [admin]', default='admin')
        self.parser.add_option('--database', type='string', help='Database for a test. [test]', default='test')
        self.parser.add_option('--mysqltest-bin', type='string', help='Mysqltest bin path. [/u01/obclient/bin/mysqltest]', default='/u01/obclient/bin/mysqltest')
        self.parser.add_option('--obclient-bin', type='string', help='OBClient bin path. [obclient]', default='obclient')
        self.parser.add_option('--test-dir', type='string', help='Test case file directory. [./mysql_test/t]', default='./mysql_test/t')
        self.parser.add_option('--result-dir', type='string', help='Result case file directory. [./mysql_test/r]', default='./mysql_test/r')
        self.parser.add_option('--record-dir', type='string', help='The directory of the result file for mysqltest.')
        self.parser.add_option('--log-dir', type='string', help='The log file directory. [./log]', default='./log')
        self.parser.add_option('--tmp-dir', type='string', help='Temporary directory for mysqltest. [./tmp]', default='./tmp')
        self.parser.add_option('--var-dir', type='string', help='Var directory to use when run mysqltest. [./var]', default='./var')
        self.parser.add_option('--test-set', type='string', help='test list, use `,` interval')
        self.parser.add_option('--test-pattern', type='string', help='Pattern for test file.')
        self.parser.add_option('--suite', type='string', help='Suite list.Multiple suites are separated with commas.')
        self.parser.add_option('--suite-dir', type='string', help='Suite case directory. [./mysql_test/test_suite]', default='./mysql_test/test_suite')
        self.parser.add_option('--init-sql-dir', type='string', help='Initiate sql directory. [../]', default='../')
        self.parser.add_option('--init-sql-files', type='string', help='Initiate sql file list.Multiple files are separated with commas.')
        self.parser.add_option('--need-init', action='store_true', help='Execute init sql file.', default=False)
        self.parser.add_option('--auto-retry', action='store_true', help='Auto retry when fails.', default=False)
        self.parser.add_option('--all', action='store_true', help='Run all suite-dir cases.', default=False)
        self.parser.add_option('--psmall', action='store_true', help='Run psmall cases.', default=False)
        # self.parser.add_option('--java', action='store_true', help='use java sdk', default=False)

    def _do_command(self, obd):
        if self.cmds:
            return obd.mysqltest(self.cmds[0], self.opts)
        else:
            return self._show_help()


class SysBenchCommand(TestMirrorCommand):

    def __init__(self):
        super(SysBenchCommand, self).__init__('sysbench', 'Run sysbench for a deployment.')
        self.parser.add_option('--component', type='string', help='The component for mysqltest.')
        self.parser.add_option('--test-server', type='string', help='The server for mysqltest. By default, the first root server in the component is the mysqltest server.')
        self.parser.add_option('--user', type='string', help='Username for a test. [root]', default='root')
        self.parser.add_option('--password', type='string', help='Password for a test.')
        self.parser.add_option('--tenant', type='string', help='Tenant for a test. [test]', default='test')
        self.parser.add_option('--database', type='string', help='Database for a test. [test]', default='test')
        self.parser.add_option('--obclient-bin', type='string', help='OBClient bin path. [obclient]', default='obclient')
        self.parser.add_option('--sysbench-bin', type='string', help='Sysbench bin path. [sysbench]', default='sysbench')
        self.parser.add_option('--script-name', type='string', help='Sysbench lua script file name. [point_select]', default='point_select.lua')
        self.parser.add_option('--sysbench-script-dir', type='string', help='The directory of the sysbench lua script file. [/usr/sysbench/share/sysbench]', default='/usr/sysbench/share/sysbench')
        self.parser.add_option('--table-size', type='int', help='Number of data initialized per table. [20000]', default=20000)
        self.parser.add_option('--tables', type='int', help='Number of initialization tables. [30]', default=30)
        self.parser.add_option('--threads', type='int', help='Number of threads to use. [32]', default=16)
        self.parser.add_option('--time', type='int', help='Limit for total execution time in seconds. [60]', default=60)
        self.parser.add_option('--interval', type='int', help='Periodically report intermediate statistics with a specified time interval in seconds. 0 disables intermediate reports. [10]', default=10)
        self.parser.add_option('--events', type='int', help='Limit for total number of events.')
        self.parser.add_option('--rand-type', type='string', help='Random numbers distribution {uniform,gaussian,special,pareto}.')
        self.parser.add_option('--percentile', type='int', help='Percentile to calculate in latency statistics. Available values are 1-100. 0 means to disable percentile calculations.')
        self.parser.add_option('--skip-trx', dest='{on/off}', type='string', help='Open or close a transaction in a read-only test. ')
        self.parser.add_option('-O', '--optimization', dest='{0/1}', type='int', help='optimization', default=1)

    def _do_command(self, obd):
        if self.cmds:
            return obd.sysbench(self.cmds[0], self.opts)
        else:
            return self._show_help()


class TestMajorCommand(MajorCommand):

    def __init__(self):
        super(TestMajorCommand, self).__init__('test', 'Run test for a running deploy deployment.')
        self.register_command(MySQLTestCommand())
        self.register_command(SysBenchCommand())


class BenchMajorCommand(MajorCommand):

    def __init__(self):
        super(BenchMajorCommand, self).__init__('bench', '')


class UpdateCommand(ObdCommand):

    def __init__(self):
        super(UpdateCommand, self).__init__('update', 'Update OBD.')

    def do_command(self):
        if os.getuid() != 0:
            ROOT_IO.error('To update OBD, you must be a root user.')
            return False
        return super(UpdateCommand, self).do_command()

    def _do_command(self, obd):
        return obd.update_obd(VERSION)


class MainCommand(MajorCommand):

    def __init__(self):
        super(MainCommand, self).__init__('obd', '')
        self.register_command(MirrorMajorCommand())
        self.register_command(ClusterMajorCommand())
        self.register_command(RepositoryMajorCommand())
        self.register_command(TestMajorCommand())
        self.register_command(UpdateCommand())
        self.parser.version = '''OceanBase Deploy: %s
REVISION: %s
BUILD_BRANCH: %s
BUILD_TIME: %s
Copyright (C) 2021 OceanBase
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.''' % (VERSION, REVISION, BUILD_BRANCH, BUILD_TIME)
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

