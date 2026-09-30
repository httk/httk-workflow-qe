# httk-workflow-qe

![Status: Early beta](https://img.shields.io/badge/status-early--beta-orange)

> **⚠️ EARLY BETA**
>
> This is an early beta release of *httk₂*. The organization of the packages
> and their APIs should not yet be regarded as stable, and may change between
> releases.

*httk-workflow-qe* adds Quantum ESPRESSO (`pw.x`) support to
[*httk-workflow*](https://github.com/httk/httk-workflow), the workflow engine of
[*httk₂*](https://github.com/httk/httk2). It provides `httk.codes.qe`: writing
`pw.x` inputs, parsing its output, stable diagnostics, supervised execution with
a classified run report, and helpers for reading workflow outputs; and the Bash
API that exposes the same helpers to Bash runners. Installing it registers the
`qe` code with *httk₂*; nothing needs to be configured.

## Install

```console
python -m pip install "httk-workflow-qe[atomistic]"
```

The `atomistic` extra (*httk-atomistic*) is needed only to write inputs from
structures.

## Use

In a Python runner:

```python
from httk.codes.qe import run_pw, write_pw_input

write_pw_input("pw.in", structure="POSCAR", pseudopotentials={"Si": "Si.upf"}, ecutwfc=25, kpoints=(4, 4, 4))
report = run_pw(["pw.x"])
print(report.classification, report.result.total_energy_ev)
```

In a Bash runner, whose manager exports the path of the QE API:

```bash
source "$HTTK_WORKFLOW_BASH_API"
: "${HTTK_WORKFLOW_QE_BASH_API:?install httk-workflow-qe}"
source "$HTTK_WORKFLOW_QE_BASH_API"
httk_qe_run -- pw.x
energy=$(httk_qe_energy --unit ev)
```

A complete example workflow package, `qe.scf`, is in
[`workflows/qe-scf`](workflows/qe-scf); `httk plugin install` of this
repository installs it. The API is documented in [`docs/usage.md`](docs/usage.md)
and at [docs.httk.org/httk-workflow-qe](https://docs.httk.org/httk-workflow-qe/).

## Running tests

`make test` runs the normal profile; `make ci` runs formatting, lint, both type
checkers and the extended tests. The end-to-end test runs the real `pw.x` only
when `HTTK_TEST_QE_COMMAND` names it or `pw.x` is on `PATH`, and skips otherwise.
