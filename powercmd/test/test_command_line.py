import unittest

from powercmd.command_line import CommandLine


class TestCommandLine(unittest.TestCase):
    def test_parse(self):
        cmdline = CommandLine('')
        self.assertEqual(cmdline.command, '')
        self.assertEqual(cmdline.named_args, {})
        self.assertEqual(cmdline.free_args, [])

        cmdline = CommandLine('foo')
        self.assertEqual(cmdline.command, 'foo')

        cmdline = CommandLine('foo bar')
        self.assertEqual(cmdline.command, 'foo')
        self.assertEqual(cmdline.free_args, ['bar'])

        cmdline = CommandLine('foo\tbar')
        self.assertEqual(cmdline.command, 'foo')
        self.assertEqual(cmdline.free_args, ['bar'])

        cmdline = CommandLine('foo \tbar')
        self.assertEqual(cmdline.command, 'foo')
        self.assertEqual(cmdline.free_args, ['bar'])

        cmdline = CommandLine('foo "bar \tbaz"')
        self.assertEqual(cmdline.command, 'foo')
        self.assertEqual(cmdline.free_args, ['bar \tbaz'])

        cmdline = CommandLine('foo \'bar \tbaz\'')
        self.assertEqual(cmdline.command, 'foo')
        self.assertEqual(cmdline.free_args, ['bar \tbaz'])

        cmdline = CommandLine('foo bar=baz')
        self.assertEqual(cmdline.command, 'foo')
        self.assertEqual(cmdline.named_args, {'bar': 'baz'})
