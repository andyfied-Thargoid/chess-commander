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
    Raises EmuError if none of the candidate displays is free, rather than
    fabricating a number that is presumably also busy.
    """
    for n in range(start, start + tries):
        d = n + 1
        try:
            busy = (os.path.exists(f"/tmp/.X{d}-lock")
                    or os.path.exists(f"/tmp/.X11-unix/X{d}"))
        except OSError:
            continue  # /tmp/.X11-unix unreadable: skip this candidate
        if not busy:
            return f":{d}"
    raise EmuError(
        f"no free Xvfb display in :{start}..:{start + tries - 1} "
        "(all locks/sockets in use)"
    )


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
    _started: bool = field(default=False, repr=False)
    _log_xvfb: str = "/tmp/emu-xvfb.log"
    _log_emu: str = "/tmp/emu-fuse.log"
    _log_files: List = field(default_factory=list, repr=False)

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
            self._log_files.append(open(self._log_xvfb, "w"))
            self._xvfb = subprocess.Popen(
                ["Xvfb", self.display, "-screen", "0", self.screen,
                 "-ac", "-nolisten", "tcp"],
                stdout=self._log_files[-1], stderr=subprocess.STDOUT,
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
            self._log_files.append(open(self._log_emu, "w"))
            self._emu = subprocess.Popen(
                cmd, env=self._env,
                stdout=self._log_files[-1], stderr=subprocess.STDOUT,
            )
            time.sleep(boot_wait)
            if self._emu.poll() is not None:
                raise EmuError(
                    f"emulator exited at startup (rc={self._emu.returncode}); "
                    "see " + self._log_emu
                )
            self._started = True
        except EmuError:
            self.stop()
            raise
        return self

    def stop(self) -> None:
        """Terminate the emulator then Xvfb. Safe to call multiple times.

        Re-waits after SIGKILL so the child is reaped (no zombie) and the
        X socket is actually gone before the display lock is cleared. Only
        clears the display lock if the session actually started, so a
        never-started session's stop() cannot delete an unrelated lock.
        """
        for proc in (self._emu, self._xvfb):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    try:
                        proc.wait(timeout=5)  # reap the killed child
                    except subprocess.TimeoutExpired:
                        pass
        self._emu = None
        self._xvfb = None
        for fh in self._log_files:
            try:
                fh.close()
            except OSError:
                pass
        self._log_files.clear()
        if self._started:
            _clear_display_lock(self.display)
            self._started = False

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

    def type_answer(self, answer: str, char_delay_ms: int = 150,
                    settle: float = 1.2) -> None:
        """Send one input *unit* (a character, a short answer, or a key) to the
        emulated program reliably, then wait for the program to react.

        This is the reliable input primitive for the 1980s programs: the
        program reads its answer as a single unit, so the whole answer (and any
        terminator such as ``\\r``) is sent in ONE ``xdotool type`` call with a
        small per-character delay and a fresh window focus. Splitting a
        character and its terminator into separate calls (or relying on
        ``xdotool key`` for an uppercase letter) is the race that makes input
        flaky under Xvfb — one call per unit is the fix.

        Args:
            answer:        the text to send, e.g. ``"P\\r"`` (menu choice + CR)
                           or ``"E2 E4\\r"`` (a full chess move and CR).
            char_delay_ms: per-character delay for ``xdotool type --delay``.
            settle:        seconds to wait after sending, so the program can
                           redraw before the next capture/step.
        """
        if not self.running:
            raise EmuError("no emulator running")
        self.focus_window()
        time.sleep(0.4)
        env = {**os.environ, "DISPLAY": self.display}
        subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay",
             str(int(char_delay_ms)), "--", answer],
            env=env, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(settle)

    def commit_entry(self, key: str = "Return", settle: float = 2.0) -> None:
        """Press a special key (default Enter) to commit staged text and wait
        for the reaction.

        This remains available for programs that stage text before a separate
        commit. Spectrum Chess I is different: it requires the full source and
        destination squares plus carriage return in one input unit, for example
        ``type_answer("E2 E4\\r")``. Lower levels reply near-instantly; higher
        levels take longer to search (see ``wait_for_computer_reply``).
        """
        if not self.running:
            raise EmuError("no emulator running")
        self.focus_window()
        time.sleep(0.4)
        env = {**os.environ, "DISPLAY": self.display}
        subprocess.run(
            ["xdotool", "key", "--clearmodifiers", key],
            env=env, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(settle)

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


def navigate_spectrum_chess_i(
    s: "EmuSession",
    *,
    colour: str = "W",
    level: int = 4,
    settle: float = 1.5,
) -> "PIL.Image.Image":
    """Drive a booted Spectrum Chess I session to a playable board, and return
    the board frame.

    Verified key sequence (one ``xdotool type`` call per input unit, each with a
    carriage return appended so the program accepts it in one read):

      1. ``P\\r``   -> PLAY (from the PLAY / ANALYSE / OR LOAD? menu)
      2. ``W\\r``   -> your colour (WHITE; use ``"B"`` for Black)
      3. ``{lvl}\\r``-> level of play, 0-6 (0 = weakest/fastest, 6 = strongest)

    After this the emulated board is shown in the standard starting position.
    If you chose White it is the *player's* move next; if Black, the computer
    (White) moves first — call ``wait_for_computer_reply`` to read it.

    Args:
        s:      a started ``EmuSession`` running Spectrum Chess I.
        colour: ``"W"`` (default, player is White) or ``"B"``.
        level:  0-6; lower = weaker/faster computer reply.
        settle: seconds to wait after each menu answer.

    Returns:
        PIL.Image of the board once the position is set up.
    """
    if colour not in ("W", "B"):
        raise EmuError("colour must be 'W' or 'B'")
    if not 0 <= level <= 6:
        raise EmuError("level must be 0-6")
    s.type_answer("P\r", settle=settle)
    s.type_answer(f"{colour}\r", settle=settle)
    s.type_answer(f"{level}\r", settle=settle)
    return s.capture()


def play_move(
    s: "EmuSession",
    move: str,
    *,
    commit: str = "Return",
    settle: float = 0.0,
    attempts: int = 3,
) -> "PIL.Image.Image":
    """Enter one player move in the running game and commit it, returning the
    resulting frame (the computer will then start searching for its reply).

    Spectrum Chess I accepts a full coordinate move with a space between the
    source and destination squares, followed by carriage return, e.g.
    ``E2 E4\\r``. The complete input must be delivered in one xdotool call;
    sending the move and Enter separately leaves the program at the player
    prompt. This retries the full input up to ``attempts`` times. After each
    attempt it checks whether the move landed — a landed move changes the board;
    an unaccepted input leaves it byte-identical.
    It returns as soon as the move is confirmed, or after the final attempt.

    The *authoritative* confirmation is a subsequent board change — pair this
    with ``wait_for_computer_reply(frame)`` to read the computer's reply.

    Args:
        s:       a started session already at the board.
        move:    the full coordinate move to type, e.g. ``"E2 E4"``.
        commit:  retained for compatibility with staged-input callers; the
                 Spectrum Chess I path commits with carriage return in the same
                 input unit.
        settle:  seconds to wait after sending before checking.
        attempts: how many times to retry the type+commit (default 3).
    """
    baseline = s.capture()
    frame = baseline
    for _attempt in range(attempts):
        s.type_answer(f"{move}\\r", settle=settle)
        frame = s.capture()
        # A landed move changes the board (the piece moves, the status line
        # updates). A dropped commit leaves the board byte-identical.
        if _frame_diff(baseline, frame) > 0:
            return frame
    return frame


def _frame_diff(a: "PIL.Image.Image", b: "PIL.Image.Image") -> int:
    """Number of pixels that differ between two same-size RGB frames (0..N).

    Used as the change detector for ``wait_for_computer_reply``: when the
    computer moves a piece, the board pixels change. Cheaper and far more
    reliable than asking an OCR model "did a piece move?" on every poll.
    """
    from PIL import ImageChops
    if a.size != b.size:
        b = b.resize(a.size)
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    # getbbox() is None when the frames are identical (all-black diff) and a
    # bounding box when anything differs. Counting the non-black pixels inside
    # that box gives a stable "how much changed" number: 0 for identical frames,
    # a large value when a chess piece has moved. (The flat histogram is laid
    # out as [R0..R255, G0..G255, B0..B255], so slicing it as one channel is a
    # bug — getbbox + pixel count is the correct, simple detector.)
    box = diff.getbbox()
    if box is None:
        return 0
    px = diff.load()
    return sum(1 for x in range(box[0], box[2])
               for y in range(box[1], box[3]) if any(px[x, y]))


def wait_for_computer_reply(
    s: "EmuSession",
    before: "PIL.Image.Image",
    *,
    timeout: float = 120.0,
    poll: float = 5.0,
    min_changed: int = 300,
) -> "PIL.Image.Image":
    """Wait until the computer has played its reply (the board changed), then
    return the new frame.

    ``before`` is the frame captured right after the player's move was
    committed. This polls ``s.capture()`` until the frame differs from
    ``before`` by at least ``min_changed`` (a moved piece changes many pixels),
    or ``timeout`` seconds elapse — whichever comes first. It returns the
    first changed frame on success, or the last frame on timeout (the caller
    should treat an unchanged board as "computer has not moved yet").

    Lower engine levels reply near-instantly; level 6 may need the full
    timeout. The frame-diff detector avoids OCR's unreliable per-poll yes/no.
    """
    deadline = time.time() + timeout
    last = s.capture()
    while time.time() < deadline:
        time.sleep(poll)
        last = s.capture()
        if _frame_diff(before, last) >= min_changed:
            return last
    return last


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    import sys
    FUSE = "/home/andyfied/src/fuse-emulator/fuse"
    SRC = "/mnt/marmot/project-data/chess-commander/sources/SpectrumChess_I.tzx"
    OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/emu_oracle_smoke.png"
    p = boot_and_capture(FUSE, SRC, OUT,
                         emulator_args=["--no-sound"],
                         ld_library_path="/tmp/lsp...")
    print("captured", p)
