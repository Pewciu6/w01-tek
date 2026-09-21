"""RGB-D SLAM: RTAB-Map over the D435 streams and the leg odometry.

    ros2 launch wojtek_slam slam.launch.py
    ros2 launch wojtek_slam slam.launch.py mode:=localization database:=~/wojtek_maps/map_x.db
    ros2 launch wojtek_slam slam.launch.py --show-args

Runs standalone (against a running camera + odometry) and is meant to be
included by the robot/sim bringup, which passes the platform's topics:

    IncludeLaunchDescription(
        PythonLaunchDescriptionSource(".../slam.launch.py"),
        launch_arguments={"depth_topic": ..., "cpus": "0,1"}.items(),
    )

Graph:

    rgb + depth + camera_info ──► rgbd_sync ──rgbd_image──► rtabmap ──► TF map->odom
                                  (approx. pair)                     ├──► cloud_map (3D)
    TF odom->base_link (leg_odometry) ───────────────────────────────┤──► map (2D grid)
    TF base_link->camera (URDF / driver) ────────────────────────────┘──► <database>

The odometry enters through TF, not through /wojtek/odom: rtabmap looks the
pose up AT THE IMAGE STAMP, interpolating between the 25-50 Hz samples,
where a synchronised odom message would be the nearest sample only -- up to
20 ms, or 0.6 deg at a 0.5 rad/s turn, more than the sensor's noise at 3 m.
The camera's timestamps and the odometry's share one clock (the robot's),
so the lookup is well-defined on both platforms.

The depth must be REGISTERED to the colour image (same optical frame and
intrinsics, the colour size an integer multiple of the depth's): the SLAM
finds features in colour and reads their range from the depth at the same
pixel. On the robot that is the driver's aligned_depth_to_color; in the sim
both images render from one MJCF camera and are registered by construction,
so the raw depth topic is the right one there (the bringup passes it).

Sessions and the database. Mapping writes RTAB-Map's database, the whole
graph with its images: the source every map product is rebuilt from, and
the input to `rtabmap-export` (PLY/mesh, offline) and to localization mode.
By default each mapping run gets a fresh, timestamped file under
database_dir (like the bringup's rosbags); passing database:= an existing
file CONTINUES that map (multi-session mapping). Localization mode needs a
database and never writes to it.
"""

import datetime
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

PKG = "wojtek_slam"
NAMESPACE = "rtabmap"

# rtabmap_ros QoS codes: 0 system default, 1 reliable, 2 best effort. Best
# effort subscribes to both the sim camera (sensor-data QoS) and the driver.
QOS_BEST_EFFORT = 2


def _setup(context, *args, **kwargs):
    def arg(name):
        return LaunchConfiguration(name).perform(context)

    def flag(name):
        return arg(name).lower() in ("true", "1")

    # Optional CPU affinity, the same treatment the camera driver gets from
    # the robot bringup: off the isolated RT cores.
    cpus = arg("cpus")
    prefix = [f"taskset -c {cpus}"] if cpus else None

    mode = arg("mode")
    if mode not in ("mapping", "localization"):
        raise ValueError(f"mode must be mapping or localization, got {mode!r}")

    database = os.path.expanduser(arg("database"))
    if not database:
        if mode == "localization":
            raise ValueError("localization needs database:=<an existing .db>")
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        database = os.path.join(
            os.path.expanduser(arg("database_dir")), f"map_{stamp}.db"
        )
    os.makedirs(os.path.dirname(database), exist_ok=True)

    # Wiring the config file cannot know: which frames this platform uses
    # and where the map goes. Layered after the file, so it wins.
    rtabmap_overrides = {
        "frame_id": arg("frame_id"),
        "odom_frame_id": arg("odom_frame_id"),
        "map_frame_id": arg("map_frame_id"),
        "database_path": database,
        # Mem/IncrementalMemory is THE mapping/localization switch in
        # RTAB-Map; InitWMWithAllNodes puts the whole saved map in working
        # memory so localization can match anywhere in it from the start.
        "Mem/IncrementalMemory": "true" if mode == "mapping" else "false",
        "Mem/InitWMWithAllNodes": "false" if mode == "mapping" else "true",
    }
    # Ground truth, when the platform has one (the sim): rtabmap stores the
    # true pose per node, so its own report tool measures the map's error
    # without a second script. Empty = no such frame, the robot.
    if arg("ground_truth_frame_id"):
        rtabmap_overrides["ground_truth_frame_id"] = arg("ground_truth_frame_id")
        rtabmap_overrides["ground_truth_base_frame_id"] = arg(
            "ground_truth_base_frame_id"
        )

    return [
        Node(
            package="rtabmap_sync",
            executable="rgbd_sync",
            name="rgbd_sync",
            namespace=NAMESPACE,
            parameters=[{
                # The pair is approximate on purpose: the sim renders colour
                # and depth on separate timers, the driver stamps them
                # together. The window is the sim's depth period (15 fps)
                # -- the nearest depth to a colour frame is always inside
                # it, and a pair further apart than that is not the same
                # view of a walking robot.
                "approx_sync": True,
                "approx_sync_max_interval": float(arg("sync_max_interval")),
                "qos": QOS_BEST_EFFORT,
                "qos_camera_info": QOS_BEST_EFFORT,
            }],
            remappings=[
                ("rgb/image", arg("rgb_topic")),
                ("rgb/camera_info", arg("rgb_info_topic")),
                ("depth/image", arg("depth_topic")),
            ],
            prefix=prefix,
            output="screen",
        ),
        Node(
            package="rtabmap_slam",
            executable="rtabmap",
            name="rtabmap",
            namespace=NAMESPACE,
            parameters=[arg("params_file"), rtabmap_overrides],
            prefix=prefix,
            output="screen",
        ),
    ]


def generate_launch_description():
    share = get_package_share_directory(PKG)
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "params_file", default_value=f"{share}/config/rtabmap.yaml",
                description="RTAB-Map settings; see the file's commentary.",
            ),
            DeclareLaunchArgument(
                "mode", default_value="mapping",
                description="mapping (grow the graph, write the database) "
                            "or localization (match against a saved one, "
                            "read-only).",
            ),
            DeclareLaunchArgument(
                "database", default_value="",
                description="RTAB-Map database. Empty = a fresh timestamped "
                            "file under database_dir (mapping); an existing "
                            "file continues that map, or is what "
                            "localization matches against.",
            ),
            DeclareLaunchArgument(
                "database_dir", default_value="~/wojtek_maps",
                description="Where fresh mapping databases go.",
            ),
            DeclareLaunchArgument(
                "rgb_topic", default_value="/camera/camera/color/image_raw",
            ),
            DeclareLaunchArgument(
                "rgb_info_topic", default_value="/camera/camera/color/camera_info",
            ),
            DeclareLaunchArgument(
                "depth_topic",
                default_value="/camera/camera/aligned_depth_to_color/image_raw",
                description="Depth REGISTERED to the colour image. The "
                            "driver's aligned product on the robot; in the "
                            "sim the raw depth already is (one render "
                            "camera), so the bringup passes that.",
            ),
            DeclareLaunchArgument(
                "sync_max_interval", default_value="0.067",
                description="Max stamp gap (s) for a colour/depth pair.",
            ),
            DeclareLaunchArgument("frame_id", default_value="base_link"),
            DeclareLaunchArgument("odom_frame_id", default_value="odom"),
            DeclareLaunchArgument("map_frame_id", default_value="map"),
            DeclareLaunchArgument(
                "ground_truth_frame_id", default_value="",
                description="Parent frame of a true pose to record per node "
                            "(sim only); empty = none.",
            ),
            DeclareLaunchArgument(
                "ground_truth_base_frame_id", default_value="base_link_gt",
            ),
            DeclareLaunchArgument(
                "cpus", default_value="",
                description="CPU affinity for both nodes (comma list); "
                            "empty = inherit.",
            ),
            OpaqueFunction(function=_setup),
        ]
    )
