"""Write ``pw.x`` input files from *httk* structures."""

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

__all__ = ["write_pw_input"]

# Names the httk.core.load dispatcher routes to the POSCAR reader (case-insensitive).
_POSCAR_NAMES = frozenset({"poscar", "contcar"})
_POSCAR_SUFFIXES = frozenset({".poscar", ".vasp"})

type _Geometry = tuple[list[str], list[float | None], list[list[float]], str, list[str], list[list[float]]]


def write_pw_input(
    path: str | os.PathLike[str],
    *,
    structure: object,
    pseudopotentials: Mapping[str, str],
    ecutwfc: float,
    kpoints: tuple[int, int, int],
    calculation: str = "scf",
    pseudo_dir: str = ".",
    prefix: str = "pwscf",
    extra: Mapping[str, Mapping[str, object]] | None = None,
) -> Path:
    """Write a ``pw.x`` input for one periodic structure.

    The input has the ``&control``, ``&system`` and ``&electrons`` namelists
    and the ``ATOMIC_SPECIES``, ``CELL_PARAMETERS angstrom``,
    ``ATOMIC_POSITIONS`` and ``K_POINTS automatic`` cards. A ``pw.x`` input is
    inherently floating point. A POSCAR path (``POSCAR``, ``CONTCAR``,
    ``*.poscar``, ``*.vasp``) is copied as the floats it contains, Direct
    coordinates as ``crystal`` and Cartesian ones as ``angstrom``; any other
    structure is written as floats of its exact values. This needs
    *httk-atomistic* (the ``atomistic`` extra).

    :param path: Write the input file to this path.
    :param structure: The structure: a POSCAR/CIF path or anything
        ``httk.atomistic.UnitcellStructureView`` accepts.
    :param pseudopotentials: Map every species name of the structure to its pseudopotential file name.
    :param ecutwfc: The wavefunction kinetic-energy cutoff in Ry.
    :param kpoints: The unshifted Monkhorst-Pack grid.
    :param calculation: The ``pw.x`` calculation type.
    :param pseudo_dir: The directory ``pw.x`` reads the pseudopotential files from.
    :param prefix: The ``pw.x`` file prefix.
    :param extra: Additional namelist variables, as ``{namelist: {name: value}}``; they
        override the generated ones, and a new namelist (e.g. ``ions``) is appended.
    :return: The written path.
    :raises ValueError: If the cutoff or grid is not positive, a species has no
        pseudopotential, or the structure cannot be read.
    """

    if not ecutwfc > 0:
        raise ValueError(f"ecutwfc must be positive, not {ecutwfc!r}")
    if len(kpoints) != 3 or any(not isinstance(n, int) or isinstance(n, bool) or n < 1 for n in kpoints):
        raise ValueError(f"kpoints must be three positive integers, not {kpoints!r}")
    if isinstance(structure, str | os.PathLike) and _is_poscar(Path(structure)):
        species, masses, cell, units, site_species, positions = _poscar_geometry(Path(structure))
    else:
        species, masses, cell, units, site_species, positions = _structure_geometry(structure)
    missing = [name for name in species if name not in pseudopotentials]
    if missing:
        raise ValueError(f"no pseudopotential given for species {', '.join(missing)}")
    namelists: dict[str, dict[str, object]] = {
        "control": {"calculation": calculation, "prefix": prefix, "pseudo_dir": pseudo_dir},
        "system": {"ibrav": 0, "nat": len(site_species), "ntyp": len(species), "ecutwfc": float(ecutwfc)},
        "electrons": {},
    }
    for name, values in (extra or {}).items():
        namelists.setdefault(name.lower(), {}).update(values)
    lines: list[str] = []
    for name, values in namelists.items():
        lines += [f"&{name}", *(f"   {key} = {_fortran(value)}" for key, value in values.items()), "/"]
    lines.append("ATOMIC_SPECIES")
    for name, mass in zip(species, masses, strict=True):
        # ponytail: pw.x needs a mass but scf/nscf never use it; 1.0 when the structure
        # carries none. Add a mass table when md/relax workflows need real masses.
        lines.append(f" {name} {1.0 if mass is None else mass!r} {pseudopotentials[name]}")
    lines += ["CELL_PARAMETERS angstrom", *(" " + " ".join(repr(x) for x in row) for row in cell)]
    lines.append(f"ATOMIC_POSITIONS {units}")
    for name, row in zip(site_species, positions, strict=True):
        lines.append(f" {name} " + " ".join(repr(x) for x in row))
    lines += ["K_POINTS automatic", " {} {} {} 0 0 0".format(*kpoints), ""]
    destination = Path(path)
    destination.write_text("\n".join(lines), encoding="utf-8")
    return destination


def _is_poscar(path: Path) -> bool:
    return path.name.lower() in _POSCAR_NAMES or path.suffix.lower() in _POSCAR_SUFFIXES


def _poscar_geometry(path: Path) -> _Geometry:
    """The POSCAR's own numbers, from the string-preserving reader mapping."""

    from httk.atomistic.integrations.vasp.io import read_poscar  # pyright: ignore[reportMissingImports]

    # The precision only sets a symmetry tolerance of the structure the reader's
    # caller would build; none is built here, and passing one avoids its warning.
    data = read_poscar(path, precision=1e-5)
    if not data.get("symbols"):
        raise ValueError(f"{path}: a VASP-4 POSCAR without a species line cannot name its species")
    cell = [[float(token) for token in row] for row in data["cell"]]
    if data.get("scale") is not None:
        scale = float(data["scale"])
    else:
        a, b, c = cell
        determinant = abs(
            a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])
        )
        scale = (float(data["volume"]) / determinant) ** (1 / 3)
    if scale != 1.0:
        cell = [[scale * x for x in row] for row in cell]
    coordinates = [[float(token) for token in row] for row in data["coords"]]
    if data["cartesian"] and scale != 1.0:
        coordinates = [[scale * x for x in row] for row in coordinates]
    symbols: Sequence[str] = data["symbols"]
    # The same species names httk.core.load gives a POSCAR: a symbol that recurs
    # in several groups is numbered per group (Si1, Si2).
    names = [
        symbol if symbols.count(symbol) == 1 else f"{symbol}{symbols[: i + 1].count(symbol)}"
        for i, symbol in enumerate(symbols)
    ]
    site_species = [name for name, count in zip(names, data["counts"], strict=True) for _ in range(count)]
    return names, [None] * len(names), cell, "angstrom" if data["cartesian"] else "crystal", site_species, coordinates


def _structure_geometry(structure: object) -> _Geometry:
    from httk.atomistic import UnitcellStructureView  # pyright: ignore[reportMissingImports]

    view = UnitcellStructureView(cast(Any, Path(structure) if isinstance(structure, str | os.PathLike) else structure))
    return (
        [item.name for item in view.species],
        [item.mass[0] if item.mass else None for item in view.species],
        [[float(x) for x in row] for row in view.lattice_vectors],
        "crystal",
        list(view.species_at_sites),
        [[float(x) for x in row] for row in view.fractional_site_positions],
    )


def _fortran(value: object) -> str:
    if isinstance(value, bool):
        return ".true." if value else ".false."
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise ValueError(f"cannot write {value!r} as a Fortran namelist value")
