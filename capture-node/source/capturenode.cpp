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

CaptureNode::CaptureNode(bool initializeWebcams, bool initializeAudio, const std::string& recording_folder) 
	: m_sync_active(false), m_shutdownrequested(false)
{
	m_external_sync_always = false;
	m_external_sync_while_recording = false;

	m_first_update_sent = false;

	m_minimim_drive_speed = 40; // Do not use drives slower than this (MB/s)
	m_bandwidth_per_thread = 200; // MB/s
	m_global_framerate = 30; // frames/second
	m_global_pulse_duration = 2000; // us

	std::cout << "Initializing hardware synch..." << std::endl;

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
#ifdef WIN32
	if (recording_folder.empty())
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
#else
	#pragma message("TODO Implement in Linux")
#endif 	
	{
		size_t speed = get_drive_speed(recording_folder);

		if (speed)
		{
			m_capture_folders.push_back(std::make_pair(recording_folder, speed));
			std::cout << "Recording folder: " << recording_folder << " " << speed << " MB/s" << std::endl;
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

#ifdef WITH_PORTAUDIO	
	// Enable first audio device
	if (initializeAudio)
	{
		m_cameras.push_back(std::make_shared<AudioCamera>());
	}
#endif

	CaptureNode::scan_for_new_devices();
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
						if (itr->value.IsBool() && (strcmp(itr->name.GetString(),"using_sync"))==0) // special case
						{
							it->set_hardware_sync(itr->value.GetBool(), global_framerate());
						}
						if (itr->value.IsDouble())
						{
							it->param_set(itr->name.GetString(), itr->value.GetDouble());
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
	if (duration_us)
		m_global_pulse_duration = duration_us;
	m_global_framerate = freq;

	// TEMPORARY options to be added to UI
	m_external_sync_always = false;
	m_external_sync_while_recording = external_sync;

	if (m_sync_active && m_sync.get())
	{
		std::cout << "Set global framerate to " << freq << std::endl;
		if (duration_us)
			std::cout << "Set global pulse duration to " << duration_us << std::endl;
		if (m_external_sync_always)
			std::cout << "Using external sync: Always" << std::endl;
		if (m_external_sync_while_recording)
			std::cout << "Using external sync: While Recording" << std::endl;

		m_sync->start(m_global_framerate, m_global_pulse_duration, m_external_sync_always);
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
	prepare_single(frame_count);
	prepare_multi_stage2();
	recording_trigger();
	finalize_single();
}

void CaptureNode::start_recording_all()
{
	prepare_multi_stage1();
	prepare_multi_stage2();
	recording_trigger();
}

void CaptureNode::prepare_single(int count)
{
	std::cout << "STATUS> Prepare Single" << std::endl;

	namespace fs = boost::filesystem;

	// Record to the fastest drive found
	std::vector<std::string> folders;
	folders.push_back(get_take_recording_folders()[0]);

	if (!fs::exists(folders[0]))
		fs::create_directories(folders[0]);

	std::cout << "Recording " << count << " frame(s) to " << folders[0] << std::endl;

	m_recording_cameras.clear();

	std::lock_guard<std::mutex> lock(m_mutex);

	for (auto& cam : m_cameras)
	{
		if (cam->capturing())
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
	}

	// Begin recording
	for (auto& cam : m_recording_cameras)
	{
		cam->start_recording(folders, true, count); // Wait for trigger
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
	
	// Pause Sync for 300 ms
	if (sync_connected())
	{
		pause_sync();
		boost::this_thread::sleep_for(boost::chrono::milliseconds(250));
		resume_sync(true);
	}
}

shared_json_doc CaptureNode::finalize_single()
{
	std::cout << "STATUS> Finalize Single" << std::endl;

	// Create new json document, to contain summary from all cameras
	shared_json_doc all_cameras_doc(new rapidjson::Document());
	all_cameras_doc->SetObject();
	rapidjson::Value cameras(rapidjson::kArrayType);

	// Block until cameras have stopped recording
	{
		for (auto& cam : m_recording_cameras)
		{
			while (cam->recording()) {
				boost::this_thread::sleep_for(boost::chrono::milliseconds(10));
			}
		}
	}
	
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

	// Finalize json structure
	all_cameras_doc->AddMember("cameras", cameras, all_cameras_doc->GetAllocator());

	m_recording_cameras.clear();

	return all_cameras_doc;
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
}

shared_json_doc CaptureNode::stop_recording_all()
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

	return all_cameras_doc;
}

void CaptureNode::pause_sync()
{
	if (m_sync.get() && m_sync_active)
	{
		m_sync->stop();
		m_sync_active = false;
	}
}

void CaptureNode::resume_sync(bool recording)
{
	if (m_sync.get() && !m_sync_active)
	{
		m_sync->start(m_global_framerate, m_global_pulse_duration, m_external_sync_always || (recording&&m_external_sync_while_recording));
		m_sync_active = true;
	}
}
