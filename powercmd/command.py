import collections
import inspect
from typing import Callable, Mapping

from powercmd.extra_typing import OrderedMapping


NO_DEFAULT = inspect._empty


class Parameter(collections.namedtuple('Parameter', ['name', 'type', 'default'])):
    def __str__(self):
        # TODO: check if type is Optional[x], print None in such case
        result = '%s: %s' % (self.name, self.type)
        if self.default is not None:
            result += ' = %s' % repr(self.default)
        return result


class Command(collections.namedtuple('Command', ['name', 'handler'])):
    @staticmethod
    def _get_handler_params(handler: Callable) -> OrderedMapping[str, inspect.Parameter]:
        """Returns a list of command parameters for given HANDLER."""
        params = inspect.signature(handler).parameters
        params = list(params.items())
        if params and params[0][0] == 'self':
            params = params[1:]  # drop 'self'
        params = collections.OrderedDict(params)  # drop 'self'
        return params

    @property
    def parameters(self) -> Mapping[str, Parameter]:
        params = self._get_handler_params(self.handler)
        return dict((name, Parameter(name=name, type=param.annotation, default=param.default))
                    for name, param in params.items())

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
                % (self.description or 'No details available.',
                   self.name,
                   ' '.join(str(param) for param in self.parameters)))
