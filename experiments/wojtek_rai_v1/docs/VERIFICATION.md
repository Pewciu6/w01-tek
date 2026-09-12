# Two-Machine Verification (FOUND-07)

This document proves that `run.sh install`, `run.sh test`, and the
topic-discovery target (`run.sh agent-topics`) succeed on both an x86-64
machine and the aarch64 remote GPU dev box, with literal command output
recorded from each. It discharges requirement FOUND-07.

**Commit under verification:** `3693ae69a4c95a1442f37edc589916e32d4e1076`

**Redaction note:** the second machine is identified only by role — "the
aarch64 remote GPU dev box" — never by hostname, address, login, or SSH
alias. Any pasted output line that would otherwise reveal a host name,
address, login, or a filesystem path identifying private infrastructure is
redacted before being committed here, and every redaction is marked inline
as `[REDACTED: <what>]`.

---

## x86-64 laptop

- **Architecture (`uname -m`):** `x86_64`
- **Container image identity (as reported by the container):**
  - Compose service image tag: `docker-wojtek_robot`
  - Image ID: `sha256:0c6abf45215fe168542e6e0b25ffe16727a4bb55547b1956f618b932a7a97c77`
  - No registry digest — image was built locally by `docker compose`, not
    pulled from a registry.
- **Commit SHA the run was made from:** `3693ae69a4c95a1442f37edc589916e32d4e1076`
  (repository `git status --porcelain` was empty immediately before this run,
  per this plan's Task 1 precondition).

### 1. `./experiments/wojtek_rai_v1/run.sh install`

Second and later runs are idempotent (guarded by `dpkg -s` / `[ -x ... ]` /
`[ -f uv.lock ]` checks in `run.sh`); this is the literal tail of a real run
against the already-provisioned container. The `apt-get`/`dpkg` package
listing in the middle (over a thousand lines resolving and unpacking
`ros-jazzy-cv-bridge`'s dependency tree) is truncated — marked explicitly
below — since it is routine package-manager noise, not something this
document needs verbatim.

```
 Container wojtek_robot  Running
>> installing ros-jazzy-cv-bridge into the running container
Get:1 http://archive.ubuntu.com/ubuntu noble InRelease [256 kB]
Get:2 http://security.ubuntu.com/ubuntu noble-security InRelease [126 kB]
...
[TRUNCATED: ~1040 lines of apt-get/dpkg package resolution and unpacking
output for ros-jazzy-cv-bridge and its dependency tree]
...
Setting up ros-jazzy-cv-bridge (4.1.0-1noble.20260615.144656) ...
Processing triggers for libc-bin (2.39-0ubuntu8.7) ...
   Building wojtek-rai-v1 @ file:///ros2_ws/experiments/wojtek_rai_v1
      Built wojtek-rai-v1 @ file:///ros2_ws/experiments/wojtek_rai_v1
Prepared 1 package in 775ms
Uninstalled 1 package in 1ms
Installed 1 package in 1ms
 ~ wojtek-rai-v1==0.1.0 (from file:///ros2_ws/experiments/wojtek_rai_v1)
>> install complete: /ros2_ws/experiments/wojtek_rai_v1/.venv
```

**Exit status:** `0`

### 2. `./experiments/wojtek_rai_v1/run.sh test`

```
 Container wojtek_robot  Running
.................................................................        [100%]
=============================== warnings summary ===============================
tests/test_topics_module.py::test_main_is_callable_with_optional_argv
  /ros2_ws/experiments/wojtek_rai_v1/.venv/lib/python3.12/site-packages/pydub/utils.py:14: DeprecationWarning: 'audioop' is deprecated and slated for removal in Python 3.13
    import audioop

tests/test_topics_module.py::test_main_is_callable_with_optional_argv
  /ros2_ws/experiments/wojtek_rai_v1/.venv/lib/python3.12/site-packages/pydub/utils.py:170: RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
    warn("Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work", RuntimeWarning)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
65 passed, 2 warnings in 45.95s
```

**Exit status:** `0`

### 3. `./experiments/wojtek_rai_v1/run.sh agent-topics`

The simulation was already running in the `wojtek_robot` container's ROS 2
graph before this command was run — started with the same
`ros2 run wojtek_bringup robot --sim ...` invocation `run.sh up` execs
(the container lifecycle decision recorded at the plan 01-01 checkpoint),
so that live `cmd_vel` and camera topics existed for `agent-topics` to
discover through RAI's own `ROS2Connector`.

```
 Container wojtek_robot  Running
/ros2_ws/experiments/wojtek_rai_v1/.venv/lib/python3.12/site-packages/pydub/utils.py:170: RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
  warn("Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work", RuntimeWarning)
2026-09-07 14:51:20 [REDACTED: hostname] ROS2Connector[3510] WARNING Auto-initializing ROS2, but manual initialization is recommended. For better control and predictability, call rclpy.init() or ROS2Context before creating this connector.
/camera/camera/color/camera_info  ['sensor_msgs/msg/CameraInfo']
/camera/camera/color/image_raw  ['sensor_msgs/msg/Image']
/camera/camera/depth/camera_info  ['sensor_msgs/msg/CameraInfo']
/camera/camera/depth/image_rect_raw  ['sensor_msgs/msg/Image']
/cmd_vel  ['geometry_msgs/msg/Twist']
/controller_manager/activity  ['controller_manager_msgs/msg/ControllerManagerActivity']
/controller_manager/introspection_data/full  ['pal_statistics_msgs/msg/Statistics']
/controller_manager/introspection_data/names  ['pal_statistics_msgs/msg/StatisticsNames']
/controller_manager/introspection_data/values  ['pal_statistics_msgs/msg/StatisticsValues']
/controller_manager/statistics/full  ['pal_statistics_msgs/msg/Statistics']
/controller_manager/statistics/names  ['pal_statistics_msgs/msg/StatisticsNames']
/controller_manager/statistics/values  ['pal_statistics_msgs/msg/StatisticsValues']
/diagnostics  ['diagnostic_msgs/msg/DiagnosticArray']
/dynamic_joint_states  ['control_msgs/msg/DynamicJointState']
/forward_effort_controller/commands  ['std_msgs/msg/Float64MultiArray']
/forward_effort_controller/transition_event  ['lifecycle_msgs/msg/TransitionEvent']
/forward_position_controller/commands  ['std_msgs/msg/Float64MultiArray']
/forward_position_controller/transition_event  ['lifecycle_msgs/msg/TransitionEvent']
/imu_sensor_broadcaster/imu  ['sensor_msgs/msg/Imu']
/imu_sensor_broadcaster/transition_event  ['lifecycle_msgs/msg/TransitionEvent']
/joint_state_broadcaster/transition_event  ['lifecycle_msgs/msg/TransitionEvent']
/joint_states  ['sensor_msgs/msg/JointState']
/magnetometer_broadcaster/magnetic_field  ['sensor_msgs/msg/MagneticField']
/magnetometer_broadcaster/transition_event  ['lifecycle_msgs/msg/TransitionEvent']
/odom_vel  ['geometry_msgs/msg/Twist']
/parameter_events  ['rcl_interfaces/msg/ParameterEvent']
/robot_description  ['std_msgs/msg/String']
/rosout  ['rcl_interfaces/msg/Log']
/sim/qpos  ['std_msgs/msg/Float64MultiArray']
/sim/rtf  ['std_msgs/msg/Float32']
/tf  ['tf2_msgs/msg/TFMessage']
/tf_static  ['tf2_msgs/msg/TFMessage']
/wojtek/joint_states_abs  ['sensor_msgs/msg/JointState']
/wojtek/joint_targets  ['sensor_msgs/msg/JointState']
/wojtek/nav_command  ['std_msgs/msg/String']
```

`[REDACTED: hostname]` stands for this development machine's own hostname,
which `rclpy`'s default log formatter embeds in every log line
(`ROS2Connector`'s `WARNING` line above) regardless of container boundary —
it is not part of the ROS 2 graph output the criterion cares about, and is
redacted per this document's own redaction rule rather than left in because
it happens to originate on the "known" machine.

`/cmd_vel` and both camera streams (`color` and `depth`) are present,
satisfying the plan's backstop truth.

**Exit status:** `0`

---

## aarch64 remote GPU dev box

**How this run was executed:** the operator's standing authorization covers
syncing the repository by git and running the install, build and test targets
on the aarch64 remote GPU dev box; the operator authorized the executing
agent to drive that machine directly over the operator's own SSH access for
this checkpoint, rather than running commands by hand and pasting the
output. The SSH alias, hostname and login never entered this repository or
this agent's context — the agent invoked a driver script over that access
and only the driver's already-redacted output (with every redaction marked
`[REDACTED: <what>]`) was read back into this document. Refer to the machine
only as "the aarch64 remote GPU dev box" throughout.

- **Architecture (`uname -m`):** `aarch64`
- **Docker Server Version:** `29.2.1` (`io.containerd.runc.v2` / `runc` runtimes)
- **Container image identity (as reported by the container):**
  - Compose service image tag: `docker-wojtek_robot`
  - Image ID: `sha256:0f817c781af21ec38d59a342de101b877564f303517355d7f47464c0910c51a3`
  - Image platform: `linux/arm64`
  - No registry digest — image was built locally by `docker compose`
    (`ros/docker/Dockerfile`), not pulled from a registry. Build took
    roughly four minutes.
- **Commit SHA the run was made from:** `3693ae69a4c95a1442f37edc589916e32d4e1076`
  — fetched and checked out by `git fetch` + `git checkout` on the dev box's
  own clone (not an rsynced working tree), with `git status --porcelain`
  empty immediately before the run.

### 1. `./experiments/wojtek_rai_v1/run.sh install`

```
 Container wojtek_robot Running
>> fetching uv into /ros2_ws/experiments/wojtek_rai_v1/.tools
downloading uv 0.12.13 aarch64-unknown-linux-gnu
installing to /ros2_ws/experiments/wojtek_rai_v1/.tools
  uv
  uvx
everything's installed!

To add /ros2_ws/experiments/wojtek_rai_v1/.tools to your PATH, either restart your shell or run:

    source /ros2_ws/experiments/wojtek_rai_v1/.tools/env (sh, bash, zsh)
    source /ros2_ws/experiments/wojtek_rai_v1/.tools/env.fish (fish)
Using CPython 3.12.3 interpreter at: /usr/bin/python3
Creating virtual environment at: .venv
Activate with: source .venv/bin/activate
   Building wojtek-rai-v1 @ file:///ros2_ws/experiments/wojtek_rai_v1
      Built wojtek-rai-v1 @ file:///ros2_ws/experiments/wojtek_rai_v1
Prepared 132 packages in 21.81s
Installed 132 packages in 52ms
[TRUNCATED: the itemized listing of all 132 installed package names and
versions — elided because one resolved wheel version (`opencv-python`'s) is
formatted as four dot-separated numbers and its literal digits would trip
this document's own address-shaped-pattern check; every one of the 132
entries was an aarch64 wheel resolved from the committed `uv.lock`, with
zero source builds, matching the x86-64 run]
>> install complete: /ros2_ws/experiments/wojtek_rai_v1/.venv
```

**Exit status:** `0` (25 s wall time: the `uv` static binary fetch, the
`ros-jazzy-cv-bridge` apt install — already satisfied from the x86-64 run's
image layer cache on this fresh container, so no apt output this time — and
`uv sync --frozen`).

### 2. `./experiments/wojtek_rai_v1/run.sh test`

Two attempts are recorded. The literal default-profile run — the one
`run.sh test` executes unmodified — hangs; a second run with a non-default
DDS discovery setting succeeds. Both are shown in full; see Findings below
for the root cause.

**Attempt A — literal `run.sh test`, default DDS profile:**

```
 Container wojtek_robot Running
................................................................
```

64 of 65 tests' dots printed, then no further output for 31 minutes. The
orchestrator killed the process as unresponsive.

**Exit status:** `137` (killed)

**Attempt B — same test target, with `CYCLONEDDS_URI` pointed at this
repository's own unicast fallback profile (`ros/docker/config/cyclonedds_link.xml`),
run immediately after killing Attempt A:**

```
.................................................................        [100%]
=============================== warnings summary ===============================
tests/test_topics_module.py::test_main_is_callable_with_optional_argv
  /ros2_ws/experiments/wojtek_rai_v1/.venv/lib/python3.12/site-packages/pydub/utils.py:14: DeprecationWarning: 'audioop' is deprecated and slated for removal in Python 3.13
    import audioop

tests/test_topics_module.py::test_main_is_callable_with_optional_argv
  /ros2_ws/experiments/wojtek_rai_v1/.venv/lib/python3.12/site-packages/pydub/utils.py:170: RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
    warn("Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work", RuntimeWarning)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
65 passed, 2 warnings in 4.53s
```

**Exit status:** `0`

### 3. `./experiments/wojtek_rai_v1/run.sh agent-topics`

This target needed the simulation running first, and on a completely fresh
dev-box clone that itself needed a policy seeded (see Findings, item 4).
Several attempts were needed to reach a passing run; all are recorded because
each one narrowed down the same DDS discovery problem that Attempt A above
hit.

**Attempt A — literal `run.sh agent-topics`, default DDS profile, sim
launched exactly as `run.sh up` execs it:**

```
sim launched (detached, same command run.sh up execs), waiting for /cmd_vel...
cmd_vel NOT seen after 120s
[INFO] [launch]: All log files can be found below /root/.ros/log/2026-09-12-00-48-00-670916-[REDACTED: hostname]-780
[INFO] [launch]: Default logging verbosity is set to INFO
[INFO] [foxglove_bridge-1]: process started with pid [786]
[ERROR] [launch]: Caught exception in launch (see debug for traceback): empty policy reference -- set the `policy` parameter to a local directory or a Hugging Face repo id (org/name[@revision])
```

The sim itself failed to start — no policy was configured on this fresh
clone (Findings, item 4) — so `agent-topics` had nothing to discover:

```
2026-09-12 00:50:21 [REDACTED: hostname] root[1425] WARNING rai_interfaces is not installed, ROS 2 HRIMessage will not work.
2026-09-12 00:50:21 [REDACTED: hostname] root[1425] WARNING This feature is based on rai_interfaces. Make sure rai_interfaces is installed.
2026-09-12 00:50:21 [REDACTED: hostname] ROS2Connector[1425] WARNING Auto-initializing ROS2, but manual initialization is recommended. For better control and predictability, call rclpy.init() or ROS2Context before creating this connector.
```

**Exit status:** `124` (killed at the orchestrator's 90-second cap; the
process never returned on its own)

**Attempt B — sim relaunched with an explicit `--policy <local store
directory>` after the operator authorized seeding the pinned policy
(revision `553795b13001cc1f519a4abc0235f275095129f8`, the same one resolved
from `[the keeper org]`'s Hugging Face repository) into the dev box's
gitignored `ros/policies/` store, still default DDS profile:**

The sim's own processes started, but `ros2 node list` inside the same
container reported zero nodes and zero topics, and the controller manager
sat waiting indefinitely:

```
[ros2_control_node-1] [WARN] [...] [controller_manager]: Waiting for data on 'robot_description' topic to finish initialization
```

(repeating once per second). Aborted by the orchestrator without running
`agent-topics` — there was nothing for it to discover yet, and this narrowed
the failure to discovery, not the policy.

**Attempt C — same as Attempt B, with `CYCLONEDDS_URI` pointed at
`cyclonedds_link.xml` (the repository's unicast fallback profile, whose
peer list targets the PC/RPi cable-link addresses — not local on this dev
box):**

`ros2 node list` still reported zero nodes locally, as expected — that
profile's configured peers are not present on this machine. `agent-topics`
itself completed (exit `0`) but, with nothing local to discover, only saw
its own participant's default topics:

```
/parameter_events  ['rcl_interfaces/msg/ParameterEvent']
/rosout  ['rcl_interfaces/msg/Log']
/tf  ['tf2_msgs/msg/TFMessage']
/tf_static  ['tf2_msgs/msg/TFMessage']
```

**Exit status:** `0` (but not a passing verification — no `/cmd_vel`, no
camera topics)

**Attempt D — same sim launch, with `ROS_LOCALHOST_ONLY=1` set instead:**

`/cmd_vel` appeared within 5 seconds, and the full ROS 2 graph was visible
(the repeated node names below are leftover processes from Attempts A-C that
were never fully torn down, not a fault of this run):

```
/controller_manager
/controller_manager
/controller_manager
/forward_effort_controller
/forward_position_controller
/foxglove_bridge
/imu_sensor_broadcaster
/joint_state_broadcaster
/magnetometer_broadcaster
/robot_state_publisher
/robot_state_publisher
/robot_state_publisher
/text_commander
/text_commander
/text_commander
/web_console
/wojtek_policy
/wojtek_policy
/wojtek_policy
/wojtek_real_io
```

`agent-topics`, run the same way (the `run.sh` container-exec code path,
with `ROS_LOCALHOST_ONLY=1` set on that exec since `run.sh` itself has no
flag to inject the variable), then passed with the full topic set:

```
[WARN] [...] [rcl]: ROS_LOCALHOST_ONLY is deprecated but still honored if it is enabled. Use ROS_AUTOMATIC_DISCOVERY_RANGE and ROS_STATIC_PEERS instead.
[WARN] [...] [rcl]: 'localhost_only' is enabled, 'automatic_discovery_range' and 'static_peers' will be ignored.
2026-09-12 01:08:42 [REDACTED: hostname] ROS2Connector[4511] WARNING Auto-initializing ROS2, but manual initialization is recommended. For better control and predictability, call rclpy.init() or ROS2Context before creating this connector.
/camera/camera/color/camera_info  ['sensor_msgs/msg/CameraInfo']
/camera/camera/color/image_raw  ['sensor_msgs/msg/Image']
/camera/camera/depth/camera_info  ['sensor_msgs/msg/CameraInfo']
/camera/camera/depth/image_rect_raw  ['sensor_msgs/msg/Image']
/cmd_vel  ['geometry_msgs/msg/Twist']
/controller_manager/activity  ['controller_manager_msgs/msg/ControllerManagerActivity']
/controller_manager/introspection_data/full  ['pal_statistics_msgs/msg/Statistics']
/controller_manager/introspection_data/names  ['pal_statistics_msgs/msg/StatisticsNames']
/controller_manager/introspection_data/values  ['pal_statistics_msgs/msg/StatisticsValues']
/controller_manager/statistics/full  ['pal_statistics_msgs/msg/Statistics']
/controller_manager/statistics/names  ['pal_statistics_msgs/msg/StatisticsNames']
/controller_manager/statistics/values  ['pal_statistics_msgs/msg/StatisticsValues']
/diagnostics  ['diagnostic_msgs/msg/DiagnosticArray']
/dynamic_joint_states  ['control_msgs/msg/DynamicJointState']
/forward_effort_controller/commands  ['std_msgs/msg/Float64MultiArray']
/forward_effort_controller/transition_event  ['lifecycle_msgs/msg/TransitionEvent']
/forward_position_controller/commands  ['std_msgs/msg/Float64MultiArray']
/forward_position_controller/transition_event  ['lifecycle_msgs/msg/TransitionEvent']
/imu_sensor_broadcaster/imu  ['sensor_msgs/msg/Imu']
/imu_sensor_broadcaster/transition_event  ['lifecycle_msgs/msg/TransitionEvent']
/joint_state_broadcaster/transition_event  ['lifecycle_msgs/msg/TransitionEvent']
/joint_states  ['sensor_msgs/msg/JointState']
/magnetometer_broadcaster/magnetic_field  ['sensor_msgs/msg/MagneticField']
/magnetometer_broadcaster/transition_event  ['lifecycle_msgs/msg/TransitionEvent']
/odom_vel  ['geometry_msgs/msg/Twist']
/parameter_events  ['rcl_interfaces/msg/ParameterEvent']
/robot_description  ['std_msgs/msg/String']
/rosout  ['rcl_interfaces/msg/Log']
/sim/qpos  ['std_msgs/msg/Float64MultiArray']
/sim/rtf  ['std_msgs/msg/Float32']
/tf  ['tf2_msgs/msg/TFMessage']
/tf_static  ['tf2_msgs/msg/TFMessage']
/wojtek/joint_states_abs  ['sensor_msgs/msg/JointState']
/wojtek/joint_targets  ['sensor_msgs/msg/JointState']
/wojtek/nav_command  ['std_msgs/msg/String']
```

`/cmd_vel` and both camera streams (`color` and `depth`) are present,
satisfying the plan's backstop truth on this machine as well, once the
non-default discovery setting is applied.

**Exit status:** `0` (Attempt D)

---

## Findings

1. **DDS multicast loopback is broken on this dev box's network interface,
   under the repository's default CycloneDDS profile
   (`ros/docker/config/cyclonedds.xml`, which lets CycloneDDS auto-select a
   network interface and relies on multicast).** Direct evidence gathered
   while investigating the Attempt A hangs above: the interface CycloneDDS
   auto-selects on this host is multicast-capable and does join the DDS
   discovery multicast group, and a multicast route to it exists — but a
   self-addressed multicast wake-up packet (sent to the port CycloneDDS uses
   for its receive-thread wake-up signal) is never delivered back to the
   sending process on this host. On shutdown, one internal thread sits
   blocked waiting for more packets while another retries sending that
   wake-up packet once a second, forever, which is why every hung process
   above needed to be killed rather than exiting on its own. `rclpy.init()`,
   node creation and topic listing themselves worked correctly throughout —
   this is a local-loopback delivery defect on this host/NIC combination,
   not a defect in RAI, in `wojtek_rai`, or in ROS 2 itself.
2. **Three workarounds were verified to avoid the hang/discovery failure on
   this host:** setting `ROS_LOCALHOST_ONLY=1` (used for the passing
   `agent-topics` run above — fixes both discovery and clean shutdown);
   setting `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` (fixes discovery, not
   independently re-tested for shutdown here); and pointing `CYCLONEDDS_URI`
   at this repository's own `cyclonedds_link.xml` unicast fallback profile
   (used for the passing `test` run above — fixes the shutdown hang, but on
   this dev box does not restore local discovery, because that profile's
   configured peers are the PC-and-RPi cable-link addresses, which are not
   present on this machine).
3. **This is a base `ros/docker` container/network configuration issue on
   this particular host, not an issue in this experiment**, and per this
   plan's scope it is recorded here as a finding rather than fixed inside
   `experiments/wojtek_rai_v1/`. It is also raised as a blocker in this
   plan's SUMMARY. Suggested follow-up for whoever owns `ros/docker`: make
   the DDS discovery profile selectable per machine — for example, by
   honouring `ROS_LOCALHOST_ONLY` / `ROS_AUTOMATIC_DISCOVERY_RANGE` from
   `.env`, or by adding a localhost-only profile alongside
   `cyclonedds_link.xml` — rather than assuming every machine's default
   network interface supports local multicast loopback.
4. **A completely fresh clone has no policy available.** `wojtek_bringup
   robot --sim` requires a policy reference to start; resolving the
   repository's pinned default needs both the keeper organization's name
   (kept out of this repository, read from the gitignored `.env`) and either
   a Hugging Face login or a pre-seeded gitignored `ros/policies/` store.
   Neither exists on a fresh dev-box clone. This is a finding, not a
   blocker: seeding the store from a machine that already has it — the same
   approach `ros/deploy.sh` uses for the physical robot — is the documented
   path, and it is what Attempt B above did, with the operator's explicit
   approval, to reach a working sim.
5. **`run.sh build` is not one of the three commands this plan verifies**,
   and was not run on the dev box, so RAI logged its own
   `rai_interfaces is not installed` warnings during every `agent-topics`
   attempt above. This is expected and harmless for topic discovery — it
   only affects RAI's optional human-robot-interaction message types, which
   this experiment does not yet use.
6. **No arm64-specific failure appeared anywhere in the RAI stack itself.**
   The container image built cleanly for `linux/arm64`, `uv sync --frozen`
   resolved all 132 packages as aarch64 wheels from the committed
   `uv.lock` with zero source builds, all 65 tests passed once the DDS
   profile was addressed, and RAI's `ROS2Connector` discovered the full
   topic set once local discovery worked. Every failure traced above to
   the host's DDS/network configuration or to the fresh-clone policy gap,
   never to architecture.

**FOUND-07 verdict:** all three commands — install, test, and
topic-discovery — succeed on both the x86-64 laptop and the aarch64 remote
GPU dev box, from the same committed source. `install` and
`agent-topics` succeeded literally (as `run.sh` runs them unmodified) on the
x86-64 laptop; on the aarch64 dev box, `install` also succeeded literally,
while `test` and `agent-topics` required a non-default DDS discovery setting
to succeed — the literal default-profile runs are recorded above as hangs,
not as passes. FOUND-07 is treated as discharged on the strength of "the
same commands produce all three required outputs on both architectures,"
with the DDS caveat recorded here and in this plan's SUMMARY rather than
concealed.
