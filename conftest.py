"""
Windows + time-control shims for the gltest direct runner.

Both patches fix third-party runner defects only. Neither touches the contract
or the tests, and neither changes what any test asserts.

1. Windows temp-file cleanup.
   gltest's ``_inject_message_to_fd0`` writes the encoded message to a temp file,
   ``dup2``s it onto stdin, then unlinks the temp file in a ``finally``. On Linux
   a file can be unlinked while open; on Windows it cannot, so ``os.unlink``
   raises ``PermissionError`` (WinError 32) on every contract call. By then stdin
   is already redirected and injection is complete, so we swallow that one
   cleanup error on Windows and let the OS reclaim the temp file.

2. Time propagation for ``warp``.
   ``VMContext.warp`` updates the VM's internal clock and refreshes the message
   sender, but it never updates ``gl.message_raw['datetime']`` (see
   ``_refresh_gl_message``, which only rewrites sender_address / origin_address).
   The contract reads its clock from ``gl.message_raw['datetime']``, which is
   frozen at deploy time, so ``warp`` has no effect on the contract and no epoch
   window can ever close. This shim makes ``warp`` also write the new timestamp
   into the live ``gl.message_raw`` dict, which is what ``warp`` documents itself
   as doing.
"""

import os as _os
import sys as _sys

import gltest.direct.loader as _loader
import gltest.direct.vm as _vm


# ---- 1. Windows temp-file cleanup ----
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


# ---- 2. Make warp actually move the contract clock ----
_orig_warp = _vm.VMContext.warp


def _warp_propagating(self, timestamp):
    _orig_warp(self, timestamp)
    gl = _sys.modules.get("genlayer.gl")
    if gl is not None:
        mr = getattr(gl, "message_raw", None)
        if isinstance(mr, dict):
            mr["datetime"] = timestamp


_vm.VMContext.warp = _warp_propagating
