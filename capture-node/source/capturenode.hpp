// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include "cameras.hpp"

#include <vector>
#include <memory>
#include <string>
#include <mutex>

class CaptureNode
{
public:
	CaptureNode(bool initializeWebcams, const std::string& recording_folder = std::string());
	~CaptureNode();

	const std::vector<std::shared_ptr<Camera> > cameraList();
	std::shared_ptr<Camera> cameraById(const char * unique_id);

	void setGlobalParams(const std::string& json);

	bool sync_ok() const { return m_sync_active; }
	std::string sync_port() const;
	int global_framerate() const { return m_global_framerate; }
	int global_pulse_duration() const { return m_global_pulse_duration; }

	void set_global_framerate(int freq, int duration_us, bool external_sync);

	void record_image_sequence(int frame_count); // Execute all steps to capture a single image
	void start_recording_all(); // Execute all steps to start recording
	shared_json_doc stop_recording_all();

	// Single Image Steps
	void prepare_single(int count = 1);
	shared_json_doc finalize_single();

	// Multi Image Steps
	void prepare_multi_stage1();
	void prepare_multi_stage2();

	void recording_trigger(); // to be called after prepare
	void pause_sync();
	void resume_sync(bool recording);

	void shutdown() { m_shutdownrequested = true; }
	bool shutdown_requested() const { return m_shutdownrequested; }

	size_t scan_for_new_devices();
	void remove_invalid_devices();

	bool can_record() const;

	const std::vector<std::pair<std::string, size_t> >& capture_folders() const { return m_capture_folders; }

protected:
	std::vector<std::string> get_take_recording_folders();

private:
	bool m_first_update_sent;
	size_t m_minimim_drive_speed;
	size_t m_bandwidth_per_thread;
	
	bool m_sync_active;
	int m_global_framerate;
	int m_global_pulse_duration;
	bool m_external_sync_always;
	bool m_external_sync_while_recording;
	int m_bitdepth_default;
	int m_bitdepth_maximum;

	std::vector<std::shared_ptr<Camera> > m_cameras;
	std::vector<std::shared_ptr<Camera> > m_recording_cameras; // cameras currently recording

	std::shared_ptr<class IHardwareSync> m_sync;

	std::vector<std::pair<std::string, size_t> > m_capture_folders;

	std::mutex m_mutex;

	bool m_shutdownrequested;
};
