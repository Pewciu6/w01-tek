---
phase: 01-isolated-rai-environment
fixed_at: 2026-09-12T09:45:09Z
review_path: .planning/phases/01-isolated-rai-environment/01-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-09-12T09:45:09Z
**Source review:** .planning/phases/01-isolated-rai-environment/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope (critical + warning): 4
- Fixed: 4
- Skipped: 0

Scope is `critical_warning` (CR-01, WR-01, WR-02, WR-03). IN-01 is
info-level and out of scope for this run. Two of the four findings
(CR-01, WR-01) were fixed and committed by a previous fixer run that
timed out before writing this report; that work is recorded below as
already on the branch. This run fixed the remaining two (WR-02, WR-03).

All work in this run was performed directly in the main checkout on
branch `gsd/phase-01-isolated-rai-environment` (no worktree), per this
run's execution constraints. Verification ran inside the `wojtek_robot`
container via `experiments/wojtek_rai_v1/run.sh test`, the same path
the phase's own CI-equivalent uses; the numbers below are reproducible
from this checkout without any separate environment.

## Fixed Issues

### CR-01: Command injection and argument-quoting loss in `run.sh`'s `container_py()` via unquoted heredoc `$*` interpolation

**Files modified:** `experiments/wojtek_rai_v1/run.sh`
**Commit:** `49d9dd1` — `fix(01): CR-01 fix command injection and quoting loss in container_py()`
**Applied fix:** Quoted the heredoc delimiter (`<<'PYEOF'`) so the host
shell performs no parameter expansion on the body, and passes the
caller's arguments as real positional parameters via `bash -s -- "$@"`
followed by `exec .venv/bin/python "$@"` inside the container, instead
of flattening them into the heredoc text as `$*`.
**Verification (from this run, re-confirmed, not re-applied):** Full
suite green (65 passed). This run additionally re-validated the fix
indirectly: `./run.sh test -m "not ros_io" -q` correctly preserved a
space-containing quoted argument (`"not ros_io"`) as one argument,
consistent with the CR-01 fix still holding.

### WR-01: Full repository read-write mount for narrow test-only needs

**Files modified:** `experiments/wojtek_rai_v1/docker/compose.override.yaml`, `experiments/wojtek_rai_v1/tests/test_isolation_boundary.py`
**Commit:** `9672446` — `fix(01): WR-01 make the repo-root container mount read-only`
**Applied fix:** Made the `../..:/ros2_ws/repo_root` mount read-only and
reworked the two boundary-probe tests
(`test_reference_inside_experiment_dir_is_allowed` /
`test_reference_one_level_outside_experiment_dir_is_rejected`) to build
their synthetic sibling-directory probe under pytest's `tmp_path`
instead of writing into the live repository tree.
**Verification (from this run, re-confirmed, not re-applied):** Full
suite green (65 passed) against the already-recreated container with
the read-only mount.

### WR-02: The one test that performs real ROS I/O reproduces a documented 31-minute hang, with no timeout guard

**Files modified:** `experiments/wojtek_rai_v1/pyproject.toml`, `experiments/wojtek_rai_v1/uv.lock`, `experiments/wojtek_rai_v1/tests/test_topics_module.py`
**Commit:** `8a9398e` — `fix(01): WR-02 bound the one real-ROS-I/O test with a timeout guard`
**Applied fix:** Chosen option: **`pytest-timeout`** (the preferred
option in the fix guidance; the fallback `signal.alarm`/`threading.Timer`
guard was not needed because the lock refresh added only the one
intended package).
- Added `pytest-timeout>=2.3.1` to the `dev` dependency group in
  `pyproject.toml`; refreshed `uv.lock` inside the running
  `wojtek_robot` container via the same tool path `run.sh install`
  uses (`uv lock && uv sync --frozen`). The resulting diff to
  `uv.lock` is purely additive (14 insertions, 0 deletions) — it adds
  only `pytest-timeout` (locked at 2.4.0), confirming the fallback
  branch was not triggered.
- Because `run.sh`'s `container_py()` sets
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, added
  `[tool.pytest.ini_options] addopts = "-p pytest_timeout"` to load the
  plugin explicitly rather than relying on autoload.
- Applied `@pytest.mark.timeout(30)` to
  `test_main_is_callable_with_optional_argv` in
  `tests/test_topics_module.py`.
- Registered a `ros_io` marker in `pyproject.toml` and applied it to
  the same test, so a profile that cannot tolerate live ROS I/O can
  deselect it via `-m "not ros_io"`, while `run.sh test`'s default
  invocation (no `-m` filter) keeps running it.
**Verification:**
- Plugin actually fires: added a scratch probe test
  (`@pytest.mark.timeout(1)` + `time.sleep(2)`), confirmed it failed
  with `Failed: Timeout (>1.0s) from pytest-timeout.`, then removed
  the scratch file (never committed).
- `./run.sh test` (default, no `-m` filter): 65 passed.
- `./run.sh test -m "not ros_io" -q`: 64 passed — exactly the one
  `ros_io`-marked test deselected, confirming the marker targets only
  the intended test.

### WR-03: Secret-shape and credential-field regexes have coverage gaps

**Files modified:** `experiments/wojtek_rai_v1/tests/test_no_secrets_in_config.py`
**Commit:** `381a520` — `fix(01): WR-03 broaden secret-shape and credential-field regexes`
**Applied fix:**
- Broadened `SECRET_SHAPE_RE`'s OpenAI-style branch from
  `sk-[A-Za-z0-9]{16,}` to `(?:sk|pk)-[A-Za-z0-9_-]{16,}`, so a real
  Anthropic-style key (`sk-ant-api03-...`, which contains hyphens a few
  characters after the prefix) is caught; the 16+ char minimum is
  preserved so a short benign `sk-`/`pk-` substring still cannot trip
  it.
- Extended `POPULATED_KEY_FIELD_RE` from
  `\b(api_key|api_token|secret)\b` to an optional `<name>_` prefix
  group followed by `(?:api_key|api_token|secret|token|password|private_key)`,
  so `client_secret`, `oauth_secret`, `*_token`, `*_password`, and
  `private_key`-style field names are now flagged (the original had no
  word boundary after an underscore, so e.g. `client_secret` never
  matched `\bsecret\b`).
- Checked both broadened patterns against every tracked file's actual
  content for false-positive risk before committing (`grep` for
  `password|_secret|_token|private_key` and for `sk-`/`pk-` across
  `.py`/`.toml`/`.md`/`.lock` files): the only pre-existing hits were
  bare credential-name *strings* inside tuples (e.g.
  `"AWS_SECRET_ACCESS_KEY"` in `wojtek_rai/config.py` and
  `tests/test_config_loading.py`), which do not match either regex
  because there is no `[=:]`-then-quoted-value immediately following.
**Verification (fail-first, then reverted):**
- Temporarily appended two commented probe lines to the tracked
  `config.toml` — an `sk-ant-api03-...`-shaped value and a
  `client_secret = "totally-fake-value"` line — and ran
  `./run.sh test tests/test_no_secrets_in_config.py -q`: the guard now
  failed with
  `AssertionError: .../config.toml: contains a secret-shaped value: ['sk-ant-api03-...']`,
  proving the fix actually closes the gap the review demonstrated.
- Reverted `config.toml` (confirmed `git diff` empty; no injected
  value was ever committed).
- `./run.sh test`: 65 passed (full suite green again).

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-09-12T09:45:09Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
