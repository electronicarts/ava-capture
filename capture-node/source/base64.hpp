// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include <string>
#include <vector>

std::string base64encode(const std::string& str);
std::string base64encode(const std::vector<unsigned char>& buf);
