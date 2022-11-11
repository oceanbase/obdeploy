
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
import textwrap
from logging import handlers
from uuid import uuid1 as uuid
from optparse import OptionParser, OptionGroup, BadOptionError, Option, IndentedHelpFormatter

from core import ObdHome
from _stdio import IO
from log import Logger
from tool import DirectoryUtil, FileUtil, COMMAND_ENV
from _errno import DOC_LINK_MSG, LockError
from _environ import ENV_DEV_MODE


ROOT_IO = IO(1)
VERSION = '<VERSION>'
REVISION = '<CID>'
BUILD_BRANCH = '<B_BRANCH>'
BUILD_TIME = '<B_TIME>'
DEBUG = True if '<DEBUG>' else False

CONST_OBD_HOME = "OBD_HOME"
CONST_OBD_INSTALL_PRE = "OBD_INSTALL_PRE"
FORBIDDEN_VARS = (CONST_OBD_HOME, CONST_OBD_INSTALL_PRE)

OBD_HOME_PATH = os.path.join(os.environ.get(CONST_OBD_HOME, os.getenv('HOME')), '.obd')
COMMAND_ENV.load(os.path.join(OBD_HOME_PATH, '.obd_environ'), ROOT_IO)


class OptionHelpFormatter(IndentedHelpFormatter):

    def format_option(self, option):
        result = []
        opts = self.option_strings[option]
        opt_width = self.help_position - self.current_indent - 2
        if len(opts) > opt_width:
            opts = "%*s%s\n" % (self.current_indent, "", opts)
            indent_first = self.help_position
        else:                       # start help on same line as opts
            opts = "%*s%-*s  " % (self.current_indent, "", opt_width, opts)
            indent_first = 0
        result.append(opts)
        if option.help:
            help_text = self.expand_default(option)
            help_lines = help_text.split('\n')
            if len(help_lines) == 1:
                help_lines = textwrap.wrap(help_text, self.help_width)
            result.append("%*s%s\n" % (indent_first, "", help_lines[0]))
            result.extend(["%*s%s\n" % (self.help_position, "", line)
                           for line in help_lines[1:]])
        elif opts[-1] != "\n":
            result.append("\n")
        return "".join(result)


class AllowUndefinedOptionParser(OptionParser):
    IS_TTY = sys.stdin.isatty()

    def __init__(self,
                usage=None,
                option_list=None,
                option_class=Option,
                version=None,
                conflict_handler="error",
                description=None,
                formatter=None,
                add_help_option=True,
                prog=None,
                epilog=None,
                allow_undefine=True,
                undefine_warn=True
        ):
        OptionParser.__init__(
            self, usage, option_list, option_class, version, conflict_handler,
            description, formatter, add_help_option, prog, epilog
        )
        self.allow_undefine = allow_undefine
        self.undefine_warn = undefine_warn

    def warn(self, msg, file=None):
        if self.IS_TTY:
            print("%s %s" % (IO.WARNING_PREV, msg))
        else:
            print('warn: %s' % msg)

    def _process_long_opt(self, rargs, values):
        try:
            value = rargs[0]
            OptionParser._process_long_opt(self, rargs, values)
        except BadOptionError as e:
            if self.allow_undefine:
                key = e.opt_str
                value = value[len(key)+1:]
                setattr(values, key.strip('-').replace('-', '_'), value if value != '' else True)
                self.undefine_warn and  self.warn(e)
            else:
                raise e

    def _process_short_opts(self, rargs, values):
        try:
            value = rargs[0]
            OptionParser._process_short_opts(self, rargs, values)
        except BadOptionError as e:
            if self.allow_undefine:
                key = e.opt_str
                value = value[len(key)+1:]
                setattr(values, key.strip('-').replace('-', '_'),  value if value != '' else True)
                self.undefine_warn and self.warn(e)
            else:
                raise e


class BaseCommand(object):

    def __init__(self, name, summary):
        self.name = name
        self.summary = summary
        self.args = []
        self.cmds = []
        self.opts = {}
        self.prev_cmd = ''
        self.is_init = False
        self.hidden = False
        self.parser = AllowUndefinedOptionParser(add_help_option=False)
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
        return self.parser.format_help(OptionHelpFormatter())


class ObdCommand(BaseCommand):

    OBD_PATH = OBD_HOME_PATH
    OBD_INSTALL_PRE = os.environ.get(CONST_OBD_INSTALL_PRE, '/')

    def init_home(self):
        version_path = os.path.join(self.OBD_PATH, 'version')
        need_update = True
        version_fobj = FileUtil.open(version_path, 'a+', stdio=ROOT_IO)
        version_fobj.seek(0)
        version = version_fobj.read()
        if VERSION != version:
            for part in ['plugins', 'config_parser', 'optimize', 'mirror/remote']:
                obd_part_dir = os.path.join(self.OBD_PATH, part)
                if DirectoryUtil.mkdir(self.OBD_PATH):
                    root_part_path = os.path.join(self.OBD_INSTALL_PRE, 'usr/obd/', part)
                    if os.path.exists(root_part_path):
                        DirectoryUtil.copy(root_part_path, obd_part_dir, ROOT_IO)
            version_fobj.seek(0)
            version_fobj.truncate()
            version_fobj.write(VERSION)
            version_fobj.flush()
        version_fobj.close()

    @property
    def dev_mode(self):
        return COMMAND_ENV.get(ENV_DEV_MODE) == "1"

    def parse_command(self):
        if self.parser.allow_undefine != True:
            self.parser.allow_undefine = self.dev_mode
        return super(ObdCommand, self).parse_command()

    def do_command(self):
        self.parse_command()
        self.init_home()
        trace_id = uuid()
        ret = False
        try:
            log_dir = os.path.join(self.OBD_PATH, 'log')
            DirectoryUtil.mkdir(log_dir)
            log_path = os.path.join(log_dir, 'obd')
            ROOT_IO.init_trace_logger(log_path, 'obd', trace_id)
            obd = ObdHome(self.OBD_PATH, self.dev_mode, ROOT_IO)
            ROOT_IO.track_limit += 1
            ROOT_IO.verbose('cmd: %s' % self.cmds)
            ROOT_IO.verbose('opts: %s' % self.opts)
            ret = self._do_command(obd)
            if not ret:
                ROOT_IO.print(DOC_LINK_MSG)
        except NotImplementedError:
            ROOT_IO.exception('command \'%s\' is not implemented' % self.prev_cmd)
        except LockError:
            ROOT_IO.exception('Another app is currently holding the obd lock.')
        except SystemExit:
            pass
        except KeyboardInterrupt:
            ROOT_IO.exception('Keyboard Interrupt')
        except:
            e = sys.exc_info()[1]
            ROOT_IO.exception('Running Error: %s' % e)
        if DEBUG:
            ROOT_IO.print('Trace ID: %s' % trace_id)
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
                if command.hidden is False:
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




class HiddenObdCommand(ObdCommand):

    def __init__(self, name, summary):
        super(HiddenObdCommand, self).__init__(name, summary)
        self.hidden = self.dev_mode is False


class HiddenMajorCommand(MajorCommand, HiddenObdCommand):

    pass


class DevCommand(HiddenObdCommand):

    def do_command(self):
        if self.hidden:
            ROOT_IO.error('`%s` is a developer command. Please start the developer mode first.\nUse `obd devmode enable` to start the developer mode' % self.prev_cmd)
            return False
        return super(DevCommand, self).do_command()


class DevModeEnableCommand(HiddenObdCommand):

    def __init__(self):
        super(DevModeEnableCommand, self).__init__('enable', 'Enable Dev Mode')

    def _do_command(self, obd):
        if COMMAND_ENV.set(ENV_DEV_MODE, "1", save=True, stdio=obd.stdio):
            obd.stdio.print("Dev Mode: ON")
            return True
        return False


class DevModeDisableCommand(HiddenObdCommand):

    def __init__(self):
        super(DevModeDisableCommand, self).__init__('disable', 'Disable Dev Mode')

    def _do_command(self, obd):
        if COMMAND_ENV.set(ENV_DEV_MODE, "0", save=True, stdio=obd.stdio):
            obd.stdio.print("Dev Mode: OFF")
            return True
        return False


class DevModeMajorCommand(HiddenMajorCommand):

    def __init__(self):
        super(DevModeMajorCommand, self).__init__('devmode', 'Developer mode switch')
        self.register_command(DevModeEnableCommand())
        self.register_command(DevModeDisableCommand())


class EnvironmentSetCommand(HiddenObdCommand):

    def __init__(self):
        super(EnvironmentSetCommand, self).__init__("set", "Set obd environment variable")

    def init(self, cmd, args):
        super(EnvironmentSetCommand, self).init(cmd, args)
        self.parser.set_usage('%s [key] [value]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            key = self.cmds[0]
            if key in FORBIDDEN_VARS:
                obd.stdio.error("Set the environment variable {} is not allowed.".format(key))
                return False
            return COMMAND_ENV.set(key, self.cmds[1], save=True, stdio=obd.stdio)
        else:
            return self._show_help()


class EnvironmentUnsetCommand(HiddenObdCommand):

    def __init__(self):
        super(EnvironmentUnsetCommand, self).__init__("unset", "Unset obd environment variable")

    def init(self, cmd, args):
        super(EnvironmentUnsetCommand, self).init(cmd, args)
        self.parser.set_usage('%s [key] [value]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 1:
            return COMMAND_ENV.delete(self.cmds[0], save=True, stdio=obd.stdio)
        else:
            return self._show_help()


class EnvironmentShowCommand(HiddenObdCommand):

    def __init__(self):
        super(EnvironmentShowCommand, self).__init__("show", "Show obd environment variables")
        self.parser.add_option('-A', '--all', action="store_true", help="Show all environment variables including system variables")

    def _do_command(self, obd):
        if self.opts.all:
            envs = COMMAND_ENV.copy().items()
        else:
            envs = COMMAND_ENV.show_env().items()
        obd.stdio.print_list(envs, ["Key", "Value"], title="Environ")
        return True


class EnvironmentClearCommand(HiddenObdCommand):

    def __init__(self):
        super(EnvironmentClearCommand, self).__init__("clear", "Clear obd environment variables")

    def _do_command(self, obd):
        return COMMAND_ENV.clear(stdio=obd.stdio)


class EnvironmentMajorCommand(HiddenMajorCommand):

    def __init__(self):
        super(EnvironmentMajorCommand, self).__init__('env', 'Environment variables for OBD')
        self.register_command(EnvironmentSetCommand())
        self.register_command(EnvironmentUnsetCommand())
        self.register_command(EnvironmentShowCommand())
        self.register_command(EnvironmentClearCommand())


class MirrorCloneCommand(ObdCommand):

    def __init__(self):
        super(MirrorCloneCommand, self).__init__('clone', 'Clone an RPM package to the local mirror repository.')
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

    def init(self, cmd, args):
        super(MirrorListCommand, self).init(cmd, args)
        self.parser.set_usage('%s [section name] [options]\n\nExample: %s local' % (self.prev_cmd, self.prev_cmd))
        return self

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
                repos = obd.mirror_manager.get_mirrors(is_enabled=None)
                for repo in repos:
                    if repo.section_name == name:
                        if not repo.enabled:
                            ROOT_IO.error('Mirror repository %s is disabled.' % name)
                            return False
                        pkgs = repo.get_all_pkg_info()
                        self.show_pkg(name, pkgs)
                        return True
                ROOT_IO.error('No such mirror repository: %s' % name)
                return False
        else:
            repos = obd.mirror_manager.get_mirrors(is_enabled=None)
            ROOT_IO.print_list(
                repos,
                ['SectionName', 'Type', 'Enabled','Update Time'],
                lambda x: [x.section_name, x.mirror_type.value, x.enabled, time.strftime("%Y-%m-%d %H:%M", time.localtime(x.repo_age))],
                title='Mirror Repository List'
            )
            ROOT_IO.print("Use `obd mirror list <section name>` for more details")
        return True


class MirrorUpdateCommand(ObdCommand):

    def __init__(self):
        super(MirrorUpdateCommand, self).__init__('update', 'Update remote mirror information.')
    
    def _do_command(self, obd):
        success = True
        current = int(time.time())
        mirrors = obd.mirror_manager.get_remote_mirrors()
        for mirror in mirrors:
            try:
                if mirror.enabled and mirror.repo_age < current:
                    success = mirror.update_mirror() and success
            except:
                success = False
                ROOT_IO.stop_loading('fail')
                ROOT_IO.exception('Fail to synchronize mirorr (%s)' % mirror.name)
        return success


class MirrorEnableCommand(ObdCommand):

    def __init__(self):
        super(MirrorEnableCommand, self).__init__('enable', 'Enable remote mirror repository.')

    def _do_command(self, obd):
        name = self.cmds[0]
        return obd.mirror_manager.set_remote_mirror_enabled(name, True)


class MirrorDisableCommand(ObdCommand):

    def __init__(self):
        super(MirrorDisableCommand, self).__init__('disable', 'Disable remote mirror repository.')

    def _do_command(self, obd):
        name = self.cmds[0]
        return obd.mirror_manager.set_remote_mirror_enabled(name, False)


class MirrorMajorCommand(MajorCommand):

    def __init__(self):
        super(MirrorMajorCommand, self).__init__('mirror', 'Manage a component repository for OBD.')
        self.register_command(MirrorListCommand())
        self.register_command(MirrorCloneCommand())
        self.register_command(MirrorCreateCommand())
        self.register_command(MirrorUpdateCommand())
        self.register_command(MirrorEnableCommand())
        self.register_command(MirrorDisableCommand())


class RepositoryListCommand(ObdCommand):

    def __init__(self):
        super(RepositoryListCommand, self).__init__('list', 'List local repository.')

    def show_repo(self, repos, name=None):
        ROOT_IO.print_list(
            repos,
            ['name', 'version', 'release', 'arch', 'md5', 'tags'], 
            lambda x: [x.name, x.version, x.release, x.arch, x.md5, ', '.join(x.tags)],
            title='%s Local Repository List' % name if name else 'Local Repository List'
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


class ClusterConfigStyleChange(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterConfigStyleChange, self).__init__('chst', 'Change Deployment Configuration Style')
        self.parser.add_option('-c', '--components', type='string', help="List the components. Multiple components are separated with commas.")
        self.parser.add_option('--style', type='string', help="Preferred Style")

    def _do_command(self, obd):
        if self.cmds:
            return obd.change_deploy_config_style(self.cmds[0], self.opts)
        else:
            return self._show_help()



class ClusterCheckForOCPChange(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterCheckForOCPChange, self).__init__('check4ocp', 'Check Whether OCP Can Take Over Configurations in Use')
        self.parser.add_option('-c', '--components', type='string', help="List the components. Multiple components are separated with commas.")
        self.parser.add_option('-V', '--version', type='string', help="OCP Version", default='3.1.1')

    def _do_command(self, obd):
        if self.cmds:
            return obd.check_for_ocp(self.cmds[0], self.opts)
        else:
            return self._show_help()


class DemoCommand(ClusterMirrorCommand):

    def __init__(self):
        super(DemoCommand, self).__init__('demo', 'Quickly start')
        self.parser.add_option('-c', '--components', type='string', help="List the components. Multiple components are separated with commas. [oceanbase-ce,obproxy-ce,obagent,prometheus,grafana]\nExample: \nstart oceanbase-ce: obd demo -c oceanbase-ce\n"
         + "start -c oceanbase-ce V3.2.3: obd demo -c oceanbase-ce --oceanbase-ce.version=3.2.3\n"
         + "start oceanbase-ce and obproxy-ce: obd demo -c oceanbase-ce,obproxy-ce", default='oceanbase-ce,obproxy-ce,obagent,prometheus,grafana')
        self.parser.allow_undefine = True
        self.parser.undefine_warn = False

    def _do_command(self, obd):
        setattr(self.opts, 'mini', True)
        setattr(self.opts, 'force', True)
        setattr(self.opts, 'clean', True)
        setattr(self.opts, 'force', True)
        setattr(self.opts, 'force_delete', True)
        return obd.demo(self.opts)


class ClusterAutoDeployCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterAutoDeployCommand, self).__init__('autodeploy', 'Deploy a cluster automatically by using a simple configuration file.')
        self.parser.add_option('-c', '--config', type='string', help="Path to the configuration file.")
        self.parser.add_option('-f', '--force', action='store_true', help="Force autodeploy, overwrite the home_path.")
        self.parser.add_option('-C', '--clean', action='store_true', help="Clean the home path if the directory belong to you.", default=False)
        self.parser.add_option('-U', '--unuselibrepo', '--ulp', action='store_true', help="Disable OBD from installing the libs mirror automatically.")
        self.parser.add_option('-A', '--auto-create-tenant', '--act', action='store_true', help="Automatically create a tenant named `test` by using all the available resource of the cluster.")
        self.parser.add_option('--force-delete', action='store_true', help="Force delete, delete the registered cluster.")
        self.parser.add_option('-s', '--strict-check', action='store_true', help="Throw errors instead of warnings when check fails.")

    def _do_command(self, obd):
        if self.cmds:
            if getattr(self.opts, 'force', False) or getattr(self.opts, 'clean', False):
                setattr(self.opts, 'skip_cluster_status_check', True)
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
        self.parser.add_option('-C', '--clean', action='store_true', help="Clean the home path if the directory belong to you.", default=False)
        self.parser.add_option('-U', '--unuselibrepo', '--ulp', action='store_true', help="Disable OBD from installing the libs mirror automatically.")
        self.parser.add_option('-A', '--auto-create-tenant', '--act', action='store_true', help="Automatically create a tenant named `test` by using all the available resource of the cluster.")
        # self.parser.add_option('-F', '--fuzzymatch', action='store_true', help="enable fuzzy match when search package")

    def _do_command(self, obd):
        if self.cmds:
            if getattr(self.opts, 'force', False) or getattr(self.opts, 'clean', False):
                setattr(self.opts, 'skip_cluster_status_check', True)
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
        self.parser.add_option('--without-parameter', '--wop', action='store_true', help='Start without parameters.')

    def _do_command(self, obd):
        if self.cmds:
            return obd.start_cluster(self.cmds[0], self.cmds[1:], self.opts)
        else:
            return self._show_help()


class ClusterStopCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterStopCommand, self).__init__('stop', 'Stop a started cluster.')
        self.parser.add_option('-s', '--servers', type='string', help="List the started servers. Multiple servers are separated with commas.")
        self.parser.add_option('-c', '--components', type='string', help="List the stoped components. Multiple components are separated with commas.")

    def _do_command(self, obd):
        if self.cmds:
            return obd.stop_cluster(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterDestroyCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterDestroyCommand, self).__init__('destroy', 'Destroy a deployed cluster.')
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
        self.parser.add_option('-c', '--components', type='string', help="List the restarted components. Multiple components are separated with commas.")
        self.parser.add_option('--with-parameter', '--wp', action='store_true', help='Restart with parameters.')

    def _do_command(self, obd):
        if self.cmds:
            if not getattr(self.opts, 'with_parameter', False):
                setattr(self.opts, 'without_parameter', True)
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
        super(ClusterEditConfigCommand, self).__init__('edit-config', 'Edit the configuration file for a specific deployment.')

    def _do_command(self, obd):
        if self.cmds:
            return obd.edit_deploy_config(self.cmds[0])
        else:
            return self._show_help()


class ClusterChangeRepositoryCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterChangeRepositoryCommand, self).__init__('reinstall', 'Reinstall a deployed component')
        self.parser.add_option('-c', '--component', type='string', help="Component name to change repository.")
        self.parser.add_option('--hash', type='string', help="Repository's hash")
        self.parser.add_option('-f', '--force', action='store_true', help="force change even start failed.")

    def _do_command(self, obd):
        if self.cmds:
            return obd.reinstall(self.cmds[0], self.opts)
        else:
            return self._show_help()


class CLusterUpgradeCommand(ClusterMirrorCommand):

    def __init__(self):
        super(CLusterUpgradeCommand, self).__init__('upgrade', 'Upgrade a cluster.')
        self.parser.add_option('-c', '--component', type='string', help="Component name to upgrade.")
        self.parser.add_option('-V', '--version', type='string', help="Target version.")
        self.parser.add_option('--skip-check', action='store_true', help="Skip all the possible checks.")
        self.parser.add_option('--usable', type='string', help="Hash list for priority mirrors, separated with `,`.", default='')
        self.parser.add_option('--disable', type='string', help="Hash list for disabled mirrors, separated with `,`.", default='')
        self.parser.add_option('-e', '--executer-path', type='string', help="Executer path.", default=os.path.join(ObdCommand.OBD_INSTALL_PRE, 'usr/obd/lib/executer'))

    def _do_command(self, obd):
        if self.cmds:
            return obd.upgrade_cluster(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterTenantCreateCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantCreateCommand, self).__init__('create', 'Create a tenant.')
        self.parser.add_option('-t', '-n', '--tenant-name', type='string', help="The tenant name. The default tenant name is [test].", default='test')
        self.parser.add_option('--max-cpu', type='float', help="Max CPU unit number.")
        self.parser.add_option('--min-cpu', type='float', help="Mind CPU unit number.")
        self.parser.add_option('--max-memory', type='string', help="Max memory unit size. Not supported after version 4.0, use `--memory-size` instead")
        self.parser.add_option('--min-memory', type='string', help="Min memory unit size. Not supported after version 4.0, use `--memory-size` instead")
        self.parser.add_option('--memory-size', type='string', help="Memory unit size. Supported since version 4.0.")
        self.parser.add_option('--max-disk-size', type='string', help="Max disk unit size. Not supported after version 4.0")
        self.parser.add_option('--log-disk-size', type='string', help="Log disk unit size.")
        self.parser.add_option('--max-iops', type='int', help="Max IOPS unit number.")
        self.parser.add_option('--min-iops', type='int', help="Min IOPS unit number.")
        self.parser.add_option('--iops-weight', type='int', help="The weight of IOPS. When Max IOPS is greater than Min IOPS, the weight of idle resources available to the current tenant. Supported since version 4.0.")
        self.parser.add_option('--max-session-num', type='int', help="Max session unit number. Not supported after version 4.0")
        self.parser.add_option('--unit-num', type='int', help="Pool unit number.")
        self.parser.add_option('-z', '--zone-list', type='string', help="Tenant zone list.")
        self.parser.add_option('--mode', type='string', help='Tenant compatibility mode. {mysql,oracle} [mysql]', default='mysql')
        self.parser.add_option('--charset', type='string', help="Tenant charset.")
        self.parser.add_option('--collate', type='string', help="Tenant COLLATE.")
        self.parser.add_option('--replica-num', type='int', help="Tenant replica number.")
        self.parser.add_option('--logonly-replica-num', type='int', help="Tenant logonly replica number.")
        self.parser.add_option('--tablegroup', type='string', help="Tenant tablegroup.")
        self.parser.add_option('--primary-zone', type='string', help="Tenant primary zone. [RANDOM].", default='RANDOM')
        self.parser.add_option('--locality', type='string', help="Tenant locality.")
        self.parser.add_option('-s', '--variables', type='string', help="Set the variables for the system tenant. [ob_tcp_invited_nodes='%'].", default="ob_tcp_invited_nodes='%'")

    def _do_command(self, obd):
        if self.cmds:
            return obd.create_tenant(self.cmds[0], self.opts)
        else:
            return self._show_help()


class ClusterTenantDropCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantDropCommand, self).__init__('drop', 'Drop a tenant.')
        self.parser.add_option('-t', '-n', '--tenant-name', type='string', help="Tenant name.")

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
        self.register_command(ClusterCheckForOCPChange())
        self.register_command(ClusterConfigStyleChange())
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
        self.register_command(ClusterChangeRepositoryCommand())
        self.register_command(ClusterTenantCommand())


class TestMirrorCommand(ObdCommand):

    def init(self, cmd, args):
        super(TestMirrorCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> [options]' % self.prev_cmd)
        return self


class MySQLTestCommand(TestMirrorCommand):

    def __init__(self):
        super(MySQLTestCommand, self).__init__('mysqltest', 'Run a mysqltest for a deployment.')
        self.parser.add_option('--mode', type='string', help='Test mode. Available values are mysql, oracle, and both.', default='both')
        # self.parser.add_option('--case-mode', type='string', help='case run mode [mysql,oracle]', default='mysql')
        self.parser.add_option('--component', type='string', help='Components for mysqltest.')
        self.parser.add_option('--test-server', type='string', help='The server for mysqltest. By default, the first root server in the component is the mysqltest server.')
        self.parser.add_option('--user', type='string', help='Username for a test. [admin]', default='admin')
        self.parser.add_option('--password', type='string', help='Password for a test. [admin]', default='admin')
        self.parser.add_option('--database', type='string', help='Database for a test. [test]', default='test')
        self.parser.add_option('--mysqltest-bin', type='string', help='Mysqltest bin path. [/u01/obclient/bin/mysqltest]', default='/u01/obclient/bin/mysqltest')
        self.parser.add_option('--obclient-bin', type='string', help='OBClient bin path. [obclient]', default='obclient')
        self.parser.add_option('--test-dir', type='string', help='Test case file directory. [./mysql_test/t]', default='./mysql_test/t')
        self.parser.add_option('--test-file-suffix', type='string', help='Test case file suffix. [.test]', default='.test')
        self.parser.add_option('--result-dir', type='string', help='Result case file directory. [./mysql_test/r]', default='./mysql_test/r')
        self.parser.add_option('--result-file-suffix', type='string', help='Result file suffix. [.result]', default='.result')
        self.parser.add_option('--record', action='store_true', help='record mysqltest execution results', default=False)
        self.parser.add_option('--record-dir', type='string', help='The directory of the result file for mysqltest.', default='./record')
        self.parser.add_option('--record-file-suffix', type='string', help='Result file suffix. [.record]', default='.record')
        self.parser.add_option('--log-dir', type='string', help='The log file directory.')
        self.parser.add_option('--tmp-dir', type='string', help='Temporary directory for mysqltest. [./tmp]', default='./tmp')
        self.parser.add_option('--var-dir', type='string', help='Var directory to use when run mysqltest. [./var]', default='./var')
        self.parser.add_option('--test-set', type='string', help='test list, use `,` interval')
        self.parser.add_option('--exclude', type='string', help='exclude list, use `,` interval')
        self.parser.add_option('--test-pattern', type='string', help='Pattern for test file.')
        self.parser.add_option('--suite', type='string', help='Suite list. Multiple suites are separated with commas.')
        self.parser.add_option('--suite-dir', type='string', help='Suite case directory. [./mysql_test/test_suite]', default='./mysql_test/test_suite')
        self.parser.add_option('--init-sql-dir', type='string', help='Initiate sql directory. [./]', default='./')
        self.parser.add_option('--init-sql-files', type='string', help='Initiate sql file list.Multiple files are separated with commas.')
        self.parser.add_option('--need-init', action='store_true', help='Execute the init SQL file.', default=False)
        self.parser.add_option('--init-only', action='store_true', help='Exit after executing init SQL.', default=False)
        self.parser.add_option('--auto-retry', action='store_true', help='Auto retry when fails.', default=False)
        self.parser.add_option('--all', action='store_true', help='Run all cases.', default=False)
        self.parser.add_option('--psmall', action='store_true', help='Run psmall cases.', default=False)
        self.parser.add_option('--special-run', action='store_true', help='run mysqltest in special mode.', default=False)
        self.parser.add_option('--sp-hint', type='string', help='run test with specified hint', default='')
        self.parser.add_option('--sort-result', action='store_true', help='sort query result', default=False)
        # self.parser.add_option('--java', action='store_true', help='use java sdk', default=False)
        self.parser.add_option('--slices', type='int', help='How many slices the test set should be')
        self.parser.add_option('--slice-idx', type='int', help='The id of slices')
        self.parser.add_option('--slb-host', type='string', help='The host of soft load balance.')
        self.parser.add_option('--exec-id', type='string', help='The unique execute id.')
        self.parser.add_option('--case-filter', type='string', help='The case filter file for mysqltest.')
        self.parser.add_option('--psmall-test', type='string', help='The file maintain psmall cases.', default='./mysql_test/psmalltest.py')
        self.parser.add_option('--psmall-source', type='string', help='The file maintain psmall source control.', default='./mysql_test/psmallsource.py')
        self.parser.add_option('--ps', action='store_true', help='Run in ps mode.', default=False)
        self.parser.add_option('--test-tags', type='string', help='The file maintain basic tags.', default='./mysql_test/test_tags.py')
        self.parser.add_option('--tags', type='string', help='Run cases by tag.', default='')
        self.parser.add_option('--regress-suite-map', type='string', help='The file maintain basic regress suite map', default='./regress_suite_map.py')
        self.parser.add_option('--regress_suite', type='string', help='Run cases by regress_suite.', default='')
        self.parser.add_option('--reboot-cases', type='string', help='The file maintain reboot cases')
        self.parser.add_option('--reboot-timeout', type='int', help='The timeout of observer bootstrap', default=0)
        self.parser.add_option('--reboot-retries', type='int', help='How many times to retry when rebooting failed', default=5)
        self.parser.add_option('--collect-all', action='store_true', help='Collect servers log.', default=False)
        self.parser.add_option('--collect-components', type='string', help='The components which need collect log, multiple components are separated with commas')
        self.parser.add_option('--case-timeout', type='int', help='The timeout of mysqltest case')
        self.parser.add_option('--log-pattern', type='string', help='The pattern for collected servers log ', default='*.log')
        self.parser.add_option('--cluster-mode', type='string', help="The mode of mysqltest")
        self.parser.add_option('--disable-reboot', action='store_true', help='Never reboot during test.', default=False)
        self.parser.add_option('--fast-reboot', action='store_true', help='Reboot using snapshots.', default=False)

    def _do_command(self, obd):
        if self.cmds:
            return obd.mysqltest(self.cmds[0], self.opts)
        else:
            return self._show_help()


class SysBenchCommand(TestMirrorCommand):

    def __init__(self):
        super(SysBenchCommand, self).__init__('sysbench', 'Run sysbench for a deployment.')
        self.parser.add_option('--component', type='string', help='Components for test.')
        self.parser.add_option('--test-server', type='string', help='The server for test. By default, the first root server in the component is the test server.')
        self.parser.add_option('--user', type='string', help='Username for a test. [root]', default='root')
        self.parser.add_option('--password', type='string', help='Password for a test.')
        self.parser.add_option('-t', '--tenant', type='string', help='Tenant for a test. [test]', default='test')
        self.parser.add_option('--database', type='string', help='Database for a test. [test]', default='test')
        self.parser.add_option('--obclient-bin', type='string', help='OBClient bin path. [obclient]', default='obclient')
        self.parser.add_option('--sysbench-bin', type='string', help='Sysbench bin path. [sysbench]', default='sysbench')
        self.parser.add_option('--script-name', type='string', help='Sysbench lua script file name. [oltp_point_select]', default='oltp_point_select.lua')
        self.parser.add_option('--sysbench-script-dir', type='string', help='The directory of the sysbench lua script file. [/usr/sysbench/share/sysbench]', default='/usr/sysbench/share/sysbench')
        self.parser.add_option('--table-size', type='int', help='Number of data initialized per table. [20000]', default=20000)
        self.parser.add_option('--tables', type='int', help='Number of initialization tables. [30]', default=30)
        self.parser.add_option('--threads', type='int', help='Number of threads to use. [16]', default=16)
        self.parser.add_option('--time', type='int', help='Limit for total execution time in seconds. [60]', default=60)
        self.parser.add_option('--interval', type='int', help='Periodically report intermediate statistics with a specified time interval in seconds. 0 disables intermediate reports. [10]', default=10)
        self.parser.add_option('--events', type='int', help='Limit for total number of events.')
        self.parser.add_option('--rand-type', type='string', help='Random numbers distribution {uniform,gaussian,special,pareto}.')
        self.parser.add_option('--percentile', type='int', help='Percentile to calculate in latency statistics. Available values are 1-100. 0 means to disable percentile calculations.')
        self.parser.add_option('--skip-trx', type='string', help='Open or close a transaction in a read-only test. {on/off}')
        self.parser.add_option('-O', '--optimization', type='int', help='optimization level {0/1}', default=1)
        self.parser.add_option('-S', '--skip-cluster-status-check', action='store_true', help='Skip cluster status check', default=False)
        self.parser.add_option('--mysql-ignore-errors', type='string', help='list of errors to ignore, or "all". ', default='1062')

    def _do_command(self, obd):
        if self.cmds:
            return obd.sysbench(self.cmds[0], self.opts)
        else:
            return self._show_help()


class TPCHCommand(TestMirrorCommand):

    def __init__(self):
        super(TPCHCommand, self).__init__('tpch', 'Run a TPC-H test for a deployment.')
        self.parser.add_option('--component', type='string', help='Components for a test.')
        self.parser.add_option('--test-server', type='string', help='The server for a test. By default, the first root server in the component is the test server.')
        self.parser.add_option('--user', type='string', help='Username for a test. [root]', default='root')
        self.parser.add_option('--password', type='string', help='Password for a test.')
        self.parser.add_option('-t', '--tenant', type='string', help='Tenant for a test. [test]', default='test')
        self.parser.add_option('--database', type='string', help='Database for a test. [test]', default='test')
        self.parser.add_option('--obclient-bin', type='string', help='OBClient bin path. [obclient]', default='obclient')
        self.parser.add_option('--dbgen-bin', type='string', help='dbgen bin path. [/usr/tpc-h-tools/tpc-h-tools/bin/dbgen]', default='/usr/tpc-h-tools/tpc-h-tools/bin/dbgen')
        self.parser.add_option('-s', '--scale-factor', type='int', help='Set Scale Factor (SF) to <n>. [1] ', default=1)
        self.parser.add_option('--tmp-dir', type='string', help='The temporary directory for executing TPC-H. [./tmp]', default='./tmp')
        self.parser.add_option('--ddl-path', type='string', help='Directory for DDL files.')
        self.parser.add_option('--tbl-path', type='string', help='Directory for tbl files.')
        self.parser.add_option('--sql-path', type='string', help='Directory for SQL files.')
        self.parser.add_option('--remote-tbl-dir', type='string', help='Directory for the tbl on target observers. Make sure that you have read and write access to the directory when you start observer.')
        self.parser.add_option('--disable-transfer', '--dt', action='store_true', help='Disable the transfer. When enabled, OBD will use the tbl files under remote-tbl-dir instead of transferring local tbl files to remote remote-tbl-dir.')
        self.parser.add_option('--dss-config', type='string', help='Directory for dists.dss. [/usr/tpc-h-tools/tpc-h-tools]', default='/usr/tpc-h-tools/tpc-h-tools/')
        self.parser.add_option('-O', '--optimization', type='int', help='Optimization level {0/1/2}. [1] 0 - No optimization. 1 - Optimize some of the parameters which do not need to restart servers. 2 - Optimize all the parameters and maybe RESTART SERVERS for better performance.', default=1)
        self.parser.add_option('--test-only', action='store_true', help='Only testing SQLs are executed. No initialization is executed.')
        self.parser.add_option('-S', '--skip-cluster-status-check', action='store_true', help='Skip cluster status check', default=False)

    def _do_command(self, obd):
        if self.cmds:
            return obd.tpch(self.cmds[0], self.opts)
        else:
            return self._show_help()


class TPCDSCommand(TestMirrorCommand):

    def __init__(self):
        super(TPCDSCommand, self).__init__('tpcds', 'Run a TPC-DS test for a deployment.')
        self.parser.add_option('--component', type='string', help='Components for a test.')
        self.parser.add_option('--test-server', type='string', help='The server for a test. By default, the first root server in the component is the test server.')
        self.parser.add_option('--user', type='string', help='Username for a test.')
        self.parser.add_option('--password', type='string', help='Password for a test.')
        self.parser.add_option('-t', '--tenant', type='string', help='Tenant for a test. [test]', default='test')
        self.parser.add_option('--mode', type='string', help='Tenant compatibility mode. {mysql,oracle} [mysql]', default='mysql')
        self.parser.add_option('--database', type='string', help='Database for a test. [test]', default='test')
        self.parser.add_option('--obclient-bin', type='string', help='OBClient bin path. [obclient]', default='obclient')
        self.parser.add_option('--tool-dir', type='string', help='tpc-ds tool dir. [/usr/tpc-ds-tools]')
        self.parser.add_option('--dsdgen-bin', type='string', help='dsdgen bin path. [$TOOL_DIR/bin/dsdgen]')
        self.parser.add_option('--idx-file', type='string', help='tpcds.idx file path. [$TOOL_DIR/bin/tpcds.idx]')
        self.parser.add_option('--dsqgen-bin', type='string', help='dsqgen bin path. [$TOOL_DIR/bin/dsqgen]')
        self.parser.add_option('--query-templates-dir', type='string', help='Query templates dir. [$TOOL_DIR/query_templates]')
        self.parser.add_option('-s', '--scale', type='int', help='Set Scale Factor (SF) to <n>. [1] ', default=1)
        self.parser.add_option('--disable-generate', '--dg', action='store_true', help='Do not generate test data.')
        self.parser.add_option('-p', '--generate-parallel', help='Generate data parallel number. [0]', default=0)
        self.parser.add_option('--tmp-dir', type='string', help='The temporary directory for executing TPC-H. [./tmp]', default='./tmp')
        self.parser.add_option('--ddl-path', type='string', help='Directory for DDL files.')
        self.parser.add_option('--sql-path', type='string', help='Directory for SQL files.')
        self.parser.add_option('--create-foreign-key', '--fk', action='store_true', help='create foreign key.')
        self.parser.add_option('--foreign-key-file', '--fk-file', action='store_true', help='SQL file for creating foreign key.')
        self.parser.add_option('--remote-dir', type='string', help='Directory for the data file on target observers. Make sure that you have read and write access to the directory when you start observer.')
        self.parser.add_option('--test-only', action='store_true', help='Only testing SQLs are executed. No initialization is executed.')

    def _do_command(self, obd):
        if self.cmds:
            return obd.tpcds(self.cmds[0], self.opts)
        else:
            return self._show_help()


class TPCCCommand(TestMirrorCommand):

    def __init__(self):
        super(TPCCCommand, self).__init__('tpcc', 'Run a TPC-C test for a deployment.')
        self.parser.add_option('--component', type='string', help='Components for a test.')
        self.parser.add_option('--test-server', type='string', help='The server for a test. By default, the first root server in the component is the test server.')
        self.parser.add_option('--user', type='string', help='Username for a test. [root]', default='root')
        self.parser.add_option('--password', type='string', help='Password for a test.')
        self.parser.add_option('-t', '--tenant', type='string', help='Tenant for a test. [test]', default='test')
        self.parser.add_option('--database', type='string', help='Database for a test. [test]', default='test')
        self.parser.add_option('--obclient-bin', type='string', help='OBClient bin path. [obclient]', default='obclient')
        self.parser.add_option('--java-bin', type='string', help='Java bin path. [java]', default='java')
        self.parser.add_option('--tmp-dir', type='string', help='The temporary directory for executing TPC-C. [./tmp]', default='./tmp')
        self.parser.add_option('--bmsql-dir', type='string', help='The directory of BenchmarkSQL.')
        self.parser.add_option('--bmsql-jar', type='string', help='BenchmarkSQL jar path.')
        self.parser.add_option('--bmsql-libs', type='string', help='BenchmarkSQL libs path.')
        self.parser.add_option('--bmsql-sql-dir', type='string', help='The directory of BenchmarkSQL sql scripts.')
        self.parser.add_option('--warehouses', type='int', help='The number of warehouses.[10]', default=10)
        self.parser.add_option('--load-workers', type='int', help='The number of workers to load data.')
        self.parser.add_option('--terminals', type='int', help='The number of terminals.')
        self.parser.add_option('--run-mins', type='int', help='To run for specified minutes.[10]', default=10)
        self.parser.add_option('--test-only', action='store_true', help='Only testing SQLs are executed. No initialization is executed.')
        self.parser.add_option('-O', '--optimization', type='int', help='Optimization level {0/1/2}. [1] 0 - No optimization. 1 - Optimize some of the parameters which do not need to restart servers. 2 - Optimize all the parameters and maybe RESTART SERVERS for better performance.', default=1)
        self.parser.add_option('-S', '--skip-cluster-status-check', action='store_true', help='Skip cluster status check', default=False)

    def _do_command(self, obd):
        if self.cmds:
            return obd.tpcc(self.cmds[0], self.opts)
        else:
            return self._show_help()


class TestMajorCommand(MajorCommand):

    def __init__(self):
        super(TestMajorCommand, self).__init__('test', 'Run test for a running deployment.')
        self.register_command(MySQLTestCommand())
        self.register_command(SysBenchCommand())
        self.register_command(TPCHCommand())
        self.register_command(TPCCCommand())
        # self.register_command(TPCDSCommand())


class DbConnectCommand(HiddenObdCommand):

    def init(self, cmd, args):
        super(DbConnectCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> [options]' % self.prev_cmd)
        return self

    def __init__(self):
        super(DbConnectCommand, self).__init__('db_connect', 'Establish a database connection to the deployment.')
        self.parser.add_option('-c', '--component', type='string', help='The component used by database connection.')
        self.parser.add_option('-s', '--server', type='string',
                               help='The server used by database connection. The first server in the configuration will be used by default')
        self.parser.add_option('-u', '--user', type='string', help='The username used by database connection. [root]', default='root')
        self.parser.add_option('-p', '--password', type='string', help='The password used by database connection.')
        self.parser.add_option('-t', '--tenant', type='string', help='The tenant used by database connection. [sys]', default='sys')
        self.parser.add_option('-D', '--database', type='string', help='The database name used by database connection.')
        self.parser.add_option('--obclient-bin', type='string', help='OBClient bin path. [obclient]', default='obclient')

    def _do_command(self, obd):
        if self.cmds:
            return obd.db_connect(self.cmds[0], self.opts)
        else:
            return self._show_help()


class DoobaCommand(HiddenObdCommand):

    def init(self, cmd, args):
        super(DoobaCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> [options]' % self.prev_cmd)
        return self

    def __init__(self):
        super(DoobaCommand, self).__init__('dooba', 'A curses powerful tool for OceanBase admin, more than a monitor')
        self.parser.add_option('-c', '--component', type='string', help='The component used by database connection.')
        self.parser.add_option('-s', '--server', type='string',
                               help='The server used by database connection. The first server in the configuration will be used by default')
        self.parser.add_option('-u', '--user', type='string', help='The username used by database connection. [root]',
                               default='root')
        self.parser.add_option('-p', '--password', type='string', help='The password used by database connection.')
        self.parser.add_option('--dooba-bin', type='string', help='Dooba bin path.')

    def _do_command(self, obd):
        if self.cmds:
            return obd.dooba(self.cmds[0], self.opts)
        else:
            return self._show_help()


class CommandsCommand(HiddenObdCommand):

    def init(self, cmd, args):
        super(CommandsCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <command> [options]' % self.prev_cmd)
        return self

    def __init__(self):
        super(CommandsCommand, self).__init__('command', 'Common tool commands')
        self.parser.add_option('-c', '--components', type='string', help='The components used by the command. The first component in the configuration will be used by default in interactive commands, and all available components will be used by default in non-interactive commands.')
        self.parser.add_option('-s', '--servers', type='string', help='The servers used by the command. The first server in the configuration will be used by default in interactive commands, and all available servers will be used by default in non-interactive commands.')

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            return obd.commands(self.cmds[0], self.cmds[1], self.opts)
        else:
            return self._show_help()


class ToolCommand(HiddenMajorCommand):

    def __init__(self):
        super(ToolCommand, self).__init__('tool', 'Tools')
        self.register_command(DbConnectCommand())
        self.register_command(CommandsCommand())
        self.register_command(DoobaCommand())


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
        return obd.update_obd(VERSION, self.OBD_INSTALL_PRE)


class MainCommand(MajorCommand):

    def __init__(self):
        super(MainCommand, self).__init__('obd', '')
        self.register_command(DevModeMajorCommand())
        self.register_command(DemoCommand())
        self.register_command(MirrorMajorCommand())
        self.register_command(ClusterMajorCommand())
        self.register_command(RepositoryMajorCommand())
        self.register_command(TestMajorCommand())
        self.register_command(UpdateCommand())
        self.register_command(EnvironmentMajorCommand())
        self.register_command(ToolCommand())
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
    sys.path.append(os.path.join(ObdCommand.OBD_INSTALL_PRE, 'usr/obd/lib/site-packages'))
    ROOT_IO.track_limit += 2
    if MainCommand().init('obd', sys.argv[1:]).do_command():
        ROOT_IO.exit(0)
    ROOT_IO.exit(1)

