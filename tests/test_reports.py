"""``run_pw`` classifies a supervised run and writes its report.

A stand-in ``pw.x`` replays a captured output, so the classification is
exercised without a real ``pw.x``.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

from conftest import DATA
from httk.codes.qe import run_pw

# Prints the named captured output, copies an optional CRASH, and exits with a code;
# run_pw appends ``-in pw.in``, which it ignores.
_REPLAY = "import shutil, sys; sys.stdout.write(open(sys.argv[1]).read()); sys.argv[3] != '-' and shutil.copy(sys.argv[3], 'CRASH'); sys.exit(int(sys.argv[2]))"


def _replay(output: str, code: int = 0, crash: str | None = None) -> list[str]:
    return [sys.executable, "-c", _REPLAY, str(DATA / output), str(code), crash or "-"]


@pytest.mark.parametrize(
    ("argv", "classification"),
    [
        (_replay("si.out"), "completed"),
        (_replay("si_noconv.out"), "nonconverged"),
        (_replay("si_relax_nstep.out"), "nonconverged"),
        (_replay("si_relax.out"), "completed"),
        (_replay("crash/si_crash.out", 1, str(DATA / "crash" / "CRASH")), "crashed"),
        (_replay("si.out", 3), "process_failure"),
    ],
)
def test_the_run_is_classified_and_reported(tmp_path: Path, argv: list[str], classification: str) -> None:
    report = run_pw(argv, directory=tmp_path)
    assert report.classification == classification
    assert report.ok == (classification == "completed")
    assert report.process.argv[-2:] == ("-in", "pw.in")
    saved = json.loads((tmp_path / "qe-run-report.json").read_text(encoding="utf-8"))
    assert saved["format"] == "httk-qe-run-report" and saved["classification"] == classification
    if classification == "completed":
        assert report.result.total_energy_ry is not None
        assert saved["result"]["total_energy_ry"] == report.result.total_energy_ry
        assert report.diagnostics == ()


def test_a_stale_crash_file_is_removed_before_the_run(tmp_path: Path) -> None:
    shutil.copy(DATA / "crash" / "CRASH", tmp_path)
    assert run_pw(_replay("si.out"), directory=tmp_path).ok
    assert not (tmp_path / "CRASH").exists()


def test_a_clean_rerun_after_a_crash_is_not_read_as_the_crash(tmp_path: Path) -> None:
    # pw.out is the supervisor's stdout capture: a rerun must replace it, not append to it.
    crash = str(DATA / "crash" / "CRASH")
    assert run_pw(_replay("crash/si_crash.out", 1, crash), directory=tmp_path).classification == "crashed"
    report = run_pw(_replay("si.out"), directory=tmp_path)
    assert report.classification == "completed"
    assert "qe.crash" not in {item.code for item in report.diagnostics}
