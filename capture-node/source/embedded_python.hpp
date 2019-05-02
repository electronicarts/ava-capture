// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include <memory>
#include <string>
#include <vector>

class INotificationListener
{
public:
	virtual ~INotificationListener() {}
	virtual void changeState(const char * state) const = 0;
	virtual void receiveMessage(const char * msg) const = 0;
};

class PythonEngine
{
public:
	~PythonEngine();

	static void Init(char * programName);
	static void RunScript(const std::string& str);

	static PythonEngine & Instance();

	// Global handlers, can be initialized before CaptureNode
	std::shared_ptr<class IHardwareSync> m_sync;
	std::vector<std::shared_ptr<class INotificationListener> > m_notification_listeners;

protected:
	PythonEngine();
	void PostContructor(char * programName);

private:
	static std::unique_ptr<PythonEngine> m_Instance;
	void *mainstate;
};
