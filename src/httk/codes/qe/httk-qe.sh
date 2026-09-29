#!/usr/bin/env bash

# Native httk Quantum ESPRESSO Bash API, version 1. Source httk-workflow.sh first.
#
# Every function is one qe-* bridge subcommand, and every option of that
# subcommand is available here: the arguments are passed through untouched.
#
#   httk_qe_write_input --options OPTIONS.json [--input pw.in]
#   httk_qe_run [--directory .] [--input pw.in] [--output pw.out] [--timeout S] -- pw.x ...
#       prints the report path; exits 0 completed, 20 crashed, 21 nonconverged,
#       22 process failure, 124 timeout
#   httk_qe_energy [--output pw.out] [--unit ry|ev]   exits 1 when there is no energy
#   httk_qe_converged [--output pw.out]               exits 1 when not converged
#   httk_qe_diagnose [--output pw.out] [--json]       exits 20 when it found anything
HTTK_QE_BASH_API_VERSION=1

_httk_qe_require_workflow_api() {
    if ! declare -F _httk_workflow_bridge >/dev/null 2>&1; then
        printf 'httk-workflow: source HTTK_WORKFLOW_BASH_API before HTTK_WORKFLOW_QE_BASH_API\n' >&2
        return 2
    fi
}

httk_qe_write_input() {
    _httk_qe_require_workflow_api || return
    _httk_workflow_bridge qe-write-input "$@"
}

httk_qe_run() {
    _httk_qe_require_workflow_api || return
    _httk_workflow_bridge qe-run "$@"
}

httk_qe_energy() {
    _httk_qe_require_workflow_api || return
    _httk_workflow_bridge qe-energy "$@"
}

httk_qe_converged() {
    _httk_qe_require_workflow_api || return
    _httk_workflow_bridge qe-converged "$@"
}

httk_qe_diagnose() {
    _httk_qe_require_workflow_api || return
    _httk_workflow_bridge qe-diagnose "$@"
}
