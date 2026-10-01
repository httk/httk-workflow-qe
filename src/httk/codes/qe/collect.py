"""Building blocks for the collect hooks of QE workflows."""

from pathlib import Path

from httk.core import DataRecord
from httk.core.datastream.compression import open_compressed, split_compression_suffix

from .outputs import parse_pw_output

__all__ = ["find_outputs", "read_total_energy"]

_TOTAL_ENERGY_DEFINITION = "https://schemas.httk.org/defs/v0.1/properties/core/total_energy"
_TOTAL_ENERGY_NAME = "_httk_total_energy"
_EXTENSIONS = (".out",)
_BANNER = b"Program PWSCF"
_HEAD_LINES = 100


def _has_banner(path: Path) -> bool:
    try:
        with path.open("rb") as raw, open_compressed(raw, compression="extension", name=path.name) as stream:
            for _, line in zip(range(_HEAD_LINES), stream, strict=False):
                if _BANNER in line:
                    return True
    except (OSError, EOFError, ValueError):
        pass
    return False


def find_outputs(directory: Path) -> tuple[Path, ...]:
    """Find the pw.x output files of a directory by their start-of-file banner.

    Only the first 100 lines of each candidate are read, so unrelated files
    such as scheduler logs are rejected cheaply. Compressed files are found too.

    :param directory: The directory to search.
    :return: The output files, sorted by name.
    """

    found = []
    for path in sorted(Path(directory).iterdir()):
        stem, _ = split_compression_suffix(path.name)
        if stem.lower().endswith(_EXTENSIONS) and path.is_file() and _has_banner(path):
            found.append(path)
    return tuple(found)


def read_total_energy(path: Path) -> DataRecord:
    """Read the converged total energy, in eV, of one pw.x output file.

    :param path: The pw.x output file.
    :return: The ``total_energy`` property as a data record.
    :raises ValueError: If the file is incomplete, holds no converged total energy, or is an
        unconverged relaxation.
    """

    result = parse_pw_output(path)
    if not result.job_done:
        raise ValueError(f"{path} is not completed: missing the JOB DONE. footer")
    energy = result.total_energy_ev
    if energy is None:
        raise ValueError(f"{path} holds no converged total energy")
    if result.ionic_converged is False:
        raise ValueError(f"{path} is a relaxation that did not converge")
    return DataRecord.from_value(_TOTAL_ENERGY_DEFINITION, _TOTAL_ENERGY_NAME, energy)
