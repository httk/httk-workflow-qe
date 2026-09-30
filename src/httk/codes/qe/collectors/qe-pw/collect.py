"""Collect hook of the ``qe.calculation.pw`` recognized-calculation collector."""

from pathlib import Path
from typing import cast

from httk.core import DataRecord
from httk.workflow.collecting import JobRecord

from httk.codes.qe.collect import find_outputs, read_total_energy


def collect(record: JobRecord) -> dict[str, DataRecord]:
    """Return the converged total energy of the run.

    :param record: The collected job record; its workdir is the calculation directory.
    :return: The ``total_energy`` output role.
    """
    (output,) = find_outputs(cast(Path, record.workdir))
    return {"total_energy": read_total_energy(output)}
