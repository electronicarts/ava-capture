// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include "nodehttpserver.hpp"
#include "capturenode.hpp"
#include "server_uplink.hpp"
#include "embedded_python.hpp"

#include "build_generated.h"

#ifdef WIN32
	#include <conio.h>
#else
	#include <stdlib.h>
	#include <sys/select.h>
	#include <termios.h>
#endif

#include <boost/thread/thread.hpp>
#include <boost/program_options.hpp>

#define DEFAULT_SERVER "ava.ea.com"
#define DEFAULT_PORT 443

#define USERNAME "pythonscript"
#define PASSWORD "xxPASSWORDxx"

#pragma warning(disable:4505) // for bool_switch

volatile int exit_requested = 0;

class UniqueProcessProtection
{
public:
	UniqueProcessProtection()
	{
#ifdef WIN32		
		const char szUniqueNamedMutex[] = "ea.ava.avacapture";
		hHandle = CreateMutex(NULL, TRUE, szUniqueNamedMutex);
		if (ERROR_ALREADY_EXISTS == GetLastError())
		{
			std::cerr << "Process is already running" << std::endl;
			exit(1);
		}
#else
	#pragma message("TODO Implement in Linux") 
#endif
	}
	~UniqueProcessProtection()
	{
#ifdef WIN32
		ReleaseMutex(hHandle); // Explicitly release mutex
		CloseHandle(hHandle); // close handle before terminating
#endif
	}
private:
#ifdef WIN32
	HANDLE hHandle;
#endif
};

#ifndef WIN32
int _kbhit()
{
	struct timeval tv = {0L,0L};
	fd_set fds;
	FD_ZERO(&fds);
	FD_SET(0, &fds);
	return select(1, &fds, NULL, NULL, &tv);
}
int _getch()
{
	return fgetc(stdin); // Will need to press Enter after entering a character
}
void signal_recieved(int sig)
{
	exit_requested = 1;
}
#endif 

int main(int argc, char** argv)
{
	#ifndef WIN32
	signal(SIGINT, signal_recieved);
	signal(SIGHUP, signal_recieved);
	#endif

	UniqueProcessProtection p;

	PythonEngine::Init(argv[0]);

	namespace po = boost::program_options;
	po::options_description desc("Options");
	desc.add_options()
		("help", "Display command line options")
		("server", po::value<std::string>()->default_value(DEFAULT_SERVER), "Server address")
		("port", po::value<int>()->default_value(DEFAULT_PORT), "Port of the server")
		("webcams", po::bool_switch()->default_value(false), "Initialize all available Webcams")
		("service", po::bool_switch()->default_value(false), "Run without the interactive prompt")
#ifdef WITH_PORTAUDIO		
		("audio", po::bool_switch()->default_value(false), "Initialize default audio capture device")
#endif
		("folder", po::value<std::string>()->default_value(std::string()), "Folder where recordings are stored");
	po::variables_map vm;
	try
	{
		po::store(po::parse_command_line(argc, argv, desc), vm); // can throw 

		if (vm.count("help"))
		{
			std::cout << desc << std::endl;
			return 0;
		}

		po::notify(vm); // throws on error, so do after help in case 
						// there are any problems 
	}
	catch (po::error& e)
	{
		std::cerr << "ERROR: " << e.what() << std::endl << std::endl;
		std::cerr << desc << std::endl;
		return 1;
	}

	// Launch Node, Server, ServerUplink

	const bool use_webcams = vm["webcams"].as<bool>();
	const bool run_as_service = vm["service"].as<bool>();

#ifdef WITH_PORTAUDIO
	const bool use_audio = vm["audio"].as<bool>();
#else
	const bool use_audio = false;
#endif
	std::string folder = vm["folder"].as<std::string>();

	std::shared_ptr<CaptureNode> node(new CaptureNode(use_webcams, use_audio, folder));

	NodeHttpServer httpd(node, 8080);
	boost::thread http_thread([&httpd]() {httpd.serve_forever(); });

	ServerUplink uplink(node, vm["server"].as<std::string>().c_str(), vm["port"].as<int>(), USERNAME, PASSWORD, GIT_REVISION);

	std::string global_params = uplink.sendKeepalive(true);
	node->setGlobalParams(global_params);

	if (run_as_service)
	{
		while (!exit_requested && !node->shutdown_requested())
		{
			boost::this_thread::sleep_for(boost::chrono::milliseconds(500));

			size_t new_devices_count = node->scan_for_new_devices();
			node->remove_invalid_devices();

			if (new_devices_count>0)
			{
				global_params = uplink.sendKeepalive(true);
				node->setGlobalParams(global_params);
			}
		}
	}
	else
	{
		// Launch Interactive Menu

		while (!exit_requested && !node->shutdown_requested())
		{
			std::cout << "-----------------------------------------------------------" << std::endl;

			for (const std::shared_ptr<Camera>& cam : node->cameraList())
			{
				std::cout << "* " << cam->toString() << std::endl;
			}

			if (node->sync_connected())
				std::cout << "*** Hardware Sync(" << node->sync_port() << ") @ " << node->global_framerate() 
					<< " Hz (" << node->global_pulse_duration() << " us) ***" << std::endl;

			std::cout <<
				"Q:Quit" << std::endl <<
				"T:Record one frame (all cameras)" << std::endl <<
				"S:Stop recording/abort (all cameras)" << std::endl <<
				"R:Start recording (all cameras)" << std::endl <<
				"F:Change hardware sync frequency (and enable HWSync on all camera)" << std::endl <<
				"D:Display all parameter values" << std::endl <<
				"i:Set camera ROI" << std::endl <<
				"V:Change parameter value (all cameras)" << std::endl <<
				"A:Run autofocus (all cameras)" << std::endl;

			while (!_kbhit() && !exit_requested && !node->shutdown_requested())
			{
				boost::this_thread::sleep_for(boost::chrono::milliseconds(200));

				size_t new_devices_count = node->scan_for_new_devices();
				node->remove_invalid_devices();

				if (new_devices_count>0)
				{
					global_params = uplink.sendKeepalive(true);
					node->setGlobalParams(global_params);
				}
			}

			if (exit_requested || node->shutdown_requested())
				break;

			char c = _getch();
			switch (c) {
			case 'q':
				exit_requested = 1;
				break;
			case 'i':
			{
				int x1,x2,y1,y2;
				std::cout << "X Min:";
				std::cin >> x1;
				std::cout << "X Max:";
				std::cin >> x2;
				std::cout << "Y Min:";
				std::cin >> y1;
				std::cout << "Y Max:";
				std::cin >> y2;
				{
					for (const std::shared_ptr<Camera>& cam : node->cameraList())
						cam->set_roi(x1,y1,x2,y2);
				}
				break;
			}
			case 't':
				// Capture a single frame from all cameras
				if (node->can_record())
					node->record_image_sequence(1);
				break;
			case 'r':
				// Begin recording AVI / MKV
				if (node->can_record())
					node->start_recording_all();
				break;
			case 's':
				// Stop Recording all cameras
				node->pause_sync();
				node->stop_recording_all();
				node->resume_sync(false);
				break;
			case 'f':
				{
					int new_freq = 30;
					int new_dur = 3000;
					std::cout << "Please enter new frequency (0 to disable sync):";
					std::cin >> new_freq;
					std::cout << "Please enter new pulse duration (microseconds):";
					std::cin >> new_dur;
					if (new_freq)
					{
						node->set_global_framerate(new_freq, new_dur, false);
						for (const std::shared_ptr<Camera>& cam : node->cameraList())
							cam->set_hardware_sync(true, new_freq);
					}
					else
					{
						for (const std::shared_ptr<Camera>& cam : node->cameraList())
							cam->set_hardware_sync(false, 0);
					}
				}
				break;
			case 'v':
				{
					std::string parameter;
					float value = 0.0f;
					std::cout << "Please enter parameter name:";
					std::cin >> parameter;
					std::cout << "Please enter value:";
					std::cin >> value;
					for (const std::shared_ptr<Camera>& cam : node->cameraList())
						cam->param_set(parameter.c_str(), value);
				}
				break;
			case 'd':
				{
					for (const std::shared_ptr<Camera>& cam : node->cameraList())
					{
						std::cout << "+++++ Camera " << cam->unique_id() << " +++++" << std::endl;
						auto list = cam->params_list();
						for (auto e : list)
						{
							std::cout << "  [" << e.first << "]: " << cam->param_get(e.first.c_str()) << std::endl;
						}
					}
				}
				break;
			default:
				std::cerr << "Unknown command" << std::endl;
				break;
			}
		}
	}

	httpd.close();
	http_thread.join();	

	if (node->shutdown_requested())
	{
		std::cout << "Restarting..." << std::endl;
		return 50;
	}
	else
	{
		std::cout << "Shutting Down..." << std::endl;
	}

	return 0;
}
