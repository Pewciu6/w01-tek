# Robot variants

A robot variant is one set of legs on the Wojtek body. Every variant uses the
same body, the same joint, sensor and actuator names, and the same 54-value
actor observation. Link lengths, masses, the contact pad and the motor limits
differ between variants.

| Variant | Legs | Standing height | Status |
|---|---|---|---|
| `wojtek` | The robot as built. | 0.12 m | Default. Every task and every existing preset. |
| `legs_v627` | The v6.27 four-bar legs, about 2.3 times longer. | 0.345 m | Simulation only. Joystick task on flat ground. No policy has been trained on it yet. |

## Selecting a variant

```bash
# Build the variant's model once. The stock model is built by plain `build`.
./training/run.sh build --robot legs_v627
./training/run.sh check --robot legs_v627

# Resolve, then train. The experiment preset selects the robot itself.
./training/run.sh train +experiment=legs_v627_locomotion --cfg job --resolve
./training/run.sh train +experiment=legs_v627_locomotion run_name=<name> seed=1
```

`robot=legs_v627` selects the variant without an experiment preset. The group
sets `task.env.robot`, `task.env.sim_dt`, the commanded height range, the fall
height and the swing height. The stock experiment presets are tuned to the
stock legs. The env refuses a run that combines `robot=legs_v627` with a stock
`command.height` range.

`run.json` records `task.env.robot`. `eval`, `report`, `courses` and `export`
rebuild the env from `run.json`, so they load the right model without a flag.
A run recorded before the key existed loads the stock robot.

## Looking at a variant

```bash
open -n -a ~/Applications/MuJoCo.app --args \
  "$PWD/ros/src/wojtek_description/mujoco/legs_v627/scene_view.xml"
```

`build` writes `scene_view.xml` next to the training scene. A viewer opens a
model at its rest pose with every control at zero. In `scene_view.xml` a
control is an offset from the home target, so the robot holds its stand and the
sliders bend the joints around it. Nothing trains on this file.

The training scene `scene_mjx.xml` takes absolute joint targets. A zero target
is outside these legs' joint ranges, so in a viewer the robot leaves its stand
until the `home` keyframe is loaded.

The built `legs_v627` model rests in the CAD keyframe pose. The CAD model
itself rests with every joint at zero, which folds each shin back along its
thigh. `build` moves the rest pose and keeps the meaning of every joint value.

The export shows a 40 mm gap between each hip housing and the thigh's cage. The
thigh frame sits 66.8 mm out along the hip axis, against 23 mm on the stock
legs. The motor block that fills the space on the real part has no mesh. The
mechanical team confirmed the offset and left the mesh out on purpose. The
block's mass is included in the thigh's inertial.

## Where a variant lives

| What | Where |
|---|---|
| Per-variant numbers, each with the reason for its value | `training/wojtek_rl/robots.py` |
| Source MJCF | `ros/src/wojtek_description/mujoco/<robot>/wojtek.xml` |
| Generated model and flat scene | `wojtek_mjx.xml` and `scene_mjx.xml` in the same directory |
| Generated viewing copy | `wojtek_view.xml` and `scene_view.xml` in the same directory |
| Visual meshes | `ros/src/wojtek_description/meshes/<robot>/` |
| Config group | `training/wojtek_rl/conf/robot/<robot>.yaml` |
| URDF leg macro | `ros/src/wojtek_description/urdf/leg_v627.urdf.xacro` |

The stock robot keeps its original paths in `wojtek_description/mujoco/`. A
variant never writes to them.

## Importing a CAD export

The mechanical team ships a leg design as a `sim_robot` archive with an MJCF, a
URDF and meshes. That MJCF is a viewer scene. It has its own floor, light and
`<option>`, and its collision is about 330 convex pieces per leg.

```bash
./training/run.sh import-robot --robot legs_v627 --archive <sim_robot.tgz>
./training/run.sh build --robot legs_v627
```

`import-robot` writes the source MJCF and copies the variant's visual meshes. It
drops the floor, the light, `<option>` and the convex collision pieces. It
keeps names, joints, inertials, actuators, sensors, the loop-closure
constraints and the CAD keyframe as exported. `build` then adds the primitive
colliders, the PD servos and the `home` keyframe, as it does for the stock
robot.

A new variant needs an entry in `robots.py` before it can be imported. A new
export of an existing variant needs its `robots.py` numbers checked again. The
height table and the leg colliders depend on the link lengths.

## What is different about `legs_v627`

**The foot.** On the stock legs the loop closes at the foot, and `foot_link` is
the ground contact. On these legs the loop closes 42 mm below the knee.
`foot_link` is that closure point and touches nothing. The pad is a 20 mm disc
at the tip of the shin, so the contact sphere sits on `sixth_link`. `build`
raises an error if the `{leg}_foot` site is not on the body the variant names
as its foot body.

**Mounting.** Front and rear legs are mounted mirrored, with the knees pointing
at each other. Rear second and third joints therefore run negative.
`Robot.leg_sign` carries that sign. The left-right mirror used by
`symmetry.enable` was checked on this model and holds unchanged.

**Height command.** The stock env extends a leg by moving the third joint twice
as far as the second. On these legs that rule swings the foot 17 cm fore and
aft. Each variant now has a `dthird_table` next to its `dsecond_table`. The
offsets for `legs_v627` were solved on the exact loop kinematics, with the foot
held under the hip. The stock table gives the same bits as the old rule.

**Timestep and solver.** The crank that drives the knee is 33 mm long. A loop
closure that opens by a few millimetres changes the leg. Measured on the built
model with `kp=60`, `kd=2`, standing for 2 s and then taking random targets
within 0.3 rad at 50 Hz:

| Timestep | Iterations | Closure `solimp` | Stand height | Loop error standing | Loop error under random targets |
|---|---|---|---|---|---|
| 4 ms | 2 | default | 0.287 m | 23.6 mm | 26.3 mm |
| 4 ms | 4 | default | 0.282 m | 11.0 mm | 13.5 mm |
| 2 ms | 4 | default | 0.338 m | 1.8 mm | 4.6 mm |
| 4 ms | 2 | 0.99 / 0.999 | 0.340 m | 0.6 mm | 152.9 mm, falls |
| 4 ms | 4 | 0.99 / 0.999 | 0.342 m | 0.6 mm | 0.8 mm |
| 2 ms | 2 | 0.99 / 0.999 | 0.345 m | 0.3 mm | 61.1 mm |
| **2 ms** | **4** | **0.99 / 0.999** | **0.345 m** | **0.3 mm** | **0.5 mm** |
| 1 ms | 4 | 0.99 / 0.999 | 0.347 m | 0.1 mm | 0.2 mm |

The bold row is the variant's setting. A control step is 10 physics steps with
4 solver iterations each, against 5 steps with 2 iterations on the stock robot.
The env refuses a `sim_dt` coarser than the variant's.

The 4 ms row with 4 iterations costs half as many physics steps. With random
targets of 1.0 rad, which throw the robot to the floor, its loop error reaches
3.8 mm against 0.7 mm at 2 ms. It became usable only after the passive-joint
friction was corrected on 2026-09-20. With the export's original friction it
reached 13.6 mm at 0.3 rad. Moving to it means changing `timestep` in
`robots.py` and `sim_dt` in the config group. A GPU step-rate measurement
should come first.

These measurements ran on CPU MuJoCo. The step rate on a GPU under MJWarp has
not been measured. `check --robot legs_v627 --gpu --backend warp` measures it
and scales the result by the timestep before comparing with the Go1 gate.

## Open questions for `legs_v627`

- `kp=60` and `kd=2` are a starting point. Standing takes about 8 N·m at the
  knee crank, so the legs sag 0.13 rad there. `task.env.pd_kp` and `pd_kd`
  override the gains per run.
- The gait clock, swing height and trot band in `legs_v627_locomotion` are
  scaled from the stock values by leg length. None of them has been trained.

## Answers from the mechanical team, 2026-09-20

- All twelve motors, abduction included, have 22 N·m. The 2 N·m and 9 N·m
  abduction limits in the export are superseded.
- The dry friction of the passive joints is 0.48 N·m on the rod's joint
  (`fourth_joint`) and 0 on the knee (`fifth_joint`). The export has 1.26 and
  1.48 N·m. `Robot.joint_frictionloss` applies the corrected values at build
  time, and the imported source file stays as exported.
- The 66.8 mm hip offset is correct. The motor block between the hip housing
  and the thigh is left out of the meshes on purpose.

## What does not support a variant yet

- `getup`, `jump` and `biped` hold literal poses and knee angles of the stock
  legs. They refuse another robot.
- Terrain arenas include the stock model and are sized to its footprint.
  `terrain.enable` refuses another robot.
- `fall.max_toggle_deg` and the `toggle_flat` reward measure an angle at the
  stock closure point. They refuse `legs_v627`.
- The course benchmark normalizes scores by the stock stance width and height.
  The SCAN planner footprint and the demo camera are sized to the stock robot.
  Scores from another variant are not comparable with archived ones.
- The bench camera sits 1.11 m above the base, which gives 1.25 m on the stock
  robot and 1.45 m on `legs_v627`.

## Deployment contract

`export` writes the variant's name as `robot` in `policy_meta.json`. For a
variant other than the stock one, `height_table` also carries `dthird` and
`leg_sign`, and `knee_singularity` is `null`. The ROS policy runtime reads
both. It refuses its `clamp_knee` option for a policy without a knee
singularity, and the real-robot launch sets `clamp_knee`. A `legs_v627` policy
therefore does not load on the real robot until that is decided on purpose.

## ROS description

`wojtek_body` in `wojtek_description` takes `legs:=stock` or `legs:=legs_v627`.
`wojtek_sim.urdf.xacro` passes the same argument through. Both leg macros use
the same link and joint names, so the `ros2_control` joint list and TF frame
names do not change.

The `legs_v627` URDF uses the MuJoCo model's joint angles. The stock URDF has
gear-correction offsets, which `joint_map.yaml` removes. A MuJoCo plant on
`legs_v627` needs the variant's scene as `model_xml` and an identity joint map.
That launch wiring does not exist yet. `wojtek_real.urdf.xacro` is unchanged
and always describes the stock legs.
