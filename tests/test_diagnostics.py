"""``diagnose_pw`` maps finished calculations to the stable ``qe.*`` codes."""

import shutil
from pathlib import Path

from conftest import DATA
from httk.codes.qe import diagnose_pw


def _codes(directory: Path, output: str) -> list[tuple[str, str]]:
    return [(item.code, item.severity) for item in diagnose_pw(directory, output=output)]


def test_a_converged_run_has_no_diagnostics() -> None:
    assert diagnose_pw(DATA, output="si.out") == ()


def test_an_unconverged_run_is_an_error() -> None:
    assert _codes(DATA, "si_noconv.out") == [("qe.scf_not_converged", "error")]


def test_a_relaxation_stopped_at_nstep_is_an_error() -> None:
    assert _codes(DATA, "si_relax_nstep.out") == [("qe.ionic_not_converged", "error")]
    assert diagnose_pw(DATA, output="si_relax.out") == ()


def test_a_crash_is_fatal_and_names_the_message() -> None:
    (diagnostic,) = diagnose_pw(DATA / "crash", output="si_crash.out")
    assert (diagnostic.code, diagnostic.severity, diagnostic.source) == ("qe.crash", "fatal", "CRASH")
    assert "bad line in namelist &control" in diagnostic.summary


def test_a_truncated_or_missing_output_is_incomplete(tmp_path: Path) -> None:
    text = (DATA / "si.out").read_text(encoding="utf-8")
    (tmp_path / "pw.out").write_text(text[: len(text) // 2], encoding="utf-8")
    assert _codes(tmp_path, "pw.out") == [("qe.incomplete", "error")]
    assert _codes(tmp_path, "absent.out") == [("qe.incomplete", "error")]
    shutil.copy(DATA / "crash" / "CRASH", tmp_path)
    assert _codes(tmp_path, "absent.out") == [("qe.crash", "fatal")]
