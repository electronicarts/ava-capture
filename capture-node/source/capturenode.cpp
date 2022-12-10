// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include "capturenode.hpp"
#include "ximeacameras.hpp"
#include "hardwaresync.hpp"
#include "drivebench.hpp"
#include "json.hpp"
#include "embedded_python.hpp"

#include <boost/filesystem.hpp>

#include <iomanip>
#include <iostream>
#include <iterator>

CaptureNode::CaptureNode(
	bool initializeWebcams, bool initializeAudio, bool initializeDummyCam, 
	const std::vector<std::string>& recording_folders) 
	: StateMachine<CaptureNodeState>(STATE_UNKNOWN), m_sync_active(false), m_shutdownrequested(false)
{
	m_external_sync_preview = false;
	m_external_sync_recording = false;

	m_first_update_sent = false;

	m_minimim_drive_speed = 40; // Do not use drives slower than this (MB/s)
	m_bandwidth_per_thread = 200; // MB/s
	m_global_framerate = 30; // frames/second
	m_global_pulse_duration = 2000; // us

	m_bitdepth_default = 8;
	m_bitdepth_maximum = 8;
	m_image_format_raw = false;

	std::cout << "Initializing hardware sync..." << std::endl;

	// Hardware Synch
	{
		// Initialize Hardware sync with default framerate
		if (PythonEngine::Instance().m_sync.get())
		{
			m_sync = PythonEngine::Instance().m_sync;
			PythonEngine::Instance().m_sync.reset();
		}

		if (m_sync.get() && m_sync->isOK())
		{
			m_sync->start(m_global_framerate, m_global_pulse_duration, false);
			m_sync_active = true;
			std::cout << "Initialized Hardware Synch on " << m_sync->port() << " to " << m_global_framerate << " Hz... (Pulse duration " << m_global_pulse_duration << " us)" << std::endl;
		}
		else
		{
			std::cout << "No Hardware Sync found" << std::endl;
		}
	}

	std::cout << "Computing drive speed..." << std::endl;

	// Benchmark disks, gather list of folders
	if (recording_folders.empty())
	{
		m_capture_folders = get_recording_folder_list();

		if (m_capture_folders.size()>1)
		{
			// Remove drives that are too slow to capture
			m_capture_folders.erase(std::remove_if(m_capture_folders.begin(),
				m_capture_folders.end(),
				[&](std::pair<std::string, size_t> x) {return x.second < m_minimim_drive_speed; }),
				m_capture_folders.end());
		}
	}
	else
	{	
		for (auto folder : recording_folders)
		{
			size_t speed = get_drive_speed(folder);
			if (speed)
			{
				m_capture_folders.push_back(std::make_pair(folder, speed));
				std::cout << "Recording folder: " << folder << " " << speed << " MB/s" << std::endl;
			}
		}
	}

	if (m_capture_folders.empty()) {
		std::cerr << "No suitable recording drives found" << std::endl;
		exit(1);
	}

	std::cout << "Initializing cameras..." << std::endl;

	// Initialize a webcam if it exists
	if (initializeWebcams)
	{ 
		std::vector<std::shared_ptr<Camera> > webcam_cameras = WebcamCamera::get_webcam_cameras();
		std::copy(webcam_cameras.begin(), webcam_cameras.end(), std::back_inserter(m_cameras));
	}

	// Initialize a dummy camera for testing
	if (initializeDummyCam)
	{ 
		std::vector<std::shared_ptr<Camera> > dummy_cameras = DummyCamera::get_dummy_cameras(2);
		std::copy(dummy_cameras.begin(), dummy_cameras.end(), std::back_inserter(m_cameras));
	}


#ifdef WITH_PORTAUDIO	
	// Enable first audio device
	if (initializeAudio)
	{
		m_cameras.push_back(std::make_shared<AudioCamera>());
	}
#endif

	CaptureNode::scan_for_new_devices();

	GotoState(STATE_PREVIEW);
}

CaptureNode::~CaptureNode()
{
	for (std::shared_ptr<Camera>& cam : m_cameras)
		cam->stop_capture();
}

bool CaptureNode::sync_connected() const 
{ 
	return (m_sync.get() && m_sync->isOK()); 
}

void CaptureNode::remove_invalid_devices()
{
	std::lock_guard<std::mutex> lock(m_mutex);

	// Remove any camera that has become invalid (and is not recording)
	m_cameras.erase(
		std::remove_if(m_cameras.begin(), m_cameras.end(), [](std::shared_ptr<Camera>& it) {return !it->is_valid(); }),
		m_cameras.end());
}

size_t CaptureNode::scan_for_new_devices()
{
	size_t new_count = 0;

	// Ximea Cameras
	std::vector<std::shared_ptr<Camera> > new_ximea_cameras;
	std::vector<std::string> removed_ximea_cameras;
	
	XimeaCamera::get_ximea_cameras(new_ximea_cameras, removed_ximea_cameras);
	
	if (!new_ximea_cameras.empty() || !removed_ximea_cameras.empty())
	{ 
		std::lock_guard<std::mutex> lock(m_mutex);

		// Cameras to invalidate
		std::for_each(removed_ximea_cameras.begin(), removed_ximea_cameras.end(), [this](const std::string& it) {

			std::shared_ptr<Camera> cam = cameraById(it.c_str());

			if (cam.get())
			{
				printf("Camera Disconnected : %s\n", cam->unique_id().c_str());
				cam->invalidate();
			}
		});

		// New cameras
		new_count = new_ximea_cameras.size();
		std::copy(new_ximea_cameras.begin(), new_ximea_cameras.end(), std::back_inserter(m_cameras));
	}

	return new_count;
}

void CaptureNode::setGlobalParams(const std::string& json)
{
	if (json.empty())
		return;

	// Parse global settings recieved from server at launch

	rapidjson::Document doc;
	doc.Parse(json.c_str());

	if (doc.HasMember("display_focus_peak"))
	{
		std::lock_guard<std::mutex> lock(m_mutex);
		for (auto& cam : m_cameras)
			cam->set_display_focus_peak(doc["display_focus_peak"].GetBool());
	}
	if (doc.HasMember("display_overexposed"))
	{
		std::lock_guard<std::mutex> lock(m_mutex);
		for (auto& cam : m_cameras)
			cam->set_display_overexposed(doc["display_overexposed"].GetBool());
	}
	if (doc.HasMember("display_histogram"))
	{
		std::lock_guard<std::mutex> lock(m_mutex);
		for (auto& cam : m_cameras)
			cam->set_display_histogram(doc["display_histogram"].GetBool());
	}
	if (doc.HasMember("bitdepth_avi"))
	{
		if (doc["bitdepth_avi"].GetInt() != m_bitdepth_default)
		{
			m_bitdepth_default = doc["bitdepth_avi"].GetInt();

			std::lock_guard<std::mutex> lock(m_mutex);
			for (auto& cam : m_cameras)
				if (!cam->recording())
					cam->set_bitdepth(m_bitdepth_default);
		}
	}
	if (doc.HasMember("bitdepth_single"))
	{
		m_bitdepth_maximum = doc["bitdepth_single"].GetInt();
	}
	if (doc.HasMember("image_format") && doc["image_format"].IsString())
	{
		m_image_format_raw = strcmp(doc["image_format"].GetString(),"raw")==0;
	}
	if (doc.HasMember("wb_R") && doc.HasMember("wb_G") && doc.HasMember("wb_B"))
	{
		std::lock_guard<std::mutex> lock(m_mutex);
		for (auto& cam : m_cameras)
			cam->updateColorBalance(doc["wb_R"].GetDouble(), doc["wb_G"].GetDouble(), doc["wb_B"].GetDouble());
	}

	if (doc.HasMember("frequency"))
	{
		int freq = 0;
		if (doc["frequency"].IsInt())
			freq = doc["frequency"].GetInt();
		if (doc["frequency"].IsString())
			freq = atoi(doc["frequency"].GetString()); // fix for bad JSON from server

		set_global_framerate(freq, 
			doc.HasMember("pulse_duration") ? doc["pulse_duration"].GetInt() : 0, 
			doc.HasMember("external_sync") ? doc["external_sync"].GetBool() : false);

		std::lock_guard<std::mutex> lock(m_mutex);

		// Enable sync on all cameras
		for (auto& cam : m_cameras)
			cam->set_hardware_sync_freq(freq);
	}

	if (doc.HasMember("sync_freq") && doc.HasMember("pulse_duration"))
	{
		// Set hardware sync frequency
		int sync_freq = doc["sync_freq"].GetInt();
		int duration = doc["pulse_duration"].GetInt();

		set_global_framerate(sync_freq, duration, 
			doc.HasMember("external_sync") ? doc["external_sync"].GetBool() : false);

		std::lock_guard<std::mutex> lock(m_mutex);

		// Activate sync on all cameras
		for (auto& cam : m_cameras)
			cam->set_hardware_sync_freq(sync_freq);
	}

	if (doc.HasMember("camera_params") && doc["camera_params"].IsArray())
	{
		const rapidjson::Value& params = doc["camera_params"];
		for (rapidjson::SizeType i = 0; i < params.Size(); i++)
		{
			if (params[i].HasMember("unique_id"))
			{
				std::string camera_name = params[i]["unique_id"].GetString();

				// TODO Camera ROI

				auto it = cameraById(camera_name.c_str());
				if (it)
				{ 
					for (rapidjson::Value::ConstMemberIterator itr = params[i].MemberBegin(); itr != params[i].MemberEnd(); ++itr)
					{
						// Apply each parameter to the camera

						if (itr->value.IsBool() && (strcmp(itr->name.GetString(),"using_sync"))==0) // special case
						{
							it->set_hardware_sync(itr->value.GetBool(), global_framerate());
						}
						else if (itr->value.IsDouble())
						{
							it->param_set(itr->name.GetString(), itr->value.GetDouble());
						}
						else if (itr->value.IsInt())
						{
							// generic parameters passed as Inegers are converted to float for param_set
							it->param_set(itr->name.GetString(), itr->value.GetInt());
						}
					}
				}			
			}
		}
	}
}

std::shared_ptr<Camera> CaptureNode::cameraById(const char * unique_id)
{
	for (auto c : m_cameras)
	{
		if (c->unique_id() == unique_id)
			return c;
	}
	return std::shared_ptr<Camera>();
}

const std::vector<std::shared_ptr<Camera> > CaptureNode::cameraList()
{ 
	std::lock_guard<std::mutex> lock(m_mutex);

	return  std::vector<std::shared_ptr<Camera> >(m_cameras);
}

std::string CaptureNode::sync_port() const
{
	if (m_sync.get())
		return m_sync->port();
	return "";
}

void CaptureNode::set_global_framerate(int freq, int duration_us, bool external_sync)
{
	// Cannot be called while recording

	if (duration_us)
		m_global_pulse_duration = duration_us;
	m_global_framerate = freq;

	m_external_sync_preview = false; // TODO: option to be added to UI
	m_external_sync_recording = external_sync;

	if (m_sync_active && m_sync.get())
	{
		std::cout << "Set global framerate to " << freq << std::endl;
		if (duration_us)
			std::cout << "Set global pulse duration to " << duration_us << std::endl;
		if (m_external_sync_preview)
			std::cout << "Using external sync: Preview" << std::endl;
		if (m_external_sync_recording)
			std::cout << "Using external sync: Recording" << std::endl;

		m_sync->start(m_global_framerate, m_global_pulse_duration, m_external_sync_preview);
	}
}

bool CaptureNode::can_record() const
{
	return m_recording_cameras.empty() && !m_capture_folders.empty();
}

std::vector<std::string> CaptureNode::get_take_recording_folders()
{
	namespace fs = boost::filesystem;

	std::vector<std::string> folders;

	std::string timestamp;
	{
		auto t = std::time(nullptr);
		auto tm = *std::localtime(&t);

		std::ostringstream oss;
		oss << std::put_time(&tm, "%Y%m%d_%H%M%S");
		timestamp = oss.str();
	}

	for (auto& it : m_capture_folders)
	{
		fs::path new_folder = fs::path(it.first) / timestamp;
		folders.push_back(new_folder.string());

		if (!fs::exists(new_folder))
			fs::create_directories(new_folder);
	}

	return folders;
}

void CaptureNode::record_image_sequence(int frame_count)
{
	setBurstCount(frame_count);
	if (frame_count>1)
	{
		GotoState(STATE_BURST_PREPARE1);
		GotoState(STATE_BURST_PREPARE2);
		GotoState(STATE_BURST_START);
		GotoState(STATE_BURST_FINALIZE);
	}
	else
	{
		GotoState(STATE_SINGLESHOT_PREPARE1);
		GotoState(STATE_SINGLESHOT_PREPARE2);
		GotoState(STATE_SINGLESHOT_START);
		GotoState(STATE_SINGLESHOT_FINALIZE);
	}
	GotoState(STATE_PREVIEW);
}

void CaptureNode::start_recording_all()
{
	GotoState(STATE_CONTINUOUS_PREPARE1);
	GotoState(STATE_CONTINUOUS_PREPARE2);
	GotoState(STATE_CONTINUOUS_START);	
}

void CaptureNode::prepare_single()
{
	std::cout << "STATUS> Prepare Single" << std::endl;

	namespace fs = boost::filesystem;

	// Record to the fastest drive found
	const std::vector<std::string> all_folders = get_take_recording_folders();

	std::cout << "Recording " << m_burstCount << " frame(s)" << std::endl;

	m_recording_cameras.clear();

	std::lock_guard<std::mutex> lock(m_mutex);

	for (auto& cam : m_cameras)
	{
		if (cam->capturing() && !cam->is_audio_only()) // Audio only devices not recorded in single-frame
		{
			cam->m_debug_in_capture_cycle = true;
			m_recording_cameras.push_back(cam);
		}
	}

	for (auto& cam : m_recording_cameras)
	{
		cam->m_debug_timings = true;
		cam->m_prepare_recording = true;
	}

	// Change bitdepth for single capture
	for (auto& cam : m_recording_cameras)
	{
		if (cam->set_bitdepth(m_bitdepth_maximum))
			cam->block_until_next_frame(0.240);
		cam->set_record_as_raw(m_image_format_raw);
	}

	std::cout << "Recording Cameras Available " << m_recording_cameras.size() << " camera(s)" << std::endl;

	// Begin recording
	int i=0;
	for (auto& cam : m_recording_cameras)
	{
		if (m_burstCount>1)
		{
			// Burst: send all folders, so that each frame gets written to a different drive

			cam->start_recording(all_folders, true, m_burstCount); // Wait for trigger
		}
		else
		{
			// Single frame: send one folder, different for each camera

			std::vector<std::string> folders;
			folders.push_back(all_folders[(i++)%all_folders.size()]);

			std::cout << "--------- BEGIN PREPARE SINGLE FILE ---------" << std::endl;
			
			cam->start_recording(folders, true, m_burstCount); // Wait for trigger
		}
	}
}

void CaptureNode::recording_trigger()
{
	std::cout << "STATUS> Trigger" << std::endl;

	// Trigger Recording on all cameras that have no hardware sync
	for (auto& cam : m_recording_cameras)
	{
		if (!cam->using_hardware_sync())
			cam->software_trigger();
	}
	
	// Make sure there is a 250ms gap and restart sync
	if (sync_connected())
	{
		boost::this_thread::sleep_for(boost::chrono::milliseconds(250));
		start_recording_sync();
	}
}

void CaptureNode::finalize_single()
{
	std::cout << "STATUS> Finalize Single" << std::endl;

	// Create new json document, to contain summary from all cameras
	shared_json_doc all_cameras_doc(new rapidjson::Document());
	all_cameras_doc->SetObject();
	rapidjson::Value cameras(rapidjson::kArrayType);

	// Block until cameras have stopped recording
	{
		int status_count = 0;
		for (auto& cam : m_recording_cameras)
		{
			cam->start_capture();
			while (cam->recording()) {
				// std::cout << "-------{} Camera recording" << std::endl;
				boost::this_thread::sleep_for(boost::chrono::milliseconds(200));
				if (status_count > 20)
				{
					cam->stop_capture();
				}
				else
				{
					status_count += 1;
				}
				std::cout << "-------{} Camera recording" << status_count << std::endl;
			}
		}
	}

	std::cout << "-------{} Camera not recording" << std::endl;
	
	for (auto& cam : m_recording_cameras)
		cam->m_debug_timings = false;

	// Get last recording summary from all cameras
	{
		for (auto& cam : m_recording_cameras)
		{
			shared_json_doc cam_summary = cam->last_summary();
			if (cam_summary)
			{
				// Merge this camera's json data into the common document
				rapidjson::Value cam_root(rapidjson::kObjectType);
				cam_root.CopyFrom(*cam_summary.get(), all_cameras_doc->GetAllocator());
				cameras.PushBack(cam_root, all_cameras_doc->GetAllocator());
			}

			cam->m_debug_in_capture_cycle = false;
			cam->set_bitdepth(m_bitdepth_default);
		}
	}

	std::cout << "-------{} Finalize json structure" << std::endl;

	// Finalize json structure
	all_cameras_doc->AddMember("cameras", cameras, all_cameras_doc->GetAllocator());

	// m_recording_cameras.clear();

	m_last_summary = all_cameras_doc;

	stop_recording_all(get_take_recording_folders());
}

void CaptureNode::prepare_multi_stage1()
{
	std::cout << "STATUS> Prepare Multi" << std::endl;

	m_recording_cameras.clear();

	std::vector<std::pair<std::shared_ptr<Camera>, int> > to_record;

	{
		std::lock_guard<std::mutex> lock(m_mutex);

		// List of cameras to record, with estimated bandwidth
		for (auto& cam : m_cameras)
		{
			if (cam->capturing())
			{
				cam->m_debug_in_capture_cycle = true;

				// Bitdepth is the same as the continuous preview, we don't need to change it
				//cam->set_bitdepth(m_bitdepth_default);

				cam->set_record_as_raw(true); // TODO Option to choose between .ava and .avi

				int nthreads = (int)(1 + (cam->bandwidth() / 1024 / 1024 / m_bandwidth_per_thread));

				std::cout << "RECORD " << cam->unique_id() << " BW:" << (cam->bandwidth()/1024/1024) << "MB/s Threads:" << nthreads << std::endl; // DEBUG

				to_record.push_back(std::make_pair(cam, nthreads));
			}
		}
	}

	std::sort(to_record.begin(), to_record.end(), [](std::pair < std::shared_ptr<Camera>, int>& a, std::pair < std::shared_ptr<Camera>, int>& b) {return a.second > b.second; });

	// Sort list of folders
	auto folders = get_take_recording_folders();

	// Start record on each camera, passing the folder to use
	int i = 0;
	for (auto it : to_record)
	{
		std::vector<std::string> cam_folders;
		for (int t = 0;t < it.second;t++, i++)
			cam_folders.push_back(folders[i%folders.size()]);

		for (auto f : cam_folders)
			std::cout << "Recording " << it.first->unique_id() << " to " << f << std::endl; // DEBUG

		it.first->start_recording(cam_folders, true);
		m_recording_cameras.push_back(it.first);
	}

	for (auto& cam : m_recording_cameras)
		cam->m_debug_timings = true;
}

void CaptureNode::prepare_multi_stage2()
{
	for (auto& cam : m_recording_cameras)
	{
		cam->remove_recording_hold();
	}

	if (sync_connected())
	{
		stop_sync(); // Stop preview pulses
	}
}

void CaptureNode::stop_recording_all()
{
	std::cout << "STATUS> Stop Recording" << std::endl;

	// Create new json document, to contain summary from all cameras
	shared_json_doc all_cameras_doc(new rapidjson::Document());
	all_cameras_doc->SetObject();
	rapidjson::Value cameras(rapidjson::kArrayType);

	for (auto& cam : m_recording_cameras)
	{
		cam->stop_recording();
	}

	for (auto& cam : m_recording_cameras)
	{
		shared_json_doc cam_summary = cam->last_summary();

		if (cam_summary)
		{ 
			// Merge this camera's json data into the common document
			rapidjson::Value cam_root(rapidjson::kObjectType);
			cam_root.CopyFrom(*cam_summary.get(), all_cameras_doc->GetAllocator());
			cameras.PushBack(cam_root, all_cameras_doc->GetAllocator());
		}
	}

	for (auto& cam : m_recording_cameras)
	{
		cam->m_debug_in_capture_cycle = false;
		cam->set_bitdepth(m_bitdepth_default);
	}

	for (auto& cam : m_recording_cameras)
		cam->m_debug_timings = false;

	// Finalize json structure
	all_cameras_doc->AddMember("cameras", cameras, all_cameras_doc->GetAllocator());

	m_recording_cameras.clear();

	m_last_summary = all_cameras_doc;
}

void CaptureNode::stop_recording_all(std::vector<std::string> folders)
{
	std::cout << "STATUS> Stop Recording" << std::endl;

	// Create new json document, to contain summary from all cameras
	shared_json_doc all_cameras_doc(new rapidjson::Document());
	all_cameras_doc->SetObject();
	rapidjson::Value cameras(rapidjson::kArrayType);

	for (auto& cam : m_recording_cameras)
	{
		cam->stop_recording(folders);
	}

	for (auto& cam : m_recording_cameras)
	{
		shared_json_doc cam_summary = cam->last_summary();

		if (cam_summary)
		{ 
			// Merge this camera's json data into the common document
			rapidjson::Value cam_root(rapidjson::kObjectType);
			cam_root.CopyFrom(*cam_summary.get(), all_cameras_doc->GetAllocator());
			cameras.PushBack(cam_root, all_cameras_doc->GetAllocator());
		}
	}

	for (auto& cam : m_recording_cameras)
	{
		cam->m_debug_in_capture_cycle = false;
		cam->set_bitdepth(m_bitdepth_default);
	}

	for (auto& cam : m_recording_cameras)
		cam->m_debug_timings = false;

	// Finalize json structure
	all_cameras_doc->AddMember("cameras", cameras, all_cameras_doc->GetAllocator());

	m_recording_cameras.clear();

	m_last_summary = all_cameras_doc;
}

void CaptureNode::stop_sync()
{
	if (m_sync.get() && m_sync_active)
	{
		m_sync->stop();
		m_sync_active = false;
	}
}

void CaptureNode::start_recording_sync()
{
	if (m_sync.get())
	{
		m_sync->start(m_global_framerate, m_global_pulse_duration, m_external_sync_recording);
		m_sync_active = true;
	}
}

void CaptureNode::start_preview_sync()
{
	if (m_sync.get())
	{
		m_sync->start(m_global_framerate, m_global_pulse_duration, m_external_sync_preview);
		m_sync_active = true;
	}
}

void CaptureNode::GenericMessage(const std::string& msg)
{
	//printf("DEBUG> Generic Message Received: %s\n", msg.c_str());

	for (auto listener : PythonEngine::Instance().m_notification_listeners)
	{
		listener->receiveMessage(msg.c_str());
	}
}

void CaptureNode::ChangeState(CaptureNodeState fromState, CaptureNodeState toState)
{
	printf("DEBUG> State Change from %s to %s\n", stateToString(fromState), stateToString(toState));

	for (auto listener : PythonEngine::Instance().m_notification_listeners)
	{
		listener->changeState(stateToString(toState));
	}

	switch (toState) {
	case STATE_PREVIEW:
		start_preview_sync();
		break;

	case STATE_SINGLESHOT_PREPARE1:
	case STATE_BURST_PREPARE1:
		prepare_single();
		break;
	case STATE_SINGLESHOT_PREPARE2:
	case STATE_BURST_PREPARE2:
		prepare_multi_stage2();
		break;
	case STATE_SINGLESHOT_START:
	case STATE_BURST_START:
		recording_trigger();
		break;
	case STATE_SINGLESHOT_FINALIZE:
	case STATE_BURST_FINALIZE:
		finalize_single();
		break;

	case STATE_CONTINUOUS_PREPARE1:
		prepare_multi_stage1();
		break;
	case STATE_CONTINUOUS_PREPARE2:
		prepare_multi_stage2();
		break;
	case STATE_CONTINUOUS_START:
		recording_trigger();
		break;
	case STATE_STOP_SYNC:
		stop_sync(); // Stop recording pulses
		break;
	case STATE_STOP:
		stop_recording_all();
		break;
	}
}

static const char * stateToString(CaptureNodeState s)
{
	switch (s) {
#define BUILD_ENUM_CASE(s) case s: return #s
	BUILD_ENUM_CASE(STATE_PREVIEW);
	BUILD_ENUM_CASE(STATE_SINGLESHOT_PREPARE1);
	BUILD_ENUM_CASE(STATE_SINGLESHOT_PREPARE2);
	BUILD_ENUM_CASE(STATE_SINGLESHOT_START);
	BUILD_ENUM_CASE(STATE_SINGLESHOT_FINALIZE);
	BUILD_ENUM_CASE(STATE_BURST_PREPARE1);
	BUILD_ENUM_CASE(STATE_BURST_PREPARE2);
	BUILD_ENUM_CASE(STATE_BURST_START);
	BUILD_ENUM_CASE(STATE_BURST_FINALIZE);
	BUILD_ENUM_CASE(STATE_CONTINUOUS_PREPARE1);
	BUILD_ENUM_CASE(STATE_CONTINUOUS_PREPARE2);
	BUILD_ENUM_CASE(STATE_CONTINUOUS_START);
	BUILD_ENUM_CASE(STATE_STOP_SYNC);
	BUILD_ENUM_CASE(STATE_STOP);
	BUILD_ENUM_CASE(STATE_EXIT);	
#undef BUILD_ENUM_CASE
	default: return "UNKNOWN";
	}
}
