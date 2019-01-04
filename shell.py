#!/usr/bin/env python3

import asyncio
import functools
import time

from typing import Sequence

from prompt_toolkit import PromptSession
from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop
from prompt_toolkit.patch_stdout import patch_stdout

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.completion.base import CompleteEvent
from prompt_toolkit.document import Document

from powercmd import Cmd
from powercmd.command_invocation import CommandInvocation
from powercmd.match_string import match_string


class CmdCompleter(Completer):
    def __init__(self, cmd: Cmd):
        self._cmd = cmd

    def _get_cmd_completions(self, incomplete_cmd: str) -> Sequence[Completion]:
        yield from (Completion(cpl, start_position=0)
                    for cpl in match_string(incomplete_cmd, self._cmd._get_all_commands()))

    def _get_argument_completions(self, incomplete_arg: str, start_position: int) -> Sequence[Completion]:
        yield from (Completion(cpl, start_position=start_position)
                    for cpl in self._cmd.completedefault(None, incomplete_arg, None, None))

    def get_completions(self, document: Document, _complete_event: CompleteEvent):
        current_cmd = ''
        if document.text.strip():
            current_cmd = document.text.strip().split(maxsplit=1)[0]

        start, end = document.find_boundaries_of_current_word()
        if not current_cmd or document.cursor_position + start == 0:  # TODO: use first non-blank instead
            yield from self._get_cmd_completions(current_cmd)
        else:
            if (start, end) == (0, 0):
                # pass the command name to get per-command completions
                text_to_complete = current_cmd + ' '
            else:
                text_to_complete = document.text[:document.cursor_position + end]

            # TODO: would be cool to exclude existing args
            yield from self._get_argument_completions(text_to_complete, start)


use_asyncio_event_loop()


class Shell(Cmd):
    def __init__(self):
        self._shutdown_requested = False
        self._session = PromptSession()
        self._completer = CmdCompleter(self)

        self.event_loop = asyncio.get_event_loop()
        self.prompt = '> '

    async def onecmd(self):
        with patch_stdout():
            cmd = await self._session.prompt(self.prompt, async_=True, completer=self._completer)

        self.default(cmd)

    async def cmdloop(self):
        try:
            while True:
                await self.onecmd()
        except EOFError:
            self._shutdown_requested = True

    def print_stuff(self, delay_s: float):
        print(time.time())
        self.event_loop.call_later(delay_s, functools.partial(self.print_stuff, delay_s))

    def run(self):
        self._shutdown_requested = False

        self.event_loop.call_soon(functools.partial(self.print_stuff, delay_s=30.0))
        self.event_loop.run_until_complete(self.cmdloop())

    def do_test(self,
                foo: int,
                bar: str,
                baz: float):
        print(f'foo {foo} bar {bar} baz {baz}')

if __name__ == '__main__':
    Shell().run()
