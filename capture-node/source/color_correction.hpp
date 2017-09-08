// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

namespace cv { class Mat; }

namespace color_correction
{
	struct rgb_color_balance {
		rgb_color_balance() : kR(1.0f), kG(1.0f), kB(1.0f) {}
		float kR;
		float kG;
		float kB;
	};

	void apply(cv::Mat& img, rgb_color_balance bal, int black_level=0);
	void linear_to_sRGB(cv::Mat& img);
}


