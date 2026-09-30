"""Quantum ESPRESSO (``pw.x``) support for *httk₂* workflows: the *httk-workflow-qe* package.

``inputs`` writes ``pw.x`` inputs, ``outputs`` parses its text output,
``diagnostics`` classifies a finished calculation, ``reports`` runs it under
supervision, and ``collect`` reads workflow outputs out of result files, for
workflow collect hooks. This package is a thin facade re-exporting their
surface. The example workflow package ``workflows/qe-scf`` in this
distribution's repository builds on it.
"""

from httk.core import register_citation

register_citation(
    applies_to="Calculations with Quantum ESPRESSO",
    references=(
        {
            "authors": ({"name": "Paolo Giannozzi"},),
            "note": "Giannozzi et al.; the DOI record lists every author",
            "title": "QUANTUM ESPRESSO: a modular and open-source software project for quantum simulations of materials",
            "journal": "Journal of Physics: Condensed Matter",
            "volume": "21",
            "pages": "395502",
            "year": "2009",
            "doi": "10.1088/0953-8984/21/39/395502",
            "bib_type": "article",
        },
        {
            "authors": ({"name": "Paolo Giannozzi"},),
            "note": "Giannozzi et al.; the DOI record lists every author",
            "title": "Advanced capabilities for materials modelling with Quantum ESPRESSO",
            "journal": "Journal of Physics: Condensed Matter",
            "volume": "29",
            "pages": "465901",
            "year": "2017",
            "doi": "10.1088/1361-648X/aa8f79",
            "bib_type": "article",
        },
    ),
)

from .diagnostics import diagnose_pw
from .inputs import write_pw_input
from .outputs import RY_TO_EV, PwResult, parse_pw_output
from .reports import PwRunReport, run_pw

__all__ = [
    "RY_TO_EV",
    "PwResult",
    "PwRunReport",
    "diagnose_pw",
    "parse_pw_output",
    "run_pw",
    "write_pw_input",
]
