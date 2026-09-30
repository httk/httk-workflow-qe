# Using the Quantum ESPRESSO helpers

*httk-workflow-qe* ships the `pw.x` helpers that workflow runners are built on,
in two languages: the Python package {py:mod}`httk.codes.qe` and the Bash QE API,
whose `httk_qe_*` functions call the same code through the *httk-workflow* shell
bridge.

## Install

```console
python -m pip install "httk-workflow-qe[atomistic]"
```

The distribution depends on *httk-core* and *httk-workflow*. Installing it
registers the `qe` code through the `httk.registry.codes.qe` registration
package, which makes the `qe-*` bridge commands and the Bash API available to
every job the manager starts; nothing needs to be configured. Writing inputs
from structures needs *httk-atomistic*, the `atomistic` extra; parsing,
diagnostics, running and collecting do not.

## Python

```python
from httk.codes.qe import run_pw, write_pw_input

write_pw_input(
    "pw.in",
    structure="POSCAR",
    pseudopotentials={"Si": "Si.upf"},
    ecutwfc=25,
    kpoints=(4, 4, 4),
    extra={"electrons": {"conv_thr": 1e-8}},
)
report = run_pw(["mpirun", "-np", "4", "pw.x"], timeout=3600)
if report.ok:
    print(report.result.total_energy_ev)
else:
    print(report.classification, [item.code for item in report.diagnostics])
```

- {py:func}`~httk.codes.qe.write_pw_input` writes the `&control`, `&system` and
  `&electrons` namelists and the `ATOMIC_SPECIES`, `CELL_PARAMETERS angstrom`,
  `ATOMIC_POSITIONS crystal` and `K_POINTS automatic` cards from a POSCAR/CIF
  path or an *httk* structure. A POSCAR path is written as the numbers it
  contains; other structures as floats of their exact values. `extra` adds or
  overrides namelist variables.
- {py:func}`~httk.codes.qe.parse_pw_output` returns a
  {py:class}`~httk.codes.qe.PwResult`: the last converged total energy (Ry, and
  eV through `total_energy_ev`; a hybrid functional's last `!!` outer-loop
  energy when present), SCF convergence and iteration count, BFGS ionic
  convergence (`None` without a relaxation), whether
  `JOB DONE.` was reached, and the error messages of `%%%%` blocks and of a
  `CRASH` file beside the output.
- {py:func}`~httk.codes.qe.run_pw` runs the command with `-in pw.in` under the
  *httk-workflow* process supervisor, saves standard output as `pw.out`, and
  returns a {py:class}`~httk.codes.qe.PwRunReport` classified as `completed`,
  `crashed`, `nonconverged`, `process_failure` or `timeout`, also written to
  `qe-run-report.json`.
- {py:func}`~httk.codes.qe.diagnose_pw` diagnoses a finished calculation.

## Diagnostics

| Code | Severity | Meaning |
| --- | --- | --- |
| `qe.crash` | fatal | `pw.x` stopped with an error message (`%%%%` block or `CRASH` file); the summary is the message |
| `qe.scf_not_converged` | error | the last SCF cycle reported `convergence NOT achieved` |
| `qe.ionic_not_converged` | error | a relaxation stopped at `nstep` (`The maximum number of steps has been reached.`) |
| `qe.incomplete` | error | no `JOB DONE.` and no error message, e.g. a killed process |

A converged, completed calculation has no diagnostics. The parser reports what
`pw.x` says: with `scf_must_converge = .false.` `pw.x` itself calls a cycle
converged, and so does the result.

## Bash

The manager exports the path of the QE API as `HTTK_WORKFLOW_QE_BASH_API` when
*httk-workflow-qe* is installed, so a Bash runner guards it and sources it after
the generic library:

```bash
source "$HTTK_WORKFLOW_BASH_API"
: "${HTTK_WORKFLOW_QE_BASH_API:?install httk-workflow-qe}"
source "$HTTK_WORKFLOW_QE_BASH_API"

httk_qe_write_input --options options.json   # the write_pw_input keywords as JSON
httk_qe_run --timeout 3600 -- mpirun -np 4 pw.x
energy=$(httk_qe_energy --unit ev)
```

| Function | Bridge command | Exit status |
| --- | --- | --- |
| `httk_qe_write_input --options FILE [--input pw.in]` | `qe-write-input` | `0` |
| `httk_qe_run [--directory] [--input] [--output] [--timeout] -- CMD...` | `qe-run` | `0` completed, `20` crashed, `21` nonconverged, `22` process failure, `124` timeout (as `vasp-run`); prints the report path |
| `httk_qe_energy [--output pw.out] [--unit ry\|ev]` | `qe-energy` | `0` and the energy, `1` when there is none |
| `httk_qe_converged [--output pw.out]` | `qe-converged` | `0` SCF converged and no unconverged relaxation, `1` otherwise |
| `httk_qe_diagnose [--output pw.out] [--json]` | `qe-diagnose` | `0` clean, `20` when it printed diagnostics |

A refused call (for example a missing output file) exits `2`.

## The example workflow

The repository's `workflows/qe-scf` is the workflow package `qe.scf`: one
Python runner step that stages the `structure` input and the pseudopotentials,
writes `pw.in`, runs `pw.x`, and fails with the first diagnostic code when the
calculation is not clean (`qe.input_invalid` when `pw.in` cannot be written
from the job's inputs). Install it with `httk plugin install` of the
repository, or use it directly with `--workflow-dir`:

```console
httk workspace settings set --key qe.command --value 'mpirun -np 4 pw.x' WORKSPACE
httk job new --workflow qe.scf --input structure=POSCAR --file Si.upf=Si.upf \
    --parameter 'pseudopotentials={"Si": "Si.upf"}'
httk workflow run
httk collect --into results.sqlite
```

Its parameters are `pseudopotentials` (species name to file name), `ecutwfc`
(Ry, default 25) and `kpoints` (default `[4, 4, 4]`); the settings `qe.command`
(default `pw.x`) and `qe.pseudo_dir` (default: the job's `files/`) say how to
run `pw.x` and where the pseudopotential files are.

## Collecting

{py:func}`~httk.codes.qe.collect.read_total_energy` reads the converged total
energy of a `pw.out` as a {py:class}`httk.core.DataRecord` of the property
`https://schemas.httk.org/defs/v0.1/properties/core/total_energy` in eV. It refuses a job whose last SCF did not converge (the parsed energy is
then `None`) and a relaxation that stopped unconverged.

The `qe.scf` hook shows how a workflow's `collect.py` locates the file with
`record.result_file` and returns the role mapping:

```python
from httk.codes.qe.collect import read_total_energy


def collect(record):
    return {"total_energy": read_total_energy(record.result_file("pw.out"))}
```

### Recognized calculations

The `qe.calculation.pw` collector lets `httk.workflow.collect_tree(root)` (and
`httk collect DIR --into db.sqlite`) collect finished, free-standing `pw.x`
runs without a workspace. A directory is recognized when it holds exactly one
`*.out` whose first 100 lines carry the `Program PWSCF` banner, found by
{py:func}`~httk.codes.qe.collect.find_outputs`, and the input `<stem>.in` beside
it (compressed or not). A `slurm-*.out` log is ignored. Several `pw.x` outputs
in one directory, or a missing input, are reported as unclaimed; an unconverged
run is claimed and then reported as a degraded item. The claim is identified by
the content of the input file, so moving the directory keeps its identity. The
collected role is `total_energy`.
