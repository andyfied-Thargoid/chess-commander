"""
Headless emulator oracle driver for Chess Commander Phase 3 fidelity gates.

Runs a 1980s chess program under Xvfb (virtual framebuffer) on compute01,
captures the emulated screen with mss (X11 XGetImage), and injects keys with
xdotool — so the real reference program can be driven and its chosen move read,
without a physical display.

This is the compute01 path for the visual reference-oracle test (see
references/visual-reference-oracle-test.md). It emits the
``<backend>.oracle.json`` deliverable that the fidelity gates score.

Design
------
- ``EmuSession`` owns one Xvfb + one emulator process and a screen-grabber.
- ``capture()`` -> PIL.Image of the current framebuffer.
- ``key()/keys()/type_text()`` inject input via xdotool.
- ``boot_and_capture()`` convenience: launch, wait, grab a frame.

The per-program *navigation* (which keys reach a given position and how the
move is displayed) is intentionally a separate concern — each 1980s program has
its own graphical I/O. The primitives here are what's shared and testable.

Only stdlib + pillow are imported at module level; mss is imported lazily
inside `capture()` (it needs a live DISPLAY). Importing this module therefore
never requires a display.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional

import PIL.Image

# Xvfb display base used for the virtual framebuffer. Chosen high to avoid
# clashing with any real display. Each session picks an unused number >= this
# so two sessions (or a stale lock) cannot collide. Must be 24-bit depth or
# mss refuses to grab it.
DEFAULT_DISPLAY_BASE = 97
XVFB_DEPTH = 24
DEFAULT_SCREEN = "512x384x24"


def _free_display(start: int = DEFAULT_DISPLAY_BASE, tries: int = 20) -> str:
    """Pick a display number whose X11 lock/socket are free, starting at `start`.

    A stale lock from a crashed session otherwise makes the next Xvfb die with
    "Server is already active for display N" — the root cause of flaky runs.
    """
    for n in range(start, start + tries):
        if not (os.path.exists(f"/tmp/.X{n+1}-lock")
                or os.path.exists(f"/tmp/.X11-unix/X{n+1}")):
            return f":{n+1}"
    return f":{start + tries}"


def _clear_display_lock(display: Optional[str]) -> None:
    """Best-effort removal of a stale X11 lock/socket for `display`."""
    if display and ":" in display and display[1:].isdigit():
        n = int(display[1:])
        for p in (f"/tmp/.X{n}-lock", f"/tmp/.X11-unix/X{n}"):
            try:
                os.remove(p)
            except OSError:
                pass


class EmuError(RuntimeError):
    """Raised when the emulator/display lifecycle fails."""


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


@dataclass
class EmuSession:
    """One Xvfb display + one emulator child process + screen grabber.

    Args:
        emulator: absolute path to the emulator binary (e.g. FUSE).
        source:   absolute path to the ROM/tape/ssd to load.
        emulator_args: extra args passed to the emulator (before the source).
        display:  Xvfb display name, or None to auto-pick a free display
                  (default). Pinned to a specific string to force one.
        screen:   Xvfb screen spec (default 512x384x24).
    """

    emulator: str
    source: str
    emulator_args: List[str] = field(default_factory=list)
    display: Optional[str] = None  # None = auto-pick a free display
    screen: str = DEFAULT_SCREEN
    ld_library_path: Optional[str] = None  # e.g. /tmp/lspec/lib for FUSE

    _xvfb: Optional[subprocess.Popen] = field(default=None, repr=False)
    _emu: Optional[subprocess.Popen] = field(default=None, repr=False)
    _env: dict = field(default_factory=dict, repr=False)
    _log_xvfb: str = "/tmp/emu-xvfb.log"
    _log_emu: str = "/tmp/emu-fuse.log"

    # ---- lifecycle -------------------------------------------------------

    def __post_init__(self) -> None:
        for name, path in (("emulator", self.emulator), ("source", self.source)):
            if not os.path.isfile(path):
                raise EmuError(f"{name} not found: {path}")
        for tool in ("Xvfb", "xdotool"):
            if not _have(tool):
                raise EmuError(f"required tool missing: {tool}")
        # Pick a free display unless the caller pinned one explicitly.
        if self.display is None:
            self.display = _free_display()

    @property
    def running(self) -> bool:
        return self._emu is not None and self._emu.poll() is None

    def start(self, boot_wait: float = 6.0) -> "EmuSession":
        """Start Xvfb + the emulator, wait for boot, return self.

        Raises EmuError if Xvfb or the emulator fails to come up. On failure
        the display lock is cleared and any partially-started process stopped,
        so a crashed session cannot poison the next one.
        """
        if self.running or self._xvfb is not None:
            raise EmuError("session already started")

        assert self.display is not None  # resolved in __post_init__
        _clear_display_lock(self.display)  # drop a stale lock for this display
        try:
            # Xvfb
            self._xvfb = subprocess.Popen(
                ["Xvfb", self.display, "-screen", "0", self.screen,
                 "-ac", "-nolisten", "tcp"],
                stdout=open(self._log_xvfb, "w"), stderr=subprocess.STDOUT,
            )
            time.sleep(1.0)
            if self._xvfb.poll() is not None:
                raise EmuError("Xvfb exited at startup; see " + self._log_xvfb)

            self._env = {
                "DISPLAY": self.display,
                "LD_LIBRARY_PATH": self.ld_library_path or os.environ.get("LD_LIBRARY_PATH", ""),
            }

            # Emulator
            cmd = [self.emulator, *self.emulator_args, self.source]
            self._emu = subprocess.Popen(
                cmd, env=self._env,
                stdout=open(self._log_emu, "w"), stderr=subprocess.STDOUT,
            )
            time.sleep(boot_wait)
            if self._emu.poll() is not None:
                raise EmuError(
                    f"emulator exited at startup (rc={self._emu.returncode}); "
                    "see " + self._log_emu
                )
        except EmuError:
            self.stop()
            _clear_display_lock(self.display)
            raise
        return self

    def stop(self) -> None:
        """Terminate the emulator then Xvfb. Safe to call multiple times.

        Also clears the display lock so the next session can reuse the number.
        """
        for proc in (self._emu, self._xvfb):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        self._emu = None
        self._xvfb = None
        _clear_display_lock(self.display)

    def __enter__(self) -> "EmuSession":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    # ---- observation -----------------------------------------------------

    def capture(self) -> "PIL.Image.Image":
        """Grab the framebuffer and return a PIL.Image (RGB)."""
        from mss import MSS  # imported lazily: needs a live DISPLAY

        if not self.running:
            raise EmuError("no emulator running")
        env = dict(os.environ, DISPLAY=self.display)
        # mss reads DISPLAY from the process env; set it for this call.
        old = os.environ.get("DISPLAY")
        os.environ["DISPLAY"] = self.display
        try:
            with MSS() as sct:
                mon = sct.monitors[1]  # monitors[0] is the union of all
                shot = sct.grab(mon)
        finally:
            if old is None:
                os.environ.pop("DISPLAY", None)
            else:
                os.environ["DISPLAY"] = old
        from PIL import Image
        return Image.frombytes("RGB", shot.size, shot.rgb)

    def capture_to(self, path: str) -> str:
        img = self.capture()
        img.save(path)
        return path

    # ---- input -----------------------------------------------------------

    def focus_window(self, retries: int = 10, interval: float = 0.3) -> bool:
        """Give the emulator window keyboard focus (returns True on success).

        Xvfb has no window manager, so ``xdotool windowactivate`` fails with
        "_NET_ACTIVE_WINDOW not supported". Instead we find the FUSE window by
        name and send XSetInputFocus directly via ``windowfocus`` (no WM
        needed). Because the window can still be mapping when we first try,
        we retry until ``getwindowfocus`` confirms the FUSE window actually
        holds focus. Returns True if focus was confirmed, False if not.
        """
        if not self.running:
            raise EmuError("no emulator running")
        assert self.display is not None  # resolved in __post_init__
        env = dict(os.environ, DISPLAY=self.display)
        r = subprocess.run(
            ["xdotool", "search", "--name", "fuse"],
            env=env, capture_output=True, text=True,
        )
        wids = r.stdout.split()
        if not wids:
            return False
        # FUSE maps a parent + child window; the emulated screen is the leaf
        # (last) window, so focus that one.
        wid = wids[-1]
        for _ in range(retries):
            # XSetInputFocus directly; no window manager required.
            subprocess.run(["xdotool", "windowfocus", wid],
                           env=env, capture_output=True)
            got = subprocess.run(
                ["xdotool", "getwindowfocus"],
                env=env, capture_output=True, text=True,
            ).stdout.strip()
            if got == wid:
                return True
            time.sleep(interval)
        return False

    def key(self, *keys: str, delay: float = 0.25) -> None:
        """Press one or more keys (xdotool key). E.g. key('Return').

        Focuses the emulator window first so the keys actually reach it.
        """
        self.focus_window()
        self._xdotool(["key", *keys], delay)

    def type_text(self, text: str, delay: float = 0.05) -> None:
        """Type a string (xdotool type). Focuses the emulator window first."""
        self.focus_window()
        self._xdotool(["type", "--", text], delay)

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)

    def _xdotool(self, args: List[str], delay: float = 0.0) -> None:
        if not self.running:
            raise EmuError("no emulator running")
        env = dict(os.environ, DISPLAY=self.display)
        subprocess.run(
            ["xdotool", *args], env=env, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if delay:
            time.sleep(delay)


def boot_and_capture(
    emulator: str,
    source: str,
    out_path: str,
    *,
    emulator_args: Optional[List[str]] = None,
    ld_library_path: Optional[str] = None,
    boot_wait: float = 6.0,
) -> str:
    """One-shot: boot the emulator, capture one frame, stop, return out_path."""
    s = EmuSession(
        emulator, source, emulator_args=emulator_args or [],
        ld_library_path=ld_library_path,
    )
    s.start(boot_wait=boot_wait)
    try:
        return s.capture_to(out_path)
    finally:
        s.stop()


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    import sys
    FUSE = "/home/andyfied/src/fuse-emulator/fuse"
    SRC = "/mnt/marmot/project-data/chess-commander/sources/SpectrumChess_I.tzx"
    OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/emu_oracle_smoke.png"
    p = boot_and_capture(FUSE, SRC, OUT,
                         emulator_args=["--no-sound"],
                         ld_library_path="/tmp/lsp...")
    print("captured", p)
