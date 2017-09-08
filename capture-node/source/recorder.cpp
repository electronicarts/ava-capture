// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include "recorder.hpp"
#include "video_encoder.hpp"
#include "cameras.hpp"
#include "color_correction.hpp"

#include <boost/filesystem.hpp>
#include <boost/algorithm/string/join.hpp>
#include <boost/format.hpp>

#include <opencv2/imgproc.hpp>
#include <opencv2/opencv.hpp>

#include <fstream>
#include <algorithm>

Recorder::Recorder(int framerate, int width, int height, int bitcount, const std::vector<std::string>& folders)
	: m_frame_count(0), m_framerate(framerate), m_closed(false), m_folders(folders), m_width(width), m_height(height), m_bitcount(bitcount), m_first_ts(0.0), m_last_ts(0.0)
{
}

Recorder::~Recorder()
{
	if (!m_closed)
		close();
}

void Recorder::append(cv::Mat img, double ts, int blacklevel)
{
	std::lock_guard<std::mutex> lock(m_mutex);

	if (m_frame_count==0)
		m_first_ts = ts;
	m_last_ts = ts;

	if (!m_closed)
		append_impl(img, ts, blacklevel);
}

void Recorder::close()
{
	std::lock_guard<std::mutex> lock(m_mutex);

	close_impl();
}

void Recorder::append_impl(cv::Mat img, double ts, int blacklevel)
{
	m_frame_count++;
}

void Recorder::close_impl()
{
	m_closed = true;
}

SimpleRecorder::SimpleRecorder(const std::string& unique_name, int framerate, int width, int height, int bitcount, const std::vector<std::string>& folders)
	: Recorder(framerate, width, height, bitcount, folders), m_unique_name(unique_name), m_dropped_frames(0)
{
}

SimpleMovieRecorder::SimpleMovieRecorder(const std::string& unique_name, int framerate, int width, int height, int bitcount, const std::vector<std::string>& folders)
	: SimpleRecorder(unique_name, framerate, width, height, bitcount, folders)
{
	namespace fs = boost::filesystem;

	int index = 0;
	for (auto folder : m_folders)
	{
		fs::path filename = fs::path(m_folders[index % m_folders.size()]) / (boost::format("%s_%03d.avi") % m_unique_name % index).str();
		m_filenames.push_back(filename.string());

		std::unique_ptr<VideoWriter> writer(new VideoWriter(filename.string().c_str(), framerate, width, height, bitcount));
		m_writers.push_back(std::move(writer));

		index++;
	}
}

int SimpleMovieRecorder::buffers_used(int type) const
{ 
	const auto& it = std::max_element(m_writers.begin(), m_writers.end(), [type](const std::unique_ptr<VideoWriter>& s1, const std::unique_ptr<VideoWriter>& s2) {
		return s1->buffers_used(type) < s2->buffers_used(type);
	});
	return (*it)->buffers_used(type);
}

void SimpleMovieRecorder::append_impl(cv::Mat img, double ts, int blacklevel)
{
	cv::Mat tempImage = img;
	if (m_bitcount>8)
		tempImage = img * (1 << (16 - m_bitcount)); // 10,12,14 bit images need to be scaled up to 16 bit value range

	if (!m_writers[m_frame_count % m_writers.size()]->addFrame(tempImage))
		m_dropped_frames++;

	Recorder::append_impl(img, ts, blacklevel);
}

void SimpleMovieRecorder::close_impl()
{
	Recorder::close_impl();

	for (auto& it : m_writers)
		it->close();
}

SimpleImageRecorder::SimpleImageRecorder(const std::string& unique_name, int framerate, int width, int height, int bitcount, bool color_bayer, color_correction::rgb_color_balance bal, const std::vector<std::string>& folders)
	: SimpleRecorder(unique_name, framerate, width, height, bitcount, folders), m_color_bayer(color_bayer), m_color_balance(bal)
{
}

void SimpleImageRecorder::append_impl(cv::Mat img, double ts, int blacklevel)
{
	namespace fs = boost::filesystem;
	fs::path filename = fs::path(m_folders[0]) / (boost::format("%s_%04i.tif") % m_unique_name % m_frame_count).str();

	m_filenames.push_back(filename.string());

	cv::Mat tempImage = img;

	if (m_color_bayer)
	{
		cv::cvtColor(img, tempImage, cv::COLOR_BayerBG2RGB);
		color_correction::apply(tempImage, m_color_balance, blacklevel);
	}

	if (m_bitcount>8)
		tempImage = tempImage * (1 << (16 - m_bitcount)); // 10,12,14 bit images need to be scaled up to 16 bit value range

	color_correction::linear_to_sRGB(tempImage); // TODO we should not do this for 8 bit, but then the image file should know it is linear

	cv::imwrite(filename.string(), tempImage);

	Recorder::append_impl(img, ts, blacklevel);
}

void SimpleImageRecorder::close_impl()
{
	Recorder::close_impl();
}

MetadataRecorder::MetadataRecorder(const std::string& unique_name, int framerate, int width, int height, int bitcount, bool color_bayer, color_correction::rgb_color_balance bal, const std::vector<std::string>& folders, Camera* parent)
	: Recorder(framerate, width, height, bitcount, folders), m_camera(parent), m_missing_frame(0), m_last_ts(0.0), m_last_black_level(0), m_color_bayer(color_bayer), m_color_balance(bal)
{
	namespace fs = boost::filesystem;

	m_timestamps.reserve(3600*120);

	// Filename for metadata log
	fs::path meta_log_path = fs::path(folders[0]) / (unique_name + ".txt");
	m_meta_log_path = meta_log_path.string();
}

void MetadataRecorder::append_impl(cv::Mat img, double ts, int blacklevel)
{
	m_timestamps.push_back(ts);

	if (m_frame_count > 1 && ((ts - m_last_ts) > (1.0/ m_framerate)*1.5)) // Count missing frames
		m_missing_frame++;
	m_last_ts = ts;

	m_last_black_level = blacklevel;

	Recorder::append_impl(img, ts, blacklevel);
}

void MetadataRecorder::close_impl()
{
	Recorder::close_impl();

	if (!m_timestamps.empty())
	{
		{
			std::ofstream stream(m_meta_log_path);

			// write header
			stream << "Filename: " << m_filename << std::endl;
			stream << "Threads: " << m_folders.size() << std::endl;
			stream << "Folder: " << boost::algorithm::join(m_folders, ",") << std::endl;
			stream << "Framerate: " << m_framerate << std::endl;

			stream << "Width: " << m_width << std::endl;
			stream << "Height: " << m_height << std::endl;
			stream << "Bit Depth: " << m_bitcount << std::endl;
			stream << "Black Level: " << m_last_black_level << std::endl;
			stream << "FrameCount: " << m_frame_count << std::endl;
			stream << "MissingFrameCount: " << m_missing_frame << std::endl;

			if (m_color_bayer)
			{
				stream << "ColorBayer: COLOR_BayerBG2RGB" << std::endl;
				stream << "ColorBalance: " << m_color_balance.kR << ", " << m_color_balance.kG << ", " << m_color_balance.kB << std::endl;
			}

			stream << "Version: " << m_camera->version() << std::endl;
			stream << "Using Sync: " << m_camera->using_hardware_sync() << std::endl;

			// Write params
			for (auto it : m_camera->params_list())
				stream << "Param " << it.first  << ":" << m_camera->param_get(it.first.c_str()) << std::endl;

			// write frames
			stream << std::endl << "frame_index;timestamp_s;delta_ms" << std::endl;
			double first_ts = m_timestamps[0];
			double last_ts = m_timestamps[0];
			for (size_t i=0;i<m_timestamps.size();i++)
			{
				stream << i << "; " << (m_timestamps[i] - first_ts) << "; " << ((m_timestamps[i] - last_ts) * 1000.0) << std::endl;
				last_ts = m_timestamps[i];
			}				
		}
	}
}

void SimpleRecorder::summarize(shared_json_doc summary)
{
	rapidjson::Value root(rapidjson::kObjectType);

	auto& a = summary->GetAllocator();

	size_t frame_size = m_width * m_height * m_bitcount / 8;
	size_t total_size = 0;

	// Store list of filenames
	rapidjson::Value filenames(rapidjson::kArrayType);
	for (auto& fn : m_filenames)
	{
		rapidjson::Value strVal;
		strVal.SetString(fn.c_str(), a);
		filenames.PushBack(strVal, a);

		total_size += boost::filesystem::file_size(fn);
	}
	root.AddMember("filenames", filenames, a);

	root.AddMember("total_size", total_size, a);
	root.AddMember("droped_frames", m_dropped_frames, a);
	
	root.AddMember("compression_ratio", (frame_size * frame_count()) / double(total_size), a);
	if (duration() > 0.0)
		root.AddMember("bandwidth", total_size / duration() / 1024 / 1024, a);

	summary->AddMember("recorder", root, a);
}

void MetadataRecorder::summarize(shared_json_doc summary)
{
	auto& a = summary->GetAllocator();

	rapidjson::Value root(rapidjson::kObjectType);
	root.AddMember("meta_filename", rapidjson::Value(m_meta_log_path.c_str(), a), a);
	root.AddMember("threads", m_folders.size(), a);
	root.AddMember("frame_count", m_frame_count, a);
	root.AddMember("width", m_width, a);
	root.AddMember("height", m_height, a);
	root.AddMember("bitdepth", m_bitcount, a);
	root.AddMember("blacklevel", m_last_black_level, a);
	root.AddMember("duration", duration(), a);
	root.AddMember("using_sync", m_camera->using_hardware_sync(), a);
	root.AddMember("missing_frames", m_missing_frame, a);
	summary->AddMember("meta", root, a);
}
