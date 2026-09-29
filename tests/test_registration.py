"""The ``qe`` code is registered through the ``codes`` registry tier, with its citation."""

import argparse
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import httk.core  # noqa: F401  (importing httk.core runs registry discovery)
from httk.core.register import code_support, known_codes


def test_qe_is_a_known_code_with_its_packaged_bash_api() -> None:
    assert "qe" in known_codes()
    assert code_support("qe").bash_api_path() == Path(str(files("httk.codes.qe").joinpath("httk-qe.sh")))


def test_the_bridge_mounts_the_qe_commands() -> None:
    parser = argparse.ArgumentParser()
    code_support("qe").resolve_bridge().add_commands(parser.add_subparsers(dest="command"))
    assert parser.parse_args(["qe-energy"]).command == "qe-energy"


def test_the_quantum_espresso_credit_is_registered_on_import() -> None:
    script = """
from httk.core import credits
assert "Calculations with Quantum ESPRESSO" not in credits.entries()
import httk.codes.qe
assert len(credits.entries()["Calculations with Quantum ESPRESSO"]) == 2
"""
    subprocess.run([sys.executable, "-c", script], check=True)
