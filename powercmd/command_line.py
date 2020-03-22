"""
Utility class for parsing command lines.
"""

import collections
import copy
import re

from typing import Mapping, Sequence, Optional, Union

from powercmd.command import Command, Parameter
from powercmd.exceptions import InvalidInput
from powercmd.extra_typing import OrderedMapping
from powercmd.split_list import split_cmdline, drop_enclosing_quotes


IncompleteArg = collections.namedtuple('IncompleteArg', ['param', 'value'])
NamedArg = collections.namedtuple('NamedArg', ['name', 'value'])
PositionalArg = collections.namedtuple('PositionalArg', ['value'])


class MissingArg: pass
MISSING_ARG = MissingArg


class CommandLine:
    """
    Partially parsed command line.

    The command line is split into base command, named and free arguments for
    easier handling.
    """

    def __init__(self, cmdline: str):
        self.raw_text = cmdline
        self.quoted_words = split_cmdline(cmdline, allow_unmatched=True)

        words = [drop_enclosing_quotes(word) for word in self.quoted_words]

        self.command = words[0] if words else ''
        self.args = []

        for word in words[1:]:
            if re.match(r'^[a-zA-Z0-9_]+=', word):
                name, value = word.split('=', maxsplit=1)
                if name in self.named_args:
                    raise ValueError('multiple values for key: %s' % (name,))
                self.args.append(NamedArg(name, value))
            else:
                self.args.append(PositionalArg(word))

    def __eq__(self, other):
        return (self.command, self.args) == (other.command, other.args)

    def __str__(self):
        return ('command = %s\nargs (%d):\n%s'
                % (self.command,
                   len(self.args),
                   '\n'.join('  %s' % x for x in self.args)))

    @property
    def named_args(self) -> Mapping[str, str]:
        return {arg.name: arg.value for arg in self.args if isinstance(arg, NamedArg)}

    @property
    def free_args(self) -> Sequence[str]:
        return [arg.value for arg in self.args if isinstance(arg, PositionalArg)]

    @property
    def has_trailing_whitespace(self) -> bool:
        if not self.raw_text:
            return False
        if self.raw_text.isspace():
            return True
        assert len(self.quoted_words) > 0
        return not self.raw_text.endswith(self.quoted_words[-1])

    def __repr__(self):
        return ('CommandLine(raw_text=%s,quoted_words=%s,command=%s,args=%s)'
                % (repr(self.raw_text), repr(self.quoted_words), repr(self.command), repr(self.args)))

    def assign_args(self,
                    cmd: Command) -> OrderedMapping[str, Union[str, MissingArg]]:
        """
        Assigns arguments to named command parameters. Does not handle default
        arguments.
        """
        args = copy.copy(self.args)

        def pop_arg(name: Optional[str]) -> Optional[str]:
            for idx, arg in enumerate(args):
                if isinstance(arg, NamedArg):
                    if arg.name == name:
                        return args.pop(idx).value

            for idx, arg in enumerate(args):
                if isinstance(arg, NamedArg) and arg.name not in cmd.parameters:
                    print('unrecognized argument: %s' % (arg.name,))
                    return args.pop(idx).value
                if isinstance(arg, PositionalArg):
                    return args.pop(idx).value

            return None

        assigned_args = collections.OrderedDict()

        for name in cmd.parameters:
            arg_value = pop_arg(name)
            if arg_value is not None:
                assigned_args[name] = arg_value
            else:
                assigned_args[name] = MISSING_ARG

        assigned_args = self._assign_free_args(cmd, assigned_args, args)
        return assigned_args

    def _assign_free_args(self,
                          cmd: Command,
                          actual: OrderedMapping[str, str],
                          free: Sequence[str]) -> Mapping[str, str]:
        """
        Returns the ACTUAL dict extended by initial FORMAL arguments matched to
        FREE values.
        """
        if len(free) > len(cmd.parameters):
            raise InvalidInput('too many free arguments: expected at most %d'
                               % (len(cmd.parameters),))

        result = copy.copy(actual)
        for name, value in zip(cmd.parameters, free):
            if result[name] is not MISSING_ARG:
                raise InvalidInput('cannot assign free argument to %s: '
                                   'argument already present' % (name,))

            result[name] = value

        return result

    def get_current_arg(self,
                        cmd: Command) -> Optional[IncompleteArg]:
        assigned_args = self.assign_args(cmd)

        last_assigned = None
        first_unassigned = None

        for name, value in assigned_args.items():
            if value is MISSING_ARG:
                if first_unassigned is None:
                    first_unassigned = name
            else:
                last_assigned = name

        if self.has_trailing_whitespace:
            if first_unassigned is not None:
                return IncompleteArg(param=cmd.parameters[first_unassigned],
                                     value='')
        else:
            if last_assigned is not None:
                return IncompleteArg(param=cmd.parameters[last_assigned],
                                     value=assigned_args[last_assigned])

        return None
