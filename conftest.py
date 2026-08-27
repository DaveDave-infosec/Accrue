"""
Windows compatibility shim for the gltest direct runner.

gltest's ``_inject_message_to_fd0`` writes the encoded message context to a temp
file, ``dup2``s it onto stdin, then unlinks the temp file in a ``finally``
block. On Linux a file can be unlinked while still open, so this works. On
Windows the temp file is still open through the redirected stdin, so
``os.unlink`` raises ``PermissionError`` (WinError 32) on every contract call,
which fails every test before any assertion runs.

By the time that unlink runs, stdin has already been redirected and
``vm._original_stdin_fd`` has already been set, so the message context is fully
injected. The only operation that failed is deleting a temp file. This shim
swallows that single cleanup error on Windows so the runner works there; the
temp file is left for the OS to reclaim. On Linux the wrapped function never
raises here, so the shim is a no-op.

This patches a third-party defect only. It does not touch the contract or the
tests, and it changes nothing about what the tests assert.
"""

import os as _os

import gltest.direct.loader as _loader

_orig_inject = _loader._inject_message_to_fd0


def _inject_message_to_fd0_win_safe(vm):
    try:
        return _orig_inject(vm)
    except PermissionError:
        # stdin is already redirected and _original_stdin_fd is set before the
        # failing unlink, so injection is complete; only temp cleanup failed.
        if _os.name == "nt":
            return None
        raise


_loader._inject_message_to_fd0 = _inject_message_to_fd0_win_safe
