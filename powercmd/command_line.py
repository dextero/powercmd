"""
Utility class for parsing command lines.
"""

import collections
import re

from typing import Mapping, Sequence

from powercmd.split_list import split_cmdline, drop_enclosing_quotes


NamedArg = collections.namedtuple('NamedArg', ['name', 'value'])
PositionalArg = collections.namedtuple('PositionalArg', ['value'])


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
