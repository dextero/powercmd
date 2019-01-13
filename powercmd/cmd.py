"""
powercmd - A generic class to build typesafe line-oriented command interpreters.

As in Cmd module, methods starting with 'do_' are considered command handlers.
That behavior can be changed by overriding the `get_command_prefixes` method.

All command handler arguments must have a type annotation. Actual values passed
to the command handler are not strings typed by the user, but objects of
appropriate types hinted by the annotations, which are constructed as follows:

1. If the type hinted by an annotation contains a static `powercmd_parse`
   function, it is called with a single string argument. The return value of
   `powercmd_parse` is passed to the command handler and is expected to be an
   instance of the annotated type.
2. Otherwise, the value is created by calling the constructor of the annotated
   type with a single argument: a string typed by the user.

Example:
    class SimpleTestCmd(powercmd.Cmd):
        def do_test_command(self,
                            int_arg: int):
            # `test_command 123` translates to `do_test_command(int('123'))`
            pass

        class CustomType:
            @staticmethod
            def powercmd_parse(text):
                return CustomType()

        def do_test_custom(self,
                           custom_arg: CustomType):
            # `test_custom 123` translates to
            # `do_test_custom(CustomType.powercmd_parse('123'))`
            pass
"""

import inspect
import sys
import traceback
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

from powercmd.command_invoker import CommandInvoker
from powercmd.command_line import CommandLine
from powercmd.commands_dict import CommandsDict
from powercmd.completer import Completer
from powercmd.exceptions import InvalidInput
from powercmd.command import Command


class Cmd:
    """
    A simple framework for writing typesafe line-oriented command interpreters.
    """
    def __init__(self):
        self._last_exception = None
        self._session = PromptSession()

        self.prompt = '> '
        self.prompt_style = Style.from_dict({'': 'bold'})

    # pylint: disable=no-self-use
    def get_command_prefixes(self):
        """
        Returns a mapping {method_command_prefix -> input_string_prefix}.
        input_string_prefix is a prefix of a command typed in the command line,
        method_command_prefix is the prefix for a matching command.

        If this function returns {'do_': ''}, then all methods whose names start
        with 'do_' will be available as commands with the same names, i.e.
        typing 'foo' will execute 'do_foo'.
        If it returned {'do_', '!'}, then one has to type '!foo' in order to
        execute 'do_foo'.
        """
        return {'do_': ''}

    def do_get_error(self):
        """
        Displays an exception thrown by last command.
        """
        if self._last_exception is None:
            print('no errors')
        else:
            traceback.print_exception(*self._last_exception)

    def do_exit(self):
        """Terminates the command loop."""
        print('exiting')
        return True

    # pylint: disable=invalid-name
    def do_EOF(self):
        """Terminates the command loop."""
        print('')
        return self.do_exit()

    # pylint: disable=arguments-differ
    def do_help(self,
                topic: str = ''):
        """
        Displays a description of given command or lists all available commands.
        """
        cmds = self._get_all_commands()

        try:
            handler = cmds.choose(topic, verbose=True)

            arg_spec = self._get_handler_params(handler)
            args_with_defaults = list((name, param.default)
                                      for name, param in arg_spec.items())

            print('%s\n\nARGUMENTS: %s %s\n'
                  % (handler.__doc__ or 'No details available.',
                     topic,
                     ' '.join('%s=%s' % (arg, repr(default))
                              if default is not inspect.Parameter.empty
                              else str(arg)
                              for arg, default in args_with_defaults)))
        except InvalidInput:
            print('no such command: %s' % (topic,))
            print('available commands: %s' % (' '.join(sorted(cmds)),))

    def _get_all_commands(self) -> CommandsDict:
        """Returns all defined commands."""
        import types

        def unbind(f):
            """
            Returns the base function if the argument is a bound one.
            https://bugs.python.org/msg166144
            """
            if not callable(f):
                raise TypeError('%s is not callable' % (repr(f),))

            self = getattr(f, '__self__', None)
            if (self is not None
                    and not isinstance(self, types.ModuleType)
                    and not isinstance(self, type)):
                if hasattr(f, '__func__'):
                    return f.__func__
                return getattr(type(f.__self__), f.__name__)

            return f

        members = inspect.getmembers(self)
        prefixes = self.get_command_prefixes()
        commands = CommandsDict()

        for name, handler in members:
            if not callable(handler):
                continue
            for prefix, substitution in prefixes.items():
                if name.startswith(prefix):
                    assert substitution + name not in commands
                    cmd_name = substitution + name[len(prefix):]
                    commands[cmd_name] = Command(name=cmd_name, handler=unbind(handler))

        return commands

    def emptyline(self):
        pass

    def default(self, cmdline):
        try:
            if not cmdline:
                return self.emptyline()

            invoker = CommandInvoker(self._get_all_commands())
            return invoker.invoke(self, cmdline=CommandLine(cmdline))
        # it's a bit too ruthless to terminate on every single broken command
        # pylint: disable=broad-except
        except Exception as e:
            self._last_exception = sys.exc_info()
            print('%s (try "get_error" for details)' % e)
        else:
            self._last_exception = None

    def onecmd(self, cmdline):
        return self.default(cmdline)

    def cmdloop(self):
        completer = Completer(self._get_all_commands())
        try:
            while True:
                with patch_stdout():
                    cmd = self._session.prompt(self.prompt, completer=completer, style=self.prompt_style)
                self.onecmd(cmd)
        except EOFError:
            pass
