"""Collect hook for the ``qe.scf`` workflow."""

from httk.codes.qe import collect_pw


def collect(record):
    """Extract the converged total energy from the job record.

    :param record: The collected job record.
    :return: The ``total_energy`` output role.
    """
    return collect_pw(record)
