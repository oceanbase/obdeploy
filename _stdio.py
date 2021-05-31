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
import traceback

from enum import Enum
from halo import Halo, cursor
from colorama import Fore
from prettytable import PrettyTable
from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar


if sys.version_info.major == 3:
    raw_input = input
    input = lambda msg: int(raw_input(msg))


class BufferIO(object):

    def __init__(self):
        self._buffer = []

    def write(self, s):
        self._buffer.append(s)

    def read(self):
        s = ''.join(self._buffer)
        self._buffer = []
        return s


class FormtatText(object):

    @staticmethod
    def format(text, color):
        return color + text + Fore.RESET

    @staticmethod
    def info(text):
        return FormtatText.format(text, Fore.BLUE)

    @staticmethod
    def success(text):
        return FormtatText.format(text, Fore.GREEN)

    @staticmethod
    def warning(text):
        return FormtatText.format(text, Fore.YELLOW)

    @staticmethod
    def error(text):
        return FormtatText.format(text, Fore.RED)


class LogSymbols(Enum): 
    
    INFO = FormtatText.info('!')
    SUCCESS = FormtatText.success('ok')
    WARNING = FormtatText.warning('!!')
    ERROR = FormtatText.error('x')


class IOTable(PrettyTable):

    @property
    def align(self):
        """Controls alignment of fields
        Arguments:

        align - alignment, one of "l", "c", or "r" """
        return self._align

    @align.setter
    def align(self, val):
        if not self._field_names:
            self._align = {}
        elif isinstance(val, dict):
            val_map = val
            for field in self._field_names:
                if field in val_map:
                    val = val_map[field]
                    self._validate_align(val)
                else:
                    val = 'l'
                self._align[field] = val
        else:
            if val:
                self._validate_align(val)
            else:
                val = 'l'
            for field in self._field_names:
                self._align[field] = val
    

class IOHalo(Halo):

    def __init__(self, text='', color='cyan', text_color=None, spinner='line', animation=None, placement='right', interval=-1, enabled=True, stream=sys.stdout):
        super(IOHalo, self).__init__(text=text, color=color, text_color=text_color, spinner=spinner, animation=animation, placement=placement, interval=interval, enabled=enabled, stream=stream)

    def start(self, text=None):
        if getattr(self._stream, 'isatty', lambda : False)():
            return super(IOHalo, self).start(text=text)
        else:
            text and self._stream.write(text)

    def stop_and_persist(self, symbol=' ', text=None):
        if getattr(self._stream, 'isatty', lambda : False)():
            return super(IOHalo, self).stop_and_persist(symbol=symbol, text=text)
        else:
            self._stream.write(' %s\n' % symbol)

    def succeed(self, text=None):
        return self.stop_and_persist(symbol=LogSymbols.SUCCESS.value, text=text)

    def fail(self, text=None):
        return self.stop_and_persist(symbol=LogSymbols.ERROR.value, text=text)

    def warn(self, text=None):
        return self.stop_and_persist(symbol=LogSymbols.WARNING.value, text=text)

    def info(self, text=None):
        return self.stop_and_persist(symbol=LogSymbols.INFO.value, text=text)


class IOProgressBar(ProgressBar):

    def __init__(self, maxval=None, text='', term_width=None, poll=1, left_justify=True, stream=None):
        widgets=['%s: ' % text, Percentage(), ' ',
                    Bar(marker='#', left='[', right=']'),
                    ' ', ETA(), ' ', FileTransferSpeed()]
        super(IOProgressBar, self).__init__(maxval=maxval, widgets=widgets, term_width=term_width, poll=poll, left_justify=left_justify, fd=stream)

    def start(self):
        self._hide_cursor()
        return super(IOProgressBar, self).start()

    def update(self, value=None):
        return super(IOProgressBar, self).update(value=value)

    def finish(self):
        self._show_cursor()
        return super(IOProgressBar, self).finish()

    def _need_update(self):
        return (self.currval == self.maxval or self.currval == 0 or getattr(self.fd, 'isatty', lambda : False)()) \
             and super(IOProgressBar, self)._need_update()

    def _check_stream(self):
        if self.fd.closed:
            return False
        try:
            check_stream_writable = self.fd.writable
        except AttributeError:
            pass
        else:
            return check_stream_writable()
        return True

    def _hide_cursor(self):
        """Disable the user's blinking cursor
        """
        if self._check_stream() and self.fd.isatty():
            cursor.hide(stream=self.fd)

    def _show_cursor(self):
        """Re-enable the user's blinking cursor
        """
        if self._check_stream() and self.fd.isatty():
            cursor.show(stream=self.fd)


class MsgLevel(object):

    CRITICAL = 50
    FATAL = CRITICAL
    ERROR = 40
    WARNING = 30
    WARN = WARNING
    INFO = 20
    DEBUG = 10
    VERBOSE = DEBUG
    NOTSET = 0


class IO(object):

    WIDTH = 64
    VERBOSE_LEVEL = 0
    WARNING_PREV = FormtatText.warning('[WARN]')
    ERROR_PREV = FormtatText.error('[ERROR]')
    
    def __init__(self, level, msg_lv=MsgLevel.DEBUG, trace_logger=None, track_limit=0, root_io=None, stream=sys.stdout):
        self.level = level
        self.msg_lv = msg_lv
        self.trace_logger = trace_logger
        self._root_io = root_io
        self.track_limit = track_limit
        self._verbose_prefix = '-' * self.level
        self.sub_ios = {}
        self.sync_obj = None
        self._out_obj = None if self._root_io else stream
        self._cur_out_obj = self._out_obj
        self._before_critical = None

    def before_close(self):
        if self._before_critical:
            try:
               self._before_critical(self)
            except:
                pass

    def __del__(self):
        self.before_close()

    def get_cur_out_obj(self):
        if self._root_io:
            return self._root_io.get_cur_out_obj()
        return self._cur_out_obj

    def _start_buffer_io(self):
        if self._root_io:
            return False
        if self._cur_out_obj != self._out_obj:
            return False
        self._cur_out_obj = BufferIO()
        return True

    def _stop_buffer_io(self):
        if self._root_io:
            return False
        if self._cur_out_obj == self._out_obj:
            return False
        text = self._cur_out_obj.read()
        self._cur_out_obj = self._out_obj
        if text:
            self.print(text)
        return True

    @staticmethod
    def set_verbose_level(level):
        IO.VERBOSE_LEVEL = level

    def _start_sync_obj(self, sync_clz, before_critical, *arg, **kwargs):
        if self._root_io:
            return self._root_io._start_sync_obj(sync_clz, before_critical, *arg, **kwargs)
        if self.sync_obj:
            return None
        if not self._start_buffer_io():
            return None
        kwargs['stream'] = self._out_obj
        try:
            self.sync_obj = sync_clz(*arg, **kwargs)
            self._before_critical = before_critical
        except Exception as e:
            self._stop_buffer_io()
            raise e
        return self.sync_obj

    def _clear_sync_ctx(self):
        self._stop_buffer_io()
        self.sync_obj = None
        self._before_critical = None

    def _stop_sync_obj(self, sync_clz, stop_type, *arg, **kwargs):
        if self._root_io:
            ret = self._root_io._stop_sync_obj(sync_clz, stop_type, *arg, **kwargs)
            self._clear_sync_ctx()
        else:
            if not isinstance(self.sync_obj, sync_clz):
                return False
            try:
                ret = getattr(self.sync_obj, stop_type)(*arg, **kwargs)
            except Exception as e:
                raise e
            finally:
                self._clear_sync_ctx()
        return ret
        
    def start_loading(self, text, *arg, **kwargs):
        if self.sync_obj:
            return False
        self.sync_obj = self._start_sync_obj(IOHalo, lambda x: x.stop_loading('fail'), *arg, **kwargs)
        if self.sync_obj:
            self._log(MsgLevel.INFO, text)
            return self.sync_obj.start(text)

    def stop_loading(self, stop_type, *arg, **kwargs):
        if not isinstance(self.sync_obj, IOHalo):
            return False
        if getattr(self.sync_obj, stop_type, False):
            return self._stop_sync_obj(IOHalo, stop_type, *arg, **kwargs)
        else:
            return self._stop_sync_obj(IOHalo, 'stop')

    def start_progressbar(self, text, maxval):
        if self.sync_obj:
            return False
        self.sync_obj = self._start_sync_obj(IOProgressBar, lambda x: x.finish_progressbar(), text=text, maxval=maxval)
        if self.sync_obj:
            self._log(MsgLevel.INFO, text)
            return self.sync_obj.start()

    def update_progressbar(self, value):
        if not isinstance(self.sync_obj, IOProgressBar):
            return False
        return self.sync_obj.update(value)

    def finish_progressbar(self):
        if not isinstance(self.sync_obj, IOProgressBar):
            return False
        return self._stop_sync_obj(IOProgressBar, 'finish')
    
    def sub_io(self, pid=None, msg_lv=None):
        if not pid:
            pid = os.getpid()
        if msg_lv is None:
            msg_lv = self.msg_lv
        key = "%s-%s" % (pid, msg_lv)
        if key not in self.sub_ios:
            self.sub_ios[key] = IO(
                self.level + 1, 
                msg_lv=msg_lv, 
                trace_logger=self.trace_logger,
                track_limit=self.track_limit,
                root_io=self._root_io if self._root_io else self
            )
        return self.sub_ios[key]

    def print_list(self, ary, field_names=None, exp=lambda x: x if isinstance(x, list) else [x], show_index=False, start=0, **kwargs):
        if not ary:
            return
        show_index = field_names is not None and show_index
        if show_index:
            show_index.insert(0, 'idx')
        table = IOTable(field_names, **kwargs)
        for row in ary:
            row = exp(row)
            if show_index:
                row.insert(start)
                start += 1
            table.add_row(row)
        self.print(table)

    def confirm(self, msg):
        while True:
            try:
                ans = raw_input('%s [y/n]: ' % msg)
                if ans == 'y':
                    return True
                if ans == 'n':
                    return False
            except:
                pass

    def _format(self, msg, *args):
        if args:
            msg = msg % args
        return msg

    def _print(self, msg_lv, msg, *args, **kwargs):
        if msg_lv < self.msg_lv:
            return
        kwargs['file'] = self.get_cur_out_obj()
        kwargs['file'] and print(self._format(msg, *args), **kwargs)
        del kwargs['file']
        self._log(msg_lv, msg, *args, **kwargs)
    
    def _log(self, levelno, msg, *args, **kwargs):
        self.trace_logger and self.trace_logger.log(levelno, msg, *args, **kwargs)

    def print(self, msg, *args, **kwargs):
        self._print(MsgLevel.INFO, msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        self._print(MsgLevel.WARN, '%s %s' % (self.WARNING_PREV, msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._print(MsgLevel.ERROR, '%s %s' % (self.ERROR_PREV, msg), *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        if self._root_io:
            return self.critical(msg, *args, **kwargs)
        self._print(MsgLevel.CRITICAL, '%s %s' % (self.ERROR_PREV, msg), *args, **kwargs)
        self.exit(kwargs['code'] if 'code' in kwargs else 255)
    
    def exit(self, code):
        self.before_close()
        sys.exit(code)

    def verbose(self, msg, *args, **kwargs):
        if self.level > self.VERBOSE_LEVEL:
            self._log(MsgLevel.VERBOSE, '%s %s' % (self._verbose_prefix, msg), *args, **kwargs)
            return
        self._print(MsgLevel.VERBOSE, '%s %s' % (self._verbose_prefix, msg), *args, **kwargs)

    if sys.version_info.major == 2:
        def exception(self, msg, *args, **kwargs):
            import linecache
            exception_msg = []
            ei = sys.exc_info()
            exception_msg.append('Traceback (most recent call last):')
            stack = traceback.extract_stack()[self.track_limit:-2]
            tb = ei[2]
            while tb is not None:
                f = tb.tb_frame
                lineno = tb.tb_lineno
                co = f.f_code
                filename = co.co_filename
                name = co.co_name
                linecache.checkcache(filename)
                line = linecache.getline(filename, lineno, f.f_globals)
                tb = tb.tb_next
                stack.append((filename, lineno, name, line))
            for line in stack:
                exception_msg.append('  File "%s", line %d, in %s' % line[:3])
                if line[3]: exception_msg.append('    ' + line[3].strip())
            lines = []
            for line in traceback.format_exception_only(ei[0], ei[1]):
                lines.append(line)
            if lines:
                exception_msg.append(''.join(lines))
            if self.level <= self.VERBOSE_LEVEL:
                msg = '%s\n%s' % (msg, '\n'.join(exception_msg))
                self.error(msg)
            else:
                msg and self.error(msg)
                self._log(MsgLevel.VERBOSE, '\n'.join(exception_msg))
    else:
        def exception(self, msg, *args, **kwargs):
            ei = sys.exc_info()
            traceback_e = traceback.TracebackException(type(ei[1]), ei[1], ei[2], limit=None)
            pre_stach = traceback.extract_stack()[self.track_limit:-2]
            pre_stach.reverse()
            for summary in pre_stach:
                traceback_e.stack.insert(0, summary)
            lines = []
            for line in traceback_e.format(chain=True):
                lines.append(line)
            if self.level <= self.VERBOSE_LEVEL:
                msg = '%s\n%s' % (msg, ''.join(lines))
                self.error(msg)
            else:
                msg and self.error(msg)
                self._log(MsgLevel.VERBOSE, ''.join(lines))

