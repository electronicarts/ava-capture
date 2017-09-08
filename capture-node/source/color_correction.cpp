// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include "color_correction.hpp"

#include <opencv2/imgproc.hpp>
#include <opencv2/opencv.hpp>

namespace color_correction
{
	void apply(cv::Mat& img, rgb_color_balance bal, int black_level)
	{
		if (img.type() == CV_8UC3)
		{
			auto to_8bit = [](float val) -> unsigned char {
				int ival = val;
				if (ival > 255)
					return 255;
				if (ival <0)
					return 0;
				return ival;
			};

			for (int i = 0; i < img.cols*img.rows; i++)
			{
				img.data[i * 3 + 2] = to_8bit(((int)img.data[i * 3 + 2] - black_level) * bal.kR); // R
				img.data[i * 3 + 1] = to_8bit(((int)img.data[i * 3 + 1] - black_level) * bal.kG); // G
				img.data[i * 3 + 0] = to_8bit(((int)img.data[i * 3 + 0] - black_level) * bal.kB); // B
			}
		}
		else if (img.type() == CV_16UC3)
		{
			auto to_16bit = [](float val) -> unsigned short {
				int ival = val;
				if (ival > 65535)
					return 65535;
				if (ival <0)
					return 0;
				return ival;
			};

			unsigned short * ptr = (unsigned short *)img.data;

			for (int i = 0; i < img.cols*img.rows; i++)
			{
				ptr[i * 3 + 2] = to_16bit(((int)ptr[i * 3 + 2] - black_level) * bal.kR); // R
				ptr[i * 3 + 1] = to_16bit(((int)ptr[i * 3 + 1] - black_level) * bal.kG); // G
				ptr[i * 3 + 0] = to_16bit(((int)ptr[i * 3 + 0] - black_level) * bal.kB); // B
			}
		}
		else
		{
			printf("Color correction not implemented for type %d\n", img.type());
		}
	}

	void linear_to_sRGB(cv::Mat& img)
	{
		// a = 0.055
		// return (np.where(rgb <= 0.00313066844, 0, (1 + a) *  np.power(np.clip(rgb, 0.0, 1.0), 1 / 2.4) - a))

		auto linear_to_srgb_normalized = [](float linear) -> float {
			// linear must be between 0.0 and 1.0
			if (linear <= 0.0031308f)
				return 12.92f * linear;
			return 1.055f * powf(linear, 1.0f / 2.4f) - 0.055f;
		};

		if (img.depth() == CV_8U)
		{
			auto to_8bit = [](float val) -> unsigned char {
				int ival = val;
				if (ival > 255)
					return 255;
				if (ival <0)
					return 0;
				return ival;
			};

			for (int i = 0; i < img.cols*img.rows*img.channels(); i++)
			{
				img.data[i] = to_8bit(linear_to_srgb_normalized(img.data[i] / 255.0f)*255.0f);
			}
		}
		else if (img.depth() == CV_16U)
		{
			auto to_16bit = [](float val) -> unsigned short {
				int ival = val;
				if (ival > 65535)
					return 65535;
				if (ival <0)
					return 0;
				return ival;
			};

			unsigned short * ptr = (unsigned short *)img.data;

			for (int i = 0; i < img.cols*img.rows*img.channels(); i++)
			{
				ptr[i] = to_16bit(linear_to_srgb_normalized(ptr[i] / 65535.0f)*65535.0f);
			}
		}
		else
		{
			printf("linear_to_sRGB not implemented for type %d\n", img.type());
		}
	}
}

