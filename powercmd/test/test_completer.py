import enum
import unittest
from typing import List, Tuple

from powercmd.completer import Completer
from powercmd.command import Command
from powercmd.commands_dict import CommandsDict
from powercmd.test import test_utils

from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document


class TestEnum(enum.Enum):
    First = 1
    Second = 2


class TestCompleter(unittest.TestCase):
    def test_complete_simple(self):
        def do_test(self,
                    arg_first: str,
                    arg_second: int,
                    third: str):
            pass

        cmds = CommandsDict()
        cmds['test'] = Command('test', do_test)
        completer = Completer(cmds)

        self.assertEqual(list(completer.get_completions(Document(text='t', cursor_position=1))),
                         [Completion('test', start_position=-1)])

        self.assertEqual(list(completer.get_completions(Document(text='test ', cursor_position=5))),
                         [Completion('arg_first', start_position=0, display_meta=str(str)),
                          Completion('arg_second', start_position=0, display_meta=str(int)),
                          Completion('third', start_position=0, display_meta=str(str))])

        self.assertEqual(list(completer.get_completions(Document(text='test arg', cursor_position=8))),
                         [Completion('arg_first', start_position=-3, display_meta=str(str)),
                          Completion('arg_second', start_position=-3, display_meta=str(int))])

        self.assertEqual(list(completer.get_completions(Document(text='test arg_f', cursor_position=10))),
                         [Completion('arg_first', start_position=-5, display_meta=str(str))])

    def test_complete_enum(self):
        def do_test(self,
                    arg: TestEnum):
            pass

        cmds = CommandsDict()
        cmds['test'] = Command('test', do_test)
        completer = Completer(cmds)

        self.assertEqual(list(completer.get_completions(Document(text='test arg=', cursor_position=9))),
                         [Completion('First', start_position=0, display_meta='1'),
                          Completion('Second', start_position=0, display_meta='2')])

    def test_complete_list(self):
        def do_test(self,
                    arg: List[TestEnum]):
            pass

        cmds = CommandsDict()
        cmds['test'] = Command('test', do_test)
        completer = Completer(cmds)

        self.assertEqual(list(completer.get_completions(Document(text='test arg=', cursor_position=9))),
                         [Completion('First', start_position=0, display_meta='1'),
                          Completion('Second', start_position=0, display_meta='2')])

        self.assertEqual(list(completer.get_completions(Document(text='test arg=First,', cursor_position=14))),
                         [Completion('First', start_position=0, display_meta='1'),
                          Completion('Second', start_position=0, display_meta='2')])

    def test_complete_tuple(self):
        class TestEnum2(enum.Enum):
            A = 1
            B = 2

        def do_test(self,
                    arg: Tuple[TestEnum, TestEnum2]):
            pass

        cmds = CommandsDict()
        cmds['test'] = Command('test', do_test)
        completer = Completer(cmds)

        self.assertEqual(list(completer.get_completions(Document(text='test arg=', cursor_position=9))),
                         [Completion('First', start_position=0, display_meta='1'),
                          Completion('Second', start_position=0, display_meta='2')])

        self.assertEqual(list(completer.get_completions(Document(text='test arg=First,', cursor_position=14))),
                         [Completion('A', start_position=0, display_meta='1'),
                          Completion('B', start_position=0, display_meta='2')])

        self.assertEqual(list(completer.get_completions(Document(text='test arg=First,A,', cursor_position=16))),
                         [])

    def test_complete_custom_completer_legacy(self):
        class TestType(object):
            @test_utils.static_mock
            @staticmethod
            def powercmd_complete(text):
                # test completer returning a list of strings instead of List[Completion]
                return ['complete'] if 'complete'.startswith(text) else []

            def __init__(self, s):
                self.s = s

        def do_test(self,
                    arg: TestType):
            pass

        cmds = CommandsDict()
        cmds['test'] = Command('test', do_test)
        completer = Completer(cmds)

        with TestType.powercmd_complete.expect_no_calls():
            self.assertEqual(list(completer.get_completions(Document(text='test arg', cursor_position=8))),
                             [Completion('arg', start_position=-3, display_meta=str(TestType))])

        with TestType.powercmd_complete.expect_call('c'):
            self.assertEqual(list(completer.get_completions(Document(text='test arg=c', cursor_position=9))),
                             [Completion('complete', start_position=-1)])
