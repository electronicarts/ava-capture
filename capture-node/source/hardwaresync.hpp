// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include <string>

class IHardwareSync
{
public:
	virtual ~IHardwareSync() {}

	virtual bool isOK() const { return false; }
	virtual void start(int framerate, int pulse_duration, bool external_sync) = 0;
	virtual void stop() = 0;
	virtual std::string port() const = 0;
};
