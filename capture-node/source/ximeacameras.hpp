// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include "cameras.hpp"

#include <string>
#include <memory>
#include <vector>
#include <set>
#include <boost/thread/thread.hpp>

#include <mutex>

typedef void *HANDLE;
class XimeaCamera;

class AcquisitionGuard
{
	// For the Ximea cameras, some settings can only be changed while the acquisition is OFF. 
	// Since the acquisition is almost always ON during regular use (preview or recording), this
	// class can be used to temporarily halt and resume acquisition around these settings changes.
	// Note: AcquisitionGuard allows recursion.
public:	
	struct Context {

		Context() 
			: recursion(0), needs_mutex(false) {}

		bool isAcquisitionPaused() const {return needs_mutex;}

		int recursion;
		bool needs_mutex; // When the guard needs to stop/start acquisition to change a setting, 
						  // we need to make sure the capture thread does not keep the mutex for itself in a busy loop.
	};
public:
	AcquisitionGuard(XimeaCamera* t);
	~AcquisitionGuard();
private:
	bool was_capturing;
	XimeaCamera* _t;
};

class XimeaCamera : public Camera
{
public:
	XimeaCamera(int deviceId);
	~XimeaCamera();

	static void get_ximea_cameras(std::vector<std::shared_ptr<Camera> >& new_camers, std::vector<std::string>& removed_ids);

protected:
	int get_param_int(const char * param, bool silent=false);
	float get_param_float(const char * param, bool silent = false);
	std::string get_param_str(const char * param);

	void set_param_int(const char * param, int value);
	void set_param_float(const char * param, float value);

	virtual void set_hardware_sync(bool enable, int framerate) override;
	virtual void set_hardware_sync_freq(int framerate) override;

	virtual bool has_lens_control() override;
	virtual void af_enable() override;
	virtual void af_move_focus(int value) override;
	virtual bool af_at_limit() override;
	virtual void fill_params_list();
	virtual void param_set(const char * name, float value) override;
	virtual float param_get(const char * name) override;

	virtual void start_capture() override;
	virtual void stop_capture() override;

	virtual bool set_bitdepth(int bitdepth) override;

	virtual void set_roi(int x_min, int y_min, int x_max, int y_max) override;
	virtual void reset_roi() override;

	virtual bool is_valid() const override;
	virtual void invalidate() override;

private:
	void captureThread();

	void setBandwidth(unsigned long long limit_mb = 0);

	bool isXiC() const;
	bool isXiQ() const;

	int m_original_width;
	int m_original_height;

	HANDLE m_deviceHandle;
	std::string m_device_name;
	boost::thread capture_thread;

	bool m_has_lens_control;
	unsigned int m_max_bandwidth;

	int m_last_bitdepth;

	static std::set<std::string> s_unique_id_list;

	std::recursive_mutex m_mutex;     // mutex to protect against concurrent changes to a camera in the ximea api

	friend class AcquisitionGuard;
	AcquisitionGuard::Context acq_ctx;
};