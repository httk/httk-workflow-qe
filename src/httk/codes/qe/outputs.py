"""Parse the text output of Quantum ESPRESSO's ``pw.x``.

Pure stdlib parsing: nothing here runs a program or imports *httk* code, so a
result can be read anywhere the output file is.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

__all__ = ["RY_TO_EV", "PwResult", "parse_pw_output"]

#: One Rydberg in electronvolts (CODATA 2018), the unit ``pw.x`` prints energies in.
RY_TO_EV: float = 13.605693122994

# "!" ends a converged SCF cycle; "!!" ends a hybrid-functional outer loop and wins.
_ENERGY = re.compile(r"^(!!?)\s+total energy\s+=\s+(\S+)\s+Ry", re.MULTILINE)
# ponytail: BFGS only (relax/vc-relax default); add damped-dynamics wording when a campaign uses it.
_IONIC = re.compile(r"(bfgs converged)|(The maximum number of steps has been reached\.)")
_CONVERGENCE = re.compile(r"convergence (has been achieved in|NOT achieved after)\s+(\d+)\s+iterations")
_ERROR_BLOCK = re.compile(r"^\s*%{20,}\s*$\n(.*?)^\s*%{20,}\s*$", re.MULTILINE | re.DOTALL)
# pw.out says "Error in routine X (n):", the CRASH file "from X : error # n".
_ROUTINE = re.compile(r"Error in routine\s+(\S+)|from\s+(\S+)\s*:\s*error")


@dataclass(frozen=True)
class PwResult:
    """What one ``pw.x`` output says about its calculation.

    The parser reports what ``pw.x`` says: with ``scf_must_converge = .false.``
    ``pw.x`` itself declares a cycle converged, and so does this result.

    :param total_energy_ry: The last converged total energy in Ry (the last ``!!`` line of a hybrid
        functional, else the last ``!`` line), or ``None``, also when the last SCF did not converge.
    :param converged: Whether the last SCF cycle converged, or ``None`` when no cycle reported.
    :param scf_iterations: The iteration count of the last SCF cycle, or ``None``.
    :param ionic_converged: Whether the ionic (BFGS) relaxation converged, ``False`` when it stopped at
        ``nstep``, or ``None`` for a calculation without one (scf, nscf).
    :param job_done: Whether ``pw.x`` reached its normal ``JOB DONE.`` end.
    :param errors: The error messages of ``%%%%`` blocks in the output and the ``CRASH`` file.
    """

    total_energy_ry: float | None
    converged: bool | None
    scf_iterations: int | None
    ionic_converged: bool | None
    job_done: bool
    errors: tuple[str, ...]

    @property
    def total_energy_ev(self) -> float | None:
        """The last converged total energy in eV, or ``None``."""
        return None if self.total_energy_ry is None else self.total_energy_ry * RY_TO_EV


def parse_pw_output(path: str | os.PathLike[str]) -> PwResult:
    """Parse one ``pw.x`` output file, folding in a ``CRASH`` file beside it.

    :param path: Read the ``pw.x`` standard output saved at this path.
    :return: The parsed result.
    :raises FileNotFoundError: If the output file does not exist.
    """

    output = Path(path)
    return _parse(output.read_text(encoding="utf-8", errors="replace"), _read(output.parent / "CRASH"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _parse(text: str, crash: str) -> PwResult:
    energies = _ENERGY.findall(text)
    outer = [value for bangs, value in energies if bangs == "!!"]
    energy = outer[-1] if outer else energies[-1][1] if energies else None
    ionic = _IONIC.findall(text)
    cycles = _CONVERGENCE.findall(text)
    converged = cycles[-1][0].startswith("has") if cycles else None
    if converged is False:
        # An earlier ionic step's "!" line must not stand in for the failed last SCF.
        energy = None
    errors: list[str] = []
    for block in _ERROR_BLOCK.findall(text + "\n" + crash):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        routine = next((match.group(1) or match.group(2) for line in lines if (match := _ROUTINE.search(line))), None)
        # The message is the text after the routine header lines, usually one line.
        message = " ".join(line for line in lines if not _ROUTINE.search(line) and not line.startswith("task #"))
        entry = f"{routine}: {message}" if routine else message
        if entry and entry not in errors:
            errors.append(entry)
    return PwResult(
        total_energy_ry=None if energy is None else float(energy),
        converged=converged,
        scf_iterations=int(cycles[-1][1]) if cycles else None,
        ionic_converged=bool(ionic[-1][0]) if ionic else None,
        job_done="JOB DONE." in text,
        errors=tuple(errors),
    )
