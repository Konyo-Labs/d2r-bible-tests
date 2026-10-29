# -*- coding: utf-8 -*-
"""REG-2998 - THE CONSOLE A PROCESS ADDRESSES IS ITS OWN, NEVER :17772 BY NAME.

MEASURED 2026-10-29 (agent-144, while profiling REG-2985): console_doctor.CONSOLE was the constant
"http://127.0.0.1:17772". A scratch console on :17991 ran its eagle, and its doctor read HIS live console: GETs,
/api/board_ownership (which runs JavaScript in the window he is looking at) and /api/window {do: frame}. stage_witness
looked up the pid listening on :17772 to read the pixels of HIS window, and organ_matrix asked :17772 by name. Every
console a law spawns on his Mac did the same.

A console's port is TV_CONTROL_PORT: control_app.CONTROL_PORT reads it and nothing else sets the port, and a child
inherits it. So a process addresses the console its environment names. It addresses his console only when nothing names
one: a CLI he runs, or a law with no console of its own. A value that will not read names NO console (None), never his.
Every place a process reaches its own console by URL or by port goes through here; the laws that DELIBERATELY read his
live console (the live panel gate, the run gate's console probes, the launchers and the keepalive) keep their own words.
"""
import os

#: his console: the port a process addresses only when nothing in its environment names another
PRIMARY = 17772
ENV = "TV_CONTROL_PORT"

#: the files that name his console's or his agent's port ON PURPOSE, and why. test_a_scratch_console_never_addresses_his
#: fails on a his-port number anywhere else in tv/*.py, and on a his-port URL outside DELIBERATE_URL.
DELIBERATE = {
    "console_port.py": "the one helper: his console is the default only when nothing names another",
    "control_app.py": "CONTROL_PORT/AGENT_PORT read the environment; _PRIMARY_CONTROL_PORT/LIVE_CONTROL_PORT decide whether this is his",
    "corroborate.py": "the primary console's port judges who wrote the eagle record - a file read, never an address",
    "board_identity_sweep.py": "his console, never ours to race: it checks his is not running before it writes",
    "console_keepalive.py": "the keepalive probes and relaunches his console",
    "console_settle.py": "the push hook waits for his console to settle (--port)",
    "launcher_decide.py": "the launchers decide about his console",
    "win_relaunch.py": "the Windows relaunch decides about his console",
    "lane_ports.py": "the ports no lane may take",
    "my_orphans.py": "the ports a cleanup must never kill",
    "render_check.py": "it refuses to serve on his port",
    "run_gates.py": "the gate asks whether his console runs before it skips or waits",
    "sweep_wilson.py": "--bank scores against his live console, on demand",
    "vault_wilson.py": "scores against his live console, on demand",
    "tv_diablo.py": "the agent's own port default (TV_PORT)",
}
DELIBERATE_URL = {
    "console_port.py": "this docstring",
    "live_panel_gate.py": "the gate reads his LIVE panel on purpose (TV_CONSOLE_URL)",
    "prove_real_intake.py": "his on-demand prover lands one beat on his live agent",
}


def port():
    """The port of the console this process belongs to. -> int, or None when the environment names one that will not read
    (an unreadable value is no console, so the caller asks nobody - never his port by mistake)"""
    raw = os.environ.get(ENV)
    if raw is None or not str(raw).strip():
        return PRIMARY
    try:
        p = int(str(raw).strip())
    except ValueError:
        return None
    return p if 0 < p < 65536 else None


def url(path=""):
    """The URL http://127.0.0.1:<port()><path>, or None when there is no console to ask. -> str | None"""
    p = port()
    return None if p is None else "http://127.0.0.1:%d%s" % (p, path)
