"""The ``qe.scf`` runner refuses invalid inputs by name, without running pw.x."""

from pathlib import Path

import pytest

from conftest import DATA, REPO_ROOT, SILICON_POSCAR


def test_an_invalid_input_fails_the_job_as_qe_input_invalid(tmp_path: Path) -> None:
    pytest.importorskip("httk.atomistic")
    from httk.workflow import TaskManager, Workspace
    from httk.workflow.scaffold import new_job

    workspace = Workspace.initialize(tmp_path / "workspace")
    workspace.set_setting("qe.command", "false")  # never reached
    (tmp_path / "POSCAR").write_text(SILICON_POSCAR, encoding="utf-8")
    job = new_job(
        workspace,
        REPO_ROOT / "workflows" / "qe-scf",
        inputs={"structure": tmp_path / "POSCAR"},
        files={"Si.upf": DATA / "Si.upf"},
        # The file exists, but the mapping names no pseudopotential for Si.
        parameters={"pseudopotentials": {"Ge": "Si.upf"}},
    )
    with TaskManager(workspace, heartbeat_interval=0.01) as manager:
        manager.run_until_idle(timeout=120.0)
    marker = workspace.find_marker_by_id(job.job_id)
    assert marker is not None and marker.kind == "failed"
    failure = workspace.read_state(marker)["failure"]
    assert failure["code"] == "qe.input_invalid"
    assert "no pseudopotential given for species Si" in failure["message"]
