// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include "video_writer_ava.hpp"
#include "recorder.hpp"

#include <opencv2/highgui.hpp>
#include <opencv2/opencv.hpp>

#include <iostream>
#include <lz4.h>
#include <chrono>
#include <tbb/pipeline.h>

struct FrameToEncode
{
	FrameToEncode() : index(0) {} 

	std::vector<unsigned char> img_buf;
	unsigned int index;
    double ts;
};

struct PacketToWrite
{
	std::vector<unsigned char> buf;
	double ts;
};

AvaVideoWriter::AvaVideoWriter(const char * filename, 
	int framerate, int width, int height, int bpp,
	bool color_bayer, int bayer_pattern, color_correction::rgb_color_balance bal) 
: m_framerate(framerate), m_width(width), m_height(height), m_closed(false), m_frame_counter(0), m_bpp(bpp)
{
	m_frame_queue.set_capacity(300); // TODO
	m_packets_in_flight = 0;
	m_frame_unused.set_capacity(300);
	m_paquet_unused.set_capacity(300);

    // File I/O: Open file
    m_f = std::fstream(filename, std::ios::out | std::ios::binary);

	// Write File Header
	struct ava_raw_info {
		unsigned char magic; // 0xED
		unsigned char version; // 1
		unsigned char channels; // 1 or 3
		unsigned char bitcount; // 8..16
		unsigned int width;
		unsigned int height;
		unsigned int blacklevel;
		unsigned char bayer0; // first row, first pixel
		unsigned char bayer1; // first row, second pixel
		unsigned char bayer2; // second row, first pixel
		unsigned char bayer3; // second row, second pixel
		float kR;
		float kG;
		float kB;

		char compression[4];
		unsigned long long index_start_offset; // offset un bytes from the start of the file where the index will start
	};

	ava_raw_info info;
	memset(&info, 0, sizeof(info));
	info.magic = 0xED;
	info.version = 1;
	info.channels = 1; // would be 3 only for RGB data
	info.bitcount = m_bpp;
	info.width = m_width;
	info.height = m_height;
	info.blacklevel = 0; // TODO
	if (color_bayer)
	{
		switch (bayer_pattern) {
			case cv::COLOR_BayerRG2RGB: info.bayer0 = 'B'; info.bayer1 = 'G'; info.bayer2 = 'G'; info.bayer3 = 'R'; break;
			case cv::COLOR_BayerBG2RGB: info.bayer0 = 'R'; info.bayer1 = 'G'; info.bayer2 = 'G'; info.bayer3 = 'B'; break;
			case cv::COLOR_BayerGR2RGB: info.bayer0 = 'G'; info.bayer1 = 'B'; info.bayer2 = 'R'; info.bayer3 = 'G'; break;
			case cv::COLOR_BayerGB2RGB: info.bayer0 = 'G'; info.bayer1 = 'R'; info.bayer2 = 'B'; info.bayer3 = 'G'; break;
			default: info.bayer0 = ' '; info.bayer1 = ' '; info.bayer2 = ' '; info.bayer3 = ' '; break;
		}
		info.kR = bal.kR;
		info.kG = bal.kG;
		info.kB = bal.kB;
	}
	info.compression[0] = 'L';
	info.compression[1] = 'Z';
	info.compression[2] = '4';

	m_f.write((const char *)&info, sizeof(ava_raw_info));

	m_offset_for_index_start = offsetof(struct ava_raw_info, index_start_offset);
	m_offset_for_packets = m_f.tellg();

	// Run TBB Pipeline in a thread
	pipeline_thread = boost::thread([this]() {

		// Prepare TBB Pipeline to encode and write frames
		tbb::filter_t<void,FrameToEncode*> f1(tbb::filter::serial_in_order, [this](tbb::flow_control& fc) -> FrameToEncode* {
				// Consume m_frame_queue
				FrameToEncode* frame = 0;
				m_frame_queue.pop(frame);
				if (!frame)
				{
					fc.stop();
					return nullptr;
				}

				return frame;
			});
		tbb::filter_t<FrameToEncode*,PacketToWrite*> f2(tbb::filter::parallel, [this](FrameToEncode * frame){

				// Encode one frame
				PacketToWrite* packet = allocate_packet();

				packet->ts = frame->ts;
				packet->buf.resize(frame->img_buf.size()*2);
				int len = LZ4_compress_default((const char *)&frame->img_buf[0], (char *)&packet->buf[0], 
					frame->img_buf.size(), packet->buf.size());
				packet->buf.resize(len);

				deallocate_frame(&frame);

				return packet;			
			});
		tbb::filter_t<PacketToWrite*,void> f3(tbb::filter::serial_in_order, [this](PacketToWrite * packet){
			
				// Write one packet to disk
				// File I/O: Write packet to disk
				m_f.write((const char *)&packet->buf[0], packet->buf.size());

				// Store timestamp with index, check if frames are missing, to build index
				m_written_packets.push_back(std::pair<double, unsigned int>(packet->ts, packet->buf.size()));

				deallocate_packet(&packet);
			});

     	tbb::filter_t<void,void> f = f1 & f2 & f3;
     	tbb::parallel_pipeline(32,f);		
	});
}

AvaVideoWriter::~AvaVideoWriter() 
{
	if (!m_closed)
		close();
}

FrameToEncode* AvaVideoWriter::allocate_frame()
{
	FrameToEncode* ptr = 0;
	m_frame_unused.try_pop(ptr);
	if (ptr) return ptr;
	return new FrameToEncode;
}

void AvaVideoWriter::deallocate_frame(FrameToEncode** frame)
{
	m_frame_unused.push(*frame);
    *frame = 0;
}

PacketToWrite* AvaVideoWriter::allocate_packet()
{
	m_packets_in_flight++;

	PacketToWrite* ptr = 0;
	m_paquet_unused.try_pop(ptr);
	if (ptr) return ptr;
	return new PacketToWrite;
}

void AvaVideoWriter::deallocate_packet(PacketToWrite** packet)
{
	m_paquet_unused.push(*packet);
    *packet = 0;

	m_packets_in_flight--;
}

bool AvaVideoWriter::addFrame(const cv::Mat& img, double ts)
{
	const int byteperpixel = m_bpp == 8 ? 1 : 2;

	FrameToEncode* frame = allocate_frame();

	// Copy image data to FrameToEncode
	frame->img_buf.resize(img.total() * img.elemSize());
	memcpy(&frame->img_buf[0], img.data, frame->img_buf.size());
    frame->ts = ts;
	frame->index = m_frame_counter;

	if (!m_frame_queue.try_push(frame))
	{
		std::cerr << "Encoder> Dropped Frame!" << std::endl;
		deallocate_frame(&frame);

		return false;
	}

	m_frame_counter++;

	return true;
}

void AvaVideoWriter::close()
{
	m_frame_queue.push(0); // Blocking push of terminator
	pipeline_thread.join();

	m_closed = true;

	unsigned long long zero = 0;
	unsigned long long index_offset = m_f.tellg();
	unsigned long long cur_packet_offset = m_offset_for_packets;

	// Write index

	for (int i=0;i<m_written_packets.size();i++)
	{
		double offset = (i>0) ? (m_written_packets[i].first - m_written_packets[i-1].first) : 0.0;
		double ts_offset_ratio = offset * m_framerate;

		// Write offset for this frame
		m_f.write((const char *)&cur_packet_offset, sizeof(unsigned long long)); 

		// Write offset=0 for missing frames (frames that were not recorded according to timestamps)
		int nb_extra_frames = int(ts_offset_ratio-0.5);
		for (int j=0;j<nb_extra_frames;j++)
			m_f.write((const char *)&zero, sizeof(unsigned long long));

		cur_packet_offset += m_written_packets[i].second;
	}

	// Write offset for start of index
	m_f.seekg(m_offset_for_index_start);
	m_f.write((const char *)&index_offset, sizeof(unsigned long long));

    // File I/O: Close file
    m_f.close();
}

int AvaVideoWriter::buffers_used(int type) const
{
	// Return a pair of values, representing Encoding and Writing buffers

	switch (type) {
	case BUFFER_ENCODING:
		return m_frame_queue.size() * 100 / m_frame_queue.capacity();
	case BUFFER_WRITING:
		return m_packets_in_flight * 100 / 32;
	}

	return 0;
}
