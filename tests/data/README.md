# Test data

Captured Quantum ESPRESSO 7.5 `pw.x` runs (serial, `OMP_NUM_THREADS=1`) of
diamond silicon.

| File | What it is |
| --- | --- |
| `si.in`, `si.out` | converged SCF: `!    total energy = -15.61554645 Ry`, `convergence has been achieved in 6 iterations`, `JOB DONE.` |
| `si_noconv.in`, `si_noconv.out` | `electron_maxstep = 2`: `convergence NOT achieved after 2 iterations: stopping`, exit status 0 |
| `crash/si_crash.in`, `crash/si_crash.out`, `crash/CRASH` | `si.in` without its `&control` namelist; `pw.x` stops in `read_namelists` with `bad line in namelist &control` and exit status 1 |
| `si_relax.in`, `si_relax.out` | `relax` from a displaced atom (`nstep = 50`, input prefix `si_relax_50`): `bfgs converged in 4 scf cycles and 3 bfgs steps`, last `!` energy -15.61554668 Ry |
| `si_relax_nstep.in`, `si_relax_nstep.out` | the same with `nstep = 2` (input prefix `si_relax_2`): `The maximum number of steps has been reached.`, exit status 0 |
| `Si.upf` | the `Si.pz-vbc.UPF` norm-conserving pseudopotential |

`Si.upf` is downloaded unmodified from
<https://pseudopotentials.quantum-espresso.org/upf_files/Si.pz-vbc.UPF>. It is
part of the Quantum ESPRESSO distribution and is licensed under the GNU General
Public License, version 2 or later (GPL-2.0-or-later). The `pw.x` outputs are
program output of those runs.
