"""Register the Quantum ESPRESSO code support implemented by :mod:`httk.codes.qe`."""

from httk.core.register import register_code

register_code("qe", bridge="httk.codes.qe._bridge", bash_api="httk.codes.qe:httk-qe.sh")
