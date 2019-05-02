// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include <vector>
#include <string>

size_t get_drive_speed(const std::string& folder);

std::vector<std::pair<std::string, size_t> > get_recording_folder_list();
