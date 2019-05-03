// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include "cameras.hpp"
#include "recorder.hpp"
#include "base64.hpp"
#include "color_correction.hpp"

#include <boost/uuid/uuid.hpp>
#include <boost/uuid/uuid_io.hpp>
#include <boost/uuid/uuid_generators.hpp>
#include <boost/filesystem.hpp>
#include <boost/asio.hpp>

#include <iostream>
#include <numeric>

#include <opencv2/imgproc.hpp>
#include <opencv2/opencv.hpp>

#include "boost/date_time/posix_time/posix_time.hpp"

//#define DEBUG_FRAME_TIMINGS

Camera::Camera()
{
	m_unique_id = boost::uuids::to_string(boost::uuids::random_generator()());
	m_model = "unknown";
	m_effective_fps = 0.0f;
	m_recording = false;
	m_waiting_for_trigger = false;
	m_waiting_for_trigger_hold = false;
	m_capturing = false;
	m_framerate = 24;
	m_width = 320;
	m_height = 200;
	m_bitcount = 8;
	m_record_frames_remaining = -1;
	m_image_counter = 0;
	m_using_hardware_sync = false;
	m_display_focus_peak = false;
	m_display_overexposed = false;
	m_display_histogram = false;
	default_preview_res = 160;
	m_preview_width = default_preview_res;
	m_preview_height = default_preview_res;
	m_color_need_debayer = false;
	m_record_as_raw = false;

	m_bayerpattern = cv::COLOR_BayerBG2RGB;

	m_debug_in_capture_cycle = false;
	m_debug_timings = false;
	m_prepare_recording = false;

	m_encoding_buffers_used = 0;
	m_writing_buffers_used = 0;

	preview_image_is_histogram = false;

	focus_peak_buffer_index = 0;
	focus_peak_buffer_count = 0;
}

Camera::~Camera()
{

}

std::string Camera::toString() const
{
	std::stringstream ss;
	ss << "Camera " << m_model << "/" << m_unique_id << " " << m_width << "x" << m_height << " rate:" << m_framerate << "fps current:" << m_effective_fps << " C:" << (m_capturing ? "Y" : "N") << " R:" << (m_recording ? "Y" : "N") << " " << m_version;
	return ss.str();
}

void Camera::got_frame_timeout()
{
	m_effective_fps = 0.0f;
}

bool Camera::block_until_next_frame(double timeout_s)
{
	int current_Frame_index = m_image_counter;

	while (timeout_s>0.0) 
	{
#ifdef DEBUG_FRAME_TIMINGS		
		printf("*** Block until next frame (%d)\n", m_image_counter);
#endif // DEBUG_FRAME_TIMINGS		

		if (m_image_counter != current_Frame_index)
			return true;
			
		boost::this_thread::sleep_for(boost::chrono::milliseconds(10));
		timeout_s -= 0.1;
	}

	return false;
}

int overexposedDisplay(const cv::Mat& source, cv::Mat& output)
{
	const int overexposed_threshold = 254;

	cv::Mat gray = source;

	if (gray.channels() == 3)
	{
		// get the max value of each channel, because we only care about overexposed pixels
		cv::Mat sourceChannels[3];
		cv::split(source, sourceChannels);
		cv::max(sourceChannels[0],sourceChannels[1],gray);
		cv::max(sourceChannels[2],gray,gray);
	}

	cv::Mat work;
	cv::threshold(gray, work, overexposed_threshold, 255, cv::THRESH_BINARY);
	cv::Mat kernel = cv::Mat::ones(5, 5, CV_8U);
	cv::dilate(work, work, kernel, cv::Point(-1, -1), 2);

	cv::Mat R;
	cv::max(work, gray, R);

	const int overexposedPixels = countNonZero(work);

	cv::Mat GB;
	cv::Mat invert = cv::Scalar::all(255) - work;
	cv::min(invert, gray, GB);

	cv::Mat arr[] = { GB, GB, R };	
	cv::merge(arr, 3, output);

	return overexposedPixels;
}

void Camera::got_image(cv::Mat img, double ts, int width, int height, int bitcount, int channels, int black_level)
{
	// Called by the camera implementation each time we recieve a new image

	//auto time1 = boost::posix_time::microsec_clock::local_time();

	if (channels != 1) {
		std::cerr << "TODO multiple channels not implemented in recorders" << std::endl;
		return;
	}

	assert(bitcount == 8 || bitcount == 16);
	assert(m_bitcount >= 8);
	assert(m_bitcount <= 16);

	// real representing this frame's time in seconds since the beginning of recording
	double frame_timestamp = ts > 0.0 ? ts : ((boost::posix_time::microsec_clock::local_time() - boost::posix_time::ptime(boost::gregorian::date(2016, 1, 1))).total_milliseconds() / 1000.0);
	if (m_image_counter == 0)
	{ 
		m_start_ts = frame_timestamp;
		m_last_ts = 0.0;
	}		
	frame_timestamp = frame_timestamp - m_start_ts;

	// Compute average effective framerate
	double dt = frame_timestamp - m_last_ts;
	m_last_ts = frame_timestamp;
	if (dt > 0.0)
	{
		ts_d.add(1.0 / dt);
		m_effective_fps = ts_d.average();
	}

#ifdef DEBUG_FRAME_TIMINGS	
	if (m_debug_timings)
		printf("*** %s %s%s%s %d (%f) %f %f\n", m_unique_id.c_str(), m_recording?"R":".", m_waiting_for_trigger?"W":".", 
			m_waiting_for_trigger_hold?"H":".",m_image_counter,ts,frame_timestamp, dt);
#endif // DEBUG_FRAME_TIMINGS			

	// Generate thumbnail for live preview
	if (!m_recording && !m_prepare_recording)
	{
		if (m_display_focus_peak)
		{
			const int FOCUS_THRESHOLD = 50; // on 255
			const double HEATMAP_SCALE = 2.5;
			const bool NORMALIZE_BRIGHTNESS = true;
			const bool TEMPORAL_DENOISE = false; // average 4 frames to reduce noise
			const int BLUR_SIZE = 151; // must be odd
			const int BRIGHTNESS_THRESHOLD = 5; // focus peak will not run if mean brightness is less than this value (too dark)
		
			cv::Mat last_image;
			cv::Mat work;

			if (m_color_need_debayer && img.channels() == 1)
			{
				cv::Mat tempImage;
				cv::cvtColor(img, tempImage, m_bayerpattern);
				cv::cvtColor(tempImage, last_image, cv::COLOR_BGR2GRAY);
			}
			else if (img.channels() == 3)
			{
				cv::cvtColor(img, last_image, cv::COLOR_BGR2GRAY); // Native Color Camera BGR
			}
			else
			{
				last_image = img.clone(); // Grayscale camera
			}

			if (m_bitcount > 8) // convert the image to 8 bit range
				last_image.convertTo(last_image, CV_8U, 1.0f / (1 << (m_bitcount - 8)));

			// Reduce resolution by 1/2
			cv::resize(last_image, last_image, cv::Size(0, 0), 0.5, 0.5, cv::INTER_AREA);

			// Average last 4 images to reduce noise
			if (TEMPORAL_DENOISE)
			{
				focus_peak_buffer[focus_peak_buffer_index] = last_image.clone();
				focus_peak_buffer_count = std::min(focus_peak_buffer_count+1,4);
				focus_peak_buffer_index = (focus_peak_buffer_index+1)%4;
				cv::Mat avgImg(cv::Size(last_image.cols, last_image.rows), CV_32FC1, cv::Scalar(0));
				for (int i=0;i<focus_peak_buffer_count;i++)
					if (focus_peak_buffer[i].cols==avgImg.cols && focus_peak_buffer[i].rows==avgImg.rows)
						cv::accumulate(focus_peak_buffer[i], avgImg);
				avgImg = avgImg / focus_peak_buffer_count;
				avgImg.convertTo(last_image, CV_8U);
			}
			
			double mean = cv::mean(last_image)[0]; // Mean brightness, only shot focus peak if within range
			if (mean>BRIGHTNESS_THRESHOLD && mean<256-BRIGHTNESS_THRESHOLD)
			{
				// Normalize brightness of the image
				if (NORMALIZE_BRIGHTNESS)
					last_image.convertTo(last_image, -1, 128.0/mean);
			
				// Compute contrast threshold
				cv::Mat kernel = cv::Mat::ones(3, 3, CV_8S);
				kernel.at<char>(1, 1) = -8;
				cv::filter2D(last_image, work, -1, kernel);
				cv::threshold(work, work, FOCUS_THRESHOLD, 255, cv::THRESH_BINARY);
	
				// Gaussian Blur on the map and apply color ramp
				cv::GaussianBlur(work,work,cv::Size(BLUR_SIZE,BLUR_SIZE),0);
				work = work * HEATMAP_SCALE; // Arbitrary scale
				cv::applyColorMap(work, work, cv::COLORMAP_HOT);
	
				// Overlay heat map on top of our original image
				cv::cvtColor(last_image, last_image, cv::COLOR_GRAY2BGR);
				cv::addWeighted(last_image, 0.2, work, 1.0, 0.0, img);
			}

			// Save preview image
			cv::Mat new_preview_image;
			cv::resize(img, new_preview_image, cv::Size(m_preview_width, m_preview_height), 0.0, 0.0, cv::INTER_NEAREST);
			color_correction::linear_to_sRGB(new_preview_image);

			{
				std::lock_guard<std::mutex> lock(m_mutex_preview_image);
				preview_image = new_preview_image;
				preview_image_is_histogram = false;
			}
		}
		else if (m_display_overexposed)
		{
			cv::Mat last_image;
			cv::Mat work;

			if (m_color_need_debayer && img.channels() == 1)
			{
				// Need to de-bayer to check overexposure
				// Important: we need to follow the same post-processing as SimpleImageRecorder::writingThread()
				cv::cvtColor(img, last_image, m_bayerpattern);
				color_correction::apply(last_image, m_color_balance, black_level);
			}
			else
			{
				last_image = img.clone(); // Grayscale or native color camera
			}

			if (m_bitcount > 8) // convert the image to 8 bit range, the histogram expects values from 0 to 255
				last_image.convertTo(last_image, CV_8U, 1.0f / (1 << (m_bitcount - 8)));

			// Overexposure check : display red overlay for overexposed areas
			overexposedDisplay(last_image, img);

			cv::Mat new_preview_image;
			cv::resize(img, new_preview_image, cv::Size(m_preview_width, m_preview_height), 0.0, 0.0, cv::INTER_NEAREST);
			color_correction::linear_to_sRGB(new_preview_image);

			{
				std::lock_guard<std::mutex> lock(m_mutex_preview_image);
				preview_image = new_preview_image;
				preview_image_is_histogram = false;
			}
		}
		else if (m_display_histogram)
		{
			int histSize = 256;
			float range[] = { 0, 256 };
			const float* histRange = { range };
			bool uniform = true; bool accumulate = false;

			cv::Mat last_image;

			if (m_color_need_debayer && img.channels() == 1)
				cv::cvtColor(img, last_image, m_bayerpattern);
			else
				last_image = img.clone(); // Grayscale camera

			if (m_bitcount > 8) // convert the image to 8 bit range, the histogram expects values from 0 to 255
				last_image.convertTo(last_image, CV_8U, 1.0f / (1 << (m_bitcount - 8)));

			int hist_w = histSize; 
			int hist_h = 256;
			cv::Mat histImage;

			{
				// Create Histogram

				cv::Mat sourceChannels[3];
				cv::Mat histChannels[3];

				cv::split(last_image, sourceChannels);

				for (int c = 0; c < last_image.channels(); c++)
				{
					histChannels[c] = cv::Mat(hist_h, hist_w, CV_8UC1, cv::Scalar(0));

					cv::Mat b_hist;
					cv::calcHist(&sourceChannels[c], 1, 0, cv::Mat(), b_hist, 1, &histSize, &histRange, uniform, accumulate);
					b_hist = b_hist * (32.0 * hist_h / (width*height));

					for (int i = 0; i < histSize; i++)
					{
						static const int extreme_width = 4;
						static const cv::Scalar highlight = cv::Scalar(255, 0, 0);
						static const cv::Scalar grey = cv::Scalar(200, 0, 0);
						line(histChannels[c],
							cv::Point(i, hist_h),
							cv::Point(i, hist_h - cvRound(b_hist.at<float>(i))),
							i <= extreme_width || i >= histSize - 1 - extreme_width ? highlight : grey);
					}
				}

				cv::merge(histChannels, last_image.channels(), histImage);
			}

			{
				std::lock_guard<std::mutex> lock(m_mutex_preview_image);
				preview_image = histImage;
				preview_image_is_histogram = true;
			}
		}
		else
		{
			// No histogram, the image is raw from the camera, or overexposed/focuspeak
			// Store smaller resized preview image

			cv::Mat new_preview_image;
			cv::Mat tempImage = img;

			// Debayer only if this is the raw from camera
			if (m_color_need_debayer && img.channels()==1)
				cv::cvtColor(img, tempImage, m_bayerpattern);

			cv::resize(tempImage, new_preview_image, cv::Size(m_preview_width, m_preview_height), 0.0, 0.0, cv::INTER_NEAREST);

			// Color-correct only if this is the raw from camera
			if (m_color_need_debayer)
				color_correction::apply(new_preview_image, m_color_balance, black_level);

			if (m_bitcount > 8) // If the image is more than 8 bit, shift values to convert preview to 8 bit range, for JPG encoding	
				new_preview_image.convertTo(new_preview_image, CV_8U, 1.0f / (1 << (m_bitcount - 8)));

			color_correction::linear_to_sRGB(new_preview_image);

			{
				std::lock_guard<std::mutex> lock(m_mutex_preview_image);
				preview_image = new_preview_image;
				preview_image_is_histogram = false;
			}
		}

		// Store full resolution preview image
		{
			std::lock_guard<std::mutex> lock(m_mutex_large_preview_image);
			large_preview_image = img.clone();
			large_preview_image_black_point = black_level;
		}
	}

	//if (m_debug_in_capture_cycle)
	//	printf("%f\n", dt);

	// Recording
	if (m_recording && !m_recorders.empty())
	{
		if (m_waiting_for_trigger && !m_waiting_for_trigger_hold)
		{
			// If we are waiting for the trigger, look for a >200 ms gap in the timestamps
			if (dt > 0.2)
			{
				//std::cout << "Recording trigger found!" << std::endl;
				m_waiting_for_trigger = false;
			}

			m_waiting_delay -= dt;
			if (m_waiting_delay < 0.0)
			{
				std::cerr << "Trigger timeout" << std::endl;
				m_got_trigger_timeout = true;
				m_waiting_for_trigger = false;
			}
		}

		if (!m_waiting_for_trigger && !m_closing_recorders)
		{
#ifdef DEBUG_FRAME_TIMINGS			
			if (m_debug_timings)
				printf("*** %s APPEND %f\n", m_unique_id.c_str(), dt);
#endif // DEBUG_FRAME_TIMINGS				
				
			// Store first frame of each recordings
			if (recording_first_frame.empty())
			{
				recording_first_frame = img.clone();
				recording_first_frame_black_level = black_level;
				recording_first_frame_index = m_recorders[0]->frame_count();
			}				

			// Accumulate frames only if we are recording, and we are not waiting for the trigger
			for (auto& r : m_recorders)
			{
				r->append(img, frame_timestamp, black_level);

				if (r->buffers_used(BUFFER_ENCODING) > 0)
					m_encoding_buffers_used = r->buffers_used(BUFFER_ENCODING);
				if (r->buffers_used(BUFFER_WRITING) > 0)
					m_writing_buffers_used = r->buffers_used(BUFFER_WRITING);
			}

		}

		if (m_record_frames_remaining > 0 && m_recorders[0]->frame_count() >= m_record_frames_remaining)
			stop_recording();
	}

	m_image_counter++;

	//auto time2 = boost::posix_time::microsec_clock::local_time();
	//std::cout << "Time: " << (time2 - time1) << std::endl;
}

void Camera::remove_recording_hold()
{
	m_waiting_for_trigger_hold = false;
}

void Camera::start_recording(const std::vector<std::string>& folders, bool wait_for_trigger, int nb_frames)
{
	// Start recording frames to the specified file
	if (!recording())
	{
		recording_first_frame.release();
		m_last_summary.reset();
		m_record_frames_remaining = nb_frames;
		m_encoding_buffers_used = 0;
		m_writing_buffers_used = 0;

		if (nb_frames>0)
			m_recorders.push_back(std::make_shared<SimpleImageRecorder>(unique_id(), framerate(), m_width, m_height, m_bitcount, m_color_need_debayer, m_bayerpattern, m_color_balance, folders, m_record_as_raw));
		else
			m_recorders.push_back(std::make_shared<SimpleMovieRecorder>(unique_id(), framerate(), m_width, m_height, m_bitcount, m_color_need_debayer, m_bayerpattern, m_color_balance, folders, m_record_as_raw));
		m_recorders.push_back(std::make_shared<MetadataRecorder>(unique_id(), framerate(), m_width, m_height, m_bitcount, m_color_need_debayer, m_color_balance, folders, this));

		m_got_trigger_timeout = false;
		m_closing_recorders = false;
		m_recording = true;
		m_prepare_recording = false;
		m_waiting_delay = 3.0;
		m_waiting_for_trigger_hold = true;
		m_waiting_for_trigger = wait_for_trigger;
	}
}

void Camera::stop_recording()
{
	// Stop Recording and close file Frames
	// Returns a dictionary with all recording data

	m_last_summary.reset();

	if (recording())
	{
		m_closing_recorders = true;

		// Close all recorders
		for (auto& r : m_recorders)
			r->close();

		// Prepare rapidjson tree to accumulate all data about this capture
		shared_json_doc d(new rapidjson::Document());
		d->SetObject();
		d->AddMember("unique_id", rapidjson::Value(unique_id().c_str(), d->GetAllocator()), d->GetAllocator());

		// Get summary data from all recorders
		for (auto& r : m_recorders)
			r->summarize(d);
		m_recorders.clear();

		// Fill summary tree with data about this capture
		{
			rapidjson::Value d_camera(rapidjson::kObjectType);
			d_camera.AddMember("unique_id", rapidjson::Value(unique_id().c_str(), d->GetAllocator()), d->GetAllocator());
			d_camera.AddMember("model", rapidjson::Value(model().c_str(), d->GetAllocator()), d->GetAllocator());
			d_camera.AddMember("version", rapidjson::Value(version().c_str(), d->GetAllocator()), d->GetAllocator());
			d_camera.AddMember("effective_fps", m_effective_fps, d->GetAllocator());
			d_camera.AddMember("framerate", framerate(), d->GetAllocator());
			d_camera.AddMember("width", width(), d->GetAllocator());
			d_camera.AddMember("height", height(), d->GetAllocator());
			d_camera.AddMember("using_hardware_sync", using_hardware_sync(), d->GetAllocator());
			d_camera.AddMember("error_trigger_timeout", m_got_trigger_timeout, d->GetAllocator());

			d->AddMember("camera", d_camera, d->GetAllocator());

			// Add custom parameters
			auto list = params_list();
			rapidjson::Value d_params(rapidjson::kObjectType);
			for (auto e : list)
			{
				rapidjson::Value strVal;
				strVal.SetString(e.first.c_str(), d->GetAllocator());
				d_params.AddMember(strVal, rapidjson::Value(param_get(e.first.c_str())), d->GetAllocator());
			}			
			d->AddMember("camera_params", d_params, d->GetAllocator());	

			if (!recording_first_frame.empty())
			{
				cv::Mat tempImage = recording_first_frame;

				if (m_color_need_debayer)
					cv::cvtColor(recording_first_frame, tempImage, m_bayerpattern);

				cv::resize(tempImage, tempImage, cv::Size(m_preview_width*2, m_preview_height*2), 0.0, 0.0, cv::INTER_AREA);

				if (m_color_need_debayer)
					color_correction::apply(tempImage, m_color_balance, recording_first_frame_black_level);

				if (m_bitcount > 8) // If the image is more than 8 bit, shift values to convert preview to 8 bit range, for JPG encoding	
					tempImage.convertTo(tempImage, CV_8U, 1.0f / (1 << (m_bitcount - 8)));

				color_correction::linear_to_sRGB(tempImage);

				d->AddMember("thumbnail_index", recording_first_frame_index, d->GetAllocator());

				std::vector<unsigned char> buf;
				if (cv::imencode(".jpg", tempImage, buf))
				{
					d->AddMember("jpeg_thumbnail", rapidjson::Value(base64encode(buf).c_str(), d->GetAllocator()), d->GetAllocator());
				}

				cv::Mat tempImageOverexposed;
				int overexposedPixels = overexposedDisplay(tempImage, tempImageOverexposed);
				if (overexposedPixels > 0)
				{
					if (cv::imencode(".jpg", tempImageOverexposed, buf))
					{
						d->AddMember("jpeg_thumbnail_overexposed", rapidjson::Value(base64encode(buf).c_str(), d->GetAllocator()), d->GetAllocator());
					}
				}
			}
			else if (!preview_image.empty())
			{
				std::vector<unsigned char> buf;
				if (get_preview_image(buf))
				{
					d->AddMember("jpeg_thumbnail", rapidjson::Value(base64encode(buf).c_str(), d->GetAllocator()), d->GetAllocator());
				}
			}

			m_last_summary = d;
			m_recording = false;
			m_waiting_for_trigger = false;
			m_waiting_for_trigger_hold = false;
			m_encoding_buffers_used = 0;
			m_writing_buffers_used = 0;
		}
	}
}

void Camera::updateColorBalance(double r, double g, double b)
{
	m_color_balance.kR = r;
	m_color_balance.kG = g;
	m_color_balance.kB = b;
}

bool Camera::get_preview_image(std::vector<unsigned char>& buf, bool* pIsHistogram)
{
	std::lock_guard<std::mutex> lock(m_mutex_preview_image);

	if (preview_image.empty())
		return false;

	if (pIsHistogram)
		*pIsHistogram = preview_image_is_histogram;

	return cv::imencode(".jpg", preview_image, buf); // cv2.IMWRITE_JPEG_QUALITY, 90
}
bool Camera::get_large_preview_image(std::vector<unsigned char>& buf)
{
	cv::Mat tempImage;

	{
		std::lock_guard<std::mutex> lock(m_mutex_large_preview_image);

		if (large_preview_image.empty())
			return false;

		if (m_color_need_debayer && large_preview_image.channels() == 1)
		{
			cv::cvtColor(large_preview_image, tempImage, m_bayerpattern);
			color_correction::apply(tempImage, m_color_balance, large_preview_image_black_point);
		}
		else
		{
			tempImage = large_preview_image;
		}

		if (m_bitcount > 8 && tempImage.depth() != CV_8U) // If the image is more than 8 bit, shift values to convert preview to 8 bit range, for JPG encoding
		{
			tempImage.convertTo(tempImage, CV_8U, 1.0f / (1 << (m_bitcount - 8)));
		}

		cv::resize(tempImage, tempImage, cv::Size(0, 0), 0.25, 0.25, cv::INTER_NEAREST);
	}

	color_correction::linear_to_sRGB(tempImage);
	return cv::imencode(".jpg", tempImage, buf); // cv2.IMWRITE_JPEG_QUALITY, 90
}

WebcamCamera::WebcamCamera(int id) : m_id(id)
{
	m_unique_id = "Webcam0";
	m_model = "Webcam";
	m_version = std::string("CV:") + CV_VERSION;

	m_cap = cv::VideoCapture(0);

	// read one frame to get frame size
	cv::Mat frame;
	m_cap >> frame;
	m_cap.release();

	m_width = frame.size[1];
	m_height = frame.size[0];

	m_framerate = 10;

	m_preview_width = default_preview_res;
	m_preview_height = m_preview_width*m_height / m_width; // keep aspect ratio for preview

	start_capture();
}

std::vector<std::shared_ptr<Camera> > WebcamCamera::get_webcam_cameras()
{
	std::vector<std::shared_ptr<Camera> > v;

	cv::VideoCapture cap(0); // open the default camera
	if (cap.isOpened())
	{
		cap.release();
		v.push_back(std::make_shared<WebcamCamera>(0));
	}

	return v;
}

void WebcamCamera::captureThread()
{
	cv::Mat frame;
	while (m_capturing)
	{
		m_cap >> frame;

		if (!frame.empty())
		{
			Camera::got_image(frame, 0, m_width, m_height, 8, 1);
		}
	}
}

void WebcamCamera::start_capture()
{
	if (!m_capturing)
	{
		m_cap = cv::VideoCapture(0);
		Camera::start_capture();

		capture_thread = boost::thread([this]() {captureThread(); });
	}
}

void WebcamCamera::stop_capture()
{
	if (m_capturing)
	{
		Camera::stop_capture();

		capture_thread.join();

		m_cap.release();
		m_effective_fps = 0;
	}
}

DummyCamera::DummyCamera(int id) : m_id(id)
{
	std::stringstream ss;
	ss << "Dummy" << id;

	m_unique_id = ss.str();
	m_model = "Dummy";
	m_version = "1.0";

	m_width = 320;
	m_height = 200;
	m_framerate = 10;

	m_preview_width = default_preview_res;
	m_preview_height = m_preview_width*m_height / m_width; // keep aspect ratio for preview

	start_capture();
}

std::vector<std::shared_ptr<Camera> > DummyCamera::get_dummy_cameras(int count)
{
	std::vector<std::shared_ptr<Camera> > v;

	for (int i=0;i<count;i++)
	{
		v.push_back(std::make_shared<DummyCamera>(i));
	}

	return v;
}

void DummyCamera::captureThread()
{
	int i=0;
	cv::Mat frame(cv::Size(m_width, m_height), CV_8UC1);
	while (m_capturing)
	{
		cv::line(frame, cv::Point(0, i), cv::Point(m_width-1, i), rand()&0xFF);

		Camera::got_image(frame, 0, m_width, m_height, 8, 1);

		boost::this_thread::sleep_for(boost::chrono::milliseconds((long)(1000.0/m_framerate)));

		i = (i+1) % m_height;
	}
}

void DummyCamera::start_capture()
{
	if (!m_capturing)
	{
		Camera::start_capture();
		capture_thread = boost::thread([this]() {captureThread(); });
	}
}

void DummyCamera::stop_capture()
{
	if (m_capturing)
	{
		Camera::stop_capture();
		capture_thread.join();
		m_effective_fps = 0;
	}
}

#ifdef WITH_PORTAUDIO

AudioCamera::AudioCamera()
{
	m_unique_id = boost::asio::ip::host_name() + "_Audio0";
	m_model = "Audio";
	m_version = AudioRecorder::get_version();

	m_width = 512;
	m_height = 256;

	m_framerate = 30;

	m_preview_width = default_preview_res;
	m_preview_height = m_preview_width*m_height / m_width; // keep aspect ratio for preview

	start_capture();
}

void AudioCamera::captureThread()
{
	static const cv::Scalar grey = cv::Scalar(200, 0, 0);
	const int sample_scale = 32768;
	const int channels = 2;
	
	while (m_capturing)
	{
		cv::Mat frame(m_height, m_width, CV_8U, cv::Scalar(0));		

		int sample_count = 0;
		const short *samples = rec->get_raw_data(sample_count);

		// Draw one frame from the audio data
		for (int i = 0; i < m_width; i++)
		{
			short min_sample = 0;
			short max_sample = 0;
			for (int s=i*sample_count/channels/m_width;s<(i+1)*sample_count/channels/m_width;s++)
			{
				min_sample = std::min(min_sample, samples[s*channels]);
				max_sample = std::max(max_sample, samples[s*channels]);
			}

			short clip = std::max(abs(min_sample),abs(max_sample)) * 256 / sample_scale;

			line(frame,
				cv::Point(i, m_height/2+max_sample*m_height/2/sample_scale),
				cv::Point(i, m_height/2+min_sample*m_height/2/sample_scale),
				cv::Scalar(clip, 0, 0));
		}
			
		cv::applyColorMap(frame, frame, cv::COLORMAP_HOT);

		Camera::got_image(frame, 0, m_width, m_height, 8, 1);

		boost::this_thread::sleep_for(boost::chrono::milliseconds(1000/m_framerate));
	}
}

void AudioCamera::start_capture()
{
	if (!m_capturing)
	{
		rec.reset(new AudioRecorder());
		rec->start(0); // start streaming without recording

		Camera::start_capture();
		capture_thread = boost::thread([this]() {captureThread(); });
	}
}

void AudioCamera::stop_capture()
{
	if (m_capturing)
	{
		Camera::stop_capture();
		
		capture_thread.join();
		m_effective_fps = 0;

		rec->stop();
	}
}

void AudioCamera::start_recording(const std::vector<std::string>& folders, bool wait_for_trigger, int nb_frames)
{
	// Start recording frames to the specified file
	if (!recording())
	{
		namespace fs = boost::filesystem;
		fs::path filename = fs::path(folders[0]) / (m_unique_id + ".wav");

		rec->stop();
		rec->start(filename.string().c_str());

		m_recording = true;
	}
}

void AudioCamera::stop_recording()
{
	if (recording())
	{
		rec->stop();

		// Prepare rapidjson tree to accumulate all data about this capture
		shared_json_doc d(new rapidjson::Document());
		d->SetObject();
		d->AddMember("unique_id", rapidjson::Value(unique_id().c_str(), d->GetAllocator()), d->GetAllocator());

		// Create summary for Audio recording
		rec->summarize(d);

		// Fill summary tree with this audio device
		{
			rapidjson::Value d_camera(rapidjson::kObjectType);
			d_camera.AddMember("unique_id", rapidjson::Value(unique_id().c_str(), d->GetAllocator()), d->GetAllocator());
			d_camera.AddMember("model", rapidjson::Value(model().c_str(), d->GetAllocator()), d->GetAllocator());
			d_camera.AddMember("version", rapidjson::Value(version().c_str(), d->GetAllocator()), d->GetAllocator());
			
			d->AddMember("camera", d_camera, d->GetAllocator());
		}
		m_last_summary = d;

		rec->start(0); // start streaming without recording
		
		m_recording = false;
	}
}

#endif // WITH_PORTAUDIO