"""Building blocks for the collect hooks of QE workflows."""

from pathlib import Path

from httk.core import DataRecord

from .outputs import parse_pw_output

__all__ = ["read_total_energy"]

_TOTAL_ENERGY_DEFINITION = "https://schemas.httk.org/defs/v0.1/properties/core/total_energy"
_TOTAL_ENERGY_NAME = "_httk_total_energy"


def read_total_energy(path: Path) -> DataRecord:
    """Read the converged total energy, in eV, of one pw.x output file.

    :param path: The pw.x output file.
    :return: The ``total_energy`` property as a data record.
    :raises ValueError: If the file holds no converged total energy or is an unconverged relaxation.
    """

    result = parse_pw_output(path)
    energy = result.total_energy_ev
    if energy is None:
        raise ValueError(f"{path} holds no converged total energy")
    if result.ionic_converged is False:
        raise ValueError(f"{path} is a relaxation that did not converge")
    return DataRecord.from_value(_TOTAL_ENERGY_DEFINITION, _TOTAL_ENERGY_NAME, energy)
