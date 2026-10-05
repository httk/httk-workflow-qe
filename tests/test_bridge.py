"""The ``qe-*`` bridge commands and the Bash API that forwards to them.

Code verbs need no attempt, so they run straight through the shell bridge.
"""

import json
import os
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import pytest

from conftest import DATA, SILICON_POSCAR


def _bridge(cwd: Path, *arguments: str) -> "subprocess.CompletedProcess[str]":
    environment = {name: value for name, value in os.environ.items() if not name.startswith("HTTK_WORKFLOW_")}
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    return subprocess.run(
        [sys.executable, "-m", "httk.workflow._shell_bridge", *arguments],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_energy_and_convergence_answers_and_absences(tmp_path: Path) -> None:
    energy = _bridge(tmp_path, "qe-energy", "--output", str(DATA / "si.out"))
    assert (energy.returncode, energy.stdout) == (0, "-15.61554645\n")
    in_ev = _bridge(tmp_path, "qe-energy", "--output", str(DATA / "si.out"), "--unit", "ev")
    assert float(in_ev.stdout) == pytest.approx(-212.4603, abs=1e-3)
    assert _bridge(tmp_path, "qe-converged", "--output", str(DATA / "si.out")).returncode == 0
    for verb in ("qe-energy", "qe-converged"):
        absent = _bridge(tmp_path, verb, "--output", str(DATA / "si_noconv.out"))
        assert (absent.returncode, absent.stdout, absent.stderr) == (1, "", "")
    refused = _bridge(tmp_path, "qe-energy", "--output", str(tmp_path / "missing.out"))
    assert refused.returncode == 2


def test_diagnose_prints_codes_and_json(tmp_path: Path) -> None:
    clean = _bridge(tmp_path, "qe-diagnose", "--output", str(DATA / "si.out"))
    assert (clean.returncode, clean.stdout) == (0, "")
    crash = _bridge(tmp_path, "qe-diagnose", "--output", str(DATA / "crash" / "si_crash.out"), "--json")
    assert crash.returncode == 20
    assert [item["code"] for item in json.loads(crash.stdout)] == ["qe.crash"]


def test_write_input_then_run_with_a_replayed_pw_x(tmp_path: Path) -> None:
    pytest.importorskip("httk.atomistic")
    (tmp_path / "POSCAR").write_text(SILICON_POSCAR, encoding="utf-8")
    options = {"structure": "POSCAR", "pseudopotentials": {"Si": "Si.upf"}, "ecutwfc": 12, "kpoints": [2, 2, 2]}
    (tmp_path / "options.json").write_text(json.dumps(options), encoding="utf-8")
    assert _bridge(tmp_path, "qe-write-input", "--options", "options.json").returncode == 0
    assert "K_POINTS automatic\n 2 2 2 0 0 0" in (tmp_path / "pw.in").read_text(encoding="utf-8")

    replay = "import sys; sys.stdout.write(open(sys.argv[1]).read())"
    ran = _bridge(tmp_path, "qe-run", "--", sys.executable, "-c", replay, str(DATA / "si_noconv.out"))
    assert (ran.returncode, ran.stdout) == (21, "qe-run-report.json\n")
    report = json.loads((tmp_path / "qe-run-report.json").read_text(encoding="utf-8"))
    assert report["classification"] == "nonconverged"


def test_the_bash_api_forwards_to_the_bridge(tmp_path: Path) -> None:
    workflow_api = files("httk.workflow").joinpath("languages", "bash", "httk-workflow.sh")
    qe_api = files("httk.codes.qe").joinpath("httk-qe.sh")
    script = f'source "{workflow_api}"; source "{qe_api}"; httk_qe_energy --output "{DATA / "si.out"}" --unit ry'
    environment = {name: value for name, value in os.environ.items() if not name.startswith("HTTK_WORKFLOW_")}
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    environment["HTTK_WORKFLOW_PYTHON"] = sys.executable
    result = subprocess.run(
        ["bash", "-c", script], cwd=tmp_path, env=environment, text=True, capture_output=True, check=False
    )
    assert (result.returncode, result.stdout) == (0, "-15.61554645\n"), result.stderr
    unguarded = subprocess.run(
        ["bash", "-c", f'source "{qe_api}"; httk_qe_energy'], text=True, capture_output=True, check=False
    )
    assert unguarded.returncode == 2 and "source HTTK_WORKFLOW_BASH_API" in unguarded.stderr


def test_no_launch_runs_the_command_as_given(tmp_path: Path) -> None:
    # _bridge strips HTTK_WORKFLOW_*; call the bridge directly with a launch prefix set.
    environment = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).parents[1] / "src"),
        "HTTK_WORKFLOW_LAUNCH": "env A=b",
    }
    command = [sys.executable, "-m", "httk.workflow._shell_bridge", "qe-run"]
    program = ["--", sys.executable, "-c", "pass"]

    def run(*flags: str) -> "subprocess.CompletedProcess[str]":
        return subprocess.run(
            [*command, *flags, *program], cwd=tmp_path, env=environment, text=True, capture_output=True, check=False
        )

    assert run("--no-launch").returncode == 22
    report = json.loads((tmp_path / "qe-run-report.json").read_text(encoding="utf-8"))
    assert report["process"]["argv"][0] == sys.executable
    assert run().returncode == 22
    report = json.loads((tmp_path / "qe-run-report.json").read_text(encoding="utf-8"))
    assert report["process"]["argv"][:2] == ["env", "A=b"]
