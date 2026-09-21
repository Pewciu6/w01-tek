# md80_hardware_interface

ros2_control `SystemInterface` for MAB MD80 drives behind a CANdle (SPI HAT
or the legacy USB dongle). The URDF `<hardware>` block picks the bus and the
CAN baudrate; every `<joint>` names its drive by `can_id`. See
`wojtek_bringup/urdf/wojtek_ros2_control.urdf.xacro` for the parameters and
the control-mode mapping (a `position` command interface is IMPEDANCE mode
with the PD law running on the drive).

## Drive link watchdog (`link_timeout_cycles`)

The CANdle library streams the drives from its own thread and only ever
overwrites an `Md80`'s state on a frame that carries that drive's CAN id.
When the SPI link or the CAN bus dies mid-run the library reports nothing:
its state simply stops changing. `read()` would keep copying it, return OK,
and the stack would look healthy while the robot is deaf (2026-09-21: motor
power cycled under a live stack, `joint_states` frozen for 30 min, every
controller `active`).

The driver therefore hooks the library's per-drive RX callback into a
`LinkMonitor` (`include/md80_hardware_interface/link_monitor.hpp`) that counts
accepted frames, and `read()` fails once any drive delivered none for more
than `link_timeout_cycles` consecutive cycles. The controller manager then
deactivates the controllers and calls `on_error`, which stops the CANdle
update loop and leaves the component `unconfigured`; the robot's
`wojtek-cm-watchdog` (`ros/deploy/rpi/`) sees that on
`/controller_manager/activity` and restarts the service once the drives
answer again.

`link_timeout_cycles` is a `<hardware>` param, 20 by default in the xacro
(100 ms at the 200 Hz `update_rate`); `0` switches the check off.

Unit test: `colcon test --packages-select md80_hardware_interface`
(`test/test_link_monitor.cpp`, needs `-DBUILD_TESTING=ON`).
