"""Extract workflow outputs from a collected ``pw.x`` job."""

from httk.core import DataRecord
from httk.workflow.collecting import JobRecord

from .outputs import parse_pw_output

__all__ = ["collect_pw"]

_TOTAL_ENERGY_DEFINITION = "https://schemas.httk.org/defs/v0.1/properties/core/total_energy"
_TOTAL_ENERGY_NAME = "_httk_total_energy"


def collect_pw(record: JobRecord, *, output: str = "pw.out") -> dict[str, object]:
    """Extract the converged total energy, in eV, of one ``pw.x`` job.

    The output is read from the job's published data when it has any, else
    from its persistent workdir.

    :param record: The collected job record.
    :param output: The ``pw.x`` output file name.
    :return: The ``total_energy`` output role.
    :raises ValueError: If the output is missing, holds no converged total energy,
        or is an unconverged relaxation.
    """

    root = record.data if record.data is not None else record.workdir
    identity = f"{record.workspace_id}:{record.job_id}"
    if root is None or not (root / output).is_file():
        raise ValueError(f"{identity}: expected the pw.x output {output!r}, but the job has none")
    result = parse_pw_output(root / output)
    energy = result.total_energy_ev
    if energy is None:
        raise ValueError(f"{identity}: {root / output} holds no converged total energy")
    if result.ionic_converged is False:
        raise ValueError(f"{identity}: {root / output} is a relaxation that did not converge")
    return {"total_energy": DataRecord.from_value(_TOTAL_ENERGY_DEFINITION, _TOTAL_ENERGY_NAME, energy)}
