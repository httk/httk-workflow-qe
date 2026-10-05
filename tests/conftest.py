"""Shared test configuration: isolate the httk configuration of every test."""

import os
import shlex
import shutil
from pathlib import Path

import pytest

# Keep each BLAS runtime of the many short-lived runner processes to one thread;
# child runners inherit this.
for _thread_limit in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_thread_limit] = "1"


@pytest.fixture(autouse=True)
def _isolated_httk_config(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give every test its own httk config and data home, so no workspace registry leaks between tests."""

    monkeypatch.setenv("HTTK_CONFIG_HOME", str(tmp_path_factory.mktemp("httk-config")))
    monkeypatch.setenv("HTTK_DATA_HOME", str(tmp_path_factory.mktemp("httk-store")))
    # A developer's launch prefix must not leak into the tests.
    monkeypatch.delenv("HTTK_WORKFLOW_LAUNCH", raising=False)


DATA = Path(__file__).resolve().parent / "data"
REPO_ROOT = Path(__file__).resolve().parent.parent

# Diamond silicon, the structure of the captured tests/data/si.in (celldm 10.26 bohr).
SILICON_POSCAR = """silicon
5.4293
0.0 0.5 0.5
0.5 0.0 0.5
0.5 0.5 0.0
Si
2
Direct
0.00 0.00 0.00
0.25 0.25 0.25
"""


def pw_command() -> list[str] | None:
    """The real ``pw.x`` command: ``HTTK_TEST_QE_COMMAND``, else ``pw.x`` on PATH, else ``None``."""

    command = os.environ.get("HTTK_TEST_QE_COMMAND") or shutil.which("pw.x")
    return shlex.split(command) if command else None


requires_pw = pytest.mark.skipif(
    pw_command() is None, reason="needs a real pw.x: set HTTK_TEST_QE_COMMAND or put pw.x on PATH"
)
