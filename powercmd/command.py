import collections
import inspect
import textwrap
from typing import Callable, Mapping

from powercmd.extra_typing import OrderedMapping


NO_DEFAULT = inspect._empty


class Parameter(collections.namedtuple('Parameter', ['name', 'type', 'default'])):
    def __new__(cls, *args, **kwargs):
        param = super().__new__(cls, *args, **kwargs)
        if param.type == inspect._empty:
            raise ValueError('Type not specified for paramter %s' % param.name)
        return param

    def __str__(self):
        # TODO: check if type is Optional[x], print None in such case
        result = '%s: %s' % (self.name, self.type)
        if self.default is not None:
            result += ' = %s' % repr(self.default)
        return result


class Command(collections.namedtuple('Command', ['name', 'handler'])):
    def __new__(cls, *args, **kwargs):
        cmd = super().__new__(cls, *args, **kwargs)
        cmd._get_parameters()
        return cmd

    def _get_handler_params(self) -> OrderedMapping[str, inspect.Parameter]:
        """Returns a list of command parameters for given HANDLER."""
        params = inspect.signature(self.handler).parameters
        params = list(params.items())
        if params and params[0][0] == 'self':
            params = params[1:]  # drop 'self'
        params = collections.OrderedDict(params)  # drop 'self'
        return params

    def _get_parameters(self) -> Mapping[str, Parameter]:
        try:
            params = self._get_handler_params()
            return collections.OrderedDict((name, Parameter(name=name,
                                                            type=param.annotation,
                                                            default=param.default))
                                           for name, param in params.items())
        except ValueError as e:
            raise ValueError('Unable to list parameters for handler: %s' % self.name) from e

    @property
    def parameters(self) -> Mapping[str, Parameter]:
        return self._get_parameters()

    @property
    def description(self) -> str:
        return self.handler.__doc__

    @property
    def short_description(self) -> str:
        if self.description is not None:
            return self.description.strip().split('\n', maxsplit=1)[0]

    @property
    def help(self):
        return ('%s\n\nARGUMENTS: %s %s\n'
                % (textwrap.dedent(self.description or 'No details available.').strip(),
                   self.name,
                   ' '.join(str(param) for param in self.parameters)))
