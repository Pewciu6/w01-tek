"""Tests for the launch file's OpaqueFunction and the parameter file.

`ros2 launch --show-args` only evaluates the argument declarations; the part
that composes the SLAM -- which nodes, wired to which topics, with which
settings layered in which order -- would otherwise stay untested until a
camera and an odometry are up.
"""

import importlib.util
from pathlib import Path

import pytest
import yaml
from launch import LaunchContext
from launch.utilities import perform_substitutions
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters

PKG_DIR = Path(__file__).resolve().parents[1]
CONFIG = PKG_DIR / "config"


@pytest.fixture(scope="module")
def launch_mod():
    path = PKG_DIR / "launch" / "slam.launch.py"
    spec = importlib.util.spec_from_file_location("slam_launch", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _context(tmp_path, **overrides):
    ctx = LaunchContext()
    defaults = {
        "params_file": str(CONFIG / "rtabmap.yaml"),
        "mode": "mapping",
        "database": "",
        "database_dir": str(tmp_path / "maps"),
        "rgb_topic": "/camera/camera/color/image_raw",
        "rgb_info_topic": "/camera/camera/color/camera_info",
        "depth_topic": "/camera/camera/aligned_depth_to_color/image_raw",
        "sync_max_interval": "0.067",
        "frame_id": "base_link",
        "odom_frame_id": "odom",
        "map_frame_id": "map",
        "ground_truth_frame_id": "",
        "ground_truth_base_frame_id": "base_link_gt",
        "cpus": "",
        "launch-prefix": "",
    }
    defaults.update(overrides)
    ctx.launch_configurations.update(defaults)
    return ctx


def _params(node, ctx):
    return evaluate_parameters(ctx, node._Node__parameters)


def _remaps(node, ctx):
    return {
        perform_substitutions(ctx, src): perform_substitutions(ctx, dst)
        for src, dst in node._Node__remappings
    }


def _prefix(node):
    return node._ExecuteLocal__process_description._Executable__prefix


def _rtabmap_params():
    with open(CONFIG / "rtabmap.yaml") as fh:
        return yaml.safe_load(fh)["/**/rtabmap"]["ros__parameters"]


def test_setup_is_sync_then_slam(launch_mod, tmp_path):
    sync, slam = launch_mod._setup(_context(tmp_path))
    assert isinstance(sync, Node) and isinstance(slam, Node)
    assert "rgbd_sync" in str(sync._Node__node_executable)
    assert slam._Node__package == "rtabmap_slam"


def test_sync_takes_the_platforms_topics(launch_mod, tmp_path):
    ctx = _context(tmp_path, depth_topic="/camera/camera/depth/image_rect_raw")
    remaps = _remaps(launch_mod._setup(ctx)[0], ctx)
    assert remaps["rgb/image"] == "/camera/camera/color/image_raw"
    assert remaps["rgb/camera_info"] == "/camera/camera/color/camera_info"
    assert remaps["depth/image"] == "/camera/camera/depth/image_rect_raw"


def test_sync_pairs_approximately_within_one_depth_period(launch_mod, tmp_path):
    """The sim renders colour and depth on separate timers; a pair has to
    tolerate that gap and no more."""
    ctx = _context(tmp_path)
    params = _params(launch_mod._setup(ctx)[0], ctx)[0]
    assert params["approx_sync"] is True
    assert 0.0 < params["approx_sync_max_interval"] <= 1 / 15 + 1e-3


def test_slam_loads_the_file_then_the_wiring(launch_mod, tmp_path):
    """File first, overrides after: each entry is its own --params-file in
    order and the last one wins, so the platform's frames beat the file."""
    ctx = _context(tmp_path, odom_frame_id="odom_x")
    params = _params(launch_mod._setup(ctx)[1], ctx)
    assert str(params[0]).endswith("rtabmap.yaml")
    assert params[1]["odom_frame_id"] == "odom_x"
    assert params[1]["frame_id"] == "base_link"


def test_mapping_gets_a_fresh_timestamped_database(launch_mod, tmp_path):
    ctx = _context(tmp_path)
    params = _params(launch_mod._setup(ctx)[1], ctx)[1]
    db = Path(params["database_path"])
    assert db.parent == tmp_path / "maps" and db.parent.is_dir()
    assert db.name.startswith("map_") and db.suffix == ".db"
    assert params["Mem/IncrementalMemory"] == "true"


def test_localization_needs_a_database_and_never_grows_it(launch_mod, tmp_path):
    with pytest.raises(ValueError):
        launch_mod._setup(_context(tmp_path, mode="localization"))
    ctx = _context(tmp_path, mode="localization", database="~/x/map.db")
    params = _params(launch_mod._setup(ctx)[1], ctx)[1]
    assert params["database_path"].endswith("/x/map.db")
    assert not params["database_path"].startswith("~")
    assert params["Mem/IncrementalMemory"] == "false"
    assert params["Mem/InitWMWithAllNodes"] == "true"


def test_unknown_mode_is_refused(launch_mod, tmp_path):
    with pytest.raises(ValueError):
        launch_mod._setup(_context(tmp_path, mode="slam"))


def test_ground_truth_is_recorded_only_when_a_platform_has_one(launch_mod, tmp_path):
    ctx = _context(tmp_path)
    assert "ground_truth_frame_id" not in _params(launch_mod._setup(ctx)[1], ctx)[1]
    ctx = _context(tmp_path, ground_truth_frame_id="odom")
    params = _params(launch_mod._setup(ctx)[1], ctx)[1]
    assert params["ground_truth_frame_id"] == "odom"
    assert params["ground_truth_base_frame_id"] == "base_link_gt"


def test_cpus_argument_pins_both_nodes(launch_mod, tmp_path):
    """On the robot both nodes go where the camera driver goes: off the
    isolated RT cores. No argument = inherit the parent's mask."""
    ctx = _context(tmp_path, cpus="0,1")
    for node in launch_mod._setup(ctx):
        assert perform_substitutions(ctx, _prefix(node)) == "taskset -c 0,1"
    ctx = _context(tmp_path)
    for node in launch_mod._setup(ctx):
        assert perform_substitutions(ctx, _prefix(node)) == ""


def test_odometry_comes_from_tf_not_from_a_message():
    """The pose is looked up at the image stamp (interpolated), which a
    synchronised odom message cannot give; and with no message there is no
    covariance to read, so the TF variances must be set."""
    params = _rtabmap_params()
    assert params["subscribe_odom"] is False
    assert params["odom_tf_linear_variance"] > 0
    assert params["odom_tf_angular_variance"] > 0


def test_library_parameters_are_strings():
    """rtabmap_ros forwards Group/Name keys verbatim to the library and
    rejects anything but a string -- a bare `true` or `3.0` fails at
    startup, after the camera is already running."""
    params = _rtabmap_params()
    library = {k: v for k, v in params.items() if "/" in k}
    assert library, "no RTAB-Map library parameters in the file"
    not_strings = {k: v for k, v in library.items() if not isinstance(v, str)}
    assert not not_strings, not_strings


def test_walking_body_keeps_its_six_degrees_of_freedom():
    """The odometry carries the body's roll/pitch from the IMU; forcing
    3DoF would paste every frame level and turn the floor into a
    washboard."""
    assert _rtabmap_params()["Reg/Force3DoF"] == "false"


def test_map_range_matches_the_cameras_clip():
    """Beyond 3 m the radial noise exceeds a map cell (the camera
    bringup's clip_distance); the grid must not trust further."""
    assert float(_rtabmap_params()["Grid/RangeMax"]) <= 3.0
