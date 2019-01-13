import enum
from typing import Sequence

import prompt_toolkit.completion
from prompt_toolkit.completion import Completion
from prompt_toolkit.completion.base import CompleteEvent
from prompt_toolkit.document import Document

from powercmd.command import Command
from powercmd.commands_dict import CommandsDict
from powercmd.match_string import match_string
from powercmd.utils import is_generic_list, is_generic_tuple, is_generic_type
from powercmd.split_list import split_list


class Completer(prompt_toolkit.completion.Completer):
    def __init__(self, commands: CommandsDict):
        self._cmds = commands

    def _complete_commands(self, incomplete_cmd: str) -> Sequence[Completion]:
        """
        Returns a sequence of command completions matching INCOMPLETE_CMD prefix.
        """
        matching_cmds = (self._cmds[cmd] for cmd in match_string(incomplete_cmd, self._cmds))
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
        return self._complete_value(inner_types[len(args) - 1], args[-1])

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
                        type_hint: type,
                        incomplete_value: str) -> Sequence[Completion]:
        """
        Returns a sequence of parameter value completions matching
        INCOMPLETE_VALUE prefix for given CMD.
        """
        if is_generic_type(type_hint):
            if is_generic_list(type_hint):
                return self._complete_generic_list(type_hint.__args__[0], incomplete_value)
            if is_generic_tuple(type_hint):
                return self._complete_generic_tuple(type_hint.__args__, incomplete_value)
            raise NotImplementedError('generic constructor for %s not implemented'
                                      % (type_hint,))

        if isinstance(type_hint, type) and issubclass(type_hint, enum.Enum):
            return self._complete_enum(type_hint, incomplete_value)
        if hasattr(type_hint, 'powercmd_complete'):
            return self._complete_custom(type_hint, incomplete_value)

        return [Completion('', display_meta=str(type_hint))]

    def get_completions(self,
                        document: Document,
                        _complete_event: CompleteEvent = None) -> Sequence[Completion]:
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
            cmd = self._cmds.choose(incomplete_cmd)
        except ValueError:
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
