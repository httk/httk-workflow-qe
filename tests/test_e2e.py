"""End to end with the real ``pw.x``: install, run, and collect the ``qe.scf`` workflow.

Runs only with a real ``pw.x`` (``HTTK_TEST_QE_COMMAND`` or ``pw.x`` on PATH).
The workflow is installed as the ``httk_plugin.toml`` plugin of this repository,
as ``httk plugin install`` does, into the test's isolated data home.
"""

import json
import shlex
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from conftest import DATA, REPO_ROOT, SILICON_POSCAR, pw_command, requires_pw

pytestmark = [requires_pw, pytest.mark.slow]


@pytest.fixture
def installed_plugin(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    from httk.core.plugins import install_plugin
    from httk.workflow.packages import _reset_plugin_workflow_cache

    source = tmp_path_factory.mktemp("plugin-source") / "httk-workflow-qe"
    shutil.copytree(REPO_ROOT / "workflows", source / "workflows", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(REPO_ROOT / "httk_plugin.toml", source)
    install_plugin(source)
    _reset_plugin_workflow_cache()
    yield
    _reset_plugin_workflow_cache()


def test_qe_scf_runs_pw_x_and_collects_the_total_energy(
    tmp_path: Path, installed_plugin: None, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("httk.atomistic")
    store = pytest.importorskip("httk.store")
    from httk.core import DataRecord, Run
    from httk.core.cli import CLIContext
    from httk.workflow import TaskManager, Workspace
    from httk.workflow.registry import register_workspace
    from httk.workflow.scaffold import new_job
    from httk.workflow.workflow_cli import command

    workspace = Workspace.initialize(tmp_path / "workspace")
    workspace.set_setting("qe.command", shlex.join(pw_command() or ()))
    (tmp_path / "POSCAR").write_text(SILICON_POSCAR, encoding="utf-8")
    job = new_job(
        workspace,
        "qe.scf",
        inputs={"structure": tmp_path / "POSCAR"},
        files={"Si.upf": DATA / "Si.upf"},
        parameters={"pseudopotentials": {"Si": "Si.upf"}, "ecutwfc": 12, "kpoints": [2, 2, 2]},
    )
    with TaskManager(workspace, heartbeat_interval=0.01) as manager:
        manager.run_until_idle(timeout=600.0)
    marker = workspace.find_marker_by_id(job.job_id)
    assert marker is not None
    assert marker.kind == "succeeded", workspace.read_state(marker).get("failure")

    register_workspace("qe", str(workspace.root))
    database = tmp_path / "results.sqlite"
    arguments = ["collect", "--workspace", "qe", "--into", str(database), "--id-base", "httk.test", "--no-id-ledger"]
    assert command(arguments, CLIContext("httk", tmp_path)) == 0
    report = json.loads(capsys.readouterr().out.splitlines()[0])
    assert set(report["outputs"]) == {"total_energy"} and report["stored"]["run"]

    with store.Backend.sqlite(database) as backend:
        searcher = store.SqlStore(backend).searcher()
        energies: list[Any] = [row.energy for row in searcher.results(energy=searcher.variable(DataRecord))]
        searcher = store.SqlStore(backend).searcher()
        runs = list(searcher.results(run=searcher.variable(Run)))
    assert [energy.value for energy in energies] == [pytest.approx(-212.46, abs=0.05)]
    assert len(runs) == 1
