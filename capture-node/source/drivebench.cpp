// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include "drivebench.hpp"

#include <vector>
#include <string>
#include <iostream>
#include <chrono>
#include <sstream>

#include <boost/algorithm/string.hpp>
#include <boost/filesystem.hpp>

#include <boost/uuid/uuid.hpp>            // uuid class
#include <boost/uuid/uuid_generators.hpp> // generators
#include <boost/uuid/uuid_io.hpp>         // streaming operators etc.

#ifdef WIN32
	#include <windows.h>
#else
	#include <fcntl.h>
#endif

size_t get_drive_speed(boost::filesystem::path dir)
{
	const size_t blocksize = 400 * 1024 * 1024; // TODO
	const size_t chunk_size = 4 * 1024 * 1024;

	std::vector<char> random(chunk_size);

	namespace fs = boost::filesystem;

	{
		try {
			if (!fs::exists(dir))
			{
				if (!fs::create_directory(dir))
				{
					std::cerr << " Error creating directory " << dir << std::endl;
					return 0;
				}
			}
		}
		catch(...)
		{
			std::cerr << " Could not create directory " << dir << std::endl;
			return 0;
		}
	}

	boost::uuids::uuid uuid = boost::uuids::random_generator()();
	std::stringstream ss;
	ss << uuid;

	fs::path temp_file = dir / (ss.str() + ".dat");

	typedef std::chrono::high_resolution_clock Clock;
	auto t1 = Clock::now();

	size_t written = 0;
	{
#ifdef WIN32		
		HANDLE hFile = CreateFileA(temp_file.string().c_str(), GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
			FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN, 
			NULL);

		if (!hFile)
		{
			std::cout << dir << " Failed to write test file" << std::endl;
			return 0;
		}

		while (written < blocksize)
		{
			DWORD written_chunk = 0;
			BOOL isOK = WriteFile(hFile, &random[0], chunk_size, &written_chunk, NULL);

			if (!isOK || written_chunk == 0)
			{
				std::cout << " Error writing to test file in " << dir << std::endl;
				return 0;
			}

			written += written_chunk;
		}
		FlushFileBuffers(hFile);
		CloseHandle(hFile);
#else
		FILE *fp;
		fp = fopen(temp_file.string().c_str(), "wb");
		setbuf(fp, NULL); // no buffering
		while (written < blocksize)
		{
			size_t written_chunk = fwrite(&random[0], 1, chunk_size, fp);

			if (written_chunk != chunk_size)
			{
				std::cout << " Error writing to test file in " << dir << std::endl;
				return 0;
			}

			written += written_chunk;
		}
		fflush(fp);
		fclose(fp);
#endif		
	}

	auto t2 = Clock::now();
	size_t speed = (written * 1E6 / std::chrono::duration_cast<std::chrono::microseconds>(t2 - t1).count() / 1024 / 1024);

	fs::space_info si = fs::space(dir);

	std::cout << dir << " " << speed << " MB/s, Available: " << (si.available / 1024 / 1024 / 1024) << " GB" << std::endl;

	fs::remove(temp_file);

	return speed;
}

size_t get_drive_speed(const std::string& folder)
{
	boost::filesystem::path dir(folder);
	return get_drive_speed(dir);
}

#ifdef WIN32

std::vector<std::string> get_drive_list()
{
	// Windows-Specific, get list of writable hard drives on the machine
	char buffer[1000];
	DWORD len = GetLogicalDriveStrings(999, buffer);

	std::vector<std::string> drives;
	for (size_t i = 0; i < len; i++)
	{
		std::string drive = &buffer[i];
		if (GetDriveType(drive.c_str()) == DRIVE_FIXED)
			drives.push_back(drive);
		i += drive.size();
	}

	return drives;
}

std::vector<std::pair<std::string, size_t> > get_recording_folder_list()
{
	namespace fs = boost::filesystem;

	std::vector<std::pair<std::string, size_t> > results;

	// Returns a list of folders that can be used for recording, with the recording speed.
	// Returns an approximation of the drive write speed (MB/s)

	std::vector<std::string> drives = get_drive_list();

	for (auto& drive : drives)
	{
		fs::path dir(drive + "ava_capture");

		size_t speed = get_drive_speed(dir);

		if (speed == 0)
			continue;

		results.push_back(std::make_pair(dir.string(), speed));
	}

	std::sort(results.begin(), results.end(), [](std::pair<std::string, size_t> a, std::pair<std::string, size_t> b) {
		return b.second < a.second;
	});

	return results;
}

#endif