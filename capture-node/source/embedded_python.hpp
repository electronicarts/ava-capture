// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include <memory>
#include <string>

class PythonEngine
{
public:
	~PythonEngine();

	static void Init(char * programName);
	static void RunScript(const std::string& str);

	static PythonEngine & Instance();

	// Global handlers, can be initialized before CaptureNode
	std::shared_ptr<class IHardwareSync> m_sync;

protected:
	PythonEngine();
	void PostContructor(char * programName);

private:
	static std::unique_ptr<PythonEngine> m_Instance;
	void *mainstate;
};
