"""Supervised ``pw.x`` execution and its classified run report."""

import dataclasses
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from httk.workflow.codes import Diagnostic, ProcessReport, ProcessSupervisor, write_json_atomic

from .diagnostics import diagnose_pw
from .outputs import PwResult, _parse, _read

__all__ = ["PwRunReport", "run_pw"]


@dataclass(frozen=True)
class PwRunReport:
    """Classified result of one supervised ``pw.x`` execution.

    The classification is one of ``completed``, ``crashed`` (a ``qe.crash``
    diagnostic), ``nonconverged``, ``process_failure`` (a nonzero exit or an
    incomplete output) and ``timeout``.

    :param process: The supervised process result.
    :param classification: The final run classification.
    :param diagnostics: The diagnostics of the finished calculation.
    :param result: What the ``pw.x`` output says.
    """

    process: ProcessReport
    classification: str
    diagnostics: tuple[Diagnostic, ...]
    result: PwResult

    @property
    def ok(self) -> bool:
        """Whether the calculation completed cleanly and converged."""
        return self.classification == "completed"

    def as_mapping(self) -> dict[str, object]:
        """Serialize the report for JSON storage.

        :return: The JSON-compatible report mapping.
        """
        return {
            "format": "httk-qe-run-report",
            "format_version": 1,
            "process": self.process.as_mapping(),
            "classification": self.classification,
            "diagnostics": [item.as_mapping() for item in self.diagnostics],
            "result": {**dataclasses.asdict(self.result), "errors": list(self.result.errors)},
        }

    def write(self, path: str | os.PathLike[str]) -> Path:
        """Write the report as JSON.

        :param path: Write the report to this path.
        :return: The report path.
        """
        destination = Path(path)
        write_json_atomic(destination, self.as_mapping())
        return destination


def run_pw(
    argv: Sequence[str],
    *,
    directory: str | os.PathLike[str] = ".",
    input_file: str = "pw.in",
    output_file: str = "pw.out",
    timeout: float | None = None,
    termination_grace: float = 10.0,
    report_path: str | os.PathLike[str] = "qe-run-report.json",
) -> PwRunReport:
    """Run ``pw.x`` under supervision and write a classified report.

    *argv* is the command that starts ``pw.x``, including any launcher such as
    ``mpirun -np 4 pw.x``; ``-in INPUT_FILE`` is appended to it. Standard output
    goes to *output_file* and standard error beside it with the suffix ``.err``.
    A ``CRASH`` file left by an earlier run is removed first, so it cannot be
    mistaken for this run's.

    :param argv: The ``pw.x`` command argument vector, without the input option.
    :param directory: Run ``pw.x`` in this directory.
    :param input_file: The input file name in *directory*.
    :param output_file: Save standard output under this name in *directory*.
    :param timeout: Stop the process after this many seconds when set.
    :param termination_grace: Allow this many seconds for graceful termination.
    :param report_path: Write the report at this directory-relative path.
    :return: The classified run report.
    """

    root = Path(directory).resolve()
    (root / "CRASH").unlink(missing_ok=True)
    output = root / output_file
    # ponytail: no live monitor or remedy ladder; add them when a real campaign needs them.
    process = ProcessSupervisor().run(
        [*argv, "-in", input_file],
        timeout=timeout,
        cwd=root,
        termination_grace=termination_grace,
        stdout_path=output,
        stderr_path=output.with_suffix(".err"),
    )
    diagnostics = (*process.diagnostics, *diagnose_pw(root, output=output_file))
    codes = {item.code for item in diagnostics}
    if process.timed_out:
        classification = "timeout"
    elif "qe.crash" in codes:
        classification = "crashed"
    elif process.returncode or "qe.incomplete" in codes:
        classification = "process_failure"
    elif codes & {"qe.scf_not_converged", "qe.ionic_not_converged"}:
        classification = "nonconverged"
    elif any(item.severity in {"error", "fatal"} for item in diagnostics):
        classification = "process_failure"
    else:
        classification = "completed"
    report = PwRunReport(process, classification, diagnostics, _parse(_read(output), _read(root / "CRASH")))
    report.write(root / report_path)
    return report
