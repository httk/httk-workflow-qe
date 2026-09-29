"""The ``qe-*`` subcommands of the private native Bash command bridge.

``httk.workflow._shell_bridge`` mounts these beside its own subcommands through
the ``codes`` registry tier, so each function of ``httk-qe.sh`` is one
invocation of one command here. A legitimately absent answer returns the
bridge's uniform exit code ``1``; a refused call raises, which the bridge
reports as ``2``. ``qe-run`` has its own outcome codes, the same as
``vasp-run``: ``0`` completed, ``20`` crashed, ``21`` nonconverged, ``22``
process failure, ``124`` timeout; ``qe-diagnose`` exits ``20`` when it
found anything, like ``vasp-diagnose``.
"""

import argparse
import json
from pathlib import Path

from httk.workflow.codes import BRIDGE_ABSENT, read_json

from .diagnostics import diagnose_pw
from .inputs import write_pw_input
from .outputs import parse_pw_output
from .reports import run_pw

_RUN_EXIT = {"completed": 0, "crashed": 20, "nonconverged": 21, "process_failure": 22, "timeout": 124}


def add_commands(commands: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register the ``qe-*`` subcommands on the bridge's subparsers.

    :param commands: the bridge's subcommand collection.
    """

    run = commands.add_parser("qe-run")
    run.add_argument("--directory", default=".")
    run.add_argument("--input", default="pw.in")
    run.add_argument("--output", default="pw.out")
    run.add_argument("--timeout", type=float)
    run.add_argument("argv", nargs=argparse.REMAINDER)
    energy = commands.add_parser("qe-energy")
    energy.add_argument("--output", default="pw.out")
    energy.add_argument("--unit", choices=("ry", "ev"), default="ry")
    converged = commands.add_parser("qe-converged")
    converged.add_argument("--output", default="pw.out")
    diagnose = commands.add_parser("qe-diagnose")
    diagnose.add_argument("--output", default="pw.out")
    diagnose.add_argument("--json", action="store_true")
    write = commands.add_parser("qe-write-input")
    write.add_argument("--options", required=True)
    write.add_argument("--input", default="pw.in")


def run_command(arguments: argparse.Namespace) -> int:
    """Run one parsed ``qe-*`` subcommand.

    :param arguments: the parsed bridge command line.
    :return: the subcommand's exit code.
    """

    command = arguments.command
    if command == "qe-run":
        argv = arguments.argv[1:] if arguments.argv[:1] == ["--"] else arguments.argv
        if not argv:
            raise ValueError("qe-run needs the pw.x command after --")
        report = run_pw(
            argv,
            directory=arguments.directory,
            input_file=arguments.input,
            output_file=arguments.output,
            timeout=arguments.timeout,
        )
        print(Path(arguments.directory, "qe-run-report.json"))
        return _RUN_EXIT[report.classification]
    if command == "qe-diagnose":
        output = Path(arguments.output)
        diagnostics = diagnose_pw(output.parent, output=output.name)
        if arguments.json:
            print(json.dumps([item.as_mapping() for item in diagnostics], sort_keys=True))
        else:
            for item in diagnostics:
                print(f"{item.code}\t{item.severity}\t{item.summary}")
        return 20 if diagnostics else 0
    if command == "qe-write-input":
        options = dict(read_json(Path(arguments.options)))
        if "kpoints" in options:
            options["kpoints"] = tuple(options["kpoints"])
        write_pw_input(arguments.input, **options)
        return 0
    result = parse_pw_output(arguments.output)
    if command == "qe-energy":
        value = result.total_energy_ry if arguments.unit == "ry" else result.total_energy_ev
        if value is None:
            return BRIDGE_ABSENT
        print(f"{value:.16g}")
        return 0
    if command == "qe-converged":
        return 0 if result.converged and result.ionic_converged is not False else BRIDGE_ABSENT
    raise AssertionError(command)
