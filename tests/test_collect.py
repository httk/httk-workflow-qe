"""``collect_pw`` gates on a converged energy and a converged relaxation."""

import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from conftest import DATA
from httk.codes.qe import RY_TO_EV, collect_pw


def _record(workdir: Path, output: str) -> Any:
    shutil.copy(DATA / output, workdir / "pw.out")
    return cast(Any, SimpleNamespace(data=None, workdir=workdir, workspace_id="ws", job_id="job"))


def test_a_converged_relaxation_is_collected(tmp_path: Path) -> None:
    energy = collect_pw(_record(tmp_path, "si_relax.out"))["total_energy"]
    assert cast(Any, energy).value == pytest.approx(-15.61554668 * RY_TO_EV)


def test_an_unconverged_relaxation_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="relaxation that did not converge"):
        collect_pw(_record(tmp_path, "si_relax_nstep.out"))


def test_an_unconverged_scf_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no converged total energy"):
        collect_pw(_record(tmp_path, "si_noconv.out"))
