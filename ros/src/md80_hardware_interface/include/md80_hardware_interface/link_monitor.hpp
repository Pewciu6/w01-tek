// Copyright (c) 2026, machinekind
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
#ifndef MD80_HARDWARE_INTERFACE__LINK_MONITOR_HPP_
#define MD80_HARDWARE_INTERFACE__LINK_MONITOR_HPP_

#include <atomic>
#include <cstdint>

namespace md80_hardware_interface
{

// Freshness of one drive's data as seen by the ros2_control read() loop.
//
// on_rx() is the drive's CANdle RX callback: the library calls it from its
// own update thread exactly when it accepted a frame carrying this drive's
// CAN id (Md80::__updateResponseData drops every other frame before the
// callback). tick() runs once per read() on the controller thread and
// answers whether the drive has gone stale: no accepted frame for more than
// `timeout_cycles` consecutive ticks. Two threads touch the counter, hence
// the atomic; the bookkeeping fields belong to the controller thread only.
struct LinkMonitor
{
  void on_rx() { rx_frames.fetch_add(1, std::memory_order_relaxed); }

  // Forget the history: the next tick() starts counting from "fresh".
  void arm()
  {
    last_seen = rx_frames.load(std::memory_order_relaxed);
    stale_cycles = 0;
  }

  // One read() cycle. Returns true once the drive has been silent for more
  // than timeout_cycles cycles in a row; timeout_cycles == 0 disables it.
  bool tick(uint32_t timeout_cycles)
  {
    const uint32_t now = rx_frames.load(std::memory_order_relaxed);
    if (now != last_seen) {
      last_seen = now;
      stale_cycles = 0;
    } else {
      ++stale_cycles;
    }
    return timeout_cycles != 0 && stale_cycles > timeout_cycles;
  }

  std::atomic<uint32_t> rx_frames{0};
  uint32_t last_seen = 0;
  uint32_t stale_cycles = 0;
};

}  // namespace md80_hardware_interface

#endif  // MD80_HARDWARE_INTERFACE__LINK_MONITOR_HPP_
