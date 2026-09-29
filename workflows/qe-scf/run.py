#!/usr/bin/env python3
"""qe.scf: one pw.x SCF calculation of one structure.

The single ``run`` step stages the structure (the ``structure`` input, staged
as ``files/POSCAR``) and the pseudopotentials named by the ``pseudopotentials``
parameter, writes ``pw.in``, runs ``pw.x`` under supervision, and fails with
the first diagnostic code (``qe.crash``, ``qe.scf_not_converged``, ...) when
the calculation is not clean; inputs ``pw.in`` cannot be written from fail
as ``qe.input_invalid``.

Settings, resolved job parameter -> ``HTTK_*`` variable -> workspace setting:

* ``qe.command``: the command that starts pw.x (default ``pw.x``), e.g.
  ``mpirun -np 4 pw.x``;
* ``qe.pseudo_dir``: the directory holding the pseudopotential files (default:
  this job's ``files/``).
"""

import shlex
import shutil
from pathlib import Path
from typing import cast

from httk.workflow import Attempt, Runner

from httk.codes.qe import run_pw, write_pw_input

run = Runner("qe.scf")


@run.step(name="run")
def run_step(a: Attempt) -> None:
    """Prepare and run pw.x, then succeed or fail with what was diagnosed."""

    pseudopotentials = a.parameter("pseudopotentials", None)
    if not isinstance(pseudopotentials, dict) or not pseudopotentials:
        a.fail("qe.input_missing", 'give the job a pseudopotentials parameter, e.g. {"Si": "Si.upf"}')
        return
    pseudo_dir = Path(str(a.setting("qe.pseudo_dir", None) or a.payload / "files"))
    for name in pseudopotentials.values():
        if not (pseudo_dir / name).is_file():
            a.fail("qe.input_missing", f"pseudopotential {name} is not in {pseudo_dir}")
            return
        shutil.copyfile(pseudo_dir / name, a.workdir / name)
    shutil.copyfile(a.payload / "files" / "POSCAR", a.workdir / "POSCAR")
    try:
        nx, ny, nz = (int(n) for n in cast(list[int], a.parameter("kpoints", [4, 4, 4])))
        write_pw_input(
            a.workdir / "pw.in",
            structure=a.workdir / "POSCAR",
            pseudopotentials=pseudopotentials,
            ecutwfc=float(cast(float, a.parameter("ecutwfc", 25))),
            kpoints=(nx, ny, nz),
        )
    except ValueError as exception:
        a.fail("qe.input_invalid", str(exception))
        return
    try:
        report = run_pw(shlex.split(str(a.setting("qe.command", "pw.x"))), directory=a.workdir)
    except OSError as exception:
        a.fail("qe.failed", f"could not start pw.x: {exception}")
        return
    if not report.ok:
        first = report.diagnostics[0] if report.diagnostics else None
        code = first.code if first else f"qe.{report.classification}"
        a.fail(code, first.summary if first else f"pw.x {report.classification}")
        return
    a.state.merge({"total_energy_ry": report.result.total_energy_ry})
    a.succeed()


if __name__ == "__main__":
    raise SystemExit(run.main())
