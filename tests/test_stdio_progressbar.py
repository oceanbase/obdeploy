# coding: utf-8

from io import StringIO
from unittest.mock import MagicMock, patch

from _stdio import BufferIO, IO, MsgLevel


def test_non_tty_progressbar_outputs_message_once_without_terminal_control_characters():
    output = BufferIO(False)
    stdio = IO(
        level=0,
        msg_lv=MsgLevel.DEBUG,
        input_stream=StringIO(),
        output_stream=output,
    )

    assert stdio.start_progressbar('Download demo.rpm (6.58 M)', 100) is False
    assert stdio.update_progressbar(100) is False
    assert stdio.finish_progressbar() is False

    assert output.read() == 'Download demo.rpm (6.58 M)\n'


def test_tty_progressbar_still_uses_progressbar_renderer():
    output = MagicMock()
    output.isatty.return_value = True
    input_stream = MagicMock()
    input_stream.isatty.return_value = True
    stdio = IO(
        level=0,
        msg_lv=MsgLevel.DEBUG,
        input_stream=input_stream,
        output_stream=output,
    )
    with patch.object(stdio, '_start_sync_obj') as progressbar:
        progressbar.return_value.start.return_value = 'started'

        assert stdio.start_progressbar('Download demo.rpm', 100) == 'started'
        progressbar.assert_called_once()


def test_tty_sub_io_still_uses_root_progressbar_renderer():
    output = MagicMock()
    output.isatty.return_value = True
    input_stream = MagicMock()
    input_stream.isatty.return_value = True
    root_stdio = IO(
        level=0,
        msg_lv=MsgLevel.DEBUG,
        input_stream=input_stream,
        output_stream=output,
    )
    stdio = root_stdio.sub_io()

    with patch.object(root_stdio, '_start_sync_obj') as progressbar:
        progressbar.return_value.start.return_value = 'started'

        assert stdio.start_progressbar('Download demo.rpm', 100) == 'started'
        progressbar.assert_called_once()
