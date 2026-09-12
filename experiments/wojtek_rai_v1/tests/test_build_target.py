"""Static, model-free guards over `run.sh build`'s colcon-tooling contract.

`run.sh build`'s dynamic behavior (actually cloning `rai_interfaces`,
resolving its rosdep keys, and colcon-building it into `ros_ws/`) can only
be exercised against the live `wojtek_robot` container over the network --
that is the plan's `<human-check>` step, not this suite (FOUND-06: no
network, no live process here). What this test checks is the deterministic,
host-readable part of the contract: the script text itself routes the build
into the experiment's own overlay, resolves rosdep keys before building, and
never references `ros/src` outside of a comment -- so a regression here (a
build target that quietly starts touching the shared `ros/src` tree, or that
skips the rosdep step Pitfall 3 requires) fails this suite immediately,
without needing Docker or a colcon build to notice.
"""

import re
from pathlib import Path


def run_sh_text(experiment_dir: Path) -> str:
    return (experiment_dir / "run.sh").read_text()


def non_comment_lines(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("#")
    )


def test_build_target_uses_its_own_overlay_base_path(experiment_dir):
    text = run_sh_text(experiment_dir)
    assert "base-paths" in text, (
        "run.sh must colcon-build with --base-paths pointed at this "
        "experiment's own ros_ws/, not the shared ros/src tree"
    )


def test_build_target_resolves_rosdep_keys_before_building(experiment_dir):
    text = run_sh_text(experiment_dir)
    assert "rosdep install" in text, (
        "run.sh build must run 'rosdep install' against the imported "
        "rai_interfaces source (Pitfall 3: vision_msgs/nav2_msgs/"
        "nav2_simple_commander/tf_transformations/portaudio19-dev are not "
        "in the image and must be resolved at build time, not skipped)"
    )


def test_build_target_never_touches_shared_ros_src(experiment_dir):
    text = run_sh_text(experiment_dir)
    stripped = non_comment_lines(text)
    matches = re.findall(r"ros/src", stripped)
    assert not matches, (
        f"run.sh references ros/src outside a comment ({len(matches)} "
        "occurrence(s)) -- rai_interfaces must build into this "
        "experiment's own ros_ws/, never the shared ros/src/ tree "
        "ros/deploy.sh rsyncs to the robot"
    )


def test_build_target_guards_on_missing_colcon(experiment_dir):
    text = run_sh_text(experiment_dir)
    assert "colcon" in text.lower() and (
        "not found" in text.lower() or "not on path" in text.lower()
    ), (
        "run.sh build must guard on colcon being available and name it in "
        "the failure message when it is not, matching the sibling "
        "experiment's guard"
    )


# T-01-13 (plan 01-03 threat register): credentials enter run.sh from the
# gitignored .env and are forwarded into the container by NAME only. A
# shell trace (`set -x`, `set -o xtrace`, `bash -x`) would print every
# expanded command line -- including any credential value that ever gets
# interpolated by a future edit -- into the terminal or a CI log. The
# mitigation plan promised this prohibition is grep-asserted, not just
# stated in a comment; this is that assertion.
SHELL_TRACE_RE = re.compile(
    r"(?:^|[;&|(\s])set\s+(?:-[a-wyzA-Z]*x[a-zA-Z]*|-o\s+xtrace)\b"
    r"|(?:^|[;&|(\s])(?:bash|sh)\s+(?:-[a-wyzA-Z]*)?-?x\b"
    r"|\bBASH_XTRACEFD\b|\bSHELLOPTS=.*xtrace",
    re.MULTILINE,
)


def test_run_sh_never_enables_shell_trace(experiment_dir):
    # Self-check first: the pattern must actually catch the shapes it
    # exists to catch, otherwise this guard would pass vacuously (T-01-17).
    for bad in ("set -x", "set -euxo pipefail", "set -o xtrace",
                "  bash -x foo.sh", "exec bash -ex", "export BASH_XTRACEFD=3"):
        assert SHELL_TRACE_RE.search(bad), f"guard regex misses {bad!r}"
    for ok in ("set -euo pipefail", "set -eo pipefail", "bash -s -- \"$@\"",
               "bash -c 'x=1'", "docker exec -i wojtek_robot bash -s"):
        assert not SHELL_TRACE_RE.search(ok), f"guard regex false-positive on {ok!r}"

    live = non_comment_lines(run_sh_text(experiment_dir))
    hits = [m.group(0).strip() for m in SHELL_TRACE_RE.finditer(live)]
    assert not hits, f"run.sh enables a shell trace (would leak credential values): {hits}"
