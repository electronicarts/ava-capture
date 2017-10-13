// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include "ximeacameras.hpp"

#ifdef WIN32
#include "xiApi.h"       // Windows
#else
#include <m3api/xiApi.h> // Linux, OSX
#endif

#include <iostream>
#include <sstream>
#include <vector>

#include <opencv2/highgui.hpp>

const bool debug_msg = true;
const int required_width_alignment = 32;

std::set<std::string> XimeaCamera::s_unique_id_list;

AcquisitionGuard::AcquisitionGuard(XimeaCamera* t) : _t(t)
{
	was_capturing = _t->m_capturing;
	if (was_capturing)
	{
		_t->acq_ctx.recursion++;
		if (_t->acq_ctx.recursion == 1) {
							
			_t->acq_ctx.needs_mutex = true;

			xiStopAcquisition(_t->m_deviceHandle);

			_t->acq_ctx.needs_mutex = false;
		}
	}
}

AcquisitionGuard::~AcquisitionGuard()
{
	if (was_capturing)
	{
		_t->acq_ctx.recursion--;
		if (_t->acq_ctx.recursion == 0)
		{
			_t->m_image_counter = 0;
			xiStartAcquisition(_t->m_deviceHandle);
		}
	}
}

XimeaCamera::XimeaCamera(int deviceId) 
: m_deviceHandle(0), m_has_lens_control(false)
{
	char buffer[512];

	memset(buffer, 0, 512);
	xiGetDeviceInfoString(deviceId, XI_PRM_DEVICE_NAME, buffer, 511);
	m_device_name = buffer;

	memset(buffer, 0, 512);
	xiGetDeviceInfoString(deviceId, XI_PRM_DEVICE_SN, buffer, 511);
	m_unique_id = buffer;
	m_model = "Ximea " + m_device_name;
	
	xiOpenDevice(deviceId, &m_deviceHandle);

	std::cout << m_model << std::endl;

	m_max_bandwidth = get_param_int(XI_PRM_AVAILABLE_BANDWIDTH); //  On the CM120, this resets the Exposure Time
	std::cout << "Bandwidth: " << m_max_bandwidth << std::endl;

	set_param_int(XI_PRM_DEBUG_LEVEL, XI_DL_FATAL);

	std::stringstream ss_version;
	ss_version << m_device_name << 
		" REV:" << get_param_int(XI_PRM_HW_REVISION) << 
		" API:" << get_param_str(XI_PRM_API_VERSION) << 
		" DRV:" << get_param_str(XI_PRM_DRV_VERSION) << 
		" FPGA:" << get_param_str(XI_PRM_FPGA1_VERSION) <<
		" CPU1:" << get_param_str(XI_PRM_MCU1_VERSION) <<
		" CPU2:" << get_param_str(XI_PRM_MCU2_VERSION) <<
		" XML:" << get_param_str(XI_PRM_XMLMAN_VERSION) <<
		" BW:" << (m_max_bandwidth / 8) << "MB/s" <<
		std::endl;
	m_version = ss_version.str();

	// Set Ximea Camera to known values
	if (m_device_name != "CB120MG-CM")
		set_param_int(XI_PRM_LIMIT_BANDWIDTH_MODE, 0);
	set_param_int(XI_PRM_EXPOSURE XI_PRMM_DIRECT_UPDATE, 5 * 1000); // microseconds
	set_param_int(XI_PRM_OFFSET_X, 0);
	set_param_int(XI_PRM_OFFSET_Y, 0);
	set_param_int(XI_PRM_AEAG, 0);
	set_param_int(XI_PRM_LUT_EN, 0);
	set_param_int(XI_PRM_GAIN XI_PRMM_DIRECT_UPDATE, 0);
	set_param_int(XI_PRM_ACQ_TIMING_MODE, XI_ACQ_TIMING_MODE_FRAME_RATE);
	if (isXiC())
		set_param_int(XI_PRM_ACQ_TIMING_MODE, XI_ACQ_TIMING_MODE_FRAME_RATE_LIMIT);
	set_param_float(XI_PRM_FRAMERATE, 30.0); // Hz	

	m_has_lens_control = get_param_int(XI_PRM_LENS_MODE XI_PRM_INFO_MAX) > 0;
	
	set_param_int(XI_PRM_BUFFER_POLICY, XI_BP_UNSAFE);
	set_param_int(XI_PRM_BUFFERS_QUEUE_SIZE, get_param_int(XI_PRM_BUFFERS_QUEUE_SIZE XI_PRM_INFO_MAX));

	if (has_lens_control())
	{ 
		af_enable();
		set_param_float(XI_PRM_LENS_APERTURE_VALUE, 5.6f); // lens defaults to f5.6
	}

	m_color_need_debayer = get_param_int(XI_PRM_COLOR_FILTER_ARRAY) > 0; // TODO Detect specific Bayer patterns

	// Default color balance for Ximea Bayer filter
	m_color_balance.kR = 1.37f;
	m_color_balance.kG = 1.00f;
	m_color_balance.kB = 2.65f;

	m_framerate = get_param_int(XI_PRM_FRAMERATE);

	// row alignment
	if (get_param_int(XI_PRM_WIDTH) % required_width_alignment != 0)
	{
		printf("Adjusting image width to %d alignment\n", required_width_alignment);
		set_param_int(XI_PRM_WIDTH, get_param_int(XI_PRM_WIDTH) - (get_param_int(XI_PRM_WIDTH) % required_width_alignment));
	}

	m_width = m_original_width = get_param_int(XI_PRM_WIDTH);
	m_height = m_original_height = get_param_int(XI_PRM_HEIGHT);
	m_preview_width = default_preview_res;
	m_preview_height = m_width>0 ? (m_preview_width*m_height / m_width) : default_preview_res; // keep aspect ratio for preview

	set_param_int(XI_PRM_BPC, XI_ON);

	if (m_width > 0 && m_height > 0 && m_deviceHandle)
	{
		printf("Ximea %s Available Bandwidth: %d MB/s (max FPS: %d at max resolution 8 bit)\n", m_device_name.c_str(), m_max_bandwidth / 8, (m_max_bandwidth * 1024 * (1024 / 8)) / m_width / m_height);
		printf("%s\n", m_version.c_str());

		set_bitdepth(8);
		fill_params_list();
		start_capture();
	}
}

XimeaCamera::~XimeaCamera()
{
	try {
		if (m_capturing)
			stop_capture();
		if (m_deviceHandle)
			xiCloseDevice(m_deviceHandle);
	}
	catch (...)
	{
		printf("Ximea Error Closing camera %s\n", m_device_name.c_str());
	}	
	m_deviceHandle = 0;
}

bool XimeaCamera::isXiC() const
{
	return m_device_name[0] == 'M' && m_device_name[1] == 'C';
}

bool XimeaCamera::isXiQ() const
{
	return m_device_name[0] == 'M' && m_device_name[1] == 'Q';
}

void XimeaCamera::set_bitdepth(int bitdepth)
{
	if (!is_valid()) return;

	int format = (bitdepth == 8) ? XI_RAW8 : XI_RAW16;

	std::lock_guard<std::recursive_mutex> lock(m_mutex);
	AcquisitionGuard g(this);

	set_param_int(XI_PRM_IMAGE_DATA_FORMAT, format);

	// Choose between 10/12 from bitdepth
	if (bitdepth != get_param_int(XI_PRM_OUTPUT_DATA_BIT_DEPTH))
	{ 
		set_param_int(XI_PRM_SENSOR_DATA_BIT_DEPTH, 12);
		set_param_int(XI_PRM_OUTPUT_DATA_BIT_DEPTH, bitdepth);
		set_param_int(XI_PRM_IMAGE_DATA_BIT_DEPTH, bitdepth);
	}

	m_bitcount = get_param_int(XI_PRM_IMAGE_DATA_BIT_DEPTH);

	printf("%s Sensor:%d bits Output:%d bits Image:%d bits (packing:%d)\n", m_device_name.c_str(),
		get_param_int(XI_PRM_SENSOR_DATA_BIT_DEPTH), get_param_int(XI_PRM_OUTPUT_DATA_BIT_DEPTH), get_param_int(XI_PRM_IMAGE_DATA_BIT_DEPTH), get_param_int(XI_PRM_OUTPUT_DATA_PACKING));

	setBandwidth();
}

void XimeaCamera::set_hardware_sync_freq(int framerate)
{
	if (debug_msg)
		printf("====> DEBUG set_hardware_sync_freq framerate:%d  was:%d\n", framerate, m_framerate);

	std::lock_guard<std::recursive_mutex> lock(m_mutex);

	Camera::set_hardware_sync_freq(framerate);

	if (m_using_hardware_sync)
	{
		AcquisitionGuard g(this);

		setBandwidth();
	}
	else
	{
		AcquisitionGuard g(this);

		// On xiQ, need to set the BW to max before setting framerate
		if (isXiQ())
			set_param_int(XI_PRM_LIMIT_BANDWIDTH, get_param_int(XI_PRM_LIMIT_BANDWIDTH XI_PRM_INFO_MAX));

		set_param_int(XI_PRM_FRAMERATE, framerate);
		m_framerate = framerate;

		setBandwidth();
	}
}

void XimeaCamera::set_hardware_sync(bool enable, int framerate)
{
	std::lock_guard<std::recursive_mutex> lock(m_mutex);

	if (debug_msg)
		printf("====> DEBUG set_hardware_sync enable:%s framerate:%d  was:%d\n", enable?"YES":"NO", framerate, m_framerate);

	if (!is_valid()) return;

	const bool framerate_change = (framerate != m_framerate);

	if (m_using_hardware_sync != enable)
	{ 
		AcquisitionGuard g(this);

		if (enable)
		{
			set_param_int(XI_PRM_GPI_SELECTOR, 1); // Pin 1
			set_param_int(XI_PRM_GPI_MODE, XI_GPI_TRIGGER);
			set_param_int(XI_PRM_TRG_SOURCE, XI_TRG_EDGE_RISING);
			set_param_int(XI_PRM_FRAMERATE, get_param_int(XI_PRM_FRAMERATE XI_PRM_INFO_MAX)); // need to set the framerate to a value higher than the hwsync
		}
		else
		{
			set_param_int(XI_PRM_TRG_SOURCE, XI_TRG_OFF); // camera runs in freerun mode
			if (m_framerate>0)
				set_param_int(XI_PRM_FRAMERATE, m_framerate);
		}

		m_using_hardware_sync = enable;
		m_framerate = enable ? framerate : get_param_int(XI_PRM_FRAMERATE);
		m_effective_fps = 0;

		if (framerate_change)
			setBandwidth();
	}
	else
	{
		m_framerate = enable ? framerate : get_param_int(XI_PRM_FRAMERATE);
		m_effective_fps = 0;

		if (framerate_change)
		{
			AcquisitionGuard g(this);
			setBandwidth();
		}
	}
}

bool XimeaCamera::has_lens_control()
{
	return m_has_lens_control;
}

void XimeaCamera::af_enable()
{
	if (get_param_int(XI_PRM_LENS_MODE) == 0)
		set_param_int(XI_PRM_LENS_MODE, 1);
}

void XimeaCamera::af_move_focus(int value)
{
	set_param_int(XI_PRM_LENS_FOCUS_MOVEMENT_VALUE, value);
	set_param_float(XI_PRM_LENS_FOCUS_MOVE, 1.0);
}

bool XimeaCamera::af_at_limit()
{
	set_param_int(XI_PRM_LENS_FEATURE_SELECTOR, XI_LENS_FEATURE_MOTORIZED_FOCUS_BOUNDED);
	return get_param_float(XI_PRM_LENS_FEATURE) > 0.5f;
}

void XimeaCamera::fill_params_list()
{
	if (!is_valid()) return;

	std::map<std::string, CameraParameter> m;

	static const std::vector<std::string> intParams = { "exposure", "framerate", "lens_mode", "lens_focus_movement_value", "lens_focus_move", "lens_focal_length" };
	static const std::vector<std::string> floatParams = { "gain", "lens_aperture_value", "lens_focus_distance", XI_PRM_CHIP_TEMP, XI_PRM_HOUS_TEMP, XI_PRM_HOUS_BACK_SIDE_TEMP, XI_PRM_SENSOR_BOARD_TEMP };

	for (const std::string& i : intParams)
	{
		if (!has_lens_control() && i[0] == 'l') // skip lens parameters for some cameras
			continue;

		CameraParameter p;

		//std::lock_guard<std::recursive_mutex> lock(m_mutex);
		
		int ival = 0;
		XI_RETURN ret = xiGetParamInt(m_deviceHandle, i.c_str(), &ival);
		if (ret != XI_OK)
			continue;

		p.last_value = ival;
		p.minimum = get_param_int((i + ":min").c_str(), true);
		p.maximum = get_param_int((i + ":max").c_str(), true);
		p.increment = get_param_int((i + ":inc").c_str(), true);
		m[i] = p;
	}

	for (const std::string& i : floatParams)
	{
		if (!has_lens_control() && i[0] == 'l') // skip lens parameters for some cameras
			continue;

		CameraParameter p;

		//std::lock_guard<std::recursive_mutex> lock(m_mutex);

		XI_RETURN ret = xiGetParamFloat(m_deviceHandle, i.c_str(), &p.last_value);
		if (ret != XI_OK)
			continue;

		p.minimum = get_param_float((i + ":min").c_str(), true);
		p.maximum = get_param_float((i + ":max").c_str(), true);
		p.increment = get_param_float((i + ":inc").c_str(), true);
		m[i] = p;
	}

	std::swap(m, m_params);
}

void XimeaCamera::param_set(const char * name, float value)
{
	if (!is_valid()) return;

	printf("Set parameter %s to %f\n", name, value);
	
	std::lock_guard<std::recursive_mutex> lock(m_mutex);

	if (strcmp(name, "lens_mode") == 0 || strcmp(name, "lens_aperture_value") == 0)
	{
		// Update without stop / start
		set_param_float(name, value);
	}
	else if (strcmp(name, "exposure") == 0 || strcmp(name, "gain") == 0)
	{
		// Update without stop/start, with direct update flag
		set_param_float((std::string(name) + XI_PRMM_DIRECT_UPDATE).c_str(), value);
	}
	else
	{
		// Stop acquisition before updating
		AcquisitionGuard g(this);
		
		set_param_float(name, value);
	}

	// Update value in param list
	auto it = m_params.find(std::string(name));
	if (it != m_params.end())
	{ 
		xiGetParamFloat(m_deviceHandle, name, &it->second.last_value);
	}
}

float XimeaCamera::param_get(const char * name)
{
	return get_param_float(name);
}

void XimeaCamera::invalidate()
{
	std::lock_guard<std::recursive_mutex> lock(m_mutex);

	if (m_deviceHandle)
	{
		HANDLE h = m_deviceHandle;
		m_deviceHandle = 0;
		xiCloseDevice(h);
	}
	m_capturing = false;
}

bool XimeaCamera::is_valid() const
{
	return m_deviceHandle != 0;
}

void XimeaCamera::get_ximea_cameras(std::vector<std::shared_ptr<Camera> >& new_cameras, std::vector<std::string>& removed_ids)
{
	std::set<std::string> all_ximeas;

	xiSetParamInt(0, XI_PRM_AUTO_BANDWIDTH_CALCULATION, XI_OFF);

	DWORD device_count = 0;
	xiGetNumberDevices(&device_count);

	// Find newly added cameras
	for (unsigned int i = 0; i < device_count; i++)
	{
		char buffer[512];
		memset(buffer, 0, 512);
		xiGetDeviceInfoString(i, XI_PRM_DEVICE_SN, buffer, 511);

		// If this camera does not already exist
		std::string unique_id(buffer);
		all_ximeas.insert(unique_id);
		if (s_unique_id_list.find(unique_id) == s_unique_id_list.end())
		{
			printf("Detected New Ximea : %s\n", buffer);

			s_unique_id_list.insert(unique_id);
			new_cameras.push_back(std::make_shared<XimeaCamera>(i));
		}
	}

	// Find removed cameras
	// everything in s_unique_id_list but not in all_ximeas
	std::copy_if(s_unique_id_list.begin(), s_unique_id_list.end(), std::back_inserter(removed_ids), [&all_ximeas](const std::string& id) {
		return all_ximeas.find(id) == all_ximeas.end();
	});

	s_unique_id_list = all_ximeas;
}


std::string XimeaCamera::get_param_str(const char * param)
{
	if (!is_valid()) return "";

	char buffer[512];
	memset(buffer, 0, 512);

	std::lock_guard<std::recursive_mutex> lock(m_mutex);

	XI_RETURN ret = xiGetParamString(m_deviceHandle, param, buffer, 511);
	if (ret != XI_OK)
		std::cerr << "XIMEA: Error(" << ret << ") reading parameter " << param << std::endl;
	return buffer;
}

int XimeaCamera::get_param_int(const char * param, bool silent)
{
	if (!is_valid()) return 0;

	std::lock_guard<std::recursive_mutex> lock(m_mutex);

	int val = 0;
	XI_RETURN ret = xiGetParamInt(m_deviceHandle, param, &val);
	if (ret != XI_OK && !silent)
		std::cerr << "XIMEA: Error(" << ret << ") reading parameter " << param << std::endl;
	return val;
}

float XimeaCamera::get_param_float(const char * param, bool silent)
{
	if (!is_valid()) return 0.0f;

	std::lock_guard<std::recursive_mutex> lock(m_mutex);

	float val = 0.0f;
	XI_RETURN ret = xiGetParamFloat(m_deviceHandle, param, &val);
	if (ret != XI_OK && !silent)
		std::cerr << "XIMEA: Error(" << ret << ") reading parameter " << param << std::endl;
	return val;
}

void XimeaCamera::set_param_int(const char * param, int value)
{
	if (!is_valid()) return;

	if (debug_msg)
		std::cerr << "XIMEA DEBUG: Set " << param << " to " << value << std::endl;

	std::lock_guard<std::recursive_mutex> lock(m_mutex);

	XI_RETURN ret = xiSetParamInt(m_deviceHandle, param, value);
	if (ret != XI_OK)
		std::cerr << "XIMEA: Error(" << ret << ") setting parameter " << param << " to " << value  << std::endl;
}

void XimeaCamera::set_param_float(const char * param, float value)
{
	if (!is_valid()) return;

	if (debug_msg)
		std::cerr << "XIMEA DEBUG: Set " << param << " to " << value << std::endl;

	std::lock_guard<std::recursive_mutex> lock(m_mutex);

	XI_RETURN ret = xiSetParamFloat(m_deviceHandle, param, value);
	if (ret != XI_OK)
		std::cerr << "XIMEA: Error(" << ret << ") setting parameter " << param << " to " << value << std::endl;
}

void XimeaCamera::captureThread()
{
	while (m_capturing && m_deviceHandle)
	{
		if (acq_ctx.isAcquisitionPaused()) // If another thread needs to lock the AcquisitionGuard, make sure 
		                         		   // we are not constantly re-locking the camera status mutex, otherwise
								           // xiStopAcquisition will block forever.
		{
			boost::this_thread::sleep_for(boost::chrono::milliseconds(2));
			continue;
		}				


		XI_IMG img;
		memset(&img, 0, sizeof(img));
		img.size = SIZE_XI_IMG_V3;
		DWORD timeout_ms = (4.0f / m_framerate) * 1000.0f; // timeout is 4 times the length of a frame

		XI_RETURN ret = xiGetImage(m_deviceHandle, timeout_ms, &img);

		if (ret == XI_TIMEOUT || ret==XI_ACQUISITION_STOPED)
		{
			got_frame_timeout();
			continue;
		}
		else if (ret == XI_DEVICE_NOT_READY)
		{
			// Camera was most probably disconnected
			std::cerr << "XI_DEVICE_NOT_READY" << std::endl;
			invalidate();
		}
		else if (ret == XI_INVALID_HANDLE)
		{
			std::cerr << "XI_INVALID_HANDLE" << std::endl;
			invalidate();
			break;
		}
		else if (ret != XI_OK)
		{
			std::cerr << "xiGetImage error " << ret << std::endl;
		}
		else
		{
			double ts = img.tsSec + img.tsUSec / 1000000.0;
			int bitcount = 0;
			int channels = 0;
			int imgtype = 0;

			switch (img.frm) {
			case XI_MONO8:
			case XI_RAW8:
				bitcount = 8;
				channels = 1;
				imgtype = CV_8UC1;
				break;
			case XI_MONO16:
			case XI_RAW16:
				bitcount = 16;
				channels = 1;
				imgtype = CV_16UC1;
				break;
			case XI_RGB24:
				bitcount = 8;
				channels = 3;
				imgtype = CV_8UC3;
				break;
			case XI_RGB32:
				bitcount = 8;
				channels = 4;
				imgtype = CV_8UC4;
				break;
			}

			cv::Mat mat(cv::Size(img.width, img.height), imgtype, img.bp, cv::Mat::AUTO_STEP);
			Camera::got_image(mat, ts, img.width, img.height, bitcount, channels, img.black_level);
		}
	}
}

void XimeaCamera::start_capture()
{	
	if (!is_valid()) return;

	if (!m_capturing)
	{
		std::lock_guard<std::recursive_mutex> lock(m_mutex);

		Camera::start_capture();

		capture_thread = boost::thread([this]() {captureThread(); });

#ifdef WIN32
		SetThreadPriority(capture_thread.native_handle(), THREAD_PRIORITY_HIGHEST);
#else
		#pragma message("TODO Implement Linux")
#endif

		m_image_counter = 0;
		xiStartAcquisition(m_deviceHandle);
	}
}

void XimeaCamera::stop_capture()
{
	if (m_capturing)
	{
		std::lock_guard<std::recursive_mutex> lock(m_mutex);

		Camera::stop_capture();
		if (m_deviceHandle)
			xiStopAcquisition(m_deviceHandle);

		if (capture_thread.get_id() != boost::this_thread::get_id())
			capture_thread.join();

		m_effective_fps = 0;		
	}
}

void XimeaCamera::reset_roi()
{
	set_roi(0, 0, m_original_width, m_original_height);
}

void XimeaCamera::set_roi(int x_min, int y_min, int x_max, int y_max)
{
	std::lock_guard<std::recursive_mutex> lock(m_mutex);

	AcquisitionGuard g(this);

	if (x_min < 0) x_min = 0;
	if (y_min < 0) y_min = 0;

	set_param_int(XI_PRM_REGION_SELECTOR, 0);
	set_param_int(XI_PRM_OFFSET_X, 0);
	set_param_int(XI_PRM_OFFSET_Y, 0);

	int x_inc = get_param_int(XI_PRM_WIDTH XI_PRM_INFO_INCREMENT);
	int y_inc = get_param_int(XI_PRM_HEIGHT XI_PRM_INFO_INCREMENT);
	int w_max = m_original_width;
	int h_max = m_original_height;

	int px = x_min - (x_min%x_inc);
	int py = y_min - (y_min%y_inc);
	int w = x_max - x_min; w = w - w%x_inc;
	int h = y_max - y_min; h = h - h%y_inc;

	// row alignment
	if (w % required_width_alignment != 0)
		w -= (w % required_width_alignment);

	if (px > w_max) px = w_max;
	if (py > h_max) py = h_max;

	if (px + w > w_max) w = w_max - px;
	if (py + h > h_max) h = h_max - py;

	set_param_int(XI_PRM_HEIGHT, h);
	set_param_int(XI_PRM_WIDTH, w);
	set_param_int(XI_PRM_OFFSET_Y, py);
	set_param_int(XI_PRM_OFFSET_X, px);

	m_width = get_param_int(XI_PRM_WIDTH);
	m_height = get_param_int(XI_PRM_HEIGHT);

	m_preview_width = default_preview_res;
	m_preview_height = m_width>0 ? (m_preview_width*m_height / m_width) : default_preview_res; // keep aspect ratio for preview

	setBandwidth();
}

void XimeaCamera::setBandwidth(unsigned long long limit_mb)
{
	// 'limit' is an optional parameter to have an upper limit on the bandwidth (in megabits), set to 0 for no limit

	std::lock_guard<std::recursive_mutex> lock(m_mutex);

	int transport_bitcount = get_param_int(XI_PRM_OUTPUT_DATA_BIT_DEPTH);
	if (transport_bitcount > 8 && get_param_int(XI_PRM_OUTPUT_DATA_PACKING) == 0)
		transport_bitcount = 16;

	// According to Ximea documentation, a megabit is 1000000 bits, not 1024*1024
	unsigned long long bw = (unsigned long long)m_framerate * (unsigned long long)m_width * (unsigned long long)m_height * (unsigned long long)transport_bitcount / (unsigned long long)(1000000);

	// add 2% padding
	bw += 32;
	bw += (bw * 2) / 100;

	// Optional upper limit on the bandwidth
	if (limit_mb && bw > limit_mb)
		bw = limit_mb;

	// max bandwidth reported by the ximea api
	if (bw > m_max_bandwidth)
		bw = m_max_bandwidth;

	std::cout << "Fr:" << m_framerate << " W:" << m_width << " H:" << m_height << " B:" << transport_bitcount << std::endl;
	std::cout << "Set Ximea bandwidth to " << bw << " megabits/s (was " << get_param_int(XI_PRM_LIMIT_BANDWIDTH) << ")" << std::endl;

	set_param_int(XI_PRM_LIMIT_BANDWIDTH, bw);
	set_param_int(XI_PRM_LIMIT_BANDWIDTH_MODE, 1);
}
