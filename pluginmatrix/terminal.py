"""Render untrusted scalar text without terminal control sequences."""
import builtins
import unicodedata


def safe_text(value) -> str:
    return ''.join(f'\\u{ord(c):04x}' if unicodedata.category(c) in ('Cc', 'Cf', 'Cs') else c for c in str(value))


def print(*values, **kwargs):
    # CLI formatting uses a leading newline; embedded newlines are data.
    rendered = []
    for value in values:
        value = str(value)
        leading = len(value) - len(value.lstrip('\n'))
        rendered.append('\n' * leading + safe_text(value[leading:]))
    builtins.print(*rendered, **kwargs)
