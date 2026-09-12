---
phase: 01-isolated-rai-environment
plan: 05
subsystem: experiments/wojtek_rai_v1
tags: [rai, isolation, two-machine, aarch64, cyclonedds, dds, verification]

requires:
  - phase: 01-isolated-rai-environment (plan 01)
    provides: "run.sh install/test/agent-topics/up targets whose literal output this plan records"
  - phase: 01-isolated-rai-environment (plan 04)
    provides: "the model-free/isolation/pinning guard suite whose 65 tests are what run.sh test runs on both machines"
provides:
  - "experiments/wojtek_rai_v1/docs/VERIFICATION.md -- literal two-machine (x86-64 laptop, aarch64 remote GPU dev box) record of run.sh install/test/agent-topics, discharging FOUND-07"
  - "A documented, host-specific DDS finding: the repository's default CycloneDDS profile relies on local multicast loopback, which is broken on the aarch64 dev box's network interface; ROS_LOCALHOST_ONLY=1 (discovery+shutdown) and the repo's own cyclonedds_link.xml (shutdown only, on this host) are both verified workarounds"
affects:
  - "Phase 2 onward -- any future dev-box run of this experiment's sim/agent-topics targets should set ROS_LOCALHOST_ONLY=1 or an equivalent local-discovery setting rather than relying on the default profile"
  - "ros/docker -- the DDS profile-selection finding is a candidate follow-up for whoever owns the base container configuration; not fixed inside this experiment"

actuals:
  tokens: 6950
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Two-machine verification recorded as literal command output tied to a single commit SHA, per machine, rather than summarized -- established in this plan for any future architecture-parity claim in this experiment"
    - "Private-infrastructure redaction: pasted terminal output is checked line-by-line before being committed, with every elision marked inline as [REDACTED: <what>], and role-only naming (\"the aarch64 remote GPU dev box\") substituted for any host identity"

key-files:
  created: []
  modified:
    - experiments/wojtek_rai_v1/docs/VERIFICATION.md

key-decisions:
  - "Task 2 checkpoint (human-action) resolved by operator authorization: the operator authorized the executing agent to drive the aarch64 dev box directly over the operator's own SSH access for this one checkpoint, rather than running commands by hand and pasting output back. The SSH alias, hostname and login never entered the repository or the agent's context; only already-redacted driver output was read back."
  - "FOUND-07 is reported as discharged, with a caveat, rather than not-discharged: install succeeded literally on both machines; test and agent-topics succeeded literally on the x86-64 laptop but needed a non-default DDS discovery setting (ROS_LOCALHOST_ONLY=1, or the repo's own unicast profile for test) to succeed on the aarch64 dev box. Both the literal default-profile failures and the passing non-default-profile runs are recorded in docs/VERIFICATION.md rather than only the passing ones, per the plan's prohibition against claiming two-machine support from an incomplete record."

requirements-completed: [FOUND-07]

coverage:
  - id: D1
    description: "run.sh install, run.sh test, and run.sh agent-topics each produce a passing, literal output on the x86-64 laptop, recorded in docs/VERIFICATION.md"
    requirement: "FOUND-07"
    verification:
      - kind: manual_procedural
        ref: "experiments/wojtek_rai_v1/docs/VERIFICATION.md § x86-64 laptop"
        status: pass
    human_judgment: false
  - id: D2
    description: "The same three commands run on the aarch64 remote GPU dev box, from a git-fetched commit (not an rsynced tree), with literal output and exit status recorded, including the default-DDS-profile hangs discovered along the way"
    requirement: "FOUND-07"
    verification:
      - kind: manual_procedural
        ref: "experiments/wojtek_rai_v1/docs/VERIFICATION.md § aarch64 remote GPU dev box"
        status: pass
    human_judgment: true
    rationale: "The dev-box run required a human-authorized checkpoint (SSH access to a private machine) and a human read-through of the redacted output for private-infrastructure leakage before this agent used it -- both are judgment calls no automated check in this repository can substitute for."
  - id: D3
    description: "No private-infrastructure identifier (hostname, address, login, alias, personal email) appears anywhere in docs/VERIFICATION.md"
    requirement: "FOUND-07"
    verification:
      - kind: other
        ref: "grep -cE '([0-9]{1,3}\\.){3}[0-9]{1,3}' experiments/wojtek_rai_v1/docs/VERIFICATION.md -> 0; grep -cE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}' experiments/wojtek_rai_v1/docs/VERIFICATION.md -> 0"
        status: pass
    human_judgment: false

duration: "~45min (this continuation; Task 1 was a separate session)"
completed: "2026-09-12"
status: complete
---

# Phase 01 Plan 05: Two-Machine Verification Summary

**docs/VERIFICATION.md now records `run.sh install`, `run.sh test`, and `run.sh agent-topics`
succeeding on both the x86-64 laptop and the aarch64 remote GPU dev box from the same commit,
with a documented host-specific DDS multicast-loopback finding rather than a silent pass.**

## Performance

- **Duration:** ~45 min (this continuation session; Task 1 ran in an earlier session)
- **Completed:** 2026-09-12
- **Tasks:** 2 (Task 1: x86-64 record + document scaffold; Task 2: aarch64 dev-box record + findings)
- **Files modified:** 1 (`experiments/wojtek_rai_v1/docs/VERIFICATION.md`, across two commits)

## Accomplishments

- `docs/VERIFICATION.md` carries a complete, literal, two-machine record for FOUND-07: architecture,
  container image identity, and the three commands' exit statuses and output, tied to commit
  `3693ae69a4c95a1442f37edc589916e32d4e1076` on both machines.
- Diagnosed and documented a real cross-machine DDS discovery defect on the aarch64 dev box: the
  repository's default CycloneDDS profile relies on local multicast loopback, which does not
  deliver on that host's network interface, hanging any `rclpy`/`ros2` process on shutdown and
  preventing same-host node discovery. Three workarounds were independently verified
  (`ROS_LOCALHOST_ONLY=1`, `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`, and this repository's own
  `cyclonedds_link.xml` unicast profile for the shutdown half only).
- Confirmed no arm64-specific failure exists anywhere in the RAI stack itself: the container image
  built cleanly for `linux/arm64`, all 132 dependencies resolved as aarch64 wheels from the
  committed `uv.lock` with zero source builds, and all 65 tests and the full topic-discovery set
  passed once the DDS setting was addressed.
- FOUND-07 is reported as discharged with the DDS caveat recorded plainly, not concealed, per the
  plan's prohibition against claiming two-machine support from an incomplete or rosy record.

## Task Commits

Each task was committed atomically (Task 1 in an earlier session):

1. **Task 1: Record the x86-64 laptop run and seed the verification document** - `a9b5d84` (docs)
2. **Task 2: Run the same three commands on the aarch64 remote GPU dev box and record the result** - `9bad565` (docs)

_No separate plan-metadata commit issued yet -- this SUMMARY and the STATE/ROADMAP/REQUIREMENTS
updates are committed together as the plan's closing commit, per this repository's `commit_docs`
configuration._

## Files Created/Modified

- `experiments/wojtek_rai_v1/docs/VERIFICATION.md` - Two-machine literal verification record;
  Task 1 added the document skeleton and the x86-64 section, Task 2 appended the aarch64 section
  and the Findings section.

## Decisions Made

- **Checkpoint resolution (Task 2, human-action):** the operator authorized the executing agent to
  drive the aarch64 dev box directly over the operator's own SSH access for this one checkpoint,
  rather than the operator running commands by hand and pasting output back. This kept the SSH
  alias, hostname, and login out of both the repository and this agent's context at every point --
  the agent only ever saw the driver's own already-redacted output, with each redaction marked
  `[REDACTED: <what>]` inline, matching this document's existing redaction contract.
- **FOUND-07 marked discharged, with a caveat, rather than not-discharged:** `install` succeeded
  literally (unmodified `run.sh install`) on both architectures. `test` and `agent-topics` succeeded
  literally on the x86-64 laptop, but on the aarch64 dev box needed a non-default DDS discovery
  setting to pass -- the literal default-profile attempts are recorded as hangs (exit `137` and
  `124`), and the passing non-default-profile attempts are recorded immediately alongside them, so
  the document does not overclaim or underclaim what was actually observed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Seeded a policy into the dev box's local store to unblock the sim launch**
- **Found during:** Task 2, first `agent-topics` attempt
- **Issue:** A completely fresh dev-box clone has no policy reference resolvable -- `wojtek_bringup
  robot --sim` requires one, and resolving the repository's pinned default needs both the keeper
  organization's Hugging Face name (kept out of the repo, read from `.env`) and either a Hugging
  Face login or a pre-seeded `ros/policies/` store. The sim launch failed immediately with
  `empty policy reference`.
- **Fix:** With the operator's explicit approval, the orchestrator seeded the pinned policy
  (revision `553795b13001cc1f519a4abc0235f275095129f8`) into the dev box's gitignored
  `ros/policies/` store from the laptop, then relaunched the sim with an explicit `--policy
  <store dir>` argument -- the same seed-then-reference approach `ros/deploy.sh` already uses for
  the physical robot.
- **Files modified:** None in this repository -- the seeded policy lives only in the dev box's
  gitignored local store, exactly as `ros/deploy.sh`'s pattern intends.
- **Verification:** The sim's own processes (controller_manager, robot_state_publisher,
  wojtek_policy, etc.) subsequently started and reached the "Configuring/Activating controllers"
  stage recorded in `docs/VERIFICATION.md`'s Attempt B/D output.
- **Committed in:** `9bad565` (documented as Findings item 4; not itself a code change)

**2. [Rule 3 - Blocking] Injected `ROS_LOCALHOST_ONLY=1` via `docker exec` because `run.sh` has no
way to pass it through**
- **Found during:** Task 2, after Attempts A-C failed to produce local ROS 2 discovery
- **Issue:** `run.sh`'s `agent-topics` and `up` targets exec fixed commands inside the container
  with no mechanism to inject an environment variable per invocation, but the fix for this host's
  DDS discovery failure (Findings item 1/2) is precisely such a variable.
- **Fix:** The orchestrator ran the identical sourcing sequence and Python invocation `run.sh`
  itself execs (`.venv/bin/python -m wojtek_rai.topics`), via `docker exec -i -e
  ROS_LOCALHOST_ONLY=1 wojtek_robot ...` directly, rather than modifying `run.sh` to add a new
  flag -- keeping this plan's file scope to `docs/VERIFICATION.md` only, per its frontmatter.
- **Files modified:** None -- this was an invocation-time workaround, not a code change. Whether
  `run.sh` should gain a first-class way to pass discovery-related environment variables is left as
  the Findings-item-3 follow-up for whoever owns `ros/docker`, not addressed in this plan.
- **Verification:** The resulting `agent-topics` run exited `0` with the full 36-topic set recorded
  in `docs/VERIFICATION.md`'s Attempt D.
- **Committed in:** `9bad565` (documented as Findings item 2/3; not itself a code change)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking, both orchestrator-side workarounds
documented rather than code changes)
**Impact on plan:** Neither deviation touched code or expanded this plan's file scope beyond
`docs/VERIFICATION.md`; both were necessary to reach a passing dev-box run at all, and both are
recorded as findings/blockers rather than silently absorbed.

## Issues Encountered

- **Blocker (not fixed inside this experiment, per plan scope):** the aarch64 dev box's network
  interface does not deliver local multicast loopback packets, which the repository's default
  CycloneDDS profile (`ros/docker/config/cyclonedds.xml`) depends on for both same-host node
  discovery and clean process shutdown. Every `rclpy`/`ros2` process launched under that default
  profile on this host hung on shutdown; two of the three verification commands additionally
  require same-host discovery, so they failed outright until a non-default setting
  (`ROS_LOCALHOST_ONLY=1`, or this repo's own `cyclonedds_link.xml` for the shutdown half only) was
  applied. Full diagnostic detail is in `docs/VERIFICATION.md`'s Findings items 1-2. This is raised
  here as a blocker for whoever owns `ros/docker`'s base container/network configuration -- see
  Findings item 3 for the suggested follow-up (make the DDS profile selectable per machine).

## User Setup Required

None - no external service configuration required. The dev-box checkpoint (Task 2) was a one-time
human-action authorization already exercised during this plan's execution, not a standing setup
step for future runs.

## Next Phase Readiness

- FOUND-07 is discharged: `docs/VERIFICATION.md` proves the experiment's install, test, and
  topic-discovery targets work on both an x86-64 laptop and an aarch64 GPU machine, which is the
  evidence Phase 2 relies on before building an agent on top of this environment.
- **Carry-forward note for Phase 2 and beyond:** any future work that launches this experiment's
  simulation or runs `agent-topics` on a machine whose default CycloneDDS profile does not support
  local multicast loopback should set `ROS_LOCALHOST_ONLY=1` (or
  `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`) rather than assuming the default profile works
  unmodified -- this is not yet fixed in `ros/docker`, only documented here.
- No blocker prevents Phase 1 from being considered complete; the DDS finding is a documented
  cross-cutting note for `ros/docker`'s owner, not a gap in this experiment's own scope.

---
*Phase: 01-isolated-rai-environment*
*Completed: 2026-09-12*
