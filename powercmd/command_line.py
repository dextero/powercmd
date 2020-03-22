"""
Utility class for parsing command lines.
"""

import collections
import re
import shlex

from typing import Mapping, Sequence


NamedArg = collections.namedtuple('NamedArg', ['name', 'value'])
PositionalArg = collections.namedtuple('PositionalArg', ['value'])


class CommandLine:
    """
    Partially parsed command line.

    The command line is split into base command, named and free arguments for
    easier handling.
    """

    def __init__(self, cmdline: str):
        # shlex.split() makes inputting strings annoying,
        # TODO: find an alternative
        words = shlex.split(cmdline)
        # words = cmdline.split()

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
        return ((self.command, self.args) == (other.command, other.args))

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

    def __repr__(self):
        return ('CommandLine(command=%s,named_args=%s,free_args=%s)'
                % (repr(self.command), repr(self.named_args), repr(self.free_args)))
