---
phase: 01-isolated-rai-environment
reviewed: 2026-09-12T00:00:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - .env.example
  - .gitignore
  - experiments/wojtek_rai_v1/.gitignore
  - experiments/wojtek_rai_v1/README.md
  - experiments/wojtek_rai_v1/config.toml
  - experiments/wojtek_rai_v1/docker/compose.override.yaml
  - experiments/wojtek_rai_v1/docs/VERIFICATION.md
  - experiments/wojtek_rai_v1/pyproject.toml
  - experiments/wojtek_rai_v1/ros/rai_interfaces.repos
  - experiments/wojtek_rai_v1/run.sh
  - experiments/wojtek_rai_v1/tests/conftest.py
  - experiments/wojtek_rai_v1/tests/test_build_target.py
  - experiments/wojtek_rai_v1/tests/test_compose_override.py
  - experiments/wojtek_rai_v1/tests/test_config_loading.py
  - experiments/wojtek_rai_v1/tests/test_isolation_boundary.py
  - experiments/wojtek_rai_v1/tests/test_model_free_guard.py
  - experiments/wojtek_rai_v1/tests/test_no_secrets_in_config.py
  - experiments/wojtek_rai_v1/tests/test_pinned_versions.py
  - experiments/wojtek_rai_v1/tests/test_repos_pin.py
  - experiments/wojtek_rai_v1/tests/test_topics_module.py
  - experiments/wojtek_rai_v1/wojtek_rai/__init__.py
  - experiments/wojtek_rai_v1/wojtek_rai/config.py
  - experiments/wojtek_rai_v1/wojtek_rai/topics.py
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-09-12T00:00:00Z
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

This phase adds a self-contained, well-documented `experiments/wojtek_rai_v1/`
tree that pins RAI's Python/ROS dependencies, extends the shared dev
container via a compose override, and covers the isolation, pinning, and
secrets rules with a genuinely fail-first-proven test suite. The credential
handling is careful throughout (names forwarded by `-e NAME`, never values;
no shell tracing; `config.toml` carries no secret field). No hardcoded
secrets, hostnames, or private-infrastructure identity were found in any
reviewed file, and `.env.example` only adds placeholder names.

One finding is a genuine, demonstrated command-injection / argument-quoting
bug in `run.sh`'s `container_py()` helper, reachable through `run.sh test
<args>`. I built a minimal reproduction (see CR-01) proving that an
argument containing shell metacharacters gets executed as real shell code
inside the container, and, independently, that an argument containing a
space (a completely normal pytest `-k` expression) gets its quoting
silently destroyed. Given the container this helper drives already carries
`privileged: true`, host `/dev`, `~/.ssh` (ro), and — after this phase — a
read-write mount of the entire repository, this is a BLOCKER.

The remaining findings are judgment calls about isolation-boundary
tightness (the orchestrator-flagged repo-root read-write mount), a testing
practicehole that reproduces a defect already documented as hung for 31
minutes on real hardware, and coverage gaps in the secrets-shape regexes.
None of these are exploited by anything in this phase's own code path
today, but they either weaken guarantees this phase's own README asserts
("nothing outside this directory imports it," "model-free," "no
credential-shaped value ever committed") or set up friction/risk for the
agent loop phase 2 adds inside this same container.

## Critical Issues

### CR-01: Command injection and argument-quoting loss in `run.sh`'s `container_py()` via unquoted heredoc `$*` interpolation

**File:** `experiments/wojtek_rai_v1/run.sh:119-143`
**Issue:**

`container_py()` builds the container-side script as an **unquoted**
heredoc (`<<PYEOF`, not `<<'PYEOF'`), so the host shell performs parameter
expansion on the heredoc body before it is ever sent to the container:

```bash
docker exec -i ${CRED_ENV_ARGS[@]+"${CRED_ENV_ARGS[@]}"} wojtek_robot bash -s <<PYEOF
...
exec .venv/bin/python $*
PYEOF
```

`$*` here is `container_py`'s own positional parameters — ultimately
`run.sh`'s own trailing CLI arguments, forwarded from the `test)` branch as
`container_py -m pytest tests -q "$@"`. Two independent, real problems
follow from flattening those arguments into unquoted text embedded in
another shell's source:

1. **Argument-boundary loss (functional bug).** Any argument containing
   whitespace is silently corrupted. A completely ordinary invocation such
   as `./run.sh test -k "test_a or test_b"` becomes, once flattened, three
   separate tokens (`test_a`, `or`, `test_b`) instead of one `-k` argument —
   pytest receives the wrong CLI shape. I reproduced this directly:
   ```
   $ bash -c 'f(){ cat <<PYEOF
   exec .venv/bin/python $*
   PYEOF
   }; f -k "test_a or test_b"'
   exec .venv/bin/python -k test_a or test_b
   ```
   The quotes around `test_a or test_b` are gone from the resulting text.

2. **Command injection (security bug).** Because the flattened text is fed
   as literal *stdin source code* to a second, independent `bash -s`
   interpreter running inside the container, any shell metacharacter in an
   argument — `` ` ``, `$(...)`, `;`, `&&`, `|` — is genuinely re-parsed and
   *executed* by that inner shell, even though the outer shell never
   evaluated it (parameter expansion does not recursively re-interpret its
   own output). I proved this end-to-end:
   ```
   $ bash -c 'f(){ cat <<PYEOF
   echo before
   exec echo .venv/bin/python $*
   PYEOF
   }; f -k "\$(touch /tmp/rai_review_injection_proof)"' | bash -s
   before
   .venv/bin/python -k
   $ ls /tmp/rai_review_injection_proof
   /tmp/rai_review_injection_proof   # file was created — injected code ran
   ```
   Applied to the real `container_py`, any caller of `./run.sh test <arg>`
   (a human typo, a CI variable, or — relevant to this project's own
   roadmap — a later phase's LLM agent constructing this command from model
   output) can execute arbitrary code inside the `wojtek_robot` container.
   That container is already `privileged: true` with host `/dev` and `~/.ssh`
   (ro) mounted, and — per this same phase — now also has a **read-write**
   mount of the entire repository (see WR-01), so the blast radius of this
   injection is severe.

**Fix:** Never embed externally-supplied argv into heredoc text. Pass
arguments as real positional parameters to the inner shell instead, using a
fully single-quoted heredoc plus `bash -s --`:

```bash
container_py() {
  docker exec -i ${CRED_ENV_ARGS[@]+"${CRED_ENV_ARGS[@]}"} wojtek_robot \
    bash -s -- "$@" <<'PYEOF'
set -eo pipefail
EXP_DIR="/ros2_ws/experiments/wojtek_rai_v1"
export UV_INSTALL_DIR="$EXP_DIR/.tools"
export PATH="$UV_INSTALL_DIR:$PATH"
source /opt/ros/jazzy/setup.bash
[ -f "$EXP_DIR/ros_ws/install/setup.bash" ] && source "$EXP_DIR/ros_ws/install/setup.bash"
cd "$EXP_DIR"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
exec .venv/bin/python "$@"
PYEOF
}
```

With the heredoc delimiter quoted (`<<'PYEOF'`), the host performs no
expansion at all on the body, and `bash -s -- "$@"` passes the caller's
arguments as the inner script's real `$1 $2 ...`/`"$@"`, preserving
quoting and never re-evaluating their contents as code. (`CONTAINER_EXP_DIR`
is a fixed literal, so hardcoding it inside the now fully-static heredoc,
as shown, is simplest; it no longer needs host-side interpolation.)

## Warnings

### WR-01: Full repository read-write mount for narrow test-only needs

**File:** `experiments/wojtek_rai_v1/docker/compose.override.yaml:39-62`
**Issue:** The third volume, `../..:/ros2_ws/repo_root`, mounts the entire
repository **read-write** into an already-privileged container. Per the
file's own comments, this exists solely so `tests/test_isolation_boundary.py`
can (a) read `ros/`, `training/`, and `ros/deploy.sh` (read-only need), and
(b) write one temp probe file under `experiments/` for its fail-first
boundary control (write need). Only (b) requires write access, and only to
`experiments/`, never to `ros/` or `training/`.

As written, any code running in this container — including whatever this
same phase's own bug (CR-01) can inject, and, more importantly, the ReAct
agent/tool registry the README says Phase 2 adds on top of this exact
container — has unrestricted write access to the production `ros/` and
`training/` trees this experiment's whole isolation model (CLAUDE.md,
README §"isolation rules") exists to protect. That defeats the "delete
`experiments/` and nothing else notices" guarantee at the container
boundary; today it is only enforced by tests running *after* the fact, not
by the container's own permissions.

**Fix:** Narrow the write surface to match what the tests actually need:
- Mount `ros/` and `training/` (or the whole repo root) `:ro`.
- Add a second, narrow read-write bind mount of only `experiments/` (not
  the full repo) for the two boundary-probe tests
  (`test_reference_inside_experiment_dir_is_allowed` /
  `test_reference_one_level_outside_experiment_dir_is_rejected`).

Better still, avoid needing any write mount at all: rewrite those two tests
to build their synthetic sibling-directory probe under pytest's `tmp_path`
and pass that path to `_grep_rl` (which would need a `cwd` parameter) instead
of writing into the live repository tree under test. That also removes the
small residual risk today of a killed/hung `pytest` process (this suite has
already been observed to hang and require a `SIGKILL`, per
`docs/VERIFICATION.md` Attempt A) leaving a stray untracked file in the
real working tree if a hang were ever to land between the probe's write and
its `finally: probe.unlink()`.

### WR-02: The one test that performs real ROS I/O reproduces a documented 31-minute hang, with no timeout guard

**File:** `experiments/wojtek_rai_v1/tests/test_topics_module.py:54-64`
**Issue:** Every doc comment in this suite (README.md, conftest.py,
test_model_free_guard.py) asserts the test suite is "model-free: no ROS
runtime, no LLM key, no GPU." `test_model_free_guard.py` only enforces this
at the *import* level (no forbidden module at module scope) — it does not
and cannot catch a test whose *body* performs real I/O.
`test_main_is_callable_with_optional_argv` calls `topics.main([])`, which
calls `list_topics()`, which constructs a real `rai.communication.ros2.ROS2Connector`
(a real `rclpy` init, node, and shutdown) against whatever ROS 2 environment
the process happens to be in.

`docs/VERIFICATION.md`'s own Attempt A records exactly this class of
failure: a `run.sh test` run that printed 64 of 65 dots and then hung for
31 minutes before being killed (exit `137`), traced to a DDS
multicast-loopback shutdown defect. Given this is the *only* test in the
suite that opens a real connector, and it is the alphabetically-last test
file, it is the most likely candidate for that exact hang. There is no
timeout at the test level (`pytest-timeout` or similar) or at the `run.sh
test` level, so a machine with this networking defect — which
`docs/VERIFICATION.md` already shows is not confined to one architecture —
makes `run.sh test` hang indefinitely instead of failing fast, defeating
the "fast enough to run on every edit" property the rest of the suite is
designed around.

**Fix:** Bound this specific test with a timeout (e.g. `@pytest.mark.timeout(30)`
via `pytest-timeout`, or a `signal.alarm`-based guard) so a DDS hang on a
given host surfaces as a clear, fast test failure rather than a silent
multi-minute stall. Consider also isolating it (a separate marker) so a CI
profile that cannot tolerate any live ROS I/O can skip just this one test
while keeping the rest of the "model-free" guarantee intact.

### WR-03: Secret-shape and credential-field regexes have coverage gaps

**File:** `experiments/wojtek_rai_v1/tests/test_no_secrets_in_config.py:67-80`
**Issue:** `SECRET_SHAPE_RE`'s OpenAI-style branch, `sk-[A-Za-z0-9]{16,}`,
requires 16+ *contiguous* alphanumerics immediately after `sk-`. Real
Anthropic-style keys (`sk-ant-api03-...`) contain hyphens a few characters
in and so never satisfy this run length — I confirmed the pattern does not
match a representative `sk-ant-...`-shaped string. Separately,
`POPULATED_KEY_FIELD_RE`'s `\b(api_key|api_token|secret)\b`-style alternation
has no word boundary between an underscore and the following word (`_` is a
word character), so a field named `client_secret` or `oauth_secret` is not
flagged either, since `\bsecret\b` never matches with a preceding `_`.

This is a guard test whose entire purpose is catching exactly these shapes
before they land in a public repository (per CLAUDE.md's hard rule); a gap
here is a false sense of safety rather than a functional bug in production
code, but it is squarely in this suite's stated scope (FOUND-04).

**Fix:** Broaden `SECRET_SHAPE_RE`'s key-shaped alternatives to allow
hyphens/underscores after the `sk-`/`pk-` prefix (e.g.
`sk-[A-Za-z0-9_-]{16,}`), and extend `POPULATED_KEY_FIELD_RE` to also match
`*_secret`, `*_token`, `*_password`, and `private_key`-style field name
suffixes, not just bare `api_key`/`api_token`/`secret`.

## Info

### IN-01: `.env.example` is now reachable through two different mounts with inconsistent path resolution

**File:** `experiments/wojtek_rai_v1/docker/compose.override.yaml:28-37`,
`experiments/wojtek_rai_v1/tests/test_no_secrets_in_config.py:46`
**Issue:** The narrow `../../.env.example:/ros2_ws/.env.example:ro` mount
(added in plan 01-03) is now redundant with the broader
`../..:/ros2_ws/repo_root` mount (added in plan 01-04), which also exposes
`.env.example` at `/ros2_ws/repo_root/.env.example`. `test_no_secrets_in_config.py`
still depends specifically on the narrower mount's path
(`REPO_ROOT = Path(__file__).resolve().parents[3]` → `/ros2_ws` inside the
container), unlike the three other test files that added a shared
`_resolve_repo_root()` helper preferring `/ros2_ws/repo_root` when
populated. Not a functional bug today (both mounts currently exist and both
resolve correctly), but the two mounts and two different resolution
strategies for "the same file" are worth consolidating the next time either
is touched, so a future removal of one mount does not silently break the
other test file.
**Fix:** Either drop the narrow `.env.example` mount and update
`test_no_secrets_in_config.py` to use the shared `_resolve_repo_root()`
pattern (pointing at `/ros2_ws/repo_root/.env.example`), or keep both but
add a one-line comment cross-referencing the dependency so they are not
removed independently.

---

_Reviewed: 2026-09-12T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
