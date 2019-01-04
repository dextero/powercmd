#!/usr/bin/env python3

import asyncio
import functools

from prompt_toolkit import PromptSession
from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop
from prompt_toolkit.patch_stdout import patch_stdout


use_asyncio_event_loop()


class Shell:
    def __init__(self):
        self._shutdown_requested = False
        self._session = PromptSession()
        self.event_loop = asyncio.get_event_loop()

    async def onecmd(self):
        with patch_stdout():
            cmd = await self._session.prompt('> ', async_=True)

        print('< ' + cmd)

    async def run_until_eof(self):
        try:
            while True:
                await self.onecmd()
        except EOFError:
            self._shutdown_requested = True

    def print_stuff(self, delay_s):
        print('stuff')
        self.event_loop.call_later(delay_s, functools.partial(self.print_stuff, delay_s))

    def run(self):
        self._shutdown_requested = False

        self.event_loop.call_soon(functools.partial(self.print_stuff, delay_s=1.0))
        self.event_loop.run_until_complete(self.run_until_eof())


if __name__ == '__main__':
    Shell().run()
