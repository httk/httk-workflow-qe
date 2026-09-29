"""``parse_pw_output`` reads real captured ``pw.x`` 7.5 output."""

from pathlib import Path

import pytest

from conftest import DATA
from httk.codes.qe import RY_TO_EV, parse_pw_output


def test_a_converged_scf_run() -> None:
    result = parse_pw_output(DATA / "si.out")
    assert result.total_energy_ry == -15.61554645
    assert result.total_energy_ev == pytest.approx(-15.61554645 * RY_TO_EV)
    assert (result.converged, result.scf_iterations, result.job_done, result.errors) == (True, 6, True, ())
    assert result.ionic_converged is None


def test_an_scf_run_that_stopped_unconverged() -> None:
    result = parse_pw_output(DATA / "si_noconv.out")
    # Only a converged cycle prints the "!" total-energy line.
    assert result.total_energy_ry is None and result.total_energy_ev is None
    assert (result.converged, result.scf_iterations, result.job_done, result.errors) == (False, 2, True, ())


def test_a_crash_reads_the_error_block_once_from_output_and_crash_file() -> None:
    result = parse_pw_output(DATA / "crash" / "si_crash.out")
    assert (result.total_energy_ry, result.converged, result.job_done) == (None, None, False)
    assert len(result.errors) == 1
    assert result.errors[0].startswith("read_namelists: bad line in namelist &control")


def test_a_converged_relaxation() -> None:
    result = parse_pw_output(DATA / "si_relax.out")
    assert (result.total_energy_ry, result.converged, result.ionic_converged) == (-15.61554668, True, True)


def test_a_relaxation_stopped_at_nstep() -> None:
    result = parse_pw_output(DATA / "si_relax_nstep.out")
    # Every SCF cycle converged; the ionic loop did not.
    assert (result.total_energy_ry, result.converged, result.ionic_converged) == (-15.61523769, True, False)
    assert result.job_done


def test_a_hybrid_functional_outer_loop_energy_wins(tmp_path: Path) -> None:
    # A synthetic snippet in pw.x's layout, not a captured run: the "!!" line of the
    # last EXX outer loop is the total energy, even with a later inner "!" line.
    (tmp_path / "pw.out").write_text(
        """
!    total energy              =     -15.80000000 Ry
!!   total energy              =     -15.81000000 Ry
!    total energy              =     -15.82000000 Ry
!!   total energy              =     -15.83000000 Ry
!    total energy              =     -15.84000000 Ry
     convergence has been achieved in   3 iterations
   JOB DONE.
""",
        encoding="utf-8",
    )
    assert parse_pw_output(tmp_path / "pw.out").total_energy_ry == -15.83


def test_a_relaxation_whose_last_scf_failed_has_no_energy(tmp_path: Path) -> None:
    # The captured relax output cut after its first "!" step, with a failed next SCF appended.
    text = (DATA / "si_relax.out").read_text(encoding="utf-8")
    first = text.index("convergence has been achieved")
    tail = "\n     convergence NOT achieved after  100 iterations: stopping\n"
    (tmp_path / "pw.out").write_text(text[: text.index("\n", first)] + tail, encoding="utf-8")
    result = parse_pw_output(tmp_path / "pw.out")
    assert (result.converged, result.total_energy_ry) == (False, None)
