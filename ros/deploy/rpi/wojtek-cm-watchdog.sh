#!/bin/bash
# wojtek-cm-watchdog: bring wojtek-robot back when the drive link dies.
#
# Three ways the control stack loses the drives, and what this loop sees:
#
#   1. ros2_control_node crashes (SPI dropout during bring-up, a throw):
#      the launch keeps the other nodes up, so the service stays "active"
#      while the controller manager (CM) process is gone.
#   2. Motor power is cut under a live stack: since the driver's link
#      watchdog (md80_hardware_interface, link_timeout_cycles) the CM
#      survives, but MD80HardwareInterface leaves the ACTIVE state -- the
#      CM publishes that on /controller_manager/activity.
#   3. The CANdle HAT resets under a live stack (seen 2026-09-21 on a 5 V
#      dip): same as 2 from the outside.
#
# In every case the fix is a fresh bring-up, and a fresh bring-up only
# works once the drives answer. So: on a dead CM or a non-active hardware
# component, stop the service (frees the SPI bus), probe the drives with
# mdtool (as the robot user: its ini pins bus=SPI), and start the service
# again when they answer. While they are silent -- motor power off -- hold,
# instead of restart-looping a stack that cannot come up.
#
# Do not install by hand: install.sh puts this into /usr/local/sbin and
# enables wojtek-cm-watchdog.service.

ROBOT_USER="${ROBOT_USER:-rpi}"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"
WS="/home/${ROBOT_USER}/wojtek_ws"
HW_NAME="MD80HardwareInterface"
SERVICE="wojtek-robot.service"
# A fresh bring-up needs this long before its hardware is expected ACTIVE;
# a younger service is never judged.
GRACE_S=60

log() { echo "$*" | systemd-cat -t wojtek-cm-watchdog; }

service_age_s() {
    local since
    since="$(systemctl show "${SERVICE}" -p ActiveEnterTimestampMonotonic --value 2>/dev/null)"
    [ -n "${since}" ] && [ "${since}" != 0 ] || { echo 0; return; }
    local now
    now="$(awk '{printf "%d", $1 * 1000000}' /proc/uptime)"
    echo $(( (now - since) / 1000000 ))
}

cm_alive() { pgrep -f '/controller_manager/ros2_control_node' >/dev/null; }

# Prints the hardware component's lifecycle label ("active", "unconfigured",
# ...) from the CM's latched activity topic, or nothing when the CM does
# not answer in time (a hung CM counts as dead for our purposes).
hw_state() {
    runuser -u "${ROBOT_USER}" -- /usr/bin/taskset -c 0,1 /bin/bash -c "
        source /opt/ros/${ROS_DISTRO}/setup.bash
        source ${WS}/install/setup.bash
        export ROS_DOMAIN_ID=42 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
               CYCLONEDDS_URI=file:///etc/cyclonedds-rpi.xml
        timeout 15 ros2 topic echo --once \
            --qos-durability transient_local --qos-reliability reliable \
            /controller_manager/activity 2>/dev/null
    " | awk -v hw="${HW_NAME}" '
        /^hardware_components:/ { in_hw = 1; next }
        in_hw && /name:/  { name = $NF }
        in_hw && /label:/ { if (name == hw) print $NF }
    '
}

drives_answer() {
    runuser -u "${ROBOT_USER}" -- /usr/local/bin/mdtool ping all 2>/dev/null \
        | grep -q "Found drives"
}

sleep 30
power_off=0
misses=0
while true; do
    sleep 10

    if systemctl is-active --quiet "${SERVICE}"; then
        if cm_alive; then
            # A healthy CM with a healthy component: nothing to do. Judge the
            # component only once bring-up had its chance.
            [ "$(service_age_s)" -ge "${GRACE_S}" ] || continue
            state="$(hw_state)"
            if [ "${state}" = "active" ]; then misses=0; continue; fi
            if [ -z "${state}" ]; then
                # No answer is also what a DDS hiccup looks like. Stopping a
                # stack that is fine would drop a standing robot, so ask twice.
                misses=$((misses + 1))
                [ "${misses}" -ge 2 ] || continue
                log "CM alive but not answering twice in a row (hung?) -- stopping ${SERVICE}"
            else
                log "${HW_NAME} is '${state}', not active -- drive link lost; stopping ${SERVICE}"
            fi
        else
            log "CM dead under a running ${SERVICE} -- stopping it"
        fi
        systemctl stop "${SERVICE}"
        power_off=0
        misses=0
        continue
    fi

    # Service down (we stopped it, or it never came up): bring it back only
    # once the drives answer. mdtool needs the SPI bus, which is free now.
    if drives_answer; then
        if [ "${power_off}" = 1 ]; then
            log "motor power BACK -- starting ${SERVICE}"
        else
            log "drives answer -- starting ${SERVICE}"
        fi
        power_off=0
        systemctl start "${SERVICE}"
        sleep "${GRACE_S}"
    elif [ "${power_off}" = 0 ]; then
        log "drives SILENT -- motor power off or bus open; waiting"
        power_off=1
    fi
done
