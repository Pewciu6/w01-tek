# wojtek_nav

Navigation for Wojtek, starting with what it stands on: **local perception**.
A rolling costmap in the `odom` frame, built from the depth camera, that
remembers what the fixed 70-degree camera can no longer see. Launch +
config only; the nodes are stock image_pipeline and nav2.

```bash
ros2 launch wojtek_nav costmap.launch.py                                   # standalone, against a running camera + odometry
ros2 launch wojtek_pc sim.launch.py model_xml:=scene_nav.xml leg_odom:=true nav:=true   # a sim session
ros2 launch wojtek_bringup robot.launch.py perception:=true nav:=true      # the robot (not run yet)
```

```
depth image ──► crop_decimate ──► point_cloud_xyz ──► nav2_costmap_2d ──► /wojtek/nav/costmap  (OccupancyGrid, odom)
(424x240)       (every 4th px)    /wojtek/nav/points   (rolling 6x6 m)     /wojtek/nav/voxel_grid
TF odom->base_link (leg_odometry), base_link->camera (URDF / driver) ──┘
```

| piece | where |
|---|---|
| odometry (`odom->base_link`) | `wojtek_odometry`; on the robot by default, in the sim with `leg_odom:=true` |
| depth stream | `wojtek_perception_bringup` (robot), `sim_camera_node` (sim); the RAW depth, 90 deg of view |
| camera extrinsics | placeholder on the robot (see the perception README), exact in the sim |
| costmap settings | `config/costmap.yaml` -- what the map is for and what every number follows from |
| test world | `wojtek_pc/config/scene_nav.xml`: a corridor with two branches, a crate, a pillar, a 0.15 m box |

## What the costmap is and is not

It is not a map of the world. It is a 6 x 6 m window that moves with the
robot and answers, per 5 cm cell: obstacle, free, or never seen. The
frame is `odom` because over a 6 m window the leg odometry's drift is
centimetres; there is no `map` frame and nothing needs one.

The property that matters is **memory**. The camera is a cone to the
front on a fixed head, blind to the sides and behind. A cell marked while
the crate was in view stays marked after the body has turned away from it
-- until the robot either sees through that cell again (a ray to a floor
point behind it clears it) or drives far enough that it leaves the window.
Free cells are kept the same way. That is what stops the robot turning
into the thing it walked past a moment ago.

Three decisions behind the configuration (the file argues each number):

- **Two observation sources on one cloud.** `depth_mark` marks from 6 cm
  above the floor up; `depth_clear` clears with rays down to the floor.
  One source cannot do both: either the floor becomes a wall or nothing
  ever clears.
- **Heights are in odom, levelled by the IMU.** The body pitches a few
  degrees with every step, 15 cm at 3 m; the odometry carries roll/pitch
  from the IMU, so the floor stays flat in this frame and the 6 cm margin
  holds. This is also why the camera's pitch extrinsic will matter on the
  robot: 1 degree of it is 5 cm at 3 m, a permanent phantom step.
- **Decimate before deprojecting.** The costmap ray-traces every point it
  is given through its 3D voxel grid. 424x240 is 100k rays a frame;
  every 4th pixel is 6k, and at a 5 cm cell that still over-samples.

## Verified (sim, 2026-09-25)

`scene_nav.xml`, `wojtek-stiff-height-locomotion`, depth 15 fps: the
crate 2 m ahead-right is marked from the spawn (23 lethal cells in its
0.6 x 0.6 m box), stays marked after walking 1.1 m towards it (34), and
**stays marked after a 92-degree turn in place that takes it out of the
view** (44). The window follows the robot; free cells behind persist.
Costmap published at ~1.7 Hz, updated at 5 Hz.

What the sim cannot show: sensor noise on the floor (the 6 cm margin is
against a noiseless floor here), the extrinsics error, and the CPU cost on
the RPi -- three C++ nodes at 15 fps and 6k points is a fraction of a core
on the PC, unmeasured on the robot.

## Next

The consumer: a planner on this window replanned about once a second, a
controller turning its path into `/cmd_vel` for `policy_node`, and a goal
contract for the VLM (a pose in `odom`). Also: negative obstacles (a hole
or a step down is *missing* floor, which this costmap reads as unknown,
not as danger) and the step-height decision for a legged robot (the
0.15 m box is a wall here; whether it should be is the policy's business).

## Tests

```bash
cd ros/src/wojtek_nav && PYTHONPATH=$PWD:$PYTHONPATH python3 -m pytest test/ -q
```

Launch composition (three nodes in order, the decimated pair published
where image_transport looks for it, the cloud landing on the topic both
observation sources read, CPU pins) and the file's invariants (rolling
window in odom, footprint covers the measured robot, marking/clearing
split by floor height, ranges match the camera).
