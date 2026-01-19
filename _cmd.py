
# coding: utf-8
# Copyright (c) 2025 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import os
import sys
import time
import textwrap
import json
import glob
import datetime
import copy
import getpass
from uuid import uuid1 as uuid, UUID
from optparse import OptionParser, BadOptionError, Option, IndentedHelpFormatter

import const
from core import ObdHome
from _stdio import IO, FormatText
from _lock import LockMode
from _types import Capacity
from tool import DirectoryUtil, FileUtil, NetUtil, COMMAND_ENV
from _errno import DOC_LINK_MSG, LockError
import _environ as ENV
from ssh import LocalClient
from const import (
    CONST_OBD_HOME,
    VERSION, REVISION, BUILD_BRANCH, BUILD_TIME, FORBIDDEN_VARS, COMP_OB_CE, COMP_ODP_CE, COMP_ODP, COMP_OCP_SERVER_CE, COMP_OB_STANDALONE,
    COMP_OCEANBASE_DIAGNOSTIC_TOOL, PKG_RPM_FILE,PKG_REPO_FILE, BUILD_PLUGIN_LIST
)


ROOT_IO = IO(1)

OBD_HOME_PATH = os.path.join(os.environ.get(CONST_OBD_HOME, os.getenv('HOME')), '.obd')
OBDIAG_HOME_PATH = os.path.join(os.environ.get(CONST_OBD_HOME, os.getenv('HOME')), COMP_OCEANBASE_DIAGNOSTIC_TOOL)
COMMAND_ENV.load(os.path.join(OBD_HOME_PATH, '.obd_environ'), ROOT_IO)
ROOT_IO.default_confirm = COMMAND_ENV.get(ENV.ENV_DEFAULT_CONFIRM, '0') == '1'


class CmdReturn(object):
    def __init__(self, cmd_result, code):
        self.exit_code = code
        self.result = cmd_result

    @property
    def code(self):
        return self.exit_code

    def __bool__(self):
        return True if self.result else False


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
            if self.prog.split()[-1] == "obdiag":
                return
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
            if self.prog.split()[-1] == "obdiag":
                return
            if self.allow_undefine:
                key = e.opt_str
                value = value[len(key)+1:]
                setattr(values, key.strip('-').replace('-', '_'),  value if value != '' else True)
                self.undefine_warn and self.warn(e)
            else:
                raise e

    def print_usage(self, file=None):
        print(self.format_help(OptionHelpFormatter()), file=file)

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
        self.has_trace = True
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
        if self.name == "obdiag":
            return
        ROOT_IO.print(self._mk_usage())
        self.parser.exit(1)

    def _mk_usage(self):
        return self.parser.format_help(OptionHelpFormatter())


class ObdCommand(BaseCommand):

    OBD_PATH = OBD_HOME_PATH
    OBD_INSTALL_PRE = COMMAND_ENV.get(ENV.ENV_OBD_INSTALL_PRE, '/')
    OBD_INSTALL_PATH = COMMAND_ENV.get(ENV.ENV_OBD_INSTALL_PATH, os.path.join(OBD_INSTALL_PRE, 'usr/obd/'))

    def init_home(self):
        version_path = os.path.join(self.OBD_PATH, 'version')
        version_fobj = FileUtil.open(version_path, 'a+', stdio=ROOT_IO)
        version_fobj.seek(0)
        version = version_fobj.read()
        if not COMMAND_ENV.get(ENV.ENV_OBD_ID):
            COMMAND_ENV.set(ENV.ENV_OBD_ID, uuid())
        if VERSION != version and BUILD_PLUGIN_LIST != '<B_PLUGIN_LIST>':
            obd_path_len = len(self.OBD_PATH) + 1
            for part in ['workflows', 'plugins', 'config_parser', 'optimize', 'mirror/remote']:
                obd_part_dir = os.path.join(self.OBD_PATH, part)
                root_part_path = os.path.join(self.OBD_INSTALL_PATH, part)
                if DirectoryUtil.mkdir(self.OBD_PATH, stdio=ROOT_IO):
                    if part != 'mirror/remote':
                        if os.path.exists(obd_part_dir):
                            backup_path = os.path.join(self.OBD_PATH, '.backup_plugin', VERSION + '_' + REVISION, part)
                            if DirectoryUtil.mkdir(backup_path, stdio=ROOT_IO):
                                DirectoryUtil.copy(obd_part_dir, backup_path, stdio=ROOT_IO)
                            if part != 'config_parser':
                                for file in glob.glob('%s/*/*/*' % obd_part_dir):
                                    if COMP_OB_CE in file or COMP_OCP_SERVER_CE in file or (COMP_ODP_CE in file and 'file_map.yaml' in file):
                                        continue
                                    if file[obd_path_len:] not in BUILD_PLUGIN_LIST:
                                        FileUtil.rm(file)
                            else:
                                for file in glob.glob('%s/*/*' % obd_part_dir):
                                    if file not in BUILD_PLUGIN_LIST:
                                        FileUtil.rm(file)

                        if os.path.exists(root_part_path):
                            if part != 'config_parser':
                                for file in glob.glob('%s/*/*/*' % obd_part_dir):
                                    if COMP_OB_CE in file or COMP_OCP_SERVER_CE in file or (COMP_ODP_CE in file and 'file_map.yaml' in file) or COMP_OB_STANDALONE in file:
                                        continue
                                    if file[obd_path_len:] not in BUILD_PLUGIN_LIST:
                                        if file.replace(COMP_ODP_CE, COMP_ODP).replace('3.2.1', '3.1.0') in BUILD_PLUGIN_LIST:
                                            continue
                                        FileUtil.rm(file)
                            else:
                                for file in glob.glob('%s/*/*' % obd_part_dir):
                                    if file[obd_path_len:] not in BUILD_PLUGIN_LIST:
                                        FileUtil.rm(file)
                if os.path.exists(root_part_path):
                    DirectoryUtil.copy(root_part_path, obd_part_dir, stdio=ROOT_IO)

            backup_path = os.path.join(self.OBD_PATH, '.backup_plugin')
            if os.path.exists(backup_path):
                dir_list = [os.path.join(backup_path, f) for f in os.listdir(backup_path)]
                sorted_dir_list = sorted(dir_list, key=lambda dir: datetime.datetime.fromtimestamp(os.path.getmtime(dir)))
                for dir in sorted_dir_list[12:]:
                    DirectoryUtil.rm(dir, stdio=ROOT_IO)
            version_fobj.seek(0)
            version_fobj.truncate()
            version_fobj.write(VERSION)
            version_fobj.flush()
        version_fobj.close()

    @property
    def dev_mode(self):
        return COMMAND_ENV.get(ENV.ENV_DEV_MODE) == "1"

    @property
    def lock_mode(self):
        return COMMAND_ENV.get(ENV.ENV_LOCK_MODE)

    @property
    def enable_log(self):
        return True

    def parse_command(self):
        if self.parser.allow_undefine != True:
            self.parser.allow_undefine = self.dev_mode
        return super(ObdCommand, self).parse_command()

    def _init_log(self):
        trace_id = uuid()
        log_dir = os.path.join(self.OBD_PATH, 'log')
        DirectoryUtil.mkdir(log_dir)
        log_path = os.path.join(log_dir, 'obd')
        ROOT_IO.init_trace_logger(log_path, 'obd', trace_id)
        ROOT_IO.exit_msg = '''Trace ID: {trace_id}
If you want to view detailed obd logs, please run: obd display-trace {trace_id}'''.format(trace_id=trace_id)

    def do_command(self):
        self.parse_command()
        self.init_home()
        ret = False
        try:
            if self.has_trace and self.enable_log:
                self._init_log()
            ROOT_IO.track_limit += 1
            if self.name == 'set-epk':
                ROOT_IO.verbose('cmd: %s' % "['******']")
            else:
                ROOT_IO.verbose('cmd: %s' % self.cmds)
            ROOT_IO.verbose('opts: %s' % self.opts)
            obd = ObdHome(home_path=self.OBD_PATH, dev_mode=self.dev_mode, lock_mode=self.lock_mode, stdio=ROOT_IO)
            obd.set_options(self.opts)
            obd.set_cmds(self.cmds)
            ret = self._do_command(obd)
            if not ret:
                from _errno import EXIST_ERROR_CODE
                ROOT_IO.exit_msg = ((DOC_LINK_MSG + "\n") if EXIST_ERROR_CODE else '') + ROOT_IO.exit_msg
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
        return ret

    def _do_command(self, obd):
        raise NotImplementedError

    def get_white_ip_list(self):
        if self.opts.white:
            return self.opts.white.split(',')
        ROOT_IO.warn("Security Risk: the whitelist is empty and anyone can request this program!")
        if ROOT_IO.confirm("Do you want to continue?"):
            return []
        wthite_ip_list = ROOT_IO.read("Please enter the whitelist, eq: '192.168.1.1'")
        raise wthite_ip_list.split(',')


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
        if COMMAND_ENV.set(ENV.ENV_DEV_MODE, "1", save=True, stdio=obd.stdio):
            obd.stdio.print("Dev Mode: ON")
            return True
        return False


class DevModeDisableCommand(HiddenObdCommand):

    def __init__(self):
        super(DevModeDisableCommand, self).__init__('disable', 'Disable Dev Mode')

    def _do_command(self, obd):
        if COMMAND_ENV.set(ENV.ENV_DEV_MODE, "0", save=True, stdio=obd.stdio):
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
        self.parser.set_usage('%s [key]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 1:
            if self.cmds[0] in FORBIDDEN_VARS:
                obd.stdio.error("Unset the environment variable {} is not allowed.".format(self.cmds[0]))
                return False
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


class TelemetryPostCommand(HiddenObdCommand):

    def __init__(self):
        super(TelemetryPostCommand, self).__init__('post', "Post telemetry data to OceanBase.By default, OBD telemetry is enabled. To disable OBD telemetry, run the `obd env set TELEMETRY_MODE 0` command. To enable OBD telemetry data printing, run `obd env set TELEMETRY_LOG_MODE 1`.")
        self.parser.add_option('-d', '--data', type='string', help="post obd data")

    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    @property
    def enable_log(self):
        return COMMAND_ENV.get(ENV.ENV_TELEMETRY_LOG_MODE, default='0') == '1'

    def init(self, cmd, args):
        super(TelemetryPostCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        return obd.telemetry_post(self.cmds[0])


class TelemetryMajorCommand(HiddenMajorCommand):

    def __init__(self):
        super(TelemetryMajorCommand, self).__init__('telemetry', "Telemetry for OB-Deploy.By default, OBD telemetry is enabled. To disable OBD telemetry, run the `obd env set TELEMETRY_MODE 0` command. To enable OBD telemetry data printing, run `obd env set TELEMETRY_LOG_MODE 1`.")
        self.register_command(TelemetryPostCommand())

    def do_command(self):
        if COMMAND_ENV.get(ENV.ENV_TELEMETRY_MODE, default='1') == '1':
            return super(TelemetryMajorCommand, self).do_command()
        else:
            ROOT_IO.critical('Telemetry is disabled. To enable OBD telemetry, run the `obd env set TELEMETRY_MODE 1` command.')
            return False


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
                if not obd.add_mirror(src):
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
        return obd.create_repository()


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
                ['SectionName', 'Type', 'Enabled', 'Avaiable' , 'Update Time'],
                lambda x: [x.section_name, x.mirror_type.value, x.enabled, x.available, time.strftime("%Y-%m-%d %H:%M", time.localtime(x.repo_age))],
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
        ret = True
        for name in self.cmds:
            ret = obd.mirror_manager.set_remote_mirror_enabled(name, True) and ret
        return ret


class MirrorDisableCommand(ObdCommand):

    def __init__(self):
        super(MirrorDisableCommand, self).__init__('disable', 'Disable remote mirror repository.')

    def _do_command(self, obd):
        ret = True
        for name in self.cmds:
            ret = obd.mirror_manager.set_remote_mirror_enabled(name, False) and ret
        return ret

class MirrorAddRepoCommand(ObdCommand):

    def __init__(self):
        super(MirrorAddRepoCommand, self).__init__('add-repo', 'Add remote mirror repository file.')

    def _do_command(self, obd):
        url = self.cmds[0]
        return obd.mirror_manager.add_repo(url)


class MirrorCleanPkgCommand(ObdCommand):

    def __init__(self):
        super(MirrorCleanPkgCommand, self).__init__('clean', 'After the list of files to be deleted is displayed, double confirm and then clean up them.')
        self.parser.add_option('-y', '--confirm', action='store_true', help="confirm to clean up.")
        self.parser.add_option('-c', '--components', type='string',  help="Clean up specified components. Separate multiple components with `,`.")
        self.parser.add_option('-t', '--type', type='string', help="Specify the file types to be deleted as '%s or %s'." % (PKG_RPM_FILE, PKG_REPO_FILE))
        self.parser.add_option('--hash', type='string', help="Repository's md5")

    def _do_command(self, obd):
        if self.opts.type and self.opts.type not in [PKG_RPM_FILE, PKG_REPO_FILE]:
            ROOT_IO.error("Invalid type specified. Please specify '%s' or '%s'." % (PKG_RPM_FILE, PKG_REPO_FILE))
            return False
        return obd.clean_pkg(self.opts)


class MirrorMajorCommand(MajorCommand):

    def __init__(self):
        super(MirrorMajorCommand, self).__init__('mirror', 'Manage a component repository for OBD.')
        self.register_command(MirrorListCommand())
        self.register_command(MirrorCloneCommand())
        self.register_command(MirrorCreateCommand())
        self.register_command(MirrorUpdateCommand())
        self.register_command(MirrorEnableCommand())
        self.register_command(MirrorDisableCommand())
        self.register_command(MirrorAddRepoCommand())
        self.register_command(MirrorCleanPkgCommand())


class RepositoryListCommand(ObdCommand):

    def __init__(self):
        super(RepositoryListCommand, self).__init__('list', 'List local repository.')
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def show_repo(self, repos, name=None):
        ROOT_IO.print_list(
            repos,
            ['name', 'version', 'release', 'arch', 'md5', 'tags', 'size'],
            lambda x: [x.name, x.version, x.release, x.arch, x.md5, ', '.join(x.tags), Capacity(x.size, 2).value],
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

    def init(self, cmd, args, need_deploy_name=True):
        super(ClusterMirrorCommand, self).init(cmd, args)
        usage = '%s <deploy name> [options]'
        if not need_deploy_name:
            usage = '%s [options]'
        self.parser.set_usage(usage % self.prev_cmd)
        return self

    def get_obd_namespaces_data(self, obd):
        data = {
            "component": {},
            "error_messages": ''
        }
        comp_data = data['component']
        for component, _ in obd.namespaces.items():
            comp_data[component] = _.get_variable('run_result')
        error = obd.stdio.get_error_buffer().read()
        data['error_messages'] = error
        return data


    def background_telemetry_task(self, obd, demploy_name=None):
        if demploy_name is None:
            demploy_name = self.cmds[0]
        data = json.dumps(self.get_obd_namespaces_data(obd))
        LocalClient.execute_command_background("nohup obd telemetry post %s --data='%s' >/dev/null 2>&1 &" % (demploy_name, data))


class ClusterConfigStyleChange(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterConfigStyleChange, self).__init__('chst', 'Change Deployment Configuration Style')
        self.parser.add_option('-c', '--components', type='string', help="List the components. Multiple components are separated with commas.")
        self.parser.add_option('--style', type='string', help="Preferred Style")

    def _do_command(self, obd):
        if self.cmds:
            return obd.change_deploy_config_style(self.cmds[0])
        else:
            return self._show_help()



class ClusterCheckForOCPChange(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterCheckForOCPChange, self).__init__('check4ocp', 'Check Whether OCP Can Take Over Configurations in Use')
        self.parser.add_option('-c', '--components', type='string', help="List the components. Multiple components are separated with commas.")
        self.parser.add_option('-V', '--version', type='string', help="OCP Version", default='3.1.1')

    def _do_command(self, obd):
        if self.cmds:
            return obd.check_for_ocp(self.cmds[0])
        else:
            return self._show_help()

class ClusterExportToOCPCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterExportToOCPCommand, self).__init__('export-to-ocp', 'Export obcluster to OCP')
        self.parser.add_option('-a', '--address', type='string', help="OCP address, example http://127.0.0.1:8080, you can find it in OCP system parameters with Key='ocp.site.url'")
        self.parser.add_option('-u', '--user', type='string', help="OCP user, this user should have create cluster privilege.")
        self.parser.add_option('-p', '--password', type='string', help="OCP user password.")
        self.parser.add_option('--host_type', type='string', help="Host type of observer, a host type will be created when there's no host type exists in ocp, the first host type will be used if this parameter is empty.", default="")
        self.parser.add_option('--credential_name', type='string', help="Credential used to connect hosts, a credential will be created if credential_name is empty or no credential with this name exists in ocp.", default="")

    def _do_command(self, obd):
        if self.cmds:
            return obd.export_to_ocp(self.cmds[0])
        else:
            return self._show_help()


class ClusterTakeoverCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTakeoverCommand, self).__init__('takeover', 'Takeover oceanbase cluster')
        self.parser.remove_option('-h')
        self.parser.add_option('--help', action='callback', callback=self._show_help, help='Show help and exit.')
        self.parser.add_option('-h', '--host', type='string', help="db connection host, default: 127.0.0.1", default='127.0.0.1')
        self.parser.add_option('-P', '--mysql-port', type='int', help="mysql port, default: 2881", default=2881)
        self.parser.add_option('-p', '--root-password', type='string', help="password of root@sys user, default: ''", default='')
        self.parser.add_option('--ssh-user', type='string', help="ssh user, default: current user")
        self.parser.add_option('--ssh-password', type='string', help="ssh password, default: ''", default='')
        self.parser.add_option('--ssh-port', type='int', help="ssh port, default: 22")
        self.parser.add_option('-t', '--ssh-timeout', type='int', help="ssh connection timeout (second), default: 30")
        self.parser.add_option('--ssh-key-file', type='string', help="ssh key file")


    def _do_command(self, obd):
        if self.cmds:
            return obd.takeover(self.cmds[0])
        else:
            return self._show_help()


class DemoCommand(ClusterMirrorCommand):

    def __init__(self):
        super(DemoCommand, self).__init__('demo', 'Quickly start, This is a basic setup with minimal resources.')
        self.parser.add_option('-c', '--components', type='string', help="List the components. Multiple components are separated with commas. [oceanbase-ce,obproxy-ce,obagent,prometheus,grafana,ob-configserver]\nExample: \nstart oceanbase-ce: obd demo -c oceanbase-ce\n"
         + "start -c oceanbase-ce V3.2.3: obd demo -c oceanbase-ce --oceanbase-ce.version=3.2.3\n"
         + "start oceanbase-ce and obproxy-ce: obd demo -c oceanbase-ce,obproxy-ce", default='oceanbase-ce,obproxy-ce,obagent,prometheus,grafana')
        self.parser.allow_undefine = True
        self.parser.undefine_warn = False

    def init(self, cmd, args, need_deploy_name=False):
        super(DemoCommand, self).init(cmd, args, need_deploy_name)
        return self

    def _do_command(self, obd):
        setattr(self.opts, 'force', True)
        setattr(self.opts, 'clean', True)
        setattr(self.opts, 'force', True)
        setattr(self.opts, 'force_delete', True)
        setattr(self.opts, 'force_kill', True)
        obd.set_options(self.opts)

        res = obd.demo()
        self.background_telemetry_task(obd, 'demo')
        return res


class PrefCommand(ClusterMirrorCommand):

    def __init__(self):
        super(PrefCommand, self).__init__('perf', 'Quickly start, This deploys OceanBase with production-optimized configuration for enhanced performance.')
        self.parser.add_option('-c', '--components', type='string', help="List the components. Multiple components are separated with commas. [oceanbase-ce,obproxy-ce,obagent,prometheus,grafana,ob-configserver]\nExample: \nstart oceanbase-ce: obd demo -c oceanbase-ce\n"
         + "start -c oceanbase-ce V3.2.3: obd perf -c oceanbase-ce --oceanbase-ce.version=3.2.3\n"
         + "start oceanbase-ce and obproxy-ce: obd perf -c oceanbase-ce,obproxy-ce", default='oceanbase-ce,obproxy-ce,obagent,prometheus,grafana')
        self.parser.allow_undefine = True
        self.parser.undefine_warn = False

    def init(self, cmd, args, need_deploy_name=False):
        super(PrefCommand, self).init(cmd, args, need_deploy_name)
        return self

    def _do_command(self, obd):
        setattr(self.opts, 'force', True)
        setattr(self.opts, 'clean', True)
        setattr(self.opts, 'force', True)
        setattr(self.opts, 'force_delete', True)
        setattr(self.opts, 'max', True)
        obd.set_options(self.opts)

        res = obd.demo(name='perf')
        self.background_telemetry_task(obd, 'perf')
        return res


class WebCommand(ObdCommand):

    def __init__(self):
        super(WebCommand, self).__init__('web', 'Start obd deploy application as web.')
        self.parser.add_option('-p', '--port', type='int', help="web server listen port", default=8680)
        self.parser.add_option('-w', '--white', type='str', help="ip white list, eq: '127.0.0.1, 192.168.1.1'.", default='')

    def _do_command(self, obd):
        if COMMAND_ENV.get(const.ENCRYPT_PASSWORD) == '1':
            ROOT_IO.error('OBD Web has been disabled. Please execute the ` obd pwd encrypt disable ` command and try again')
            return False
        from service.app import OBDWeb
        # white_ip_list = self.get_white_ip_list()
        url = '/#/updateWelcome' if self.cmds and self.cmds[0] in ('upgrade', 'update') else ''

        if self.opts.port < 1024:
            ROOT_IO.error('The port number must be in the range of 1025-65535.')
            return False

        ROOT_IO.print('start OBD WEB in 0.0.0.0:%s' % self.opts.port)
        ROOT_IO.print('please open http://{0}:{1}{2}'.format(NetUtil.get_host_ip(), self.opts.port, url))
        try:
            COMMAND_ENV.set(ENV.ENV_DISABLE_PARALLER_EXTRACT, True, stdio=obd.stdio)
            OBDWeb(obd, None, self.OBD_INSTALL_PATH).start(self.opts.port)
        except KeyboardInterrupt:
            ROOT_IO.print('Keyboard Interrupt')
        except BaseException as e:
            ROOT_IO.exception('Runtime Error %s' % e)
        finally:
            ROOT_IO.print('stop OBD WEB')
        return True

class ClusterAutoDeployCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterAutoDeployCommand, self).__init__('autodeploy', 'Deploy a cluster automatically by using a simple configuration file.')
        self.parser.add_option('-c', '--config', type='string', help="Path to the configuration file.")
        self.parser.add_option('-f', '--force', action='store_true', help="Force autodeploy, overwrite the home_path.")
        self.parser.add_option('-C', '--clean', action='store_true', help="Clean the home_path if the directory belong to you.", default=False)
        self.parser.add_option('--generate-consistent-config', '--gcc', action='store_true', help="Generate consistent config")
        self.parser.add_option('-U', '--unuselibrepo', '--ulp', action='store_true', help="Disable OBD from installing the libs mirror automatically.")
        self.parser.add_option('-A', '--auto-create-tenant', '--act', action='store_true', help="Automatically create a tenant named `test` by using all the available resource of the cluster.")
        self.parser.add_option('--force-delete', action='store_true', help="Force delete, delete the registered cluster.")
        self.parser.add_option('-S', '--strict-check', action='store_true', help="Throw errors instead of warnings when check fails.")

    def _do_command(self, obd):
        if self.cmds:
            if getattr(self.opts, 'force', False) or getattr(self.opts, 'clean', False):
                setattr(self.opts, 'skip_cluster_status_check', True)
                obd.set_options(self.opts)
            name = self.cmds[0]
            if obd.genconfig(name):
                self.opts.config = ''
                obd.set_cmds(self.cmds[1:])
                res = obd.deploy_cluster(name) and obd.start_cluster(name)
                self.background_telemetry_task(obd)
                return res
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
        self.parser.add_option('-i', '--interactive', action='store_true', help="Interactive deployment cluster, including deployment and startup.")
        # self.parser.add_option('-F', '--fuzzymatch', action='store_true', help="enable fuzzy match when search package")

    def _do_command(self, obd):
        if getattr(self.opts, 'interactive'):
            name = self.cmds[0] if self.cmds else ''
            return obd.interactive_deploy(name)
        else:
            if self.cmds:
                if getattr(self.opts, 'force', False) or getattr(self.opts, 'clean', False):
                    setattr(self.opts, 'skip_cluster_status_check', True)
                    obd.set_options(self.opts)
                setattr(self.opts, 'check_root_user', True)
                res = obd.deploy_cluster(self.cmds[0])
                self.background_telemetry_task(obd)
                if res and COMMAND_ENV.get(const.INTERACTIVE_INSTALL, '0') == '0':
                    obd.stdio.print(FormatText.success('Please execute ` obd cluster start %s ` to start' % self.cmds[0]))
                return res
            else:
                return self._show_help()


class ClusterScaleoutCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterScaleoutCommand, self).__init__('scale_out', 'Scale out cluster with an additional deploy yaml file.')
        self.parser.add_option('-c', '--config', type='string', help="Path to the configuration yaml file.")
        self.parser.add_option('-f', '--force', action='store_true', help="Force deploy, overwrite the home_path.", default=False)
        self.parser.add_option('-C', '--clean', action='store_true', help="Clean the home path if the directory belong to you.", default=False)
        self.parser.add_option('-t', '--scale_out_timeout', type='int', help="Scale out timeout in seconds.", default=3600)

    def _do_command(self, obd):
        if self.cmds:
            return obd.scale_out(self.cmds[0])
        else:
            return self._show_help()


class ClusterComponentAddCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterComponentAddCommand, self).__init__('add', 'Add components for cluster')
        self.parser.add_option('-c', '--config', type='string', help="Path to the configuration yaml file.")
        self.parser.add_option('-f', '--force', action='store_true', help="Force deploy, overwrite the home_path.", default=False)
        self.parser.add_option('-C', '--clean', action='store_true', help="Clean the home path if the directory belong to you.", default=False)
        self.parser.add_option('--confirm', action='store_true', help='Confirm to restart the cluster after add ob-configserver.', default=False)

    def _do_command(self, obd):
        if self.cmds:
            return obd.add_components(self.cmds[0], need_confirm=not getattr(self.opts, 'confirm', False))
        else:
            return self._show_help()


class ClusterComponentDeleteCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterComponentDeleteCommand, self).__init__('del', 'Add components for cluster')
        self.parser.add_option('-f', '--force', action='store_true', help="Force delete components.", default=False)
        self.parser.add_option('--ignore-standby', '--igs', action='store_true', help="Force kill the observer while standby tenant in others cluster exists.")

    def init(self, cmd, args):
        super(ClusterComponentDeleteCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <component> ... [component]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if self.cmds and len(self.cmds) >= 2:
            return obd.delete_components(self.cmds[0], self.cmds[1:])
        else:
            return self._show_help()


class ClusterComponentMajorCommand(MajorCommand):

    def __init__(self):
        super(ClusterComponentMajorCommand, self).__init__('component', 'Add or delete component for cluster')
        self.register_command(ClusterComponentAddCommand())
        self.register_command(ClusterComponentDeleteCommand())


class ClusterStartCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterStartCommand, self).__init__('start', 'Start a deployed cluster.')
        self.parser.add_option('-s', '--servers', type='string', help="List of servers to be started. Multiple servers are separated with commas.")
        self.parser.add_option('-c', '--components', type='string', help="List of components to be started. Multiple components are separated with commas.")
        self.parser.add_option('-f', '--force-delete', action='store_true', help="Force delete, delete the registered cluster.")
        self.parser.add_option('-S', '--strict-check', action='store_true', help="Throw errors instead of warnings when check fails.")
        self.parser.add_option('--with-parameter', '--wp', action='store_true', help='Start with parameters.')
        self.parser.add_option('--service-names', '--sn', type='string', help='List of services to be started for PowerRAG. Multiple services are separated with commas.')

    def _do_command(self, obd):
        if self.cmds:
            obd.set_cmds(self.cmds[1:])
            res = obd.start_cluster(self.cmds[0])
            self.background_telemetry_task(obd)
            return res
        else:
            return self._show_help()


class ClusterStopCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterStopCommand, self).__init__('stop', 'Stop a started cluster.')
        self.parser.add_option('-s', '--servers', type='string', help="List of servers to be stoped. Multiple servers are separated with commas.")
        self.parser.add_option('-c', '--components', type='string', help="List of components to be stoped. Multiple components are separated with commas.")
        self.parser.add_option('--service-names', '--sn', type='string', help='List of services to be stoped for PowerRAG. Multiple services are separated with commas.')

    def _do_command(self, obd):
        if self.cmds:
            res = obd.stop_cluster(self.cmds[0])
            self.background_telemetry_task(obd)
            return res
        else:
            return self._show_help()


class ClusterDestroyCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterDestroyCommand, self).__init__('destroy', 'Destroy a deployed cluster.')
        self.parser.add_option('-f', '--force-kill', action='store_true', help="Force kill the running observer process in the working directory.")
        self.parser.add_option('--confirm', action='store_true', help='Confirm to destroy.')
        self.parser.add_option('--ignore-standby', '--igs', action='store_true', help="Force kill the observer while standby tenant in others cluster exists.")

    def _do_command(self, obd):
        if self.cmds:
            res = obd.destroy_cluster(self.cmds[0], need_confirm=not getattr(self.opts, 'confirm', False))
            return res
        else:
            return self._show_help()


class ClusterPruneConfigCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterPruneConfigCommand, self).__init__('prune-config', 'Remove configuration files for destroyed or configured clusters.')
        self.parser.add_option('--confirm', action='store_true', help='Confirm to prune configuration files.')

    def _do_command(self, obd):
        if self.cmds:
            res = obd.prune_config(self.cmds[0], need_confirm=not getattr(self.opts, 'confirm', False))
            return res
        else:
            return self._show_help()


class ClusterDisplayCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterDisplayCommand, self).__init__('display', 'Display the information for a cluster.')
        self.parser.add_option('--encryption-passkey', '--epk', type='string', help="Encryption passkey.")

    def _do_command(self, obd):
        if self.cmds:
            return obd.display_cluster(self.cmds[0])
        else:
            return self._show_help()


class ClusterRestartCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterRestartCommand, self).__init__('restart', 'Restart a started cluster.')
        self.parser.add_option('-s', '--servers', type='string', help="List of servers to be restarted. Multiple servers are separated with commas.")
        self.parser.add_option('-c', '--components', type='string', help="List of components to be restarted. Multiple components are separated with commas.")
        self.parser.add_option('--with-parameter', '--wp', action='store_true', help='Restart with parameters.')

    def _do_command(self, obd):
        if self.cmds:
            # if not getattr(self.opts, 'with_parameter', False):
            #     setattr(self.opts, 'without_parameter', True)
            obd.set_options(self.opts)
            res = obd.restart_cluster(self.cmds[0])
            self.background_telemetry_task(obd)
            return res
        else:
            return self._show_help()


class ClusterRedeployCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterRedeployCommand, self).__init__('redeploy', 'Redeploy a started cluster.')
        self.parser.add_option('-f', '--force-kill', action='store_true', help="Force kill the running observer process in the working directory.")
        self.parser.add_option('--confirm', action='store_true', help='Confirm to redeploy.')
        self.parser.add_option('--ignore-standby', '--igs', action='store_true', help="Force kill the observer while standby tenant in others cluster exists.")

    def _do_command(self, obd):
        if self.cmds:
            res = obd.redeploy_cluster(self.cmds[0], need_confirm=not getattr(self.opts, 'confirm', False))
            self.background_telemetry_task(obd)
            return res
        else:
            return self._show_help()


class ClusterReloadCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterReloadCommand, self).__init__('reload', 'Reload a started cluster.')

    def _do_command(self, obd):
        if self.cmds:
            res = obd.reload_cluster(self.cmds[0])
            self.background_telemetry_task(obd)
            return res
        else:
            return self._show_help()


class ClusterListCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterListCommand, self).__init__('list', 'List all the deployments.')
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

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
            ROOT_IO.default_confirm = False
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
            return obd.reinstall(self.cmds[0])
        else:
            return self._show_help()


class CLusterUpgradeCommand(ClusterMirrorCommand):

    def __init__(self):
        super(CLusterUpgradeCommand, self).__init__('upgrade', 'Upgrade a cluster.')
        self.parser.add_option('-c', '--component', type='string', help="Component name to upgrade.")
        self.parser.add_option('-V', '--version', type='string', help="Target version.")
        self.parser.add_option('--tag', type='string', help="Docker component tag.")
        self.parser.add_option('-i', '--image-name', type='string', help="Docker component image name.")
        self.parser.add_option('--skip-check', action='store_true', help="Skip all the possible checks.")
        self.parser.add_option('--usable', type='string', help="Hash list for priority mirrors, separated with `,`.", default='')
        self.parser.add_option('--disable', type='string', help="Hash list for disabled mirrors, separated with `,`.", default='')
        self.parser.add_option('-e', '--executer-path', type='string', help="Executer path.", default=os.path.join(ObdCommand.OBD_INSTALL_PATH, 'lib/executer'))
        self.parser.add_option('-t', '--script-query-timeout', type='string', help="The timeout(s) for executing sql in upgrade scripts. Supported since version 4.1.0", default='')
        self.parser.add_option('--ignore-standby', '--igs', action='store_true', help="Force upgrade, before upgrade standby tenant`s cluster.")
        self.parser.add_option('--oms-backup-path', type='string', help="Upgrade the OMS backup meta data directory", default=os.path.join(os.path.expanduser('~'), 'oms', 'meta_backup_data'))
        self.parser.add_option('--disable-oms-backup', '--dob', action='store_true', help="disable OMS backup meta data.")

    def _do_command(self, obd):
        oms_upgrade_mode = None
        if len(self.cmds) == 2 and self.cmds[1] in ['offline', 'online']:
            oms_upgrade_mode = self.cmds[1]
            del self.cmds[1]
        if self.cmds:
            res = obd.upgrade_cluster(self.cmds[0], oms_upgrade_mode)
            self.background_telemetry_task(obd)
            return res
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
        self.parser.add_option('--time-zone', type='string', help="Tenant time zone. The default tenant time_zone is [+08:00].")
        self.parser.add_option('-s', '--variables', type='string', help="Set the variables for the system tenant. [ob_tcp_invited_nodes='%'].", default="ob_tcp_invited_nodes='%'")
        self.parser.add_option('-o', '--optimize', type='string', help="Specify scenario optimization when creating a tenant, the default is consistent with the cluster dimension.\n{express_oltp, complex_oltp, olap, htap, kv}\nSupported since version 4.3.")
        self.parser.add_option('--password', type='string', help="When creating a tenant, set password for user.")

    def _do_command(self, obd):
        if len(self.cmds) == 1:
            setattr(self.opts, '%s_root_password' % getattr(self.opts, 'tenant_name', 'sys'), getattr(self.opts, 'password', ''))
            return obd.create_tenant(self.cmds[0])
        else:
            return self._show_help()


class ClusterTenantCreateStandByCommand(ClusterTenantCreateCommand):

    def __init__(self):
        super(ClusterTenantCreateStandByCommand, self).__init__()
        self.name = 'create-standby'
        self.summary = 'Create a standby tenant.'
        self.parser.remove_option('-t')
        self.parser.remove_option('--max-memory')
        self.parser.remove_option('--min-memory')
        self.parser.remove_option('--max-disk-size')
        self.parser.remove_option('--max-session-num')
        self.parser.remove_option('--mode')
        self.parser.remove_option('--charset')
        self.parser.remove_option('--collate')
        self.parser.remove_option('--logonly-replica-num')
        self.parser.remove_option('--tablegroup')
        self.parser.remove_option('-s')
        self.parser.add_option('-t', '-n', '--tenant-name', type='string', help="The standby tenant name. The default tenant name is consistent with the primary tenant name.", default='')
        self.parser.add_option('--standbyro-password', type='string', help="standbyro user password.")
        self.parser.add_option('-p', '--tenant-root-password', type='string', help="tenant root password,for crate standby user.")
        self.parser.add_option('--type', type='string', help="Standby tenant data sync mode. Supports 'SERVICE' and 'LOCATION' modes. Defaults: 'SERVICE'.", default='SERVICE')
        self.parser.add_option('-d', '--data_backup_uri', type='string',help='The path to the directory where the backups are stored.')
        self.parser.add_option('-a', '--archive_log_uri', type='string',help='The Path to the directory where archive logs are stored.')
        self.parser.add_option('-D', '--decryption', type='string', help='The decryption password for all backups. example: key1,key2,key3')


    def init(self, cmd, args):
        super(ClusterTenantCreateStandByCommand, self).init(cmd, args)
        self.parser.set_usage('%s <standby deploy name> <primary deploy name> <primary tenant name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 3:
            return obd.create_standby_tenant(self.cmds[0], self.cmds[1], self.cmds[2])
        else:
            return self._show_help()


class ClusterTenantSwitchoverCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantSwitchoverCommand, self).__init__('switchover', 'Switchover primary-standby tenant.')
        self.parser.add_option('-p', '--tenant-root-password', type='string', help="tenant root password")
        self.parser.add_option('--standbyro-password', type='string', help="standbyro user password.")
        self.parser.add_option('--standby_archive_log_uri', type='string', help='The storage directory path for standby tenant archive logs.')
        self.parser.add_option('--primary_archive_log_uri', type='string', help='The storage directory path for primary tenant archive logs.')

    def init(self, cmd, args):
        super(ClusterTenantSwitchoverCommand, self).init(cmd, args)
        self.parser.set_usage('%s <standby deploy name> <standby tenant name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            return obd.switchover_tenant(self.cmds[0], self.cmds[1])
        else:
            return self._show_help()


class ClusterTenantFailoverCommand(ClusterMirrorCommand):
    def __init__(self):
        super(ClusterTenantFailoverCommand, self).__init__('failover', 'failover standby tenant.')
        self.parser.add_option('-p', '--tenant-root-password', type='string', help="tenant root password")

    def init(self, cmd, args):
        super(ClusterTenantFailoverCommand, self).init(cmd, args)
        self.parser.set_usage('%s <standby deploy name> <standby tenant name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            self.cmds.append('failover')
            return obd.failover_decouple_tenant(self.cmds[0], self.cmds[1], self.cmds[2])
        else:
            return self._show_help()


class ClusterTenantDecoupleCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantDecoupleCommand, self).__init__('decouple', 'decouple standby tenant.')
        self.parser.add_option('-p', '--tenant-root-password', type='string', help="tenant root password")

    def init(self, cmd, args):
        super(ClusterTenantDecoupleCommand, self).init(cmd, args)
        self.parser.set_usage('%s <standby deploy name> <standby tenant name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            self.cmds.append('decouple')
            return obd.failover_decouple_tenant(self.cmds[0], self.cmds[1], self.cmds[2])
        else:
            return self._show_help()


class ClusterTenantDropCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantDropCommand, self).__init__('drop', 'Drop a tenant.')
        self.parser.add_option('-t', '-n', '--tenant-name', type='string', help="Tenant name.")
        self.parser.add_option('--ignore-standby', '--igs', action='store_true', help="Force drop tenant when it has standby tenant, the standby tenants will become unavailable.")

    def _do_command(self, obd):
        if self.cmds:
            return obd.drop_tenant(self.cmds[0])
        else:
            return self._show_help()


class ClusterTenantListCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantListCommand, self).__init__('show', 'Show the list of tenant.')
        self.parser.add_option('-t', '--tenant', type='string', help='Tenant name', default='')
        self.parser.add_option('-g', '--graph', action='store_true', help='view standby by graph')

    def _do_command(self, obd):
        if self.cmds:
            return obd.list_tenant(self.cmds[0])
        else:
            return self._show_help()


class ClusterTenantOptimizeCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantOptimizeCommand, self).__init__('optimize','Optimizing existing tenant scenarios')
        self.parser.add_option('-o', '--optimize', type='string', help='Optimize scenarios,the default is consistent with the cluster dimension.\n{express_oltp, complex_oltp, olap, htap, kv}\nSupported since version 4.3.')
        self.parser.add_option('-p', '--tenant-root-password', type='string', help="tenant root password.")

    def init(self, cmd, args):
        super(ClusterTenantOptimizeCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <tenant name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            return obd.tenant_optimize(self.cmds[0], self.cmds[1])
        else:
            return self._show_help()


class ClusterInitServerEnvCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterInitServerEnvCommand, self).__init__('init4env', 'Init server environment.')

    def _do_command(self, obd):
        if self.cmds:
            res = obd.init_cluster_env(self.cmds[0])
            return res
        else:
            return self._show_help()


class ClusterTenantSetBackupConfigCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantSetBackupConfigCommand, self).__init__('set-backup-config', 'Set backup config for tenant.')
        self.parser.add_option('-d', '--data_backup_uri', type='string', help='The directory path where the backup will be stored.')
        self.parser.add_option('-a', '--archive_log_uri', type='string', help='The directory path where the archive logs will be stored.')
        self.parser.add_option('-c', '--log_archive_concurrency', type='int', help='Configure the total number of working threads for log archiving.')
        self.parser.add_option('-b', '--binding', type='string', help="Set the archiving and business priority mode. Supports 'OPTIONAL' and 'MANDATORY' modes. Defaults: 'OPTIONAL'.")
        self.parser.add_option('-s', '--ha_low_thread_score', type='int', help='Specifies the number of current working threads for low-priority threads.')
        self.parser.add_option('-i', '--piece_switch_interval', type='string', help='Configure the piece switch interval. Range: [1d, 7d].')
        self.parser.add_option('-l', '--archive_lag_target', type='string', help='Sets the target lag time for log archiving processes.')
        self.parser.add_option('-D', '--delete_policy', type='string', help="Policy for deleting backup data. Only supports 'default'.")
        self.parser.add_option('-r', '--delete_recovery_window', type='string', help='Defines the recovery window for which data delete policies apply.')

    def init(self, cmd, args):
        super(ClusterTenantSetBackupConfigCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <tenant name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            return obd.tenant_set_backup_config(self.cmds[0], self.cmds[1])
        else:
            return self._show_help()


class ClusterTenantBackupCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantBackupCommand, self).__init__('backup', 'Backup the specified tenant.')
        self.parser.add_option('-m', '--backup_mode', type='string', help="The backup mode: 'incremental' for incremental backup or 'full' for a full backup. Defaults: 'full'.")
        self.parser.add_option('-e', '--encryption', type='string', help='The password for encrypting the backup set.')
        self.parser.add_option('-P', '--plus_archive', type='string', help='Whether to include archive logs within the backup process for a combined data and log backup.')

    def init(self, cmd, args):
        super(ClusterTenantBackupCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <tenant name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            return obd.tenant_backup(self.cmds[0], self.cmds[1])
        else:
            return self._show_help()


class ClusterTenantRestoreCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantRestoreCommand, self).__init__('restore', 'Restore tenant from backup.')
        self.parser.add_option('-z', '--zone', type='string', help='The zones of the tenant. example: zone1,zone2,zone3')
        self.parser.add_option('--unit-num', type='int', help='The number of units in each zone. Default: 1.', default=1)
        self.parser.add_option('--replica-type ', type='string', help='The replica type of the tenant.')
        self.parser.add_option('-p', '--primary-zone', type='string', help="The primary zone of the tenant to be restored.")
        self.parser.add_option('-T', '--timestamp', type='string', help='The timestamp to restore to.')
        self.parser.add_option('-S', '--scn', type='int', help="The SCN to restore to. Default: 0.")
        self.parser.add_option('-s', '--ha-high-thread-score', type='int', help='The high thread score for HA. Range: [0, 100]')
        self.parser.add_option('-c', '--concurrency', type='int', help='The number of threads to use for the restore operation.')
        self.parser.add_option('-D', '--decryption', type='string', help='The decryption password for all backups. example: key1,key2,key3')
        self.parser.add_option('-k', '--kms-encrypt-info', type='string', help='The KMS encryption information.')
        self.parser.add_option('--memory-size', type='string', help='The memory size of the resource unit config')
        self.parser.add_option('--max-cpu', type='int', help='The max cpu of the resource unit config, should be greater than 1.')
        self.parser.add_option('--min-cpu', type='int', help='The min cpu of the resource unit config, should be greater than 1.If not set, the min cpu will be set to the max cpu.')
        self.parser.add_option('--max-iops', type='int', help='The max iops of the resource unit config.If not set, the max iops will be set default value by observer.')
        self.parser.add_option('--min-iops', type='int', help='The min iops of the resource unit config.If not set, the min iops will be set default value by observer.')
        self.parser.add_option('--log-disk-size', type='string', help='The log disk size of the resource unit config.If not set, the log disk size will be set default value by observer.')

    def init(self, cmd, args):
        super(ClusterTenantRestoreCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <tenant name> <data backup uri> <archive log uri> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 4:
            return obd.tenant_restore(self.cmds[0], self.cmds[1], self.cmds[2], self.cmds[3])
        else:
            return self._show_help()


class ClusterTenantQueryBackupTaskCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantQueryBackupTaskCommand, self).__init__('backup-show', 'Show backup task.')

    def init(self, cmd, args):
        super(ClusterTenantQueryBackupTaskCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <tenant name>' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            return obd.query_backup_or_restore_task(self.cmds[0], self.cmds[1], 'backup')
        else:
            return self._show_help()


class ClusterTenantQueryRestoreTaskCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantQueryRestoreTaskCommand, self).__init__('restore-show', 'Show restore task.')

    def init(self, cmd, args):
        super(ClusterTenantQueryRestoreTaskCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <tenant name>' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            return obd.query_backup_or_restore_task(self.cmds[0], self.cmds[1], 'restore')
        else:
            return self._show_help()


class ClusterTenantCancelBackupTaskCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantCancelBackupTaskCommand, self).__init__('backup-cancel', 'Cancel task for backup.')

    def init(self, cmd, args):
        super(ClusterTenantCancelBackupTaskCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <tenant name>' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            return obd.cancel_backup_or_restore_task(self.cmds[0], self.cmds[1], 'backup')
        else:
            return self._show_help()


class ClusterTenantCancelRestoreTaskCommand(ClusterMirrorCommand):

    def __init__(self):
        super(ClusterTenantCancelRestoreTaskCommand, self).__init__('restore-cancel', 'Cancel task for restore.')

    def init(self, cmd, args):
        super(ClusterTenantCancelRestoreTaskCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <tenant name>' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            return obd.cancel_backup_or_restore_task(self.cmds[0], self.cmds[1], 'restore')
        else:
            return self._show_help()

class ClusterTenantRecoverCommand(ClusterMirrorCommand):
    def __init__(self):
        super(ClusterTenantRecoverCommand, self).__init__('recover', 'Modify the recovery target of the new standby tenant')
        self.parser.add_option('-T', '--timestamp', type='string', help='The timestamp to restore to.')
        self.parser.add_option('-S', '--scn', type='int', help="The SCN to restore to.")
        self.parser.add_option('-u', '--unlimited', action='store_true', help="Continuously replay archived source logs")

    def init(self, cmd, args):
        super(ClusterTenantRecoverCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <tenant name>' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            return obd.log_recover(self.cmds[0], self.cmds[1])
        else:
            return self._show_help()

class ClusterTenantSwitchLogSourceCommand(ClusterMirrorCommand):
    def __init__(self):
        super(ClusterTenantSwitchLogSourceCommand, self).__init__('switch-log-source', 'Switch standby tenant sync mode')
        self.parser.add_option('--type', type='string', help="Standby tenant data sync mode. Supports 'SERVICE' and 'LOCATION' modes. Defaults: 'SERVICE'.", default='SERVICE')
        self.parser.add_option('-a', '--archive_log_uri', type='string',help='The Path to the directory where archive logs are stored.')
        self.parser.add_option('-p', '--tenant-root-password', type='string', help="tenant root password,for crate standby user.")
        self.parser.add_option('--standbyro-password', type='string', help="standbyro user password.")

    def init(self, cmd, args):
        super(ClusterTenantSwitchLogSourceCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <tenant name>' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 2:
            return obd.switch_log_source(self.cmds[0], self.cmds[1])
        else:
            return self._show_help()


class ClusterTenantCommand(MajorCommand):

    def __init__(self):
        super(ClusterTenantCommand, self).__init__('tenant', 'Create, drop or list a tenant.')
        self.register_command(ClusterTenantCreateCommand())
        self.register_command(ClusterTenantDropCommand())
        self.register_command(ClusterTenantListCommand())
        self.register_command(ClusterTenantCreateStandByCommand())
        self.register_command(ClusterTenantSwitchoverCommand())
        self.register_command(ClusterTenantFailoverCommand())
        self.register_command(ClusterTenantDecoupleCommand())
        self.register_command(ClusterTenantOptimizeCommand())
        self.register_command(ClusterTenantSetBackupConfigCommand())
        self.register_command(ClusterTenantBackupCommand())
        self.register_command(ClusterTenantRestoreCommand())
        self.register_command(ClusterTenantQueryBackupTaskCommand())
        self.register_command(ClusterTenantQueryRestoreTaskCommand())
        self.register_command(ClusterTenantCancelBackupTaskCommand())
        self.register_command(ClusterTenantCancelRestoreTaskCommand())
        self.register_command(ClusterTenantRecoverCommand())
        self.register_command(ClusterTenantSwitchLogSourceCommand())


class ClusterMajorCommand(MajorCommand):

    def __init__(self):
        super(ClusterMajorCommand, self).__init__('cluster', 'Deploy and manage a cluster.')
        self.register_command(ClusterCheckForOCPChange())
        self.register_command(ClusterExportToOCPCommand())
        self.register_command(ClusterConfigStyleChange())
        self.register_command(ClusterAutoDeployCommand())
        self.register_command(ClusterDeployCommand())
        self.register_command(ClusterStartCommand())
        self.register_command(ClusterStopCommand())
        self.register_command(ClusterDestroyCommand())
        self.register_command(ClusterPruneConfigCommand())
        self.register_command(ClusterDisplayCommand())
        self.register_command(ClusterListCommand())
        self.register_command(ClusterRestartCommand())
        self.register_command(ClusterRedeployCommand())
        self.register_command(ClusterEditConfigCommand())
        self.register_command(ClusterReloadCommand())
        self.register_command(ClusterReloadCommand())
        self.register_command(CLusterUpgradeCommand())
        self.register_command(ClusterChangeRepositoryCommand())
        self.register_command(ClusterTenantCommand())
        self.register_command(ClusterScaleoutCommand())
        self.register_command(ClusterComponentMajorCommand())
        self.register_command(ClusterTakeoverCommand())
        self.register_command(ClusterInitServerEnvCommand())


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
        self.parser.add_option('--threads', type='string', help='Number of threads to use. [16]', default='16')
        self.parser.add_option('--time', type='int', help='Limit for total execution time in seconds. [60]', default=60)
        self.parser.add_option('--interval', type='int', help='Periodically report intermediate statistics with a specified time interval in seconds. 0 disables intermediate reports. [10]', default=10)
        self.parser.add_option('--events', type='int', help='Limit for total number of events.')
        self.parser.add_option('--rand-type', type='string', help='Random numbers distribution {uniform,gaussian,special,pareto}.')
        self.parser.add_option('--percentile', type='int', help='Percentile to calculate in latency statistics. Available values are 1-100. 0 means to disable percentile calculations.')
        self.parser.add_option('--skip-trx', type='string', help='Open or close a transaction in a read-only test. {on/off}')
        self.parser.add_option('-O', '--optimization', type='int', help='Optimization level {0/1/2}. [1] 0 - No optimization. 1 - Optimize some of the parameters which do not need to restart servers. 2 - Optimize all the parameters and maybe RESTART SERVERS for better performance.', default=1)
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
        self.parser.add_option('--direct-load', action='store_true', help="Enable load data by direct feature.")
        self.parser.add_option('--parallel', type='int', help='The degree of parallelism for loading data. [max_cpu * unit_count]')

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
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

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
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

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


class CommandsCommand(ObdCommand):

    def init(self, cmd, args):
        super(CommandsCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> <command> [options]' % self.prev_cmd)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def __init__(self):
        super(CommandsCommand, self).__init__('command', 'Common tool commands')
        self.parser.add_option('-c', '--components', type='string', help='The components used by the command. The first component in the configuration will be used by default in interactive commands, and all available components will be used by default in non-interactive commands.')
        self.parser.add_option('-s', '--servers', type='string', help='The servers used by the command. The first server in the configuration will be used by default in interactive commands, and all available servers will be used by default in non-interactive commands.')
        self.parser.undefine_warn = False

    def _do_command(self, obd):
        if len(self.cmds) in [2, 3]:
            return obd.commands(self.cmds[0], self.cmds[1], self.opts)
        else:
            return self._show_help()


class ToolCommand(MajorCommand):

    def __init__(self):
        super(ToolCommand, self).__init__('tool', 'Tools')
        self.register_command(DbConnectCommand())
        self.register_command(CommandsCommand())
        self.register_command(DoobaCommand())
        self.register_command(ToolListCommand())
        self.register_command(ToolInstallCommand())
        self.register_command(ToolUninstallCommand())
        self.register_command(ToolUpdateCommand())


class BenchMajorCommand(MajorCommand):

    def __init__(self):
        super(BenchMajorCommand, self).__init__('bench', '')


class UpdateCommand(ObdCommand):

    def __init__(self):
        super(UpdateCommand, self).__init__('update', 'Update OBD.')

    def do_command(self):
        uid = os.getuid()
        if uid != 0 and not DirectoryUtil.get_owner(self.OBD_INSTALL_PRE):
            ROOT_IO.error('To update OBD, you must be the owner of %s.' % self.OBD_INSTALL_PRE)
            return False
        return super(UpdateCommand, self).do_command()
    
    def _do_command(self, obd):
        return obd.update_obd(VERSION, self.OBD_INSTALL_PRE, self.OBD_INSTALL_PATH)


class DisplayTraceCommand(ObdCommand):

    def __init__(self):
        super(DisplayTraceCommand, self).__init__('display-trace', 'display trace_id log.')
        self.has_trace = False

    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    @property
    def enable_log(self):
        return False

    def _do_command(self, obd):
        from ssh import LocalClient
        if not self.cmds:
            return self._show_help()
        log_dir = os.path.join(obd.home_path, 'log/obd')
        trace_id = self.cmds[0]
        ROOT_IO.verbose('Get log by trace_id')
        try:
            if UUID(trace_id).version != 1:
                ROOT_IO.critical('%s is not trace id' % trace_id)
                return False
        except:
            ROOT_IO.print('%s is not trace id' % trace_id)
            return False
        cmd = 'grep -h "\[{}\]" $(ls -tr {}*) | sed "s/\[{}\] //g" '.format(trace_id, log_dir, trace_id)
        data = LocalClient.execute_command(cmd)
        ROOT_IO.print(data.stdout)
        return True


class ObdiagCommand(ObdCommand):

    def __init__(self):
        super(ObdiagCommand, self).__init__('obdiag', 'Oceanbase Diagnostic Tool')

    def _do_command(self, obd):
        args = copy.copy(self.args)
        if args[0]=="deploy" and len(args)==1:
            ROOT_IO.print("Use 'obd tool install %s' instead" % COMP_OCEANBASE_DIAGNOSTIC_TOOL)
            return obd.install_tool(COMP_OCEANBASE_DIAGNOSTIC_TOOL)
        for i in range(len(self.args)):
            if isinstance(self.args[i], str) and (self.args[i].startswith('--') or self.args[i].startswith('-')):
                if self.args[i] == "--help" or self.args[i] == "-h":
                    return obd.obdiag_func(self.args, None)
                else:
                    args.remove(self.args[i-1])
                    return obd.obdiag_func(args, self.args[i-1])
        if len(self.args) > 0:
            args.remove(self.args[-1])
            return obd.obdiag_func(args, self.args[-1])
        else:
            return self._show_help() 


class ObdiagCommandBak(MajorCommand):
    
    def __init__(self):
        super(ObdiagCommand, self).__init__('obdiag', 'Oceanbase Diagnostic Tool')
        self.register_command(ObdiagDeployCommand())
        self.register_command(ObdiagGatherCommand())
        self.register_command(ObdiagAnalyzeCommand())
        self.register_command(ObdiagCheckCommand())
        self.register_command(ObdiagRcaCommand())
        self.register_command(ObdiagUpdateSceneCommand())


class ObdiagDeployCommand(ObdCommand):


    def __init__(self):
        super(ObdiagDeployCommand, self).__init__('deploy', 'deploy obdiag')
        self.parser.allow_undefine = True
        self.parser.undefine_warn = False

    def _do_command(self, obd):
        ROOT_IO.print("Use 'obd tool install %s' instead" % COMP_OCEANBASE_DIAGNOSTIC_TOOL)
        return obd.install_tool(COMP_OCEANBASE_DIAGNOSTIC_TOOL)


class ObdiagGatherMirrorCommand(ObdCommand):
    
    def init(self, cmd, args):
        super(ObdiagGatherMirrorCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if self.cmds:
            return obd.obdiag_online_func(self.cmds[0], "gather_%s" % self.name, self.opts)
        else:
            return self._show_help()


class ObdiagGatherCommand(MajorCommand):
    
    def __init__(self):
        super(ObdiagGatherCommand, self).__init__('gather', 'Gather oceanbase diagnostic info')
        self.register_command(ObdiagGatherAllCommand())
        self.register_command(ObdiagGatherLogCommand())
        self.register_command(ObdiagGatherSysStatCommand())
        self.register_command(ObdiagGatherStackCommand())
        self.register_command(ObdiagGatherPerfCommand())
        self.register_command(ObdiagGatherSlogCommand())
        self.register_command(ObdiagGatherClogCommand())
        self.register_command(ObdiagGatherPlanMonitorCommand())
        self.register_command(ObdiagGatherObproxyLogCommand())
        self.register_command(ObdiagGatherSceneCommand())
        self.register_command(ObdiagGatherAshReportCommand())


class ObdiagGatherSceneCommand(MajorCommand):
    
    def __init__(self):
        super(ObdiagGatherSceneCommand, self).__init__('scene', 'Gather scene diagnostic info')
        self.register_command(ObdiagGatherSceneListCommand())
        self.register_command(ObdiagGatherSceneRunCommand())


class ObdiagRcaCommand(MajorCommand):
    
    def __init__(self):
        super(ObdiagRcaCommand, self).__init__('rca', 'root cause analysis of oceanbase problem')
        self.register_command(ObdiagRcaListCommand())
        self.register_command(ObdiagRcaRunCommand())


class ObdiagGatherAllCommand(ObdiagGatherMirrorCommand):

    def init(self, cmd, args):
        super(ObdiagGatherAllCommand, self).init(cmd, args)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def __init__(self):
        super(ObdiagGatherAllCommand, self).__init__('all', 'Gather oceanbase diagnostic info')
        self.parser.add_option('--from', type='string', help="specify the start of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--to', type='string', help="specify the end of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--since', type='string',  help="Specify time range that from 'n' [d]ays, 'n' [h]ours or 'n' [m]inutes. before to now. format: <n> <m|h|d>. example: 1h.",default='30m')
        self.parser.add_option('--scope', type='string', help="log type constrains, choices=[observer, election, rootservice, all]",default='all')
        self.parser.add_option('--grep', type='string', help="specify keywords constrain")
        self.parser.add_option('--encrypt', type='string', help="Whether the returned results need to be encrypted, choices=[true, false]", default="false")
        self.parser.add_option('--store_dir', type='string', help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir",default=OBDIAG_HOME_PATH)

class ObdiagGatherLogCommand(ObdiagGatherMirrorCommand):
    
    def init(self, cmd, args):
        super(ObdiagGatherLogCommand, self).init(cmd, args)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def __init__(self):
        super(ObdiagGatherLogCommand, self).__init__('log', 'Gather oceanbase logs from oceanbase machines')
        self.parser.add_option('--from', type='string', help="specify the start of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--to', type='string', help="specify the end of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--since', type='string',  help="Specify time range that from 'n' [d]ays, 'n' [h]ours or 'n' [m]inutes. before to now. format: <n> <m|h|d>. example: 1h.",default='30m')
        self.parser.add_option('--scope', type='string', help="log type constrains, choices=[observer, election, rootservice, all]",default='all')
        self.parser.add_option('--grep', type='string', help="specify keywords constrain")
        self.parser.add_option('--encrypt', type='string', help="Whether the returned results need to be encrypted, choices=[true, false]", default="false")
        self.parser.add_option('--store_dir', type='string', help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir",default=OBDIAG_HOME_PATH)


class ObdiagGatherSysStatCommand(ObdiagGatherMirrorCommand):
    
    def init(self, cmd, args):
        super(ObdiagGatherSysStatCommand, self).init(cmd, args)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def __init__(self):
        super(ObdiagGatherSysStatCommand, self).__init__('sysstat', 'Gather Host information')
        self.parser.add_option('--store_dir', type='string', help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir",default=OBDIAG_HOME_PATH)


class ObdiagGatherStackCommand(ObdiagGatherMirrorCommand):
    
    def init(self, cmd, args):
        super(ObdiagGatherStackCommand, self).init(cmd, args)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def __init__(self):
        super(ObdiagGatherStackCommand, self).__init__('stack', 'Gather stack')
        self.parser.add_option('--store_dir', type='string', help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir",default=OBDIAG_HOME_PATH)


class ObdiagGatherPerfCommand(ObdiagGatherMirrorCommand):
    
    def init(self, cmd, args):
        super(ObdiagGatherPerfCommand, self).init(cmd, args)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def __init__(self):
        super(ObdiagGatherPerfCommand, self).__init__('perf', 'Gather perf')
        self.parser.add_option('--store_dir', type='string', help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--scope', type='string', help="perf type constrains, choices=[sample, flame, pstack, all]",default='all')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir",default=OBDIAG_HOME_PATH)


class ObdiagGatherSlogCommand(ObdiagGatherMirrorCommand):
    
    def init(self, cmd, args):
        super(ObdiagGatherSlogCommand, self).init(cmd, args)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def __init__(self):
        super(ObdiagGatherSlogCommand, self).__init__('slog', 'Gather slog')
        self.parser.add_option('--from', type='string', help="specify the start of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--to', type='string', help="specify the end of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--since', type='string',  help="Specify time range that from 'n' [d]ays, 'n' [h]ours or 'n' [m]inutes. before to now. format: <n> <m|h|d>. example: 1h.",default='30m')
        self.parser.add_option('--encrypt', type='string', help="Whether the returned results need to be encrypted, choices=[true, false]", default="false")
        self.parser.add_option('--store_dir', type='string', help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir",default=OBDIAG_HOME_PATH)


class ObdiagGatherClogCommand(ObdiagGatherMirrorCommand):
    
    def init(self, cmd, args):
        super(ObdiagGatherClogCommand, self).init(cmd, args)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def __init__(self):
        super(ObdiagGatherClogCommand, self).__init__('clog', 'Gather clog')
        self.parser.add_option('--from', type='string', help="specify the start of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--to', type='string', help="specify the end of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--since', type='string',  help="Specify time range that from 'n' [d]ays, 'n' [h]ours or 'n' [m]inutes. before to now. format: <n> <m|h|d>. example: 1h.",default='30m')
        self.parser.add_option('--encrypt', type='string', help="Whether the returned results need to be encrypted, choices=[true, false]", default="false")
        self.parser.add_option('--store_dir', type='string', help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir",default=OBDIAG_HOME_PATH)


class ObdiagGatherPlanMonitorCommand(ObdiagGatherMirrorCommand):
    
    def init(self, cmd, args):
        super(ObdiagGatherPlanMonitorCommand, self).init(cmd, args)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def __init__(self):
        super(ObdiagGatherPlanMonitorCommand, self).__init__('plan_monitor', 'Gather ParalleSQL information')
        self.parser.add_option('--trace_id', type='string', help='sql trace id')
        self.parser.add_option('--store_dir', type='string', help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--env', type='string', help='''env, eg: "{db_connect='-h127.0.0.1 -P2881 -utest@test -p****** -Dtest'}"''')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir",default=OBDIAG_HOME_PATH)


class ObdiagGatherObproxyLogCommand(ObdiagGatherMirrorCommand):
    
    def init(self, cmd, args):
        super(ObdiagGatherObproxyLogCommand, self).init(cmd, args)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def __init__(self):
        super(ObdiagGatherObproxyLogCommand, self).__init__('obproxy_log', 'Gather obproxy log from obproxy machines')
        self.parser.add_option('--from', type='string', help="specify the start of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--to', type='string', help="specify the end of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--since', type='string',  help="Specify time range that from 'n' [d]ays, 'n' [h]ours or 'n' [m]inutes. before to now. format: <n> <m|h|d>. example: 1h.",default='30m')
        self.parser.add_option('--scope', type='string', help="log type constrains, choices=[obproxy, obproxy_limit, obproxy_stat, obproxy_digest, obproxy_slow, obproxy_diagnosis, obproxy_error, all]", default='all')
        self.parser.add_option('--grep', type='string', help="specify keywords constrain")
        self.parser.add_option('--encrypt', type='string', help="Whether the returned results need to be encrypted, choices=[true, false]", default="false")
        self.parser.add_option('--store_dir', type='string', help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir",default=OBDIAG_HOME_PATH)


class ObdiagGatherSceneListCommand(ObdCommand):

    def __init__(self):
        super(ObdiagGatherSceneListCommand, self).__init__('list', 'root cause analysis of oceanbase problem list')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir",default=OBDIAG_HOME_PATH)
    
    def init(self, cmd, args):
        super(ObdiagGatherSceneListCommand, self).init(cmd, args)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def _do_command(self, obd):
        return obd.obdiag_offline_func("gather_scene_list", self.opts)


class ObdiagGatherSceneRunCommand(ObdCommand):

    def __init__(self):
        super(ObdiagGatherSceneRunCommand, self).__init__('run', 'root cause analysis of oceanbase problem')
        self.parser.add_option('--scene', type='string', help="Specify the scene to be gather")
        self.parser.add_option('--from', type='string', help="specify the start of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--to', type='string', help="specify the end of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--since', type='string',  help="Specify time range that from 'n' [d]ays, 'n' [h]ours or 'n' [m]inutes. before to now. format: <n> <m|h|d>. example: 1h.",default='30m')
        self.parser.add_option('--env', type='string', help='env, eg: "{env1=xxx, env2=xxx}"')
        self.parser.add_option('--store_dir', type='string', help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir",default=OBDIAG_HOME_PATH)
    
    def init(self, cmd, args):
        super(ObdiagGatherSceneRunCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> [options]' % self.prev_cmd)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def _do_command(self, obd):
        if len(self.cmds) > 0:
            return obd.obdiag_online_func(self.cmds[0], "gather_scene_run", self.opts)
        else:
            return self._show_help()


class ObdiagGatherAshReportCommand(ObdCommand):

    def __init__(self):
        super(ObdiagGatherAshReportCommand, self).__init__('ash', 'Gather ash report')
        self.parser.add_option('--trace_id', type='string',
                               help="The TRACE.ID of the SQL to be sampled, if left blank or filled with NULL, indicates that TRACE.ID is not restricted.")
        self.parser.add_option('--sql_id', type='string',
                               help="The SQL.ID, if left blank or filled with NULL, indicates that SQL.ID is not restricted.")
        self.parser.add_option('--wait_class', type='string',
                               help='Event types to be sampled.')
        self.parser.add_option('--report_type', type='string',
                               help='Report type, currently only supports text type.', default='TEXT')
        self.parser.add_option('--from', type='string',
                               help="specify the start of the time range. format: 'yyyy-mm-dd hh:mm:ss'")
        self.parser.add_option('--to', type='string',
                               help="specify the end of the time range. format: 'yyyy-mm-dd hh:mm:ss'")
        self.parser.add_option('--store_dir', type='string',
                               help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir", default=OBDIAG_HOME_PATH)

    def init(self, cmd, args):
        super(ObdiagGatherAshReportCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> [options]' % self.prev_cmd)
        return self

    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def _do_command(self, obd):
        if len(self.cmds) > 0:
            return obd.obdiag_online_func(self.cmds[0], "gather_ash", self.opts)
        else:
            return self._show_help()

class ObdiagAnalyzeMirrorCommand(ObdCommand):
    
    def init(self, cmd, args):
        super(ObdiagAnalyzeMirrorCommand, self).init(cmd, args)
        self.parser.set_usage('%s [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        offline_args_sign = '--files'
        if self.args and (offline_args_sign in self.args):
            return obd.obdiag_offline_func("analyze_%s" % self.name, self.opts)
        if self.cmds:
            return obd.obdiag_online_func(self.cmds[0], "analyze_%s" % self.name, self.opts)
        else:
            return self._show_help()


class ObdiagAnalyzeCommand(MajorCommand):
    
    def __init__(self):
        super(ObdiagAnalyzeCommand, self).__init__('analyze', 'Analyze oceanbase diagnostic info')
        self.register_command(ObdiagAnalyzeLogCommand())
        self.register_command(ObdiagAnalyzeFltTraceCommand())

class ObdiagAnalyzeLogCommand(ObdiagAnalyzeMirrorCommand):
    
    def init(self, cmd, args):
        super(ObdiagAnalyzeLogCommand, self).init(cmd, args)
        self.parser.set_usage(
            '%s <deploy name> [options]' % self.prev_cmd)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def __init__(self):
        super(ObdiagAnalyzeLogCommand, self).__init__('log', 'Analyze oceanbase log from online observer machines or offline oceanbase log files')
        self.parser.add_option('--from', type='string', help="specify the start of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--to', type='string', help="specify the end of the time range. format: yyyy-mm-dd hh:mm:ss")
        self.parser.add_option('--since', type='string',  help="Specify time range that from 'n' [d]ays, 'n' [h]ours or 'n' [m]inutes. before to now. format: <n> <m|h|d>. example: 1h.",default='30m')
        self.parser.add_option('--scope', type='string', help="log type constrains, choices=[observer, election, rootservice, all]",default='all')
        self.parser.add_option('--grep', type='string', help="specify keywords constrain")
        self.parser.add_option('--log_level', type='string', help="oceanbase logs greater than or equal to this level will be analyze, choices=[DEBUG, TRACE, INFO, WDIAG, WARN, EDIAG, ERROR]")
        self.parser.add_option('--files', type='string', help="specify files")
        self.parser.add_option('--store_dir', type='string', help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir",default=OBDIAG_HOME_PATH)


class ObdiagAnalyzeFltTraceCommand(ObdiagAnalyzeMirrorCommand):
    
    def init(self, cmd, args):
        super(ObdiagAnalyzeFltTraceCommand, self).init(cmd, args)
        self.parser.set_usage(
            '%s <deploy name> [options]' % self.prev_cmd)
        return self
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def __init__(self):
        super(ObdiagAnalyzeFltTraceCommand, self).__init__('flt_trace', 'Analyze oceanbase trace.log from online observer machines or offline oceanbase trace.log files')
        self.parser.add_option('--flt_trace_id', type='string', help="flt trace id, . format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        self.parser.add_option('--files', type='string', help="specify files")
        self.parser.add_option('--top', type='string', help="top leaf span", default=5)
        self.parser.add_option('--recursion', type='string', help="Maximum number of recursion", default=8)
        self.parser.add_option('--output', type='string', help="Print the result to the maximum output line on the screen", default=60)
        self.parser.add_option('--store_dir', type='string', help='the dir to store gather result, current dir by default.', default='./')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir", default=OBDIAG_HOME_PATH)


class ObdiagCheckCommand(ObdCommand):
    
    def __init__(self):
        super(ObdiagCheckCommand, self).__init__('check', 'check oceanbase cluster')
        self.parser.add_option('--cases', type='string', help="The name of the check task set that needs to be executed")
        self.parser.add_option('--store_dir', type='string', help='ouput report path', default='./check_report/')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir", default=OBDIAG_HOME_PATH)
    
    def init(self, cmd, args):
        super(ObdiagCheckCommand, self).init(cmd, args)
        self.parser.set_usage(
            '%s <deploy name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) > 0:
            return obd.obdiag_online_func(self.cmds[0], "checker", self.opts)
        else:
            return self._show_help()

class ObdiagRcaListCommand(ObdCommand):
    
    def __init__(self):
        super(ObdiagRcaListCommand, self).__init__('list', 'root cause analysis of oceanbase problem list')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir", default=OBDIAG_HOME_PATH)
    
    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def _do_command(self, obd):
        return obd.obdiag_offline_func("rca_list", self.opts)


class ObdiagRcaRunCommand(ObdCommand):
    
    def __init__(self):
        super(ObdiagRcaRunCommand, self).__init__('run', 'to run root cause analysis of oceanbase problem')
        self.parser.add_option('--scene', type='string', help="The name of the rca scene set that needs to be executed")
        self.parser.add_option('--store_dir', type='string', help='ouput result path', default='./rca/')
        self.parser.add_option('--input_parameters', type='string', help='parameters')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir", default=OBDIAG_HOME_PATH)
    
    def init(self, cmd, args):
        super(ObdiagRcaRunCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) > 0:
            return obd.obdiag_online_func(self.cmds[0], "rca_run", self.opts)
        else:
            return self._show_help()


class ObdiagUpdateSceneCommand(ObdCommand):
    
    def __init__(self):
        super(ObdiagUpdateSceneCommand, self).__init__('update', 'update obdiag scenes')
        self.parser.add_option('--file', type='string', help="obdiag update cheat file path")
        self.parser.add_option('--force', type='string', help='Force Update')
        self.parser.add_option('--obdiag_dir', type='string', help="obdiag install dir", default=OBDIAG_HOME_PATH)
    
    def init(self, cmd, args):
        super(ObdiagUpdateSceneCommand, self).init(cmd, args)
        self.parser.set_usage('%s [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        return obd.obdiag_offline_func("update_scene", self.opts)


class BinlogCommand(MajorCommand):

    def __init__(self):
        super(BinlogCommand, self).__init__('binlog', 'binlog service tools')
        self.register_command(BinlogCreateCommand())
        self.register_command(BinlogStartCommand())
        self.register_command(BinlogStopCommand())
        self.register_command(BinlogShowCommand())
        self.register_command(BinlogDropCommand())


class BinlogCreateCommand(ObdCommand):

    def __init__(self):
        super(BinlogCreateCommand, self).__init__('create', 'Apply binlog to create instance')
        self.parser.add_option('--replicate-num', type='int', help="Number of copies", default=1)
        self.parser.add_option('-d', '--obproxy-deployname', '--odp', type='string', help='Obproxy deploy name')
        self.parser.add_option('-p', '--cdcro-password', type='string', help='Password of user `cdcro`.If user already been created manually, you need to enter the password here.')

    def init(self, cmd, args):
        super(BinlogCreateCommand, self).init(cmd, args)
        self.parser.set_usage('%s <binlog deploy name>  <oceanbase deploy name> <ceanbase tenant name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 3:
            return obd.binlog_create_instance(self.cmds[0], self.cmds[1], self.cmds[2])
        else:
            return self._show_help()


class BinlogShowCommand(ClusterMirrorCommand):

    def __init__(self):
        super(BinlogShowCommand, self).__init__('show', 'Show the list of binlog instances')
        self.parser.add_option('-d', '--deploy-name', type='str', help="Oceanbase deploy name, must be entered together with `--tenant-name`")
        self.parser.add_option('-t', '-n', '--tenant-name', type='str', help='Tenant name, must be entered together with `--deploy-name`')

    def _do_command(self, obd):
        if len(self.cmds) == 1:
            return obd.show_binlog_instance(self.cmds[0])
        else:
            return self._show_help()


class BinlogStartCommand(ObdCommand):

    def __init__(self):
        super(BinlogStartCommand, self).__init__('start', 'Start binlog instance')

    def init(self, cmd, args):
        super(BinlogStartCommand, self).init(cmd, args)
        self.parser.set_usage('%s <binlog deploy name>  <oceanbase deploy name> <ceanbase tenant name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 3:
            return obd.start_binlog_instances(self.cmds[0], self.cmds[1], self.cmds[2])
        else:
            return self._show_help()


class BinlogStopCommand(ObdCommand):

    def __init__(self):
        super(BinlogStopCommand, self).__init__('stop', 'Stop binlog instance')

    def init(self, cmd, args):
        super(BinlogStopCommand, self).init(cmd, args)
        self.parser.set_usage('%s <binlog deploy name>  <oceanbase deploy name> <ceanbase tenant name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 3:
            return obd.stop_binlog_instances(self.cmds[0], self.cmds[1], self.cmds[2])
        else:
            return self._show_help()


class BinlogDropCommand(ObdCommand):

    def __init__(self):
        super(BinlogDropCommand, self).__init__('drop', 'Drop binlog instance')

    def init(self, cmd, args):
        super(BinlogDropCommand, self).init(cmd, args)
        self.parser.set_usage('%s <binlog deploy name>  <oceanbase deploy name> <ceanbase tenant name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 3:
            return obd.drop_binlog_instances(self.cmds[0], self.cmds[1], self.cmds[2])
        else:
            return self._show_help()


class HostCommand(MajorCommand):

    def __init__(self):
        super(HostCommand, self).__init__('host', 'Host tools')
        self.register_command(HostPrecheckCommand())
        self.register_command(HostInitCommand())
        self.register_command(HostUserCommand())


class HostUserCommand(MajorCommand):

    def __init__(self):
        super(HostUserCommand, self).__init__('user', 'Host user tools')
        self.register_command(HostUserInitCommand())


class HostPrecheckCommand(ObdCommand):

    def __init__(self):
        super(HostPrecheckCommand, self).__init__('precheck', 'Pre check host system parameters')
        self.parser.add_option('-p', '--password', type='str', help="Password of username, default is empty.")
        self.parser.add_option('-u', '--username', type='str', help="Users to be checked (default: ssh user).")
        self.parser.add_option('--ssh-key-file', type='string', help="ssh key file")

    def init(self, cmd, args):
        super(HostPrecheckCommand, self).init(cmd, args)
        self.parser.set_usage('%s [<ssh username>] [<server ip>]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        # Set default values: username = current user, ip = 127.0.0.1
        username = getpass.getuser() if len(self.cmds) == 0 else self.cmds[0]
        ip = '127.0.0.1' if len(self.cmds) <= 1 else self.cmds[1]
        
        if len(self.cmds) == 3 and self.cmds[2] == 'code100':
            cmd_ret = obd.precheck_host(username, ip, dev=True)
            if isinstance(cmd_ret, bool):
                return cmd_ret
            return CmdReturn(cmd_ret, cmd_ret)
        elif len(self.cmds) <= 2:
            # Normal case: 0, 1, or 2 arguments (defaults applied above)
            return obd.precheck_host(username, ip)
        else:
            return self._show_help()


class HostInitCommand(ObdCommand):

    def __init__(self):
        super(HostInitCommand, self).__init__('init', 'Init server environment.')
        self.parser.add_option('-p', '--password', type='str', help="Password of username, default is empty.")
        self.parser.add_option('-u', '--username', type='str', help="Users to be checked (default: ssh user).")
        self.parser.add_option('--ssh-key-file', type='string', help="ssh key file")

    def init(self, cmd, args):
        super(HostInitCommand, self).init(cmd, args)
        self.parser.set_usage('%s [<ssh username>] [<server ip>]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        # Set default values: username = current user, ip = 127.0.0.1
        username = getpass.getuser() if len(self.cmds) == 0 else self.cmds[0]
        ip = '127.0.0.1' if len(self.cmds) <= 1 else self.cmds[1]
        
        if len(self.cmds) == 3 and self.cmds[2] == 'code101':
            cmd_ret = obd.init_host(username, ip, dev=True)
            if isinstance(cmd_ret, bool):
                return cmd_ret
            return CmdReturn(cmd_ret, cmd_ret)
        elif len(self.cmds) <= 2:
            # Normal case: 0, 1, or 2 arguments (defaults applied above)
            return obd.init_host(username, ip)
        else:
            return self._show_help()


class HostUserInitCommand(ObdCommand):

    def __init__(self):
        super(HostUserInitCommand, self).__init__('init', 'Init host user.')
        self.parser.add_option('-u', '--username', type='str', help="username, default is admin.")
        self.parser.add_option('-p', '--password', type='str', help="Password of username.")
        self.parser.add_option('--host', type='str', help="host ip, default is 127.0.0.1.")

    def _do_command(self, obd):
        return obd.host_user_init()


class DevHostInitCommand(ObdCommand):

    def __init__(self):
        super(DevHostInitCommand, self).__init__('dev-init', 'Init server environment.')
        self.parser.add_option('-p', '--password', type='str', help="If passwordless login is enabled, the password parameter can be omitted during authentication.")

    def init(self, cmd, args):
        super(DevHostInitCommand, self).init(cmd, args)
        self.parser.set_usage('%s <username>  <server ip> ... [server ip]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) >= 2:
            cmd_ret = obd.init_host(self.cmds[0], self.cmds[1:], dev=True)
            if isinstance(cmd_ret, bool):
                return cmd_ret
            return CmdReturn(cmd_ret, cmd_ret)
        else:
            return self._show_help()



class ToolListCommand(ObdCommand):

    def __init__(self):
        super(ToolListCommand, self).__init__('list', 'list tool')

    @property
    def lock_mode(self):
        return LockMode.NO_LOCK

    def _do_command(self, obd):
        if self.cmds:
            return self._show_help()
        else:
            return obd.list_tools()


class ToolInstallCommand(ObdCommand):

    def __init__(self):
        super(ToolInstallCommand, self).__init__('install', 'install tool')
        self.parser.add_option('-V', '--version', type='string', help="The version of tool.")
        self.parser.add_option('-p', '--prefix', type='string', help="The install prefix path of tool.")
        self.parser.add_option('-y', '--assumeyes', action='store_true', help="answer yes for all questions", default=False)
        self.parser.add_option('-f', '--force', action='store_true', help="Force install if the tool is already present and conflicts between tools.", default=False)

    def init(self, cmd, args):
        super(ToolInstallCommand, self).init(cmd, args)
        self.parser.set_usage('%s <tool name> [options]' % self.prev_cmd)
        return self
    
    def _do_command(self, obd):
        if self.cmds:
            if self.opts.assumeyes:
                ROOT_IO.default_confirm = True
            setattr(self.opts, 'tool_install_flag', True)
            obd.set_options(self.opts)
            res = obd.install_tool(self.cmds[0])
            return res
        else:
            return self._show_help()


class ToolUninstallCommand(ObdCommand):

    def __init__(self):
        super(ToolUninstallCommand, self).__init__('uninstall', 'uninstall tool')
        self.parser.add_option('-y', '--assumeyes', action='store_true', help="answer yes for all questions", default=False)
        self.parser.add_option('-f', '--force', action='store_true', help="Force uninstall if the tool is already required by other tools.", default=False)

    def init(self, cmd, args):
        super(ToolUninstallCommand, self).init(cmd, args)
        self.parser.set_usage('%s <tool name> [options]' % self.prev_cmd)
        return self
    
    def _do_command(self, obd):
        if self.cmds:
            if self.opts.assumeyes:
                ROOT_IO.default_confirm = True
            res = obd.uninstall_tool(self.cmds[0])
            return res
        else:
            return self._show_help()


class ToolUpdateCommand(ObdCommand):

    def __init__(self):
        super(ToolUpdateCommand, self).__init__('update', 'update tool')
        self.parser.add_option('-V', '--version', type='string', help="The version of tool.")
        self.parser.add_option('-p', '--prefix', type='string', help="The install prefix path of tool.")
        self.parser.add_option('-y', '--assumeyes', action='store_true', help="answer yes for all questions", default=False)
        self.parser.add_option('-f', '--force', action='store_true', help="Force install if the tool is already present and conflicts between tools.", default=False)

    def init(self, cmd, args):
        super(ToolUpdateCommand, self).init(cmd, args)
        self.parser.set_usage('%s <tool name> [options]' % self.prev_cmd)
        return self
    
    def _do_command(self, obd):
        if self.cmds:
            if self.opts.assumeyes:
                ROOT_IO.default_confirm = True
            res = obd.update_tool(self.cmds[0])
            return res
        else:
            return self._show_help()

class LicenseCommand(MajorCommand):
    def __init__(self):
        super(LicenseCommand, self).__init__('license', 'Register and display license.')
        self.register_command(LicenseLoadCommand())
        self.register_command(LicenseDisplayCommand())

class LicenseLoadCommand(ObdCommand):
    def __init__(self):
        super(LicenseLoadCommand, self).__init__('load', 'Register license.')
        self.parser.add_option('-f', '--file', type='string', help="license file", default=None)

    def init(self, cmd, args):
        super(LicenseLoadCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name> [options]' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if self.cmds:
            return obd.load_license(self.cmds[0])
        else:
            return self._show_help()

class LicenseDisplayCommand(ObdCommand):
    def __init__(self):
        super(LicenseDisplayCommand, self).__init__('show', 'Show the license.')
    def init(self, cmd, args):
        super(LicenseDisplayCommand, self).init(cmd, args)
        self.parser.set_usage('%s <deploy name>' % self.prev_cmd)
        return self
    def _do_command(self, obd):
        if self.cmds:
            return obd.show_license(self.cmds[0])
        else:
            return self._show_help()


class PasswordMajorCommand(MajorCommand):
    def __init__(self):
        super(PasswordMajorCommand, self).__init__('pwd', 'Obd cluster password management.')
        self.register_command(EncryptionManagerCommand())
        self.register_command(SetPassKeyCommand())


class EncryptionManagerCommand(ObdCommand):
    def __init__(self):
        super(EncryptionManagerCommand, self).__init__('encrypt', 'Enable or disable encryption')
        self.parser.add_option('--encryption-passkey', '--epk', type='string', help="Encryption passkey.")

    def init(self, cmd, args):
        super(EncryptionManagerCommand, self).init(cmd, args)
        self.parser.set_usage('%s <enable or disable>' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 1 and self.cmds[0] in ['enable', 'disable']:
            return obd.encrypt_manager(self.cmds[0] == 'enable')
        else:
            return self._show_help()


class SetPassKeyCommand(ObdCommand):
    def __init__(self):
        super(SetPassKeyCommand, self).__init__('set-epk', 'Set encryption pass key.')
        self.parser.add_option('-c', '--current-passkey', type='string', help="Current encryption passkey")
        self.parser.add_option('-f', '--force', action='store_true', help="Force set passkey. ")

    def init(self, cmd, args):
        super(SetPassKeyCommand, self).init(cmd, args)
        self.parser.set_usage('%s <new decryption passkey>' % self.prev_cmd)
        return self

    def _do_command(self, obd):
        if len(self.cmds) == 1:
            return obd.set_encryption_passkey(self.cmds[0])
        else:
            return self._show_help()


class SeekdbMirrorCommand(ObdCommand):

    def init(self, cmd, args, need_deploy_name=True):
        super(SeekdbMirrorCommand, self).init(cmd, args)
        if need_deploy_name and not self.cmds:
            return self._show_help()
        return self


class SeekdbDeployCommand(SeekdbMirrorCommand):

    def __init__(self):
        super(SeekdbDeployCommand, self).__init__('deploy', 'Deploy a seekdb cluster.')
        self.parser.add_option('-f', '--force', action='store_true', help="Force deploy, clear the working directory.")
        self.parser.add_option('-C', '--clean', action='store_true', help="Clean deploy, clear the working directory if it belongs to the current user.")
        self.parser.add_option('-U', '--ulp', '--unuselibrepo', action='store_true', help="Disable automatic dependency handling.")
        self.parser.add_option('-A', '--act', '--auto-create-tenant', action='store_true', help="Auto create tenant during bootstrap.")

    def _do_command(self, obd):
        if self.cmds:
            obd.set_options(self.opts)
            res = obd.deploy_cluster(self.cmds[0])
            self.background_telemetry_task(obd)
            return res
        else:
            return self._show_help()


class SeekdbStartCommand(SeekdbMirrorCommand):

    def __init__(self):
        super(SeekdbStartCommand, self).__init__('start', 'Start a deployed seekdb cluster.')
        self.parser.add_option('-s', '--servers', type='string', help="List of servers to be started. Multiple servers are separated with commas.")
        self.parser.add_option('-S', '--strict-check', action='store_true', help="Throw errors instead of warnings when check fails.")
        self.parser.add_option('--without-parameter', '--wop', action='store_true', help='Start without parameters.')

    def _do_command(self, obd):
        if self.cmds:
            obd.set_cmds(self.cmds[1:])
            res = obd.start_cluster(self.cmds[0])
            self.background_telemetry_task(obd)
            return res
        else:
            return self._show_help()


class SeekdbStopCommand(SeekdbMirrorCommand):

    def __init__(self):
        super(SeekdbStopCommand, self).__init__('stop', 'Stop a started seekdb cluster.')
        self.parser.add_option('-s', '--servers', type='string', help="List of servers to be stopped. Multiple servers are separated with commas.")

    def _do_command(self, obd):
        if self.cmds:
            obd.set_cmds(self.cmds[1:])
            res = obd.stop_cluster(self.cmds[0])
            self.background_telemetry_task(obd)
            return res
        else:
            return self._show_help()


class SeekdbRestartCommand(SeekdbMirrorCommand):

    def __init__(self):
        super(SeekdbRestartCommand, self).__init__('restart', 'Restart a started seekdb cluster.')
        self.parser.add_option('-s', '--servers', type='string', help="List of servers to be restarted. Multiple servers are separated with commas.")
        self.parser.add_option('--with-parameter', '--wp', action='store_true', help='Restart with parameters.')

    def _do_command(self, obd):
        if self.cmds:
            obd.set_options(self.opts)
            res = obd.restart_cluster(self.cmds[0])
            self.background_telemetry_task(obd)
            return res
        else:
            return self._show_help()


class SeekdbDestroyCommand(SeekdbMirrorCommand):

    def __init__(self):
        super(SeekdbDestroyCommand, self).__init__('destroy', 'Destroy a deployed seekdb cluster.')
        self.parser.add_option('-f', '--force-kill', action='store_true', help="Force kill the running seekdb process in the working directory.")
        self.parser.add_option('--confirm', action='store_true', help='Confirm to destroy.')

    def _do_command(self, obd):
        if self.cmds:
            res = obd.destroy_cluster(self.cmds[0], need_confirm=not getattr(self.opts, 'confirm', False))
            return res
        else:
            return self._show_help()


class SeekdbDisplayCommand(SeekdbMirrorCommand):

    def __init__(self):
        super(SeekdbDisplayCommand, self).__init__('display', 'Display the information for a seekdb cluster.')
        self.parser.add_option('--encryption-passkey', '--epk', type='string', help="Encryption passkey.")

    def _do_command(self, obd):
        if self.cmds:
            return obd.display_cluster(self.cmds[0])
        else:
            return self._show_help()


class SeekdbMajorCommand(MajorCommand):

    def __init__(self):
        super(SeekdbMajorCommand, self).__init__('seekdb', 'Deploy and manage a seekdb cluster.')
        self.register_command(SeekdbDeployCommand())
        self.register_command(SeekdbStartCommand())
        self.register_command(SeekdbStopCommand())
        self.register_command(SeekdbRestartCommand())
        self.register_command(SeekdbDestroyCommand())
        self.register_command(SeekdbDisplayCommand())


class MainCommand(MajorCommand):

    def __init__(self):
        super(MainCommand, self).__init__('obd', '')
        self.register_command(DevModeMajorCommand())
        self.register_command(DemoCommand())
        self.register_command(PrefCommand())
        self.register_command(WebCommand())
        self.register_command(MirrorMajorCommand())
        self.register_command(ClusterMajorCommand())
        self.register_command(SeekdbMajorCommand())
        self.register_command(RepositoryMajorCommand())
        self.register_command(TestMajorCommand())
        self.register_command(UpdateCommand())
        self.register_command(DisplayTraceCommand())
        self.register_command(EnvironmentMajorCommand())
        self.register_command(TelemetryMajorCommand())
        self.register_command(ToolCommand())
        self.register_command(ObdiagCommand())
        self.register_command(BinlogCommand())
        self.register_command(HostCommand())
        self.register_command(LicenseCommand())
        self.register_command(PasswordMajorCommand())
        self.parser.version = '''OceanBase Deploy: %s
REVISION: %s
BUILD_BRANCH: %s
BUILD_TIME: %s
Copyright (C) 2025 OceanBase
License Apache 2.0: Apache version 2 or later <https://www.apache.org/licenses/LICENSE-2.0>.
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
    sys.path.append(os.path.join(ObdCommand.OBD_INSTALL_PATH, 'lib/site-packages'))
    ROOT_IO.track_limit += 2
    ret = MainCommand().init(sys.argv[0], sys.argv[1:]).do_command()
    if isinstance(ret, CmdReturn):
        ROOT_IO.exit(ret.code)
    else:
        if ret:
            ROOT_IO.exit(0)
        ROOT_IO.exit(1)

