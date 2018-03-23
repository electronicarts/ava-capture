// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include <vector>
#include <string>
#include <memory>
#include <mutex>

#include <opencv2/highgui.hpp>

#include "json.hpp"
#include "color_correction.hpp"
#include "video_encoder.hpp"

enum { BUFFER_ENCODING, BUFFER_WRITING };

class Recorder
{
public:
	Recorder(int framerate, int width, int height, int bitcount, const std::vector<std::string>& folders);
	virtual ~Recorder();

	int frame_count() const { return m_frame_count; }

	void append(cv::Mat img, double ts, int blacklevel);
	void close();

	virtual void summarize(shared_json_doc summary) = 0;

	virtual int buffers_used(int type) const { return 0; }

	double duration() const {
		return m_last_ts - m_first_ts;
	}

protected:
	virtual void append_impl(cv::Mat img, double ts, int blacklevel);
	virtual void close_impl();

protected:
	std::string m_filename;
	int m_width;
	int m_height;
	int m_bitcount;
	int m_framerate;
	int m_frame_count;
	std::vector<std::string> m_folders;
	double m_first_ts;
	double m_last_ts;

private:
	bool m_closed;
	std::mutex m_mutex;
};

class SimpleRecorder : public Recorder
{
public:
	SimpleRecorder(const std::string& unique_name, int framerate, int width, int height, int bitcount, const std::vector<std::string>& folders);

	virtual void summarize(shared_json_doc summary) override;

protected:
	std::vector<std::string> m_filenames;
	std::string m_unique_name;
	int m_dropped_frames;
};

class SimpleImageRecorder : public SimpleRecorder
{
public:
	SimpleImageRecorder(const std::string& unique_name, int framerate, int width, int height, int bitcount, bool color_bayer, int bayer_pattern, color_correction::rgb_color_balance bal, const std::vector<std::string>& folders);

protected:
	virtual void append_impl(cv::Mat img, double ts, int blacklevel) override;
	virtual void close_impl() override;

	bool m_color_bayer;
	int m_bayerpattern;
	color_correction::rgb_color_balance m_color_balance;
};

class SimpleMovieRecorder : public SimpleRecorder
{
public:
	SimpleMovieRecorder(const std::string& unique_name, int framerate, int width, int height, int bitcount, const std::vector<std::string>& folders);

	virtual int buffers_used(int type) const override;

protected:
	virtual void append_impl(cv::Mat img, double ts, int blacklevel) override;
	virtual void close_impl() override;

private:
	std::vector<std::unique_ptr<VideoWriter> > m_writers;
};

class MetadataRecorder : public Recorder
{
public:
	MetadataRecorder(const std::string& unique_name, int framerate, int width, int height, int bitcount, bool color_bayer, color_correction::rgb_color_balance bal, const std::vector<std::string>& folders, class Camera* parent);

	virtual void summarize(shared_json_doc summary) override;

protected:
	virtual void append_impl(cv::Mat img, double ts, int blacklevel) override;
	virtual void close_impl() override;

private:
	std::string m_meta_log_path;
	std::vector<double> m_timestamps;

	Camera* m_camera;

	double m_last_ts;
	int m_missing_frame;

	int m_last_black_level;

	bool m_color_bayer;
	color_correction::rgb_color_balance m_color_balance;
};
