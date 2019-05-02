// Copyright (C) 2019 Electronic Arts Inc.  All rights reserved.

#pragma once

namespace cv { class Mat; }

class VideoWriter
{
public:
	VideoWriter() {}
	virtual ~VideoWriter() {}

	virtual bool addFrame(const cv::Mat& img, double ts) = 0;
	virtual void close() = 0;
	virtual int buffers_used(int type) const = 0;
};
