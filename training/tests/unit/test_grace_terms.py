"""The grace terms (feet_touchdown, support) and the flat_grace_v1 preset.

Model-free: the term math is pure (module-level helpers in env.py), the
preset is read as yaml. No env is built here (the tests/unit guard).
"""

from pathlib import Path

import numpy as np
import pytest
import yaml

from wojtek_rl import env as wojtek_env
from wojtek_rl.env import support_shortfall, touchdown_cost, wz_charge

PRESET_YAML = (
    Path(__file__).resolve().parents[2]
    / "wojtek_rl/conf/experiment/flat_grace_v1.yaml"
)


# -- touchdown_cost -----------------------------------------------------------


def test_touchdown_charges_only_the_feet_that_just_landed():
    vz = np.array([-1.0, -0.5, -2.0, -0.1])
    first = np.array([True, False, True, False])
    assert float(touchdown_cost(vz, first)) == pytest.approx(1.0 + 4.0)


def test_touchdown_ignores_upward_and_zero_speed():
    vz = np.array([0.3, 0.0, 0.0, 0.0])
    first = np.array([True, True, True, True])
    assert float(touchdown_cost(vz, first)) == 0.0


def test_touchdown_is_zero_without_a_touchdown():
    vz = np.array([-1.0, -1.0, -1.0, -1.0])
    assert float(touchdown_cost(vz, np.zeros(4, dtype=bool))) == 0.0


# -- support_shortfall --------------------------------------------------------


@pytest.mark.parametrize(
    "contact, min_contact, expected",
    [
        ([1, 1, 1, 1], 2, 0.0),  # standing / four down
        ([1, 0, 0, 1], 2, 0.0),  # diagonal trot, no flight
        ([1, 0, 0, 0], 2, 1.0),  # three feet up
        ([0, 0, 0, 0], 2, 2.0),  # flight phase
        ([1, 0, 0, 1], 3, 1.0),  # a trot under the walk setting
        ([1, 1, 0, 1], 3, 0.0),  # statically stable walk
    ],
)
def test_support_shortfall_counts_missing_feet(contact, min_contact, expected):
    got = float(support_shortfall(np.array(contact, dtype=bool), min_contact))
    assert got == pytest.approx(expected)


# -- wz_charge ----------------------------------------------------------------


def test_wz_charge_is_unity_with_no_fade():
    assert wz_charge(0.9, 0.0, 0.0) == 1.0


def test_wz_charge_fades_near_binarily_to_the_floor():
    assert float(wz_charge(0.0, 0.1, 0.35)) == pytest.approx(1.0)
    assert float(wz_charge(0.05, 0.1, 0.35)) == pytest.approx(0.5)
    assert float(wz_charge(0.5, 0.1, 0.35)) == pytest.approx(0.35)
    assert float(wz_charge(-0.5, 0.1, 0.0)) == pytest.approx(0.0)


# -- defaults and the preset --------------------------------------------------


def test_grace_terms_are_off_by_default():
    cfg = wojtek_env.default_config()
    assert cfg.reward.scales.feet_touchdown == 0.0
    assert cfg.reward.scales.support == 0.0
    assert cfg.reward.support_min_contact == 2


def test_preset_scale_keys_exist_in_code_defaults():
    """A typo'd scale key would train with the term silently absent (the
    reward sum iterates the code's keys, not yaml's)."""
    preset = yaml.safe_load(PRESET_YAML.read_text())
    default_scales = set(wojtek_env.default_config().reward.scales.keys())
    preset_scales = set(preset["task"]["env"]["reward"]["scales"].keys())
    unknown = preset_scales - default_scales
    assert not unknown, f"preset sets unknown reward scales: {sorted(unknown)}"


def test_preset_turns_the_grace_terms_on_at_the_keeper_plant():
    preset = yaml.safe_load(PRESET_YAML.read_text())
    env_cfg = preset["task"]["env"]
    scales = env_cfg["reward"]["scales"]
    assert scales["feet_touchdown"] < 0
    assert scales["support"] < 0
    assert scales["base_accel"] < 0
    assert env_cfg["reward"]["glide_height"] > 0.03
    # The deployed quiet keeper's servo contract (kp 40 / kd 0.8), so the
    # run compares to it and needs no launch change on the robot.
    assert env_cfg["pd_kp"] == 40.0
    assert env_cfg["pd_kd"] == 0.8
    assert preset["defaults"] == ["flat_quiet_v6"]
