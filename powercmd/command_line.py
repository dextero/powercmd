"""
Utility class for parsing command lines.
"""

import collections
import re
import shlex


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
        self.named_args = collections.OrderedDict()
        self.free_args = []

        for word in words[1:]:
            if re.match(r'^[a-zA-Z0-9_]+=', word):
                name, value = word.split('=', maxsplit=1)
                if name in self.named_args:
                    raise ValueError('multiple values for key: %s' % (name,))
                self.named_args[name] = value
            else:
                self.free_args.append(word)

    def __eq__(self, other):
        return ((self.command, self.named_args, self.free_args)
                == (other.command, other.named_args, other.free_args))

    def __str__(self):
        return ('command = %s\nnamed_args (%d):\n%s\nfree_args (%d):\n%s'
                % (self.command,
                   len(self.named_args),
                   '\n'.join('  %s=%s' % kv for kv in self.named_args.items()),
                   len(self.free_args),
                   '\n'.join('  %s' % x for x in self.free_args)))

    def __repr__(self):
        return ('CommandLine(command=%s,named_args=%s,free_args=%s)'
                % (repr(self.command), repr(self.named_args), repr(self.free_args)))
