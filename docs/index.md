# *httk-workflow-qe*

This site documents the *httk-workflow-qe* module. For the full documentation
of *httk₂*, see [docs.httk.org](https://docs.httk.org).

The module adds Quantum ESPRESSO (`pw.x`) support to *httk-workflow*: the Python
helpers in `httk.codes.qe` (input writing, output parsing, diagnostics,
supervised execution and result-reading helpers), the Bash API a Bash runner
sources as `$HTTK_WORKFLOW_QE_BASH_API`, and the `qe-*` bridge commands behind
that API. Installing it registers the `qe` code with *httk₂* through the
`httk.registry.codes.qe` registration package. The repository also carries the
example workflow package `qe.scf`.

```{admonition} Quick links
:class: tip

- {doc}`usage` — the Python and Bash API, the example workflow, and the diagnostics
- {doc}`reference/index` — the generated API reference
```

## Install

```console
python -m pip install "httk-workflow-qe[atomistic]"
```

```{toctree}
:maxdepth: 2
:caption: Documentation

usage
reference/index
```
