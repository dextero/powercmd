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
