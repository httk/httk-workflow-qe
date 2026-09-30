"""Recognized-calculation collection of finished free-standing pw.x runs."""

import bz2
import lzma
import shutil
from pathlib import Path
from typing import Any, cast

import pytest
from httk.workflow import claims, collect_tree

from conftest import DATA
from httk.codes.qe import RY_TO_EV
from httk.codes.qe.collect import find_outputs
from httk.codes.qe.outputs import parse_pw_output

NAME = "qe.calculation.pw"
ENERGY = -15.61554668 * RY_TO_EV


def _run(directory: Path, *, source: str = "si", compress: bool = False) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for ext in ("out", "in"):
        data = (DATA / f"{source}.{ext}").read_bytes()
        if compress:
            (directory / f"si.{ext}.bz2").write_bytes(bz2.compress(data))
        else:
            (directory / f"si.{ext}").write_bytes(data)
    return directory


def test_a_converged_run_is_collected(tmp_path: Path) -> None:
    _run(tmp_path / "a")
    (job,) = list(collect_tree(tmp_path))
    assert (job.run.source_id or "").startswith(f"{NAME}:")
    (claim,) = [c for c in claims(tmp_path) if c.kind == "claimed"]
    assert job.run.source_id == f"{NAME}:{claim.identity}"
    assert cast(Any, job.outputs["total_energy"]).value == pytest.approx(ENERGY)


def test_an_unconverged_run_is_claimed_and_degraded(tmp_path: Path) -> None:
    _run(tmp_path / "a", source="si_noconv")
    assert [c.kind for c in claims(tmp_path)] == ["claimed"]
    (job,) = list(collect_tree(tmp_path))
    assert job.outputs.get("total_energy") is None


def test_a_scheduler_log_is_no_candidate(tmp_path: Path) -> None:
    (tmp_path / "slurm-1.out").write_text("starting job\n" * 5, encoding="utf-8")
    assert find_outputs(tmp_path) == ()
    assert list(claims(tmp_path)) == []
    assert list(collect_tree(tmp_path)) == []


def test_two_outputs_are_unclaimed(tmp_path: Path) -> None:
    _run(tmp_path / "a")
    shutil.copy(DATA / "si.out", tmp_path / "a" / "other.out")
    (only,) = claims(tmp_path)
    assert only.kind == "unclaimed"
    assert only.reason is not None and "several" in only.reason and "other.out" in only.reason


def test_a_missing_input_is_unclaimed(tmp_path: Path) -> None:
    _run(tmp_path / "a")
    (tmp_path / "a" / "si.in").unlink()
    (only,) = claims(tmp_path)
    assert only.kind == "unclaimed"
    assert only.reason == "no si.in beside si.out"


def test_compressed_files_are_collected(tmp_path: Path) -> None:
    directory = _run(tmp_path / "a", compress=True)
    packed = directory / "si.in.bz2"
    (directory / "si.in.lzma").write_bytes(lzma.compress(bz2.decompress(packed.read_bytes()), format=lzma.FORMAT_ALONE))
    packed.unlink()
    (job,) = list(collect_tree(tmp_path))
    assert cast(Any, job.outputs["total_energy"]).value == pytest.approx(ENERGY)


def test_a_dotted_stem_finds_its_input(tmp_path: Path) -> None:
    _run(tmp_path / "a")
    directory = tmp_path / "a"
    (directory / "si.out").rename(directory / "si.relax.out")
    (directory / "si.in").rename(directory / "si.relax.in")
    (only,) = claims(tmp_path)
    assert only.kind == "claimed"
    (directory / "si.relax.in").unlink()
    (only,) = claims(tmp_path)
    assert only.reason == "no si.relax.in beside si.relax.out"


def test_a_compressed_output_parses_like_the_plain_one(tmp_path: Path) -> None:
    packed = tmp_path / "si.out.bz2"
    packed.write_bytes(bz2.compress((DATA / "si.out").read_bytes()))
    assert parse_pw_output(packed) == parse_pw_output(DATA / "si.out")
