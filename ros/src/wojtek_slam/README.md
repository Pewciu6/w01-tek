# wojtek_slam

RGB-D SLAM for Wojtek: RTAB-Map over the D435 streams and the leg
odometry. Owns `map->odom` and the map products; launch + config only,
the way `wojtek_perception_bringup` composes the camera driver.

```bash
ros2 launch wojtek_slam slam.launch.py                       # standalone, against a running camera + odometry
ros2 launch wojtek_pc sim.launch.py model_xml:=scene_slam.xml leg_odom:=true slam:=true   # a sim mapping session
ros2 launch wojtek_bringup robot.launch.py perception:=true slam:=true                    # the robot (untested yet)
```

```
rgb + depth + camera_info ──► rgbd_sync ──rgbd_image──► rtabmap ──► TF map->odom
                              (approx. pair)                     ├──► /rtabmap/cloud_map   (3D, PointCloud2)
TF odom->base_link (leg_odometry) ───────────────────────────────┤──► /rtabmap/map         (2D OccupancyGrid)
TF base_link->camera (URDF / driver) ────────────────────────────┘──► ~/wojtek_maps/map_<stamp>.db
```

| piece | where |
|---|---|
| odometry (`odom->base_link`) | `wojtek_odometry`, on the robot by default, in the sim with `leg_odom:=true` |
| camera streams | `wojtek_perception_bringup` (robot), `sim_camera_node` (sim) |
| camera extrinsics (`base_link->camera_link`) | placeholder on the robot (see the perception README), the URDF in the sim |
| SLAM settings | `config/rtabmap.yaml`, every deliberate value explained there |
| map products | `/rtabmap/cloud_map`, `/rtabmap/map`, the database |
| offline tools | `rtabmap-report --loop ~/wojtek_maps` (error vs ground truth, sim), `rtabmap-export` (PLY/mesh), `rtabmap-databaseViewer` |

## What the SLAM does and does not do here

The pose between corrections is the odometry's. RTAB-Map keeps a graph of
keyframes (a node every 0.1 m or 6 deg), each linked to the previous one
by the odometry's increment; the only pose corrections are loop closures
and proximity links, found by matching image features of the current
node against earlier ones, then verified geometrically, then handed to
the graph optimiser. `map->odom` moves only when such a link is accepted
-- at most twice a second, and never in new territory. Everything in
between is `wojtek_odometry`.

Two consequences for how a session is driven:

- **Loops close only from a similar viewpoint.** The features are
  colour-image features, so a corridor walked back the other way is a new
  place to the camera. Turn 360 degrees in place at the start, at
  junctions and at the end of a circuit: those nodes face every direction
  and a later pass from any side has something to match.
- **The map is only as good as the odometry between closures.** A wrong
  odometry increment (a collision, a carried robot) is a wrong edge in the
  graph, and a closure can only distribute it, not undo it.

## Measured (sim, 2026-09-21)

`scene_slam.xml`, `wojtek-stiff-height-locomotion`, a 13.5 m circuit
around the island at 0.3 m/s with a 360-degree scan at the start and at
the end, ground truth recorded per node (`ground_truth_frame_id`):

| | RMSE vs ground truth |
|---|---|
| odometry alone | 0.091 m |
| SLAM (38 loop closures, all correct: 2 mm / 0.08 deg) | 0.085 m |
| end of the loop: odometry / SLAM | 0.21 m / 0.07 m |

RTAB-Map tick: 94 ms average, 603 ms max, on the PC.

**The scene matters more than any parameter.** The first session ran on
the training scene's checkerboard floor: 2 closures accepted, both
wrong, the map turned by 90 degrees, RMSE 0.82 m where the odometry alone
was 0.085 m. A checkerboard is the pathological input for a visual place
recogniser (every square metre is every other, rotated by any multiple of
90 degrees), which is why `scene_slam.xml` exists: a walled room where
every surface wears its own non-repeating random-dot texture. Real rooms
are closer to the second than to the first, but a long blank corridor is
closer to the first; expect the odometry to carry those.

## Sessions and the database

Mapping writes RTAB-Map's database (`database_dir`, default
`~/wojtek_maps`, one timestamped file per run, like the bringup's
rosbags). It holds the whole graph with its images: every map product is
rebuilt from it, `rtabmap-export` turns it into a PLY/mesh, and
`mode:=localization database:=<file>` matches against it read-only.
`database:=<existing file>` in mapping mode continues that map.

## On the robot

Not run yet. What is known: the two nodes go to the non-isolated cores
(`slam_cpus`, default `0,1`, next to the camera driver), the depth input
is the driver's `aligned_depth_to_color` (registered to colour, 70 deg
FOV -- the one consumer for which that trade is right), and the odometry
edge comes from `leg_odometry_node` over TF. The RPi core budget with the
camera already at ~0.7 of a core is the open question; the plan is to map
on the PC from the robot's streams first and move the SLAM onboard when
the budget is measured, not before.

## Tests

```bash
cd ros/src/wojtek_slam && PYTHONPATH=$PWD:$PYTHONPATH python3 -m pytest test/ -q
```

Launch composition (nodes, topics, the file-then-overrides parameter
order, mapping vs localization, CPU pins) and the invariants of the
parameter file (library keys are strings, 6 DoF stays on, the grid's
range matches the camera's clip, odometry comes from TF).
