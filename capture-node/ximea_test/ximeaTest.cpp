// ximeaTest.cpp : test ximeas bandwidth and version

#include "stdafx.h"

#ifdef WIN32
#include <xiApi.h>       // Windows
#else
#include <m3api/xiApi.h> // Linux, OSX
#endif
#include <memory.h>

#include <string>
#include <vector>

#include <opencv2/opencv.hpp>
using namespace cv;

#define HandleResult(res,place) if (res!=XI_OK) {printf("Error after %s (%d)\n",place,res); exit(1);}

int get_param_int(HANDLE xiH, const char * what)
{
	int val = 0;
	XI_RETURN ret = xiGetParamInt(xiH, what, &val);
	if (ret != XI_OK)
		printf("Error reading parameter %s (ret=%d)\n", what, ret);
	return val;
}

void set_param_int(HANDLE xiH, const char * what, int value)
{
	XI_RETURN ret = xiSetParamInt(xiH, what, value);
	if (ret != XI_OK)
		printf("Error setting parameter %s to %d (ret=%d)\n", what, value, ret);
	else
		printf("%s=%d\n", what, get_param_int(xiH, what));
}

std::string get_param_str(HANDLE xiH, const char * what)
{
	char buffer[256] = "";
	xiGetParamString(xiH, what, buffer, 255);
	return std::string(buffer);
}

int captureSomeFrames(HANDLE xiH)
{
	int failed = 0;

	XI_RETURN stat = XI_OK;

	float framerate = 0.0f;
	xiGetParamFloat(xiH, "framerate", &framerate);
	printf("START CAPTURE AT %.1f FPS\n", framerate);

	printf("Sensor:%d bits Output:%d bits Image:%d bits (packing:%d) black:%d\n",
		get_param_int(xiH, XI_PRM_SENSOR_DATA_BIT_DEPTH), get_param_int(xiH, XI_PRM_OUTPUT_DATA_BIT_DEPTH), get_param_int(xiH, XI_PRM_IMAGE_DATA_BIT_DEPTH), get_param_int(xiH, XI_PRM_OUTPUT_DATA_PACKING), get_param_int(xiH, XI_PRM_IMAGE_BLACK_LEVEL));

	printf("Starting acquisition...\n");
	stat = xiStartAcquisition(xiH);
	HandleResult(stat, "xiStartAcquisition");

	double last_ts = 0.0;

#define EXPECTED_IMAGES 1
	for (int images = 0; images < EXPECTED_IMAGES; images++)
	{
		XI_IMG image;
		memset(&image, 0, sizeof(image));
		image.size = SIZE_XI_IMG_V3;

		// getting image from camera
		stat = xiGetImage(xiH, 5000, &image);
		HandleResult(stat, "xiGetImage");

		const char *fileName = "example.png";
		int width = 1024;
		int height = 1024;
		int byte_per_pixel = 1;
		int max_pixel_value = 255;
		Mat img_raw = Mat(height, width, CV_8UC1, image.bp, cv::Mat::AUTO_STEP);
		std::vector<int> compression_params;
		compression_params.push_back(IMWRITE_PNG_COMPRESSION);
		compression_params.push_back(0);
		imwrite(fileName, img_raw, compression_params);

		double ts = image.tsSec + image.tsUSec / 1000000.0;
		unsigned char pixel = *(unsigned char*)image.bp;

		printf("Image %03d (%dx%d) received from camera. FirstPixel:%d BlackPoint:%d (stat=%d) ", images, (int)image.width, (int)image.height, pixel, image.black_level, stat);
		if (images > 0)
		{
			double effective_fps = 1.0 / (ts - last_ts);
			printf("Delta:%.1fms  Fps:%.1f ", (ts - last_ts)*1000.0, effective_fps);

			if (abs(effective_fps - framerate) > 0.01f*framerate)
			{
				failed++;
				printf(" FAIL");
			}

		}
		printf("\n");

		last_ts = ts;
	}

	printf("Stopping acquisition...\n");
	stat = xiStopAcquisition(xiH);
	HandleResult(stat, "xiStopAcquisition");

	return failed;
}

int _tmain(int argc, char* argv[])
{
	int errors = 0;

	XI_RETURN stat = XI_OK;
	HANDLE xiH = NULL;

	// Disable bancdwidth calculation for all cameras
	xiSetParamInt(0, XI_PRM_AUTO_BANDWIDTH_CALCULATION, XI_OFF);

	// Make sure no devices are connected at this time
	DWORD numDevices = 0;
	xiGetNumberDevices(&numDevices);
	if (numDevices<=0)
	{
		printf("Make sure at least one camera is connected when launching this test");
		return 1;
	}

	for (DWORD i = 0; i < numDevices; i++)
	{
		char buffer[512];

		memset(buffer, 0, 512);
		xiGetDeviceInfoString(i, XI_PRM_DEVICE_NAME, buffer, 511);
		printf("Camera %d %s\n", i, buffer);

		// Retrieving a handle to the camera device 
		printf("Opening Camera %d...\n", i);
		stat = xiOpenDevice(i, &xiH);
		HandleResult(stat, "xiOpenDevice");

		set_param_int(xiH, XI_PRM_DEBUG_LEVEL, XI_DL_FATAL);

		printf("VERSION ");
		printf(" REV:%d", get_param_int(xiH, XI_PRM_HW_REVISION));
		printf(" API:%s", get_param_str(xiH, XI_PRM_API_VERSION).c_str());
		printf(" DRV:%s", get_param_str(xiH, XI_PRM_DRV_VERSION).c_str());
		printf(" FPGA:%s", get_param_str(xiH, XI_PRM_FPGA1_VERSION).c_str());
		printf(" CPU1:%s", get_param_str(xiH, XI_PRM_MCU1_VERSION).c_str());
		printf(" CPU2:%s", get_param_str(xiH, XI_PRM_MCU2_VERSION).c_str());
		printf(" XML:%s", get_param_str(xiH, XI_PRM_XMLMAN_VERSION).c_str());
		printf(" HW:%d\n", get_param_int(xiH, XI_PRM_HW_REVISION));

#ifdef WIN32
	#define EXPECTED_API_VERSION "V4.13.17.00"
	#define EXPECTED_DRV_VERSION "2.00.05"
	#define EXPECTED_F1_VERSION "01.18"
	#define EXPECTED_C1_VERSION "04.22"
	#define EXPECTED_C2_VERSION "02.04"
	#define EXPECTED_XML_VERSION "02.04.01"
#else
	#define EXPECTED_API_VERSION "V4.27.03.00"
	#define EXPECTED_DRV_VERSION "0"
	#define EXPECTED_F1_VERSION "01.18"
	#define EXPECTED_C1_VERSION "04.22"
	#define EXPECTED_C2_VERSION "02.04"
	#define EXPECTED_XML_VERSION "02.04.01"
#endif

		if (get_param_str(xiH, XI_PRM_API_VERSION) != EXPECTED_API_VERSION) {
			printf("INVALID XI_PRM_API_VERSION %s expecting %s\n", get_param_str(xiH, XI_PRM_API_VERSION).c_str(), EXPECTED_API_VERSION);
			exit(1);
		}
		if (get_param_str(xiH, XI_PRM_DRV_VERSION) != EXPECTED_DRV_VERSION) {
			printf("INVALID XI_PRM_DRV_VERSION %s expecting %s\n", get_param_str(xiH, XI_PRM_DRV_VERSION).c_str(), EXPECTED_DRV_VERSION);
			exit(1);
		}
		if (get_param_str(xiH, XI_PRM_FPGA1_VERSION) != EXPECTED_F1_VERSION) {
			printf("INVALID XI_PRM_FPGA1_VERSION %s expecting %s\n", get_param_str(xiH, XI_PRM_FPGA1_VERSION).c_str(), EXPECTED_F1_VERSION);
			exit(1);
		}
		if (get_param_str(xiH, XI_PRM_MCU1_VERSION) != EXPECTED_C1_VERSION) {
			printf("INVALID XI_PRM_MCU1_VERSION %s expecting %s\n", get_param_str(xiH, XI_PRM_MCU1_VERSION).c_str(), EXPECTED_C1_VERSION);
			exit(1);
		}
		if (get_param_str(xiH, XI_PRM_MCU2_VERSION) != EXPECTED_C2_VERSION) {
			printf("INVALID XI_PRM_MCU2_VERSION %s expecting %s\n", get_param_str(xiH, XI_PRM_MCU2_VERSION).c_str(), EXPECTED_C2_VERSION);
			exit(1);
		}
		if (get_param_str(xiH, XI_PRM_XMLMAN_VERSION) != EXPECTED_XML_VERSION) {
			printf("INVALID XI_PRM_XMLMAN_VERSION %s expecting %s\n", get_param_str(xiH, XI_PRM_XMLMAN_VERSION).c_str(), EXPECTED_XML_VERSION);
			exit(1);
		}
	}

	// Setting all camera parameters
	set_param_int(xiH, XI_PRM_EXPOSURE, 5 * 1000); // microseconds
	set_param_int(xiH, XI_PRM_OFFSET_X, 0);
	set_param_int(xiH, XI_PRM_OFFSET_Y, 0);
	set_param_int(xiH, XI_PRM_AEAG, 0);
	set_param_int(xiH, XI_PRM_LUT_EN, 0);
	set_param_int(xiH, XI_PRM_GAIN, 0);
	//set_param_int(xiH, XI_PRM_ACQ_TIMING_MODE, XI_ACQ_TIMING_MODE_FRAME_RATE);
	set_param_int(xiH, XI_PRM_ACQ_TIMING_MODE, XI_ACQ_TIMING_MODE_FRAME_RATE_LIMIT);
	set_param_int(xiH, XI_PRM_FRAMERATE, 30); // Hz	
	set_param_int(xiH, XI_PRM_BUFFER_POLICY, XI_BP_UNSAFE);
	set_param_int(xiH, XI_PRM_BUFFERS_QUEUE_SIZE, get_param_int(xiH, XI_PRM_BUFFERS_QUEUE_SIZE XI_PRM_INFO_MAX));
	set_param_int(xiH, XI_PRM_GPI_SELECTOR, 1); // Pin 1
	set_param_int(xiH, XI_PRM_GPI_MODE, XI_GPI_TRIGGER);
	set_param_int(xiH, XI_PRM_TRG_SOURCE, XI_TRG_EDGE_RISING);
	set_param_int(xiH, XI_PRM_BPC, XI_ON);
	//set_param_int(xiH, XI_PRM_IMAGE_BLACK_LEVEL, 0);
	set_param_int(xiH, XI_PRM_IMAGE_DATA_FORMAT, XI_RAW8);

	int m_max_bandwidth = get_param_int(xiH, XI_PRM_AVAILABLE_BANDWIDTH);
	printf("Max Bandwdth: %d Mbit/s\n", m_max_bandwidth);

	printf("Size of one frame: %d\n", get_param_int(xiH, XI_PRM_HEIGHT) * get_param_int(xiH, XI_PRM_WIDTH));
	printf("XI_PRM_IMAGE_PAYLOAD_SIZE=%d\n", get_param_int(xiH, XI_PRM_IMAGE_PAYLOAD_SIZE));
	printf("MAX XI_PRM_ACQ_TRANSPORT_BUFFER_SIZE=%d\n", get_param_int(xiH, XI_PRM_ACQ_TRANSPORT_BUFFER_SIZE XI_PRM_INFO_MAX));	
	printf("XI_PRM_ACQ_TRANSPORT_BUFFER_SIZE=%d\n", get_param_int(xiH, XI_PRM_ACQ_TRANSPORT_BUFFER_SIZE));
	printf("XI_PRM_ACQ_BUFFER_SIZE=%d\n", get_param_int(xiH, XI_PRM_ACQ_BUFFER_SIZE));

	int framerates[] = { 10,20,30,70,72,44,45,64,63,20,50 }; // fails for 46 to 64
	for (int i = 0; i < sizeof(framerates) / sizeof(framerates[0]); i++)
	{
		int m_bitcount = 8;
		int m_height = get_param_int(xiH, XI_PRM_HEIGHT);
		int m_width = get_param_int(xiH, XI_PRM_WIDTH);
		int m_framerate = framerates[i];

		unsigned long long bw = (unsigned long long)m_framerate * (unsigned long long)m_width * (unsigned long long)m_height * (unsigned long long)8 / (unsigned long long)(1000000);

		// add 2% padding
		bw += (bw * 2) / 100;

		//unsigned long long bw = 3000; // TEMPORARY HARDCODED

		// max bandwidth reported by the ximea api
		if (bw > m_max_bandwidth)
			bw = m_max_bandwidth;

		printf("Fr:%d W:%d H:%d B:%d\n", m_framerate, m_width, m_height, m_bitcount);
		printf("Set Ximea bandwidth to %I64d megabits/s (was %d)\n", bw, get_param_int(xiH, XI_PRM_LIMIT_BANDWIDTH));

		set_param_int(xiH, XI_PRM_TRG_SOURCE, XI_TRG_OFF); // camera runs in freerun mode
		set_param_int(xiH, XI_PRM_FRAMERATE, m_framerate);
		set_param_int(xiH, XI_PRM_LIMIT_BANDWIDTH, bw); //  bw);
		set_param_int(xiH, XI_PRM_LIMIT_BANDWIDTH_MODE, 1);
		//set_param_int(xiH, XI_PRM_LIMIT_BANDWIDTH_MODE, 0);
		errors += captureSomeFrames(xiH);
	}

	xiCloseDevice(xiH);

	if (errors>0) {
		printf("\nFAILED\n");
		return 1;
	}

	printf("\nSUCCESS\n");
	return 0;
}

