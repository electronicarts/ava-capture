// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include "video_encoder.hpp"
#include "recorder.hpp"

#include <iostream>

#include <opencv2/highgui.hpp>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/imgutils.h>
}

bool VideoWriter::s_global_init = false;
int VideoWriter::s_frame_row_alignment = 32;

int ffio_set_buf_size(AVIOContext *s, int buf_size)
{
	uint8_t *buffer;
	buffer = (uint8_t*)av_malloc(buf_size);
	if (!buffer)
		return AVERROR(ENOMEM);

	av_free(s->buffer);
	s->buffer = buffer;
	s->orig_buffer_size =
		s->buffer_size = buf_size;
	s->buf_ptr = buffer;

	s->buf_end = s->buffer + s->buffer_size;
	s->write_flag = 1;
	
	return 0;
}

VideoWriter::VideoWriter(const char * filename, int framerate, int width, int height, int bpp)
	: m_framerate(framerate), m_width(width), m_height(height), m_closed(false), m_frame_counter(0),
		m_av_stream(0), m_fmt_ctx(0), m_c(0), m_format_opts(0), m_bpp(bpp)
{
	m_frame_queue.set_capacity(300); // TODO
	m_paquet_queue.set_capacity(300);

	if (!s_global_init)
	{
		s_global_init = true;
		av_register_all();
	}

	AVPixelFormat in_pix_fmt = m_bpp==8?AV_PIX_FMT_GRAY8:AV_PIX_FMT_GRAY16LE;
	AVCodecID codec_id = AV_CODEC_ID_FFVHUFF; // AV_CODEC_ID_HUFFYUV AV_CODEC_ID_FFV1 AV_CODEC_ID_FFVHUFF

	av_dict_set(&m_format_opts, "pix_fmt_in", m_bpp==8?"gray":"gray16le", 0);
	av_dict_set_int(&m_format_opts, "width_in", m_width, 0);
	av_dict_set_int(&m_format_opts, "height_in", m_height, 0);
	av_dict_set_int(&m_format_opts, "width_out", m_width, 0);
	av_dict_set_int(&m_format_opts, "height_out", m_height, 0);
	av_dict_set(&m_format_opts, "codec", "ffvhuff", 0);

	AVCodec *codec = NULL;
	int ret;
		
	ret = avformat_alloc_output_context2(&m_fmt_ctx, NULL, NULL, filename);

	// Find Codec
	codec = avcodec_find_encoder(codec_id);
	if (!codec) 
	{
		std::cerr << "Codec not found" << std::endl;
		return;
	}

	m_av_stream = avformat_new_stream(m_fmt_ctx, codec);

	m_c = avcodec_alloc_context3(codec);
	if (!m_c) 
	{
		std::cerr << "Could not allocate video codec context" << std::endl;
		return;
	}

	m_c->bit_rate = 400000;
	m_c->width = m_width;
	m_c->height = m_height;
	m_c->time_base = m_av_stream->time_base = av_make_q(1, m_framerate);
	m_c->gop_size = 12; // emit one intra frame every twelve frames at most
	m_c->max_b_frames = 1;
	m_c->pix_fmt = in_pix_fmt;

	if (m_width % s_frame_row_alignment != 0)
	{
		std::cerr << "Fatal Error: Image width must be a multiple of " << s_frame_row_alignment << std::endl;
		return;
	}

	if (m_fmt_ctx->oformat->flags & AVFMT_GLOBALHEADER)
		m_c->flags |= CODEC_FLAG_GLOBAL_HEADER;

	if (avcodec_open2(m_c, codec, &m_format_opts) < 0) 
	{
		std::cerr << "Could not open codec" << std::endl;
		return;
	}

#if LIBAVCODEC_VERSION_MAJOR>=57 && LIBAVCODEC_VERSION_MINOR>=14	
	// copy the stream parameters to the muxer
	ret = avcodec_parameters_from_context(m_av_stream->codecpar, m_c);
	if (ret < 0) 
	{
		std::cerr << "Could not copy the stream parameters" << std::endl;
		return;
	}
#else
	// copy the stream parameters to the muxer
	ret = avcodec_copy_context(m_av_stream->codec, m_c);
	if (ret < 0) 
	{
		std::cerr << "Could not copy the stream parameters" << std::endl;
		return;
	}
#endif

	// open the output file, if needed
	if (!(m_fmt_ctx->oformat->flags & AVFMT_NOFILE)) 
	{
		ret = avio_open2(&m_fmt_ctx->pb, filename, AVIO_FLAG_WRITE, 0, 0);
		if (ret < 0) 
		{
			std::cerr << "Could not open file " << filename << std::endl;
			return;
		}

		// TODO implement my own IO

		ffio_set_buf_size(m_fmt_ctx->pb, 64 * 1024 * 1024); // TODO
	}

	avformat_write_header(m_fmt_ctx, &m_format_opts);

	encode_thread = boost::thread([this]() {encodingThread(); });
	write_thread = boost::thread([this]() {writingThread(); });
}

VideoWriter::~VideoWriter()
{
	if (!m_closed)
		close();
}

int VideoWriter::buffers_used(int type) const
{
	// Return a pair of values, representing Encoding and Writing buffers

	switch (type) {
	case BUFFER_ENCODING:
		return m_frame_queue.size() * 100 / m_frame_queue.capacity();
	case BUFFER_WRITING:
		return m_paquet_queue.size() * 100 / m_paquet_queue.capacity();
	}

	return 0;
}

void VideoWriter::encodingThread()
{
	// This thread consumes frames in m_frame_queue
	// TODO This could be replaced with tbb::pipeline if we need multiple threads per stream, and we are sure
	// the codec can be parallelized.

	while (1)
	{
		AVFrame* frame = 0;
		m_frame_queue.pop(frame);
		if (!frame)
			break;

		// Encode one frame
		{
			int ret = 0;
			int got_output = 0;

			// Encode image data
			AVPacket* packet = new AVPacket;
			av_init_packet(packet);
			packet->data = NULL;    // packet data will be allocated by the encoder
			packet->size = 0;

			// Encode Frame
			ret = avcodec_encode_video2(m_c, packet, frame, &got_output);

			// Deallocate frame memory (TODO: return to available queue)
			deallocate_frame(&frame);

			{
				// Write encoded frame to queue
				if (got_output)
				{
					if (!m_paquet_queue.try_push(packet))
					{
						std::cerr << "Writer> Dropped Frame!" << std::endl;
						delete packet;
					}
				}
				else
				{
					delete packet;
				}
			}
		}
	}
}

void VideoWriter::writingThread()
{
	// This thread consumes packets from m_paquet_queue

	while (1)
	{
		AVPacket* packet = 0;
		m_paquet_queue.pop(packet);
		if (!packet)
			break;		

		// Write one packet to disk
		{
			packet->stream_index = m_av_stream->index;
			av_interleaved_write_frame(m_fmt_ctx, packet);

			av_packet_unref(packet);
			delete packet;
		}
	}
}

bool VideoWriter::addFrame(const cv::Mat& img)
{
	const int byteperpixel = m_bpp == 8 ? 1 : 2;

	AVFrame* frame = allocate_frame(); // TODO We should not allocate each frame, there whould be a queue of available frame struct to use.
	memcpy(frame->data[0], img.data, m_width*m_height*byteperpixel);
	frame->pts = m_frame_counter;
	if (!m_frame_queue.try_push(frame))
	{
		std::cerr << "Encoder> Dropped Frame!" << std::endl;
		deallocate_frame(&frame);

		return false;
	}

	m_frame_counter++;

	return true;
}

void VideoWriter::close()
{
	int ret;

	m_frame_queue.push(0); // Blocking push of terminator
	m_paquet_queue.push(0); // Blocking push of terminator
	encode_thread.join();
	write_thread.join();

	m_closed = true;

	// Delayed Frames
	for (int got_output = 1; got_output; m_frame_counter++) 
	{
		AVPacket pkt;
		av_init_packet(&pkt);
		pkt.data = NULL;    // packet data will be allocated by the encoder
		pkt.size = 0;

		ret = avcodec_encode_video2(m_c, &pkt, NULL, &got_output);
		if (ret < 0) 
		{
			std::cerr << "Error encoding frame" << std::endl;
			return;
		}
		if (got_output) 
		{
			pkt.stream_index = m_av_stream->index;
			av_interleaved_write_frame(m_fmt_ctx, &pkt);

			av_packet_unref(&pkt);
		}
	}

	av_write_trailer(m_fmt_ctx);

	avcodec_close(m_c);
	av_free(m_c);


	// Close the output file
	if (!(m_fmt_ctx->oformat->flags & AVFMT_NOFILE))
		avio_closep(&m_fmt_ctx->pb);

	if (m_fmt_ctx)
		avformat_free_context(m_fmt_ctx);
	av_dict_free(&m_format_opts);
}

AVFrame* VideoWriter::allocate_frame()
{
	AVFrame* frame = 0;

	frame = av_frame_alloc();
	if (!frame)
	{
		std::cerr << "Could not allocate video frame" << std::endl;
		return 0;
	}
	frame->format = m_c->pix_fmt;
	frame->width = m_c->width;
	frame->height = m_c->height;

	int ret = av_image_alloc(frame->data, frame->linesize, m_c->width, m_c->height, m_c->pix_fmt, s_frame_row_alignment);
	if (ret < 0)
	{
		std::cerr << "Could not allocate raw picture buffer" << std::endl;
		return 0;
	}

	return frame;
}

void VideoWriter::deallocate_frame(AVFrame** frame)
{
	if (*frame)
	{
		av_freep(&(*frame)->data[0]);
		av_frame_free(frame);
	}
}
