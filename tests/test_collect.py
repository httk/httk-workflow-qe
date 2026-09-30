"""``read_total_energy`` gates on a converged energy and relaxation; the hook reads ``pw.out``."""

import runpy
import shutil
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest
from httk.workflow.collecting import JobRecord

from conftest import DATA
from httk.codes.qe import RY_TO_EV
from httk.codes.qe.collect import read_total_energy

HOOK = Path(__file__).parents[1] / "workflows" / "qe-scf" / "collect.py"
JOB_ID = "12345678-1234-4234-8234-123456789abc"


def test_a_converged_relaxation_is_read() -> None:
    assert cast(Any, read_total_energy(DATA / "si_relax.out")).value == pytest.approx(-15.61554668 * RY_TO_EV)


def test_an_unconverged_relaxation_is_refused() -> None:
    with pytest.raises(ValueError, match="relaxation that did not converge"):
        read_total_energy(DATA / "si_relax_nstep.out")


def test_an_unconverged_scf_is_refused() -> None:
    with pytest.raises(ValueError, match="no converged total energy"):
        read_total_energy(DATA / "si_noconv.out")


def test_the_packaged_hook_reads_the_workdir_output(tmp_path: Path) -> None:
    (tmp_path / "run").mkdir()
    shutil.copy(DATA / "si_relax.out", tmp_path / "run" / "pw.out")
    record = JobRecord(
        workspace_root=tmp_path,
        workspace_id="ws",
        job_id=JOB_ID,
        job_key=f"job--{JOB_ID}",
        job={},
        runner_provenance=None,
        state="succeeded",
        failure=None,
        placement=PurePosixPath("jobs"),
        payload_path=PurePosixPath(f"jobs/job--{JOB_ID}"),
        workdir_path=PurePosixPath("run"),
        data_path=None,
        data_generation=None,
        provenance={},
        runner_steps=None,
        children={},
        declarations={},
    )
    outputs = runpy.run_path(str(HOOK))["collect"](record)
    assert set(outputs) == {"total_energy"}
    assert outputs["total_energy"].value == pytest.approx(-15.61554668 * RY_TO_EV)
