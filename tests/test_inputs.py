"""``write_pw_input`` writes an input the real ``pw.x`` accepts."""

import logging
import os
import re
import subprocess
from pathlib import Path

import pytest

from conftest import DATA, SILICON_POSCAR, pw_command, requires_pw
from httk.codes.qe import parse_pw_output, write_pw_input

pytest.importorskip("httk.atomistic")


def _write(tmp_path: Path, **extra: object) -> str:
    (tmp_path / "POSCAR").write_text(SILICON_POSCAR, encoding="utf-8")
    options: dict[str, object] = {
        "structure": tmp_path / "POSCAR",
        "pseudopotentials": {"Si": "Si.upf"},
        "ecutwfc": 12.0,
        "kpoints": (2, 2, 2),
    }
    write_pw_input(tmp_path / "pw.in", **(options | extra))  # type: ignore[arg-type]
    return (tmp_path / "pw.in").read_text(encoding="utf-8")


def test_the_input_has_the_namelists_and_cards(tmp_path: Path) -> None:
    text = _write(tmp_path, extra={"electrons": {"conv_thr": 1e-8}, "system": {"nosym": True}})
    for line in ("&control", "&system", "&electrons", "   calculation = 'scf'", "   nat = 2", "   ntyp = 1"):
        assert line in text.splitlines()
    assert "   ecutwfc = 12.0" in text and "   conv_thr = 1e-08" in text and "   nosym = .true." in text
    assert re.search(r"^ATOMIC_SPECIES\n Si 1\.0 Si\.upf$", text, re.MULTILINE)
    # The POSCAR's own numbers, scaled by its 5.4293 scale factor.
    assert "CELL_PARAMETERS angstrom\n 0.0 2.71465 2.71465\n 2.71465 0.0 2.71465\n 2.71465 2.71465 0.0\n" in text
    assert "ATOMIC_POSITIONS crystal\n Si 0.0 0.0 0.0\n Si 0.25 0.25 0.25\n" in text
    assert text.endswith("K_POINTS automatic\n 2 2 2 0 0 0\n")


_HEXAGONAL = """GaN
1.0
3.84 0.0 0.0
-1.92 3.325538 0.0
0.0 0.0 6.0
Ga N
2 2
Direct
0.333333 0.666667 0.0
0.666667 0.333333 0.5
0.333333 0.666667 0.375
0.666667 0.333333 0.875
"""


def test_a_poscar_is_written_as_the_floats_it_contains(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    (tmp_path / "gan.poscar").write_text(_HEXAGONAL, encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        write_pw_input(
            tmp_path / "pw.in",
            structure=tmp_path / "gan.poscar",
            pseudopotentials={"Ga": "Ga.upf", "N": "N.upf"},
            ecutwfc=30,
            kpoints=(4, 4, 2),
        )
    assert caplog.records == []
    text = (tmp_path / "pw.in").read_text(encoding="utf-8")
    assert "CELL_PARAMETERS angstrom\n 3.84 0.0 0.0\n -1.92 3.325538 0.0\n 0.0 0.0 6.0\n" in text
    assert " Ga 0.333333 0.666667 0.0\n Ga 0.666667 0.333333 0.5\n N 0.333333 0.666667 0.375\n" in text
    assert "   ntyp = 2" in text and "   nat = 4" in text


def test_invalid_options_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no pseudopotential given for species Si"):
        _write(tmp_path, pseudopotentials={"Ge": "Ge.upf"})
    with pytest.raises(ValueError, match="kpoints"):
        _write(tmp_path, kpoints=(2, 0, 2))
    with pytest.raises(ValueError, match="ecutwfc"):
        _write(tmp_path, ecutwfc=0)


@requires_pw
def test_the_real_pw_x_accepts_the_input(tmp_path: Path) -> None:
    command = pw_command()
    assert command is not None
    _write(tmp_path)
    (tmp_path / "Si.upf").symlink_to(DATA / "Si.upf")
    with (tmp_path / "pw.out").open("wb") as output:
        subprocess.run(
            [*command, "-in", "pw.in"],
            cwd=tmp_path,
            stdout=output,
            stderr=subprocess.DEVNULL,
            env=os.environ | {"OMP_NUM_THREADS": "1"},
            check=True,
            timeout=300,
        )
    result = parse_pw_output(tmp_path / "pw.out")
    assert result.converged and result.job_done
    assert result.total_energy_ry == pytest.approx(-15.6155, abs=1e-3)
