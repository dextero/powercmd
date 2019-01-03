"""
Utility function for splitting a string into list of elements.
"""

_DELIMITERS = {
    '(': ')',
    '[': ']',
    '{': '}',
    '"': '"',
    "'": "'",
}


def split_list(text: str,
               separator: str = ',',
               allow_unmatched: bool = False):
    """
    Splits TEXT on SEPARATOR, preserving SEPARATOR nested inside pairs of
    parens, brackets, braces and quotes.

    If ALLOW_UNMATCHED is False, an exception is thrown if the parens/quotes
    are unbalanced.
    """

    if len(separator) != 1:
        raise ValueError('only single-character separators are supported')
    if separator in _DELIMITERS:
        raise ValueError('delimiters: %s are not supported'
                         % (''.join(_DELIMITERS),))

    stack = []
    start = 0

    for idx, char in enumerate(text):
        if stack:
            if stack[-1] == char:
                stack.pop()
        elif char in _DELIMITERS:
            stack.append(_DELIMITERS[char])
        elif char == separator:
            yield text[start:idx]
            start = idx + 1

    if not allow_unmatched and stack:
        raise ValueError('text contains unmatched delimiters: %s (text = %s)'
                         % (''.join(stack), text))

    yield text[start:]
