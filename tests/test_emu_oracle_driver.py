"""
Tests for the headless emulator oracle driver (tools/emu_oracle_driver.py).

The driver's pure logic (argument building, lifecycle guards, error handling)
is tested unconditionally. The end-to-end capture test that needs a live Xvfb +
FUSE is skipped when those tools/files are not present, matching the repo's
convention of skipping hardware-dependent tests.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Load the driver from tools/ (it is a script, not a package module).
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DRIVER_PATH = _REPO_ROOT / "tools" / "emu_oracle_driver.py"
_spec = importlib.util.spec_from_file_location("emu_oracle_driver", _DRIVER_PATH)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
sys.modules["emu_oracle_driver"] = mod  # register BEFORE exec (dataclasses need it)
_spec.loader.exec_module(mod)

EmuSession = mod.EmuSession
EmuError = mod.EmuError

FUSE = "/home/andyfied/src/fuse-emulator/fuse"
SPECTRUM_I = "/mnt/marmot/project-data/chess-commander/sources/SpectrumChess_I.tzx"
LSP = "/tmp/lspec/lib"


# ---- pure logic (always run) --------------------------------------------

def test_missing_emulator_raises():
    with pytest.raises(EmuError):
        EmuSession("/nonexistent/fuse", SPECTRUM_I)


def test_missing_source_raises():
    with pytest.raises(EmuError):
        EmuSession(FUSE, "/nonexistent/source.tzx")


def test_default_display_and_depth():
    # 24-bit depth is required for mss. The display is auto-picked (None) to
    # avoid colliding with any real or stale display; the base is a high
    # number so the free picker stays clear of real displays.
    assert "24" in mod.DEFAULT_SCREEN
    assert mod.DEFAULT_DISPLAY_BASE >= 97
    s = EmuSession(FUSE, SPECTRUM_I)
    assert s.display.startswith(":") and int(s.display[1:]) >= 97


def test_running_false_before_start():
    s = EmuSession(FUSE, SPECTRUM_I)  # FUSE exists; source exists on this host
    assert s.running is False


def test_double_start_raises():
    s = EmuSession(FUSE, SPECTRUM_I)
    # Simulate an already-started session without a real process.
    class _FakeProc:
        def poll(self):
            return None  # still alive
    s._emu = _FakeProc()
    with pytest.raises(EmuError, match="already started"):
        s.start()


def test_xdotool_requires_running():
    s = EmuSession(FUSE, SPECTRUM_I)
    with pytest.raises(EmuError, match="no emulator running"):
        s.key("Return")


def test_capture_requires_running():
    s = EmuSession(FUSE, SPECTRUM_I)
    with pytest.raises(EmuError, match="no emulator running"):
        s.capture()


def test_stop_never_started_does_not_clear_lock(tmp_path):
    """stop() on a never-started session must not delete a display lock that
    belongs to someone else (the display was only provisionally picked in
    __post_init__)."""
    # Use a display that is NOT in the free range, so _free_display won't
    # naturally pick it and no other session owns it.
    s = EmuSession(FUSE, SPECTRUM_I, display=":97")
    lock = "/tmp/.X97-lock"
    # Create a sentinel lock file (stand-in for a real X lock).
    Path(lock).write_text("sentinel")
    try:
        s.stop()  # must NOT clear it, since the session never started
        assert Path(lock).exists(), "stop() cleared an unrelated display lock"
    finally:
        Path(lock).unlink(missing_ok=True)


def test_free_display_raises_when_none_free(monkeypatch):
    """_free_display must raise EmuError (not fabricate a number) when every
    candidate display is busy."""
    monkeypatch.setattr(mod.os.path, "exists", lambda p: True)
    with pytest.raises(EmuError, match="no free Xvfb display"):
        mod._free_display(start=97, tries=20)


# ---- end-to-end capture (skip when tools/files absent) -------------------

def _tools_present() -> bool:
    return (
        mod._have("Xvfb")
        and mod._have("xdotool")
        and os.path.isfile(FUSE)
        and os.path.isfile(SPECTRUM_I)
        and os.path.isdir(LSP)
    )


@pytest.mark.skipif(not _tools_present(), reason="Xvfb/FUSE/sources not present")
def test_boot_and_capture_produces_nonblank_frame(tmp_path):
    out = tmp_path / "frame.png"
    mod.boot_and_capture(
        FUSE, SPECTRUM_I, str(out),
        emulator_args=["--no-sound"],
        ld_library_path=LSP,
        boot_wait=6.0,
    )
    assert out.exists()
    from PIL import Image
    im = Image.open(str(out)).convert("RGB")
    assert im.size == (512, 384)
    # The emulated Spectrum Chess screen is not blank: it must contain more
    # than a handful of distinct colors (a black screen would be 1-2).
    px = im.load()
    distinct = {px[x, y] for x in range(0, im.width, 4)
                for y in range(0, im.height, 4)}
    assert len(distinct) > 10, f"frame looks blank: only {len(distinct)} colors"


@pytest.mark.skipif(not _tools_present(), reason="Xvfb/FUSE/sources not present")
def test_keyboard_input_reaches_emu(tmp_path):
    """At least one keypress must visibly change the framebuffer.

    Probing the Spectrum Chess I screen showed several keys change the display
    (~128-150 px) once the tape has loaded, but delivery under Xvfb is
    timing-sensitive (a single fixed key can be flaky). So this test tries a
    small set of keys and passes if ANY of them visibly changes the screen —
    a robust "input reaches the emu" signal — while still FAILING if none of
    them do (i.e. xdotool is not delivering at all).

    NOTE: per-key reliability (which exact key, and deterministically) is a
    separate, harder problem to solve before the full oracle can be trusted.
    """
    from PIL import ImageChops

    def delta_px(a, b):
        d = ImageChops.difference(a, b)
        bbox = d.getbbox()
        if not bbox:
            return 0
        px = d.load()
        return sum(1 for x in range(bbox[0], bbox[2])
                   for y in range(bbox[1], bbox[3]) if any(px[x, y]))

    s = EmuSession(FUSE, SPECTRUM_I, emulator_args=["--no-sound"],
                   ld_library_path=LSP)
    s.start(boot_wait=8.0)
    try:
        # Retry the key sweep up to 3 rounds: under Xvfb the tape can load
        # slowly, so the first round's keys may land before the program is
        # interactive. Each round re-captures a fresh baseline. A successful
        # round (any key changes >=20px) breaks out early.
        best = 0
        for _round in range(3):
            for key in ("w", "W", "Return", "space", "S"):
                before = s.capture()
                s.key(key)
                s.wait(1.0)
                after = s.capture()
                best = max(best, delta_px(before, after))
                if best >= 20:
                    break
            if best >= 20:
                break
        assert best >= 20, (
            f"no keypress visibly changed the screen (best delta={best}px) — "
            "xdotool input is not reaching the emu"
        )
    finally:
        s.stop()
