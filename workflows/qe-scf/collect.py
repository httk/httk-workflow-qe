"""Collect hook for the ``qe.scf`` workflow.

The run leaves ``pw.out`` in the persistent workdir.
"""

from httk.codes.qe.collect import read_total_energy


def collect(record):
    """Return the converged total energy of the run.

    :param record: The collected job record.
    :return: The ``total_energy`` output role.
    """
    return {"total_energy": read_total_energy(record.result_file("pw.out"))}
