// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include <string>
#include <map>
#include <deque>
#include <memory>
#include <mutex>

#include "json.hpp"
#include "color_correction.hpp"

#include <opencv2/highgui.hpp>

#include <boost/thread/thread.hpp>

class Recorder;

struct CameraParameter {
	float last_value;
	float minimum;
	float maximum;
	float increment;
};

template <typename T, int maxValueCount>
class CircularBuffer
{
public:
	CircularBuffer() : count(0), index(0) {}
	void add(T value)
	{
		if (count < maxValueCount)
			values[count++] = value;
		else
			values[index] = value;
		index = (index + 1) % maxValueCount;
	}
	T average() const 
	{
		if (count == 0)
			return 0;
		T val = 0;
		for (int i = 0; i < count; i++)
			val += values[i];
		return val / count;
	}
	void clear()
	{
		count = index = 0;
	}

private:
	int count;
	int index;
	T values[maxValueCount];
};

class Camera
{
public:
	Camera();
	virtual ~Camera();

	size_t bandwidth() const
	{
		// Returns the uncompressed data bandwidth in bytes / seconds
		return (size_t)(m_width) * m_height * framerate() * (m_bitcount>8?2:1);
	}

	void got_image(cv::Mat img, double ts, int width, int height, int bitcount, int channels, int black_level=0);
	void got_frame_timeout(); // an image was not recieved

	virtual void set_hardware_sync(bool enable, int framerate)
	{
		// needs to be implemented for each camera
		m_using_hardware_sync = enable;
		set_hardware_sync_freq(framerate);
	}

	virtual void set_hardware_sync_freq(int framerate)
	{
		// if we are simply changing the hw frequency
		m_effective_fps = 0;
		if (m_using_hardware_sync)
			m_framerate = framerate;
	}

	virtual bool has_lens_control() { return false; };
	virtual void af_enable() {};
	virtual void af_move_focus(int value) {};
	virtual bool af_at_limit() { return false; };

	virtual const std::map<std::string, CameraParameter>& params_list() {
		// Returns the list of custom parameters for this camera
		return m_params;
	}
	virtual void param_set(const char * name, float value) {
		// Sets the value of this parameter on the camera
	}
	virtual float param_get(const char * name) {
		// Reads the value of this parameter on the camera
		return 0.0f;
	}

	virtual void start_capture()
	{
		// Start Capturing Frames and storing the preview image
		m_effective_fps = 0;
		ts_d.clear();
		m_capturing = true;
	}

	virtual void stop_capture()
	{
		// Stop Capturing Frames
		m_effective_fps = 0;
		m_capturing = false;
	}

	virtual bool is_valid() const { return true; } // If a camera becomes invalid it will be removed
	virtual void invalidate() {}

	virtual void start_recording(const std::vector<std::string>& folders, bool wait_for_trigger, int nb_frames=-1);
	virtual void stop_recording();

	virtual void set_bitdepth(int bitdepth) {}

	virtual void set_roi(int x_min, int y_min, int x_max, int y_max) {}
	virtual void reset_roi() {}

	std::string toString() const;
	std::string unique_id() const { return m_unique_id; }
	std::string model() const { return m_model; }
	std::string version() const { return m_version; }
	int bpp() const { return m_bitcount; }
	int width() const { return m_width; }
	int height() const { return m_height; }
	int preview_width() const { return m_preview_width; }
	int preview_height() const { return m_preview_height; }
	float effective_fps() const { return m_effective_fps; }
	bool using_hardware_sync() const { return m_using_hardware_sync; }
	bool recording() const { return m_recording; }
	bool capturing() const { return m_capturing; }

	int framerate() const { return m_framerate; }

	int encoding_buffers_used() const { return m_encoding_buffers_used; }
	int writing_buffers_used() const { return m_writing_buffers_used; }

	bool get_preview_image(std::vector<unsigned char>& buf, bool* pIsHistogram=0);
	bool get_large_preview_image(std::vector<unsigned char>& buf);

	void set_display_focus_peak(bool e) { m_display_focus_peak = e; }
	void set_display_overexposed(bool e) { m_display_overexposed = e; }
	void set_display_histogram(bool e) { m_display_histogram = e; }

	void software_trigger() { m_waiting_for_trigger_hold = false;  m_waiting_for_trigger = false; }
	void remove_recording_hold();

	shared_json_doc last_summary() { return m_last_summary; }

	bool m_debug_in_capture_cycle;

protected:
	int default_preview_res;

	std::string m_unique_id;
	std::string m_model;
	std::string m_version;

	int m_framerate;
	int m_width;
	int m_height;
	int m_preview_width;
	int m_preview_height;

	float m_effective_fps;

	int m_encoding_buffers_used;
	int m_writing_buffers_used;

	bool m_recording;
	bool m_waiting_for_trigger;
	bool m_waiting_for_trigger_hold;
	bool m_closing_recorders;
	bool m_capturing;

	bool m_display_focus_peak;
	bool m_display_overexposed;
	bool m_display_histogram;
	bool m_using_hardware_sync;
	bool m_color_need_debayer; // this is a color camera that needs to be de-bayered

	bool m_got_trigger_timeout;

	int m_bitcount;
	int m_record_frames_remaining;
	int m_image_counter;

	double m_start_ts;
	double m_last_ts;
	double m_waiting_delay;

	color_correction::rgb_color_balance m_color_balance;

	CircularBuffer<double, 10> ts_d;

	// Small preview stream when we are not recording
	std::mutex m_mutex_preview_image;
	cv::Mat preview_image;
	bool preview_image_is_histogram;

	// Large preview image when we are not recording
	std::mutex m_mutex_large_preview_image;
	cv::Mat large_preview_image;
	int large_preview_image_black_point;
	
	// Store first frame of each recording
	cv::Mat recording_first_frame;
	int recording_first_frame_black_level;

	shared_json_doc m_last_summary;

	std::vector<std::shared_ptr<Recorder> > m_recorders;

	std::map<std::string, CameraParameter> m_params;

	// work space for focus peak
	cv::Mat focus_peak_buffer[4];
	int focus_peak_buffer_index;
	int focus_peak_buffer_count;
};

class WebcamCamera : public Camera
{
public:
	WebcamCamera(int id);

	static std::vector<std::shared_ptr<Camera> > get_webcam_cameras();

protected:
	void captureThread();
	void start_capture() override;
	void stop_capture() override;

private:
	int m_id;
	cv::VideoCapture m_cap;
	boost::thread capture_thread;
};