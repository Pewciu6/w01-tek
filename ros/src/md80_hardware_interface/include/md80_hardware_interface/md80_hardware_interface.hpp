// Copyright (c) 2024, Jakub Delicat
// Copyright (c) 2024, Stogl Robotics Consulting UG (haftungsbeschränkt)
// (template)
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef MICROROS_HARDWARE_INTERFACES__MICROROS_HARDWARE_INTERFACES_HPP_
#define MICROROS_HARDWARE_INTERFACES__MICROROS_HARDWARE_INTERFACES_HPP_

#include <memory>
#include <string>
#include <vector>

#include <rclcpp/rclcpp.hpp>

#include "hardware_interface/handle.hpp"
#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/lexical_casts.hpp"
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "md80_hardware_interface/visibility_control.h"
#include "rclcpp/macros.hpp"
#include "rclcpp_lifecycle/state.hpp"
#include "std_msgs/msg/float32_multi_array.hpp"

#include "candle.hpp"
#include "md80_hardware_interface/link_monitor.hpp"
namespace md80_hardware_interface
{

struct JointInfo
{
  double position = 0.0;
  double velocity = 0.0;
  double effort = 0.0;
};

struct PID
{
  float kp;
  float ki;
  float kd;
  float windup;
};

struct MD80Info
{
  JointInfo state;
  JointInfo command;
  int can_id;
  mab::Md80Mode_E control_mode;
  // IMPEDANCE with a [position, effort] interface pair: write() forwards
  // command.effort as the drive's feed-forward torque (tau_ff policies).
  bool has_effort_ff = false;
  float max_torque;
  PID q_pid;
  PID dq_pid;
  PID ddq_pid;
};

class MD80HardwareInterface : public hardware_interface::SystemInterface
{
public:
  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::CallbackReturn on_init(
    const hardware_interface::HardwareInfo & info) override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::CallbackReturn on_configure(
    const rclcpp_lifecycle::State & previous_state) override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  std::vector<hardware_interface::StateInterface> export_state_interfaces() override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::CallbackReturn on_activate(
    const rclcpp_lifecycle::State & previous_state) override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::CallbackReturn on_deactivate(
    const rclcpp_lifecycle::State & previous_state) override;

  // Entered by the controller manager after read() reports the drive link
  // lost. Stops the CANdle update loop (which also disables the drives, best
  // effort on a dead bus) and leaves the component UNCONFIGURED. Recovery is
  // a fresh bring-up: the robot's wojtek-cm-watchdog restarts the service
  // once the drives answer again.
  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::CallbackReturn on_error(
    const rclcpp_lifecycle::State & previous_state) override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::return_type read(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::return_type write(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

private:
  void parse_urdf_joint_info(MD80Info & md80, const hardware_interface::ComponentInfo & info);

  std::shared_ptr<mab::Candle> find_candle_by_motor_can_id(uint16_t can_id);
  void add_candle_instances();
  void try_to_initialize_motors();
  void set_config_to_md80();
  void set_modes();

  void zero_encoders();
  void enable_motors();
  void disable_motors();
  void register_link_monitors();
  void arm_link_monitors();
  // The link check behind read(): the CAN ids that went stale, empty when
  // every drive delivered a fresh frame within link_timeout_cycles.
  std::vector<int> stale_drives();

  void reset_command();
  void log_current_joint_position();

  std::vector<MD80Info> md80_info_;
  std::vector<double> initial_positions_;
  // Bench mode (URDF <hardware> param "dry_run"): keep the CANdle update loop
  // running so encoder states stream, but never enable the drives -- no
  // torque can reach the motors regardless of what is commanded.
  bool dry_run_ = false;

  // Drive link watchdog (URDF <hardware> param "link_timeout_cycles", 0 =
  // off). The CANdle library streams the drives from its own thread and
  // only ever overwrites the Md80 state on a frame that carries that
  // drive's CAN id; read() copies whatever is there. When the SPI link or
  // the CAN bus dies mid-run nothing in the library reports it -- the state
  // simply stops changing, read() keeps returning OK and the stack looks
  // healthy while it is deaf (seen 2026-09-21: motor power cycled under a
  // live stack, joint_states frozen for 30 min, controllers "active"). One
  // monitor per drive counts the frames the library accepted for it; a drive
  // that delivered none for link_timeout_cycles consecutive read() calls
  // fails read(), which the controller manager turns into on_error.
  uint32_t link_timeout_cycles_ = 0;
  bool link_armed_ = false;
  std::vector<std::unique_ptr<LinkMonitor>> link_monitors_;

  std::vector<std::shared_ptr<mab::Candle>> candle_instances;
};

}  // namespace md80_hardware_interface

#endif  // MICROROS_HARDWARE_INTERFACES__MICROROS_HARDWARE_INTERFACES_HPP_
