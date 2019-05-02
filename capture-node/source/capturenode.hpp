// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include "cameras.hpp"
#include "statemachine.hpp"

#include <vector>
#include <memory>
#include <string>
#include <mutex>

enum CaptureNodeState
{
	STATE_UNKNOWN = 0,
	STATE_PREVIEW,
	STATE_STOP_SYNC,
	STATE_STOP,

	STATE_SINGLESHOT_PREPARE1,
	STATE_SINGLESHOT_PREPARE2,
	STATE_SINGLESHOT_START,
	STATE_SINGLESHOT_FINALIZE,

	STATE_BURST_PREPARE1,
	STATE_BURST_PREPARE2,
	STATE_BURST_START,
	STATE_BURST_FINALIZE,

	STATE_CONTINUOUS_PREPARE1,
	STATE_CONTINUOUS_PREPARE2,
	STATE_CONTINUOUS_START,

	STATE_EXIT,
};

static const char * stateToString(CaptureNodeState s);

class CaptureNode : public StateMachine<CaptureNodeState>
{
public:
	CaptureNode(bool initializeWebcams, bool initializeAudio, bool initializeDummyCam, 
		const std::vector<std::string>& recording_folders = std::vector<std::string>());
	~CaptureNode();

	const std::vector<std::shared_ptr<Camera> > cameraList();
	std::shared_ptr<Camera> cameraById(const char * unique_id);

	void setGlobalParams(const std::string& json);

	bool sync_connected() const;
	std::string sync_port() const;

	int global_framerate() const { return m_global_framerate; }
	int global_pulse_duration() const { return m_global_pulse_duration; }

	void set_global_framerate(int freq, int duration_us, bool external_sync);

	void record_image_sequence(int frame_count); // Execute all steps to capture a single image
	void start_recording_all(); // Execute all steps to start recording
	void stop_recording_all();

	shared_json_doc get_last_summary() const { return m_last_summary;  }

	// Single Image Steps
	void prepare_single();
	void finalize_single();

	// Multi Image Steps
	void prepare_multi_stage1();
	void prepare_multi_stage2();

	void recording_trigger(); // to be called after prepare

	// start/stop sync signal
	void stop_sync();
	void start_recording_sync();
	void start_preview_sync();

	void shutdown() { m_shutdownrequested = true; }
	bool shutdown_requested() const { return m_shutdownrequested; }

	size_t scan_for_new_devices();
	void remove_invalid_devices();

	bool can_record() const;

	void setBurstCount(int c) { m_burstCount = c; }
	int getBurstCount() const {return m_burstCount; }

	const std::vector<std::pair<std::string, size_t> >& capture_folders() const { return m_capture_folders; }

	void GenericMessage(const std::string& msg);

protected:
	virtual void ChangeState(CaptureNodeState fromState, CaptureNodeState toState) override;

	std::vector<std::string> get_take_recording_folders();

private:
	bool m_first_update_sent;
	size_t m_minimim_drive_speed;
	size_t m_bandwidth_per_thread;
	
	bool m_sync_active;
	int m_global_framerate;
	int m_global_pulse_duration;
	bool m_external_sync_preview;
	bool m_external_sync_recording;
	int m_bitdepth_default;
	int m_bitdepth_maximum;
	int m_burstCount;
	bool m_image_format_raw;

	std::vector<std::shared_ptr<Camera> > m_cameras;
	std::vector<std::shared_ptr<Camera> > m_recording_cameras; // cameras currently recording

	std::shared_ptr<class IHardwareSync> m_sync;

	std::vector<std::pair<std::string, size_t> > m_capture_folders;

	std::mutex m_mutex;

	bool m_shutdownrequested;

	shared_json_doc m_last_summary;
};
