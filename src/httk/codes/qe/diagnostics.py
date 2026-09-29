"""Classify a finished ``pw.x`` calculation into stable diagnostics."""

import os
from pathlib import Path

from httk.workflow.codes import Diagnostic

from .outputs import _parse, _read

__all__ = ["diagnose_pw"]


def diagnose_pw(directory: str | os.PathLike[str] = ".", *, output: str = "pw.out") -> tuple[Diagnostic, ...]:
    """Diagnose a ``pw.x`` calculation from its output and ``CRASH`` file.

    The codes are stable: ``qe.crash`` (fatal; ``pw.x`` stopped with an error
    message), ``qe.scf_not_converged`` (error; the last SCF cycle did not
    converge), ``qe.ionic_not_converged`` (error; a relaxation stopped at
    ``nstep``), and ``qe.incomplete`` (error; no ``JOB DONE.`` and no error
    message, e.g. a killed process). A converged, completed run has none. A
    missing output file is diagnosed like an empty one.

    :param directory: Read the calculation files from this directory.
    :param output: The name of the saved ``pw.x`` standard output in *directory*.
    :return: The diagnostics, empty for a clean run.
    """

    path = Path(directory) / output
    crash = path.parent / "CRASH"
    result = _parse(_read(path), _read(crash))
    diagnostics: list[Diagnostic] = []
    if result.errors:
        source = "CRASH" if crash.is_file() else output
        diagnostics.append(Diagnostic("qe.crash", "fatal", result.errors[0], source, "\n".join(result.errors)))
    elif not result.job_done:
        diagnostics.append(Diagnostic("qe.incomplete", "error", f"{output} has no JOB DONE. line", output))
    if result.converged is False:
        diagnostics.append(
            Diagnostic(
                "qe.scf_not_converged",
                "error",
                f"SCF convergence NOT achieved after {result.scf_iterations} iterations",
                output,
            )
        )
    if result.ionic_converged is False:
        diagnostics.append(
            Diagnostic("qe.ionic_not_converged", "error", "the ionic relaxation reached nstep unconverged", output)
        )
    return tuple(diagnostics)
