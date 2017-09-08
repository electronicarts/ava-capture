// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include "base64.hpp"

#include <sstream>

#include <boost/archive/iterators/base64_from_binary.hpp>
#include <boost/archive/iterators/transform_width.hpp>

std::string base64encode(const std::string& str)
{
	typedef
		boost::archive::iterators::base64_from_binary<
		boost::archive::iterators::transform_width<const char *, 6, 8>
		>
		base64_text;

	std::stringstream os;
	std::copy(
		base64_text(str.c_str()),
		base64_text(str.c_str() + str.size()),
		std::ostream_iterator<char>(os)
	);

	return os.str();
}

std::string base64encode(const std::vector<unsigned char>& buf)
{
	typedef
		boost::archive::iterators::base64_from_binary<
		boost::archive::iterators::transform_width<const char *, 6, 8>
		>
		base64_text;

	std::stringstream os;
	std::copy(
		base64_text(&buf[0]),
		base64_text(&buf[0] + buf.size()),
		std::ostream_iterator<char>(os)
	);

	return os.str();
}
