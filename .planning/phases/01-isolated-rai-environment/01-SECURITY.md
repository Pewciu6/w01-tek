---
phase: 01
slug: isolated-rai-environment
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-09-12
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Public repository ↔ private infrastructure | Everything tracked is public; hostnames, addresses, logins, SSH aliases, the keeper HF org and credential values must never cross into it | identity strings, credential values (high) |
| Host `.env` ↔ `wojtek_robot` container | `run.sh` sources the gitignored `.env` and forwards credential **names** via `docker exec -e NAME`; values never appear on a command line or in output | vendor / tracing API keys (high) |
| `experiments/wojtek_rai_v1/` ↔ `ros/`, `training/` | Experiment code must never be importable from, written under, or shipped by production paths (`ros/deploy.sh` rsyncs `ros/src/` only) | Python imports, colcon overlays, rsync sources (high) |
| PyPI / GitHub ↔ experiment venv and overlay | `rai-core`, `rai-whoami`, their LangChain/LangGraph transitives and `rai_interfaces` enter from the network at install/build time | third-party code (medium–high) |
| Laptop ↔ aarch64 remote GPU dev box | Verification runs over the operator's own SSH alias; captured output is redacted before it is recorded | shell output, container logs (high for identity) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Tampering | RAI's unconstrained langchain/langgraph transitives | high | mitigate | `uv.lock` tracked; `run.sh` uses `uv sync --frozen` once the lock exists (01-01) | closed |
| T-01-02 | Elevation of Privilege | Experiment reachable by `ros/deploy.sh` | high | mitigate | Nothing under `ros/src`; overlay built into `experiments/wojtek_rai_v1/ros_ws/`; branch diff touches no file under `ros/` or `training/` | closed |
| T-01-03 | Tampering | `run.sh` apt-get / docker exec in the shared privileged container | medium | mitigate | Only the named `wojtek_robot` container, never `docker run`; `UV_INSTALL_DIR`/`UV_CACHE_DIR` inside the experiment; `ros/docker/` unmodified | closed |
| T-01-04 | Information Disclosure | `run.sh` echoing environment values | medium | mitigate | No `set -x`; credentials forwarded name-only (`-e NAME`) | closed |
| T-01-05 | Tampering | `uv` standalone installer fetched at install time | medium | mitigate | Existence guard; installed into gitignored `.tools/`; never baked into the image | closed |
| T-01-06 | Denial of Service | RAI process joining the live DDS domain | low | accept | Read-only discovery on a simulation-only graph (`topics.py`: connector → `get_topics_names_and_types()` → shutdown; no publisher/service/action) | closed (accepted) |
| T-01-07 | Tampering | `vcs import` of `rai_interfaces` from a moving branch | high | mitigate | `.repos` pins a 40-char SHA; `test_repos_pin.py` rejects branch names | closed |
| T-01-08 | Elevation of Privilege | Built `rai_interfaces` landing under `ros/src/` | high | mitigate | `colcon --base-paths ros_ws` + explicit build/install/log bases; `test_repos_pin.py` asserts nothing under `ros/src` | closed |
| T-01-09 | Tampering | `rosdep install -y` pulling packages into the shared container | medium | mitigate | `--from-paths ros_ws/src --ignore-src` scoping | closed |
| T-01-10 | Repudiation | Built commit not recoverable later | medium | mitigate | Resolved SHA committed in `.repos` and repeated in 01-02-SUMMARY.md | closed |
| T-01-11 | Information Disclosure | Credential committed into `config.toml` / `.env.example` | high | mitigate | `config.toml` has no credential field; `test_no_secrets_in_config.py` secret-shape scan (broadened by WR-03, `381a520`) over every tracked file, fail-first proven | closed |
| T-01-12 | Information Disclosure | Private infrastructure identity in a tracked file | high | mitigate | `PRIVATE_IDENTITY_RE` scan in `test_no_secrets_in_config.py`, fail-first proven; auditor re-ran both regexes over all tracked files: zero hits | closed |
| T-01-13 | Information Disclosure | `run.sh` echoing a credential value into a terminal/CI log | high | mitigate | Name-only forwarding (`run.sh` `CRED_ENV_ARGS`); no shell trace; **grep-asserted** by `tests/test_build_target.py::test_run_sh_never_enables_shell_trace` (`21d01f0`, fail-first proven) | closed |
| T-01-14 | Information Disclosure | Prompts/completions leaving via a tracing backend | low | accept | `use_langfuse = false`, `use_langsmith = false` in `config.toml`; no tracing host committed; enabling tracing is later work (FOUND-05) | closed (accepted) |
| T-01-15 | Spoofing | Unknown vendor string silently selecting no credentials | low | mitigate | `required_env_vars` raises `ValueError` naming the vendor; covered by `test_config_loading.py` | closed |
| T-01-16 | Elevation of Privilege | Production package importing the experiment | high | mitigate | `test_isolation_boundary.py` scans `ros/`, `training/`, root scripts and statically parses `ros/deploy.sh` rsync sources; repo-root mount narrowed to `:ro` (WR-01, `9672446`) | closed |
| T-01-17 | Tampering | Guard test passing vacuously | high | mitigate | Every scan asserts non-empty discovery; `MIN_EXPECTED_TEST_FILES`; unconditional-skip check; fail-first controls execute in the suite | closed |
| T-01-18 | Tampering | Silent dependency drift after re-resolve | medium | mitigate | `test_pinned_versions.py` exact `==` pins and resolved lockfile entries for the transitives | closed |
| T-01-19 | Spoofing | Compose override mounting the wrong host directory | medium | mitigate | `test_compose_override.py` resolves the source against the base compose directory and compares with `os.path.samefile`; fail-first control | closed |
| T-01-20 | Information Disclosure | README naming the dev box's host/address/login/alias | high | mitigate | README names the machine by role only; covered by the tracked-file identity scan | closed |
| T-01-21 | Information Disclosure | Host/address/login pasted into `docs/VERIFICATION.md` | high | mitigate | Redaction rule stated in the doc; inline `[REDACTED: …]` markers; version string elided where digits matched the address shape; both acceptance greps return 0 | closed |
| T-01-22 | Repudiation | Evidence recorded against no identifiable commit | medium | mitigate | Commit `3693ae6…` recorded; dev-box run from a `git fetch` + `checkout` clone with clean porcelain | closed |
| T-01-23 | Tampering | Two-machine support claimed from one machine's run | high | mitigate | One section per machine; default-profile hangs recorded verbatim (exit 137 / 124) beside the passing `ROS_LOCALHOST_ONLY=1` runs; verdict states the DDS caveat | closed |
| T-01-24 | Elevation of Privilege | Standing authorization stretched to training / deployment / robot | high | mitigate | Limits stated in the doc; only install, test, agent-topics ran on the dev box; the one extension (seeding the gitignored policy store) was operator-approved and recorded; no training job, no deployment, no hardware | closed |
| T-01-SC | Tampering | First PyPI install of `rai-core` / `rai-whoami` | high | mitigate | `blocking-human` package-legitimacy gate; approval of 2.12.0 / 0.0.5 against PyPI/GitHub recorded in 01-01-SUMMARY.md before the first `uv sync` | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01-01 | T-01-06 | Phase 1's ROS surface is read-only topic discovery on a simulation-only graph; no publisher, service client or action goal exists, so the 50 Hz policy loop cannot be disturbed. Revisit when Phase 2 adds a `cmd_vel` publisher. | plan 01-01 threat model (operator-approved plan) | 2026-09-07 |
| AR-01-02 | T-01-14 | Tracing ships disabled (upstream default and project requirement); no tracing host is committed. Enabling it is a separate, later decision (FOUND-05). | plan 01-03 threat model (operator-approved plan) | 2026-09-07 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-12 | 25 | 24 | 1 (T-01-13: mitigation not grep-asserted) | gsd-security-auditor (opus) |
| 2026-09-12 | 25 | 25 | 0 | orchestrator — added `test_run_sh_never_enables_shell_trace` (`21d01f0`), suite 66 passed |

Context consumed by the audit: 01-REVIEW.md / 01-REVIEW-FIX.md (CR-01 `49d9dd1`, WR-01 `9672446`, WR-03 `381a520`, WR-02 `8a9398e`, all fixed), 01-VERIFICATION.md (passed).

Out-of-band note (not a register item): during phase verification an agent's diagnostic `env | grep` echoed a real `OPENAI_API_KEY` from the operator's global shell environment into that agent's transcript. Nothing entered the repository. The operator was advised to rotate the key and agents in this project are instructed not to dump the environment.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-12
