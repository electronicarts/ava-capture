// Copyright (C) 2019 Electronic Arts Inc.  All rights reserved.

#pragma once

namespace cv { class Mat; }

#include <tbb/concurrent_queue.h>
#include <boost/thread.hpp>
#include <fstream>

#include "video_writer.hpp"
#include "color_correction.hpp"

struct FrameToEncode;
struct PacketToWrite;

class AvaVideoWriter : public VideoWriter
{
public:
	AvaVideoWriter(const char * filename, 
		int framerate, int width, int height, int bpp,
		bool color_bayer, int bayer_pattern, color_correction::rgb_color_balance bal);
	virtual ~AvaVideoWriter();

	virtual bool addFrame(const cv::Mat& img, double ts) override;
	virtual void close() override;
	virtual int buffers_used(int type) const override;

protected:
	FrameToEncode* allocate_frame();
	void deallocate_frame(FrameToEncode** frame);

	PacketToWrite* allocate_packet();
	void deallocate_packet(PacketToWrite** frame);

private:
	int m_frame_counter;
	int m_framerate;
	int m_width;
	int m_height;
	int m_bpp;
	bool m_closed;

	unsigned int m_offset_for_index_start;
	unsigned int m_offset_for_packets;

	std::fstream m_f;

	std::vector<std::pair<double, unsigned int> > m_written_packets;

	tbb::concurrent_bounded_queue<FrameToEncode*> m_frame_unused;
	tbb::concurrent_bounded_queue<PacketToWrite*> m_paquet_unused;

	tbb::concurrent_bounded_queue<FrameToEncode*> m_frame_queue;
	tbb::atomic<int> m_packets_in_flight;

	boost::thread pipeline_thread;
};
