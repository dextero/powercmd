import unittest
from typing import List, Tuple

from powercmd.test import test_utils
from powercmd.command_invoker import CommandInvoker
from powercmd.command_line import CommandLine
from powercmd.commands_dict import CommandsDict


class TestCommandInvoker(unittest.TestCase):
    def test_invoke_primitive_str(self):
        @test_utils.mock
        def do_test(self, str_var: str):
            pass

        cmds = CommandsDict()
        cmds['test'] = do_test

        invoker = CommandInvoker(cmds)
        with do_test.expect_call(str_var='str'):
            invoker.invoke(CommandLine('test str'))

    def test_invoke_primitive_int(self):
        @test_utils.mock
        def do_test(self, int_var: int):
            pass

        cmds = CommandsDict()
        cmds['test'] = do_test

        invoker = CommandInvoker(cmds)
        with do_test.expect_call(int_var=42):
            invoker.invoke(CommandLine('test 42'))

    def test_invoke_class(self):
        class ClassConstructor(str):
            pass

        @test_utils.mock
        def do_test(self,
                    cls_var: ClassConstructor):
            pass

        cmds = CommandsDict()
        cmds['test'] = do_test

        invoker = CommandInvoker(cmds)
        with do_test.expect_call(cls_var=ClassConstructor('cls')):
            invoker.invoke(CommandLine('test cls'))

    def test_invoke_free_args(self):
        def do_test(self,
                    first: str,
                    second: int):
            pass

        cmds = CommandsDict()
        cmds['test'] = do_test

        invoker = CommandInvoker(cmds)
        with do_test.expect_call(first='first',
                                 second=2):
            invoker.invoke(CommandLine('test first 2'))

    def test_invoke_named_args(self):
        @test_utils.mock
        def do_test(self,
                    first: str,
                    second: int):
            pass

        cmds = CommandsDict()
        cmds['test'] = do_test

        invoker = CommandInvoker(cmds)
        with do_test.expect_call(first='first',
                                 second=2):
            invoker.invoke(CommandLine('test first=first second=2'))
        with do_test.expect_call(first='first',
                                 second=2):
            invoker.invoke(CommandLine('test second=2 first=first'))

    def test_invoke_mixed_free_named(self):
        @test_utils.mock
        def do_test(self,
                    first: str,
                    second: int):
            pass

        cmds = CommandsDict()
        cmds['test'] = do_test

        invoker = CommandInvoker(cmds)
        with do_test.expect_call(first='first',
                                 second=2):
            invoker.invoke(CommandLine('test first second=2'))

        with do_test.expect_no_calls():
            invoker.invoke(CommandLine('test first=first 2'))

    def test_invoke_list(self):
        @test_utils.mock
        def do_test(self,
                    arg: List[int]):
            pass

        cmds = CommandsDict()
        cmds['test'] = do_test

        invoker = CommandInvoker(cmds)
        with do_test.expect_call(arg=[3, 42]):
            invoker.invoke(CommandLine('test arg=[3,42]'))

    def test_construct_tuple(self):
        @test_utils.mock
        def do_test(self,
                    arg: Tuple[float, str]):
            pass

        cmds = CommandsDict()
        cmds['test'] = do_test

        invoker = CommandInvoker(cmds)
        with do_test.expect_call(arg=(float(3), 'foo')):
            invoker.invoke(CommandLine('test arg=(3,foo)'))
