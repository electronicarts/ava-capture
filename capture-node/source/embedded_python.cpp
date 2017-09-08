// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

// we do this so that python doesn't add _d to the lib name
#ifdef _DEBUG
#undef _DEBUG
#include <Python.h>
#define _DEBUG
#else
#include <Python.h>
#endif

#include "embedded_python.hpp"
#include "hardwaresync.hpp"

#include <iostream>

std::unique_ptr<PythonEngine> PythonEngine::m_Instance;

class ScopedPythonLock {
public:
	ScopedPythonLock() {
		gstate = PyGILState_Ensure();
	}
	~ScopedPythonLock() {
		PyGILState_Release(gstate);
	}
private:
	PyGILState_STATE gstate;
};

class HardwareSyncPythonWrapper : public IHardwareSync
{
public:
	HardwareSyncPythonWrapper(PyObject * obj) : handler(obj)
	{
		Py_INCREF(handler);
	}
	~HardwareSyncPythonWrapper()
	{
		Py_DECREF(handler);
		handler = 0;
	}
	bool isOK() const override
	{
		ScopedPythonLock lock;

		PyObject* ret = PyObject_CallMethod(handler, "is_active", 0);
		return !!PyObject_IsTrue(ret);
	}
	void start(int framerate, int pulse_duration, bool external_sync) override
	{
		ScopedPythonLock lock;

		PyObject_CallMethod(handler, "start", "(i,i,i)", framerate, pulse_duration, external_sync?1:0);
	}
	void stop() override
	{
		ScopedPythonLock lock;

		PyObject_CallMethod(handler, "stop", 0);
	}
	std::string port() const override
	{
		if (!PyObject_HasAttrString(handler, "port"))
			return std::string();

		PyObject* ret2 = PyObject_GetAttrString(handler, "port");

		Py_ssize_t len = 0;
		char * buffer = 0;
		PyString_AsStringAndSize(ret2, &buffer, &len);

		return std::string(buffer);
	}
private:
	PyObject * handler;
};

static PyObject *
avacapture_set_sync(PyObject *self, PyObject *args)
{
	// Register handler for the Hardware Sync

	PyObject * handler = 0;

	if (!PyArg_ParseTuple(args, "O", &handler))
		return NULL;

	if (handler)
	{
		// Store the handler in a shared_ptr, to be picked up by CaptureNode
		PythonEngine::Instance().m_sync.reset(new HardwareSyncPythonWrapper(handler));
	}

	int sts = 0;
	return Py_BuildValue("i", sts);
}

static PyMethodDef AvaCaptureMethods[] = {
	{ "set_sync", avacapture_set_sync, METH_VARARGS, "Set hardware sync handler." },
	{NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initavacapture(void)
{
	(void)Py_InitModule("avacapture", AvaCaptureMethods);
}

PythonEngine::PythonEngine() : mainstate(0)
{

}

void PythonEngine::PostContructor(char * programName)
{
	Py_NoSiteFlag = 1;
	Py_SetProgramName(programName);
#ifdef WIN32	
	Py_SetPythonHome(".");
#endif
	Py_InitializeEx(0);

	PyEval_InitThreads();
	
	mainstate = PyThreadState_Swap(NULL);
	PyEval_ReleaseLock();

	{
		ScopedPythonLock lock;
		initavacapture(); // Register our avacapture Python module
	}

	RunScript("import sys\nimport os\nsys.path.append(os.getcwd())\nsys.path.append('./site-packages')\nimport autorun\n");
}

PythonEngine::~PythonEngine()
{
	PyEval_AcquireLock();
	PyThreadState_Swap((PyThreadState*)mainstate);
	Py_Finalize();
}

PythonEngine & PythonEngine::Instance()
{
	return *m_Instance.get();
}

void PythonEngine::Init(char * programName)
{
	m_Instance.reset(new PythonEngine()); // call to Instance() is not valid inside constructor
	m_Instance->PostContructor(programName); // call to Instance() will be valid here
}

void PythonEngine::RunScript(const std::string& str)
{
	ScopedPythonLock lock;

	PyRun_SimpleString(str.c_str());
}
