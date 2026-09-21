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

#include <gtest/gtest.h>

#include "md80_hardware_interface/link_monitor.hpp"

using md80_hardware_interface::LinkMonitor;

TEST(LinkMonitor, FreshFramesNeverTrip)
{
  LinkMonitor m;
  m.arm();
  for (int i = 0; i < 1000; ++i) {
    m.on_rx();
    EXPECT_FALSE(m.tick(20));
  }
}

TEST(LinkMonitor, SilenceTripsAfterTimeoutCycles)
{
  LinkMonitor m;
  m.arm();
  m.on_rx();
  EXPECT_FALSE(m.tick(3));  // fresh
  EXPECT_FALSE(m.tick(3));  // stale 1
  EXPECT_FALSE(m.tick(3));  // stale 2
  EXPECT_FALSE(m.tick(3));  // stale 3 == timeout: still tolerated
  EXPECT_TRUE(m.tick(3));   // stale 4 > timeout
}

TEST(LinkMonitor, OneFrameResetsTheCount)
{
  LinkMonitor m;
  m.arm();
  EXPECT_FALSE(m.tick(2));
  EXPECT_FALSE(m.tick(2));
  m.on_rx();
  EXPECT_FALSE(m.tick(2));  // fresh again
  EXPECT_FALSE(m.tick(2));
  EXPECT_FALSE(m.tick(2));
  EXPECT_TRUE(m.tick(2));
}

TEST(LinkMonitor, SlowerFrameRateThanCyclesIsFine)
{
  // The CANdle loop can run slower than the controller: a frame every 3rd
  // cycle must pass with timeout 20.
  LinkMonitor m;
  m.arm();
  for (int i = 0; i < 300; ++i) {
    if (i % 3 == 0) m.on_rx();
    EXPECT_FALSE(m.tick(20)) << "cycle " << i;
  }
}

TEST(LinkMonitor, ZeroTimeoutDisables)
{
  LinkMonitor m;
  m.arm();
  for (int i = 0; i < 100; ++i) EXPECT_FALSE(m.tick(0));
}

TEST(LinkMonitor, ArmForgetsOldFrames)
{
  // Frames that arrived before arm() (bring-up traffic) neither count as
  // fresh nor as stale: the first tick after arm() starts at "fresh".
  LinkMonitor m;
  m.on_rx();
  m.on_rx();
  m.arm();
  EXPECT_FALSE(m.tick(1));  // stale 1
  EXPECT_TRUE(m.tick(1));   // stale 2 > 1
  m.arm();
  EXPECT_FALSE(m.tick(1));
}

int main(int argc, char ** argv)
{
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
