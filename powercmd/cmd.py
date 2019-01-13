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

import copy
import enum
import inspect
import sys
import traceback
import typing
from typing import Any, Callable, List, Mapping, Sequence, Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.completion.base import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

from powercmd.command_invocation import CommandInvocation
from powercmd.extra_typing import OrderedMapping
from powercmd.match_string import match_string
from powercmd.split_list import split_list
from powercmd.command import Command, Parameter


def _is_generic_list(annotation: Any):
    # python<3.7 reports List in __origin__, while python>=3.7 reports list
    return getattr(annotation, '__origin__', None) in (List, list)


def _is_generic_tuple(annotation: Any):
    # python<3.7 reports Tuple in __origin__, while python>=3.7 reports tuple
    return getattr(annotation, '__origin__', None) in (Tuple, tuple)


def _is_generic_type(annotation: Any) -> bool:
    """
    Checks if the type described by ANNOTATION is a generic one.
    """
    return (_is_generic_list(annotation)
            or _is_generic_tuple(annotation))


class CmdCompleter(Completer):
    def __init__(self, cmd: 'Cmd'):
        self._cmd = cmd

    def _complete_commands(self, incomplete_cmd: str) -> Sequence[Completion]:
        """
        Returns a sequence of command completions matching INCOMPLETE_CMD prefix.
        """
        cmds = self._cmd._get_all_commands()
        matching_cmds = (cmds[cmd] for cmd in match_string(incomplete_cmd, cmds))
        yield from (Completion(cmd.name,
                               start_position=-len(incomplete_cmd),
                               display_meta=cmd.short_description)
                    for cmd in matching_cmds)

    def _complete_params(self, cmd: Command, incomplete_param: str) -> Sequence[Completion]:
        """
        Returns a sequence of parameter name completions matching INCOMPLETE_PARAM
        prefix for given CMD.
        """
        matching_params = (cmd.parameters[param]
                           for param in match_string(incomplete_param, cmd.parameters))
        yield from (Completion(param.name,
                               start_position=-len(incomplete_param),
                               display_meta=str(param.type))
                    for param in matching_params)

    def _complete_generic_list(self,
                               inner_type: type,
                               incomplete_value: str):
        """
        Returns completions for a list of values of INNER_TYPE.
        """
        args = list(split_list(incomplete_value, allow_unmatched=True))
        return self._complete_value(inner_type, args[-1])

    def _complete_generic_tuple(self,
                                inner_types: Sequence[type],
                                incomplete_value: str):
        """
        Returns completions for one of tuple values matching one of INNER_TYPES.
        """
        args = list(split_list(incomplete_value, allow_unmatched=True))
        if len(args) > len(inner_types):
            return []
        return self._complete_value(self, inner_types[len(args) - 1])

    def _complete_enum(self,
                       enum: type,
                       incomplete_value: str):
        """
        Returns completions for an class derived from enum.Enum type.
        """
        matching_names = match_string(incomplete_value, (val.name for val in list(enum)))
        matching_vals = (enum[name] for name in matching_names)
        yield from (Completion(val.name,
                               start_position=-len(incomplete_value),
                               display_meta=val.value)
                    for val in matching_vals)

    def _complete_custom(self,
                         type: type,
                         incomplete_value: str):
        """
        Returns a list of completion using type.powercmd_complete method.
        """
        completions = type.powercmd_complete(incomplete_value)
        # allow powercmd_complete to return lists of strings for backward compatibility
        if completions and not isinstance(completions[0], Completion):
            completions = (Completion(cpl,
                                      start_position=-len(incomplete_value))
                           for cpl in completions)
        return completions

    def _complete_value(self,
                        type: type,
                        incomplete_value: str) -> Sequence[Completion]:
        """
        Returns a sequence of parameter value completions matching
        INCOMPLETE_VALUE prefix for given CMD.
        """
        if _is_generic_type(type):
            if _is_generic_list(type):
                return self._complete_generic_list(type.__args__[0], incomplete_value)
            if _is_generic_tuple(type):
                return self._complete_generic_tuple(type.__args__, incomplete_value)
            raise NotImplementedError('generic constructor for %s not implemented'
                                      % (type,))

        if issubclass(type, enum.Enum):
            return self._complete_enum(type, incomplete_value)
        if hasattr(type, 'powercmd_complete'):
            return self._complete_custom(type, incomplete_value)

        return [Completion('', display_meta=str(type))]

    def get_completions(self,
                        document: Document,
                        _complete_event: CompleteEvent) -> Sequence[Completion]:
        """
        Returns a sequence of completions for given command line.
        """
        incomplete_cmd = ''
        if document.text.strip():
            incomplete_cmd = document.text.strip().split(maxsplit=1)[0]

        start, end = document.find_boundaries_of_current_word(WORD=True)
        start += document.cursor_position
        end += document.cursor_position
        current_word = document.text[start:end]

        current_word_is_command = (document.text[:start].strip() == '')
        if current_word_is_command:
            return self._complete_commands(incomplete_cmd)

        try:
            cmd = self._cmd.choose_cmd(incomplete_cmd)
        except Cmd.SyntaxError:
            # invalid command
            return []

        incomplete_param = current_word
        if '=' not in incomplete_param:
            return self._complete_params(cmd, incomplete_param)

        param_name, incomplete_value = incomplete_param.split('=', maxsplit=1)
        param = cmd.parameters.get(param_name)
        if not param:
            return []

        # TODO: would be cool to exclude existing params
        return self._complete_value(param.type, incomplete_value)


class Cmd:
    """
    A simple framework for writing typesafe line-oriented command interpreters.
    """
    class SyntaxError(Exception):
        """An error raised if the input cannot be parsed as a valid command."""

    def __init__(self):
        self._last_exception = None
        self._session = PromptSession()

        self.completer = CmdCompleter(self)
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

    def _get_list_ctor(self,
                       annotation: typing.List) -> Callable[[str], typing.List]:
        """
        Returns a function that parses a string representation of a list
        defined by ANNOTATION.

        Examples:
            "[1,2,3]" -> List[int]
            "1,2,3" -> List[int]
        """
        if len(annotation.__args__) != 1:
            raise TypeError('List may only have one type parameter, got %s'
                            % (annotation,))
        internal_type = annotation.__args__[0]
        internal_ctor = self.get_constructor(internal_type)

        def construct_list(text):
            if text[0] == '[' and text[-1] == ']':
                text = text[1:-1]
            return [internal_ctor(txt) for txt in split_list(text)]

        return construct_list

    def _get_tuple_ctor(self,
                        annotation: typing.Tuple) -> Callable[[str], typing.Tuple]:
        """
        Returns a function that parses a string representation of a tuple
        defined by ANNOTATION.

        Examples:
            "(1,foo)" -> Tuple[int, str]
        """
        internal_types = getattr(annotation, '__args__', None)
        if internal_types is None:
            raise TypeError('%s is not a tuple type' % (repr(annotation),))

        def construct_tuple(text):
            if text[0] == '(' and text[-1] == ')':
                text = text[1:-1]

            sub_txts = list(split_list(text))
            if len(sub_txts) != len(internal_types):
                raise TypeError('mismatched lengths: %d strings, %d tuple types' % (len(sub_txts), len(internal_types)))

            tuple_list = []
            for cls, txt in zip(internal_types, sub_txts):
                tuple_list.append(self.get_constructor(cls)(txt))

            return tuple(tuple_list)

        return construct_tuple

    # pylint: disable=no-self-use
    def get_constructor(self,
                        annotation: Any) -> Callable[[str], Any]:
        """
        Returns a callable that parses a string and returns an object of an
        appropriate type defined by the ANNOTATION.
        """
        def ensure_callable(arg):
            """Raises an exception if the argument is not callable."""
            if not callable(arg):
                raise TypeError('invalid type: ' + repr(arg))
            return arg

        if _is_generic_type(annotation):
            return self.get_generic_constructor(annotation)
        if issubclass(annotation, enum.Enum):
            # Enum class allows accessing values by string via [] operator
            return annotation.__getitem__
        if hasattr(annotation, 'powercmd_parse'):
            return getattr(annotation, 'powercmd_parse')

        if annotation is bool:
            # Booleans are actually quite special. In python bool(nonempty seq)
            # is always True, therefore if used verbatim, '0' would evaluate to
            # True, which, if you ask me, looks highly counter-intuitive.
            return lambda value: value not in ('', '0', 'false', 'False')

        return {
            bytes: lambda text: bytes(text, 'ascii'),
        }.get(annotation, ensure_callable(annotation))

    def get_generic_constructor(self,
                                annotation: Any) -> Callable[[str], Any]:
        """
        Returns a function that constructs a generic type from given string.
        It is used for types like List[Foo] to apply a Foo constructor for each
        list element.
        """
        if _is_generic_list(annotation):
            return self._get_list_ctor(annotation)
        if _is_generic_tuple(annotation):
            return self._get_tuple_ctor(annotation)

        raise NotImplementedError('generic constructor for %s not implemented'
                                  % (annotation,))

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
        all_handlers = self._get_all_commands()

        try:
            handler = self.choose_cmd(all_handlers, topic, verbose=True)

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
        except Cmd.SyntaxError:
            print('no such command: %s' % (topic,))
            print('available commands: %s' % (' '.join(sorted(all_handlers)),))

    def _construct_arg(self,
                       formal_param: inspect.Parameter,
                       value: str) -> Any:
        """
        Constructs an argument from string VALUE, with the type defined by an
        annotation to the FORMAL_PARAM.
        """
        ctor = self.get_constructor(formal_param.type)
        try:
            return ctor(value)
        except ValueError as e:
            raise Cmd.SyntaxError(e)

    def _construct_args(self,
                        formal: OrderedMapping[str, inspect.Parameter],
                        named_args: Mapping[str, str],
                        free_args: Sequence[str]):
        """
        Parses a list of actual call parameters by calling an appropriate
        constructor for each of them.
        """
        typed_args = {}
        extra_free = []

        for name, value in named_args.items():
            if name not in formal:
                print('unrecognized argument: %s' % (name,))
                extra_free.append('%s=%s' % (name, value))
            elif name in typed_args:
                raise Cmd.SyntaxError('duplicate value for argument: %s' % (name,))
            else:
                typed_args[name] = self._construct_arg(formal[name], value)

        typed_args = self._assign_free_args(formal, typed_args,
                                            free_args + extra_free)
        typed_args = Cmd._fill_default_args(formal, typed_args)
        return typed_args

    def _assign_free_args(self,
                          formal: OrderedMapping[str, inspect.Parameter],
                          actual: OrderedMapping[str, str],
                          free: Sequence[str]) -> Mapping[str, str]:
        """
        Returns the ACTUAL dict extended by initial FORMAL arguments matched to
        FREE values.
        """
        if len(free) > len(formal):
            raise Cmd.SyntaxError('too many free arguments: expected at most %d'
                                  % (len(formal),))

        result = copy.copy(actual)
        for name, value in zip(formal, free):
            if name in result:
                raise Cmd.SyntaxError('cannot assign free argument to %s: '
                                      'argument already present' % (name,))

            result[name] = self._construct_arg(formal[name], value)

        return result

    @staticmethod
    def _fill_default_args(formal: Mapping[str, inspect.Parameter],
                           actual: Mapping[str, str]):
        """
        Returns the ACTUAL dict extended by default values of unassigned FORMAL
        parameters.
        """
        result = copy.copy(actual)
        for name, param in formal.items():
            if (name not in result
                    and param.default is not inspect.Parameter.empty):
                result[name] = param.default

        return result

    def _get_all_commands(self) -> Mapping[str, Command]:
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
        commands = {}

        for name, handler in members:
            if not callable(handler):
                continue
            for prefix, substitution in prefixes.items():
                if name.startswith(prefix):
                    assert substitution + name not in commands
                    cmd_name = substitution + name[len(prefix):]
                    commands[cmd_name] = Command(name=cmd_name, handler=unbind(handler))

        return commands

    def choose_cmd(self,
                   short_cmd: str,
                   verbose: bool = False) -> Command:
        """Returns a command handler that matches SHORT_CMD."""
        cmds = self._get_all_commands()
        matches = match_string(short_cmd, cmds, verbose=verbose)

        if not matches:
            raise Cmd.SyntaxError('no such command: %s' % (short_cmd,))
        elif len(matches) > 1:
            raise Cmd.SyntaxError('ambigious command: %s (possible: %s)'
                                  % (short_cmd, ' '.join(matches)))
        else:
            return cmds[matches[0]]

    def _execute_cmd(self,
                     command: CommandInvocation) -> Any:
        """Executes given COMMAND."""
        cmd = self.choose_cmd(command.command, verbose=True)
        typed_args = self._construct_args(cmd.parameters,
                                          command.named_args, command.free_args)

        return cmd.handler(self, **typed_args)

    def emptyline(self):
        pass

    def default(self, cmdline):
        try:
            if not cmdline:
                return self.emptyline()

            return self._execute_cmd(CommandInvocation.from_cmdline(cmdline))
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
        try:
            while True:
                with patch_stdout():
                    cmd = self._session.prompt(self.prompt, completer=self.completer, style=self.prompt_style)
                self.onecmd(cmd)
        except EOFError:
            pass
