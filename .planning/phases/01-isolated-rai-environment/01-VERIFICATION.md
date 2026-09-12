---
phase: 01-isolated-rai-environment
verified: 2026-09-12T00:00:00Z
status: passed
score: 4/4 roadmap success criteria verified; 24/24 plan-level must-have truths verified
behavior_unverified: 0
overrides_applied: 0
must_haves:
  truths:
    - "run.sh install installs exactly rai-core==2.12.0 and rai-whoami==0.0.5, with every langchain/langgraph distribution pinned in the committed uv.lock, idempotently, on both x86-64 and aarch64"
    - "run.sh test exits 0 with no LLM key, no ROS daemon and no GPU, and fails if anything outside experiments/wojtek_rai_v1/ imports it or if ros/deploy.sh could ship it"
    - "run.sh agent-topics lists the live simulation's cmd_vel and camera topics through RAI's own ROS2Connector, with zero edits under ros/"
    - "Vendor and tracing keys enter only through the gitignored .env; config.toml carries no credential; a fail-first-proven test rejects secret-shaped values in tracked config"
  artifacts:
    - path: "experiments/wojtek_rai_v1/run.sh"
      provides: "install | build | test | container | agent | agent-topics | up entry point"
    - path: "experiments/wojtek_rai_v1/pyproject.toml"
      provides: "exact pins for rai-core, rai-whoami"
    - path: "experiments/wojtek_rai_v1/uv.lock"
      provides: "locked transitive langchain/langgraph versions"
    - path: "experiments/wojtek_rai_v1/docker/compose.override.yaml"
      provides: "bind-mounts the experiment into wojtek_robot without editing ros/docker/"
    - path: "experiments/wojtek_rai_v1/wojtek_rai/topics.py"
      provides: "list_topics/format_topics/main via RAI's ROS2Connector"
    - path: "experiments/wojtek_rai_v1/ros/rai_interfaces.repos"
      provides: "rai_interfaces pinned to a commit SHA"
    - path: "experiments/wojtek_rai_v1/wojtek_rai/config.py"
      provides: "config_path/load_experiment_config/required_env_vars"
    - path: "experiments/wojtek_rai_v1/config.toml"
      provides: "vendor config template, no credential field"
    - path: "experiments/wojtek_rai_v1/tests/test_isolation_boundary.py"
      provides: "FOUND-01 import-boundary + deploy-reachability guard"
    - path: "experiments/wojtek_rai_v1/tests/test_pinned_versions.py"
      provides: "FOUND-02 exact-pin + lockfile guard"
    - path: "experiments/wojtek_rai_v1/tests/test_compose_override.py"
      provides: "FOUND-03 static-half guard"
    - path: "experiments/wojtek_rai_v1/tests/test_model_free_guard.py"
      provides: "FOUND-06 self-referential model-free guard"
    - path: "experiments/wojtek_rai_v1/tests/test_no_secrets_in_config.py"
      provides: "FOUND-04 secret-shape + private-identity guard"
    - path: "experiments/wojtek_rai_v1/README.md"
      provides: "status, scope, usage, isolation-rule documentation"
    - path: "experiments/wojtek_rai_v1/docs/VERIFICATION.md"
      provides: "two-machine literal command-output record for FOUND-07"
  key_links:
    - from: "experiments/wojtek_rai_v1/run.sh"
      to: "experiments/wojtek_rai_v1/docker/compose.override.yaml"
      via: "docker compose -f ros/docker/compose.yaml -f docker/compose.override.yaml up -d"
    - from: "experiments/wojtek_rai_v1/run.sh"
      to: "experiments/wojtek_rai_v1/wojtek_rai/topics.py"
      via: "agent-topics execs container_py -m wojtek_rai.topics"
    - from: "experiments/wojtek_rai_v1/wojtek_rai/topics.py"
      to: "rai.communication.ros2.ROS2Connector"
      via: "function-local import + get_topics_names_and_types()"
  prohibitions:
    - statement: "Nothing under ros/ or training/ is edited or references the experiment; the experiment is unreachable by ros/deploy.sh"
      status: resolved
      verification: test
findings:
  - "An OpenAI API key was found set as a live environment variable in the verifier's host shell during this verification session (unrelated to any tracked repository file — it is not present in .env.example, config.toml, or any tracked source). It was echoed once into a diagnostic `env | grep` tool call during this session and is now visible in this verification transcript. This is independent of the phase's own FOUND-04 guard (which only scans tracked files and passed correctly) but is a real-world exposure the operator should rotate the key for and be aware the value now sits in this session's tool-call history."
---

# Phase 01: Isolated RAI Environment Verification Report

**Phase Goal:** A developer can bring up a pinned, self-contained RAI environment that discovers
the running Wojtek simulation's ROS 2 topics, on either machine, without touching production
packages.
**Verified:** 2026-09-12
**Status:** passed
**Re-verification:** No — initial verification

## Note on `mode: mvp`

ROADMAP.md marks this phase `Mode: mvp`, but the phase goal is not phrased as a User Story
(`As a ..., I want ..., so that ....`) — it reads as an infrastructure/tooling goal, and all five
phases in this milestone carry the same `mode: mvp` tag uniformly, which looks like a template
default rather than a deliberate per-phase choice for this foundation phase. I did not force this
report into the MVP "User Flow Coverage" table format, since there is no user-facing flow to trace
in Phase 1 (no chat, no agent, no UI — the phase's own README says so explicitly). Standard
goal-backward verification against the four ROADMAP success criteria was used instead. Flagging
this as an observation only, not a gap.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | One `run.sh` target installs the pinned RAI stack (`rai-core==2.12.0`, `rai-whoami==0.0.5`, `rai_interfaces` at a commit SHA, LangChain/LangGraph locked) and succeeds on both x86-64 and aarch64 | ✓ VERIFIED | `pyproject.toml` pins both packages exactly; `uv.lock` (3048 lines) resolves all langchain*/langgraph* transitives; `ros/rai_interfaces.repos` pins a 40-char commit SHA (`2398f1f3e4c96d790365492294599439a38cdf9a`), not a branch/tag. `docs/VERIFICATION.md` records `run.sh install` exiting 0 with literal output on both the x86-64 laptop and the aarch64 dev box (132 aarch64 wheels resolved from the same committed `uv.lock`, zero source builds) |
| 2 | With the sim running, one `run.sh` command starts the RAI process and lists live topics (`cmd_vel`, camera), zero edits under `ros/docker/`, `ros/sim.sh`, or `ros/src/` | ✓ VERIFIED | The accepted 01-01 decision (recorded, human-approved) replaced "with `ros/sim.sh` already running" with `run.sh`'s own container/`up` lifecycle, since neither `ros/sim.sh` nor `ros/dev.sh` has an extension seam — this is the binding interpretation per the orchestrator's brief. `run.sh agent-topics` → `wojtek_rai.topics.main` → `rai.communication.ros2.ROS2Connector.get_topics_names_and_types()`, function-local import, read-only. Live run in 01-01-SUMMARY and `docs/VERIFICATION.md` shows `/cmd_vel`, `/camera/.../color/image_raw`, `/camera/.../depth/image_rect_raw` present on both machines. `git diff --stat main...HEAD -- ros/ training/` is empty (independently re-run) |
| 3 | `run.sh test` passes with no LLM key/ROS runtime/GPU, and fails if anything outside the experiment imports it or if `ros/deploy.sh` could ship it | ✓ VERIFIED | Independently re-ran `./experiments/wojtek_rai_v1/run.sh test` myself: **65 passed, 0 skipped**, no vendor key required by the suite. `tests/test_isolation_boundary.py` and `tests/test_model_free_guard.py` exist, are non-stub, and per 01-04-SUMMARY each of their guarantees was demonstrated fail-first (reference from `training/`, stray path under `ros/src/`, widened `deploy.sh` rsync source, module-scope `rclpy` import — each caught red, each reverted clean) |
| 4 | Vendor/tracing keys enter only via gitignored `.env`; `config.toml` has placeholders only; a test rejects secret-looking values in tracked config | ✓ VERIFIED | `config.toml` (read directly) contains only vendor/model names, base URLs and tracing toggles (`false` by default) — no credential field exists in its schema. `.env.example` (via `git show HEAD:.env.example`) declares 7 empty placeholder names (`OPENAI_API_KEY`, `AWS_*`, `GOOGLE_API_KEY`, `LANGFUSE_*`), no values. `tests/test_no_secrets_in_config.py` exists and is part of the 65-test green run; 01-03-SUMMARY documents a fail-first demonstration (synthetic `sk-...` value injected into `config.toml` → 1 failed / 29 passed → reverted → 30/30) |

**Score:** 4/4 roadmap success criteria verified, 0 present-but-behavior-unverified.

### FOUND-07 two-machine finding (not a gap)

`docs/VERIFICATION.md` (read in full, independently) shows `run.sh install` succeeding literally,
unmodified, on both architectures. `run.sh test` and `run.sh agent-topics` also succeed on both,
but on the aarch64 dev box only after setting a non-default DDS discovery variable
(`ROS_LOCALHOST_ONLY=1` / `CYCLONEDDS_URI` override) — the literal default-profile attempts are
recorded as hangs (exit `137`/`124`), not silently passed over. The root cause is a multicast-
loopback delivery defect on that specific host's network interface in the *base* `ros/docker`
CycloneDDS profile, explicitly out of this experiment's scope per plan 01-05's own must-haves
("any arm64 breakage originating inside the base container configuration is recorded ... as a
finding, not fixed inside the experiment"). I verified that finding requirement holds: the finding
is recorded (§ Findings 1–3), `ros/` is untouched, and no arm64-specific defect exists in the RAI
stack itself (132/132 packages resolved as aarch64 wheels, 65/65 tests passed once the DDS setting
was applied). Given the phase's own literal success-criterion wording ("one `run.sh` target
installs ... and succeeds on both") is about the install step, and the plan's own must-haves
anticipated and scoped this exact caveat, this is treated as a **documented finding**, not a gap.
**Carry-forward for Phase 2+:** any future dev-box run of this experiment needs the same DDS
workaround; `ros/docker`'s owner should consider making the discovery profile selectable per
machine.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `experiments/wojtek_rai_v1/run.sh` | install\|build\|test\|container\|agent\|agent-topics\|up | ✓ VERIFIED | All 7 subcommands present; independently re-ran `install`/`test`/`agent-topics` |
| `experiments/wojtek_rai_v1/pyproject.toml` | `rai-core==2.12.0` exact pin | ✓ VERIFIED | Confirmed by direct read |
| `experiments/wojtek_rai_v1/uv.lock` | ≥50 lines, locked transitives | ✓ VERIFIED | 3048 lines, 73 langchain/langgraph references |
| `experiments/wojtek_rai_v1/docker/compose.override.yaml` | mounts wojtek_robot, no DDS env override | ✓ VERIFIED | Confirmed by direct read; no `environment:` block |
| `experiments/wojtek_rai_v1/wojtek_rai/topics.py` | list_topics/format_topics/main | ✓ VERIFIED | All three defined; function-local `rai`/`rclpy` import |
| `experiments/wojtek_rai_v1/ros/rai_interfaces.repos` | pinned commit SHA | ✓ VERIFIED | 40-char SHA, not a branch/tag |
| `experiments/wojtek_rai_v1/wojtek_rai/config.py` | config_path/load_experiment_config/required_env_vars | ✓ VERIFIED | All three defined |
| `experiments/wojtek_rai_v1/config.toml` | `[vendor]`, no credential field | ✓ VERIFIED | Confirmed by direct read |
| `experiments/wojtek_rai_v1/tests/test_isolation_boundary.py` | FOUND-01 guard | ✓ VERIFIED | 7 tests present, non-stub |
| `experiments/wojtek_rai_v1/tests/test_pinned_versions.py` | FOUND-02 guard | ✓ VERIFIED | 9 tests present, non-stub |
| `experiments/wojtek_rai_v1/tests/test_compose_override.py` | FOUND-03 guard | ✓ VERIFIED | 6 tests present, non-stub |
| `experiments/wojtek_rai_v1/tests/test_model_free_guard.py` | FOUND-06 guard | ✓ VERIFIED | 13 tests present, non-stub |
| `experiments/wojtek_rai_v1/tests/test_no_secrets_in_config.py` | FOUND-04 guard | ✓ VERIFIED | 7 tests present, non-stub |
| `experiments/wojtek_rai_v1/README.md` | `## Status`, layout, isolation rules | ✓ VERIFIED | Confirmed by direct read |
| `experiments/wojtek_rai_v1/docs/VERIFICATION.md` | `aarch64` two-machine record | ✓ VERIFIED | Confirmed by direct read, full document |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `run.sh` | `docker/compose.override.yaml` | `-f docker/compose.override.yaml` | ✓ WIRED | `run.sh:104` |
| `run.sh` (`agent-topics`) | `wojtek_rai/topics.py` | `container_py -m wojtek_rai.topics` | ✓ WIRED | `run.sh:332` |
| `wojtek_rai/topics.py` | `rai.communication.ros2.ROS2Connector` | function-local import + `get_topics_names_and_types()` | ✓ WIRED | Confirmed in source |
| `run.sh` | `ros/rai_interfaces.repos` | `build` target `vcs import` | ✓ WIRED | Per 01-02-SUMMARY, re-verified via passing `test_repos_pin.py` |
| `wojtek_rai/config.py` | `config.toml` | `config_path()` anchored on `__file__` | ✓ WIRED | Confirmed in source |

### Isolation / Prohibition Checks (independently re-run)

| Check | Command | Result |
|-------|---------|--------|
| No production edits | `git diff --stat main...HEAD -- ros/ training/` | empty |
| No `rai`/experiment path under `ros/src/` | `ls ros/src \| grep -i rai` | no match (exit 1) |
| No experiment reference in `ros/`/`training/` | `grep -rl wojtek_rai ros/ training/` | no match |
| `ros/deploy.sh` rsync sources | inspected | resolve only inside `ros/`, never into `experiments/` |
| Full test suite | `./experiments/wojtek_rai_v1/run.sh test` | **65 passed, 0 skipped** (re-run live on this machine) |
| Debt markers | `grep -rn "TBD\|FIXME\|XXX"` over experiment tree | none found |
| `.env.example` secrets | `git show HEAD:.env.example` | 7 placeholder names, all empty |
| `docs/VERIFICATION.md` private-identity scan | dotted-quad IP / email regex | 0 matches each (re-run independently) |

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|------------|--------|----------|
| FOUND-01 | 01-01, 01-04 | ✓ SATISFIED | Isolation boundary enforced by `test_isolation_boundary.py`, proven fail-first |
| FOUND-02 | 01-01, 01-02, 01-04 | ✓ SATISFIED | Exact pins + lockfile guard, `rai_interfaces` SHA pin |
| FOUND-03 | 01-01, 01-04 | ✓ SATISFIED | Compose override extends service, no DDS env redeclaration |
| FOUND-04 | 01-03 | ✓ SATISFIED | Secret-shape/identity guard proven fail-first; no credential in tracked files |
| FOUND-06 | 01-01, 01-03, 01-04 | ✓ SATISFIED | 65/65 tests pass with no key/ROS/GPU; self-referential model-free guard |
| FOUND-07 | 01-05 | ✓ SATISFIED (documented DDS caveat, see above) | Two-machine literal record in `docs/VERIFICATION.md` |

No orphaned requirements: REQUIREMENTS.md's Phase 1 row lists exactly FOUND-01/02/03/04/06/07,
matching what all five plans' `requirements:` frontmatter fields declare in aggregate.

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in the experiment tree. The two
"not implemented until Phase 2" strings in `run.sh` (the `agent` stub) are an explicitly documented,
in-scope stub per 01-01-SUMMARY's "Known Stubs" section and the ROADMAP's own phase boundary
(`AGT-01` etc. are Phase 2 requirements) — not a debt marker.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full model-free suite passes with no LLM/ROS/GPU precondition claim | `./experiments/wojtek_rai_v1/run.sh test` | 65 passed, 0 skipped, 37.68s | ✓ PASS |
| No production-tree edits | `git diff --stat main...HEAD -- ros/ training/` | empty | ✓ PASS |
| No experiment leakage into `ros/src/` | `ls ros/src \| grep -i rai` | no match | ✓ PASS |
| `.env.example` carries only placeholders | `git show HEAD:.env.example \| grep KEY` | 8 empty-valued names | ✓ PASS |

### Human Verification Required

None. Every must-have truth in this phase was either directly re-verified by this verifier or was
already demonstrated fail-first by the executing agent with reproducible commands recorded in the
SUMMARYs, and I independently re-ran the full test suite and the key isolation checks myself rather
than trusting the SUMMARY claims alone.

### Gaps Summary

No gaps. All four ROADMAP success criteria and all 24 plan-level must-have truths across the five
plans are backed by artifacts that exist, are substantive (non-stub, non-empty), are wired into
`run.sh`'s real execution path, and pass when independently re-run on this machine. The one
FOUND-07 caveat (aarch64 DDS discovery needing a non-default setting) is a documented, in-scope
finding attributable to the base `ros/docker` container's network configuration on that specific
host, not a Phase 1 defect — the plan itself anticipated exactly this class of finding and the
phase's success criterion wording (the install step) is met literally on both architectures.

### Out-of-band finding (not part of Phase 1 scope)

During verification, this session's host shell was found to have a live `OPENAI_API_KEY`
environment variable set — unrelated to this repository (not present in any tracked file; the
project's own `FOUND-04` guard, which scans tracked files only, correctly found nothing). It was
inadvertently echoed once by a diagnostic `env | grep` command during this verification and is now
visible in this session's tool-call history. This does not affect the phase's pass/fail status
(FOUND-04 is about tracked repository content), but the operator should rotate that key given its
value now sits in a Claude Code session transcript, and should be aware that broad `env` dumps are
risky commands to run in agent sessions on machines that have real credentials exported globally.

---

_Verified: 2026-09-12_
_Verifier: Claude (gsd-verifier)_
