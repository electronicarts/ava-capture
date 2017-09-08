// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include "httpserver.hpp"

#include <boost/asio.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/thread/thread.hpp>

#include <iostream>

#define HTTP_SERVER_MULTI_THREADED

using namespace boost;
using namespace boost::system;
using namespace boost::asio;

HttpServer::HttpServer(int port) : m_port(port)
{
}

HttpServer::~HttpServer()
{

}

void HttpServer::close()
{
	m_io_service.stop();
}

void HttpServer::accept_and_run(ip::tcp::acceptor& acceptor, io_service& io_service)
{
	std::shared_ptr<Session> session = CreateSession();

	acceptor.async_accept(session->socket, [this, session, &acceptor, &io_service](const error_code& accept_error)
	{
		accept_and_run(acceptor, io_service);
		if (!accept_error)
		{
			Session::run(session);
		}
	});
}

void Session::read_content(std::shared_ptr<Session> session, size_t len)
{
	session->request.content.reserve(len);

	// Check if our data is already available in session->buff
	if (session->buff.in_avail())
	{
		std::istream stream{ &session->buff };
		session->request.content += std::string(std::istreambuf_iterator<char>(stream), {}); // read entire stream into request.content

		if (session->request.content.size() >= len)
		{
			std::shared_ptr<std::string> str = std::make_shared<std::string>(session->server->handleRequest(session));
			asio::async_write(session->socket, boost::asio::buffer(str->c_str(), str->length()), [session, str](const error_code& e, std::size_t s)
			{
				//std::cout << "done" << std::endl;
			});
		}
	}

	// More data to download
	if (len > session->request.content.size())
	{
		asio::async_read(session->socket, session->buff, boost::asio::transfer_exactly(len - session->request.content.size()), [session](const error_code& e, std::size_t s)
		{
			std::istream stream{ &session->buff };
			session->request.content += std::string(std::istreambuf_iterator<char>(stream), {}); // read entire stream into request.content

			std::shared_ptr<std::string> str = std::make_shared<std::string>(session->server->handleRequest(session));
			asio::async_write(session->socket, boost::asio::buffer(str->c_str(), str->length()), [session, str](const error_code& e, std::size_t s)
			{
				//std::cout << "done" << std::endl;
			});
		});
	}
}

void Session::read_next_headers(std::shared_ptr<Session> session)
{
	asio::async_read_until(session->socket, session->buff, '\r', [session](const error_code& e, std::size_t s)
	{
		// Get Header Line
		std::string line, ignore;
		std::istream stream{ &session->buff };
		std::getline(stream, line, '\r');
		std::getline(stream, ignore, '\n');

		// std::cout << "HTTP Server DEBUG " << line << std::endl;

		session->request.addLine(line);

		// Decide if we want to continue headers or read content
		if (line.length() == 0)
		{
			if (session->request.content_length() == 0)
			{
				std::shared_ptr<std::string> str = std::make_shared<std::string>(session->server->handleRequest(session));
				asio::async_write(session->socket, boost::asio::buffer(str->c_str(), str->length()), [session, str](const error_code& e, std::size_t s)
				{
					//std::cout << "done" << std::endl;
				});
			}
			else
			{
				read_content(session, session->request.content_length());
			}
		}
		else
		{
			read_next_headers(session);
		}
	});

}

void Session::read_request(std::shared_ptr<Session> session)
{
	std::string line, ignore;
	std::istream stream{ &session->buff };
	std::getline(stream, line, '\r');
	std::getline(stream, ignore, '\n');

	//std::cout << "HTTP Server DEBUG " << line << std::endl;

	session->request.addLine(line);

	read_next_headers(session);
}

void Session::run(std::shared_ptr<Session> session)
{
	// Read First Line of HTTP Request
	asio::async_read_until(session->socket, session->buff, '\r', [session](const error_code& e, std::size_t s)
	{
		//std::cout << "HTTP Server connection" << std::endl;

		session->read_request(session);
	});
}

std::string HttpServer::handleRequest(std::shared_ptr<Session> session)
{
	std::cout << "HTTP Server: " << session->request.method << " " << session->request.url << " " << session->request.version << std::endl;

	std::stringstream ssOut;

	if (session->request.url == "/")
	{ 
		std::stringstream ssContent;
		ssContent << "<html><body><h1>Hello World</h1><p>This is a test web server</p>";
		ssContent << "<p>Your URL was " << session->request.url << "</p>";
		ssContent << "</body></html>";

		std::string sHTML = ssContent.str();

		ssOut << "HTTP/1.1 200 OK" << std::endl;
		ssOut << "content-type: text/html" << std::endl;
		ssOut << "content-length: " << sHTML.length() << std::endl;
		ssOut << std::endl;
		ssOut << sHTML;
	}
	else
	{
		std::string sHTML = "Not Found";
		ssOut << "HTTP/1.1 404 OK" << std::endl;
		ssOut << "content-type: text/html" << std::endl;
		ssOut << "content-length: " << sHTML.length() << std::endl;
		ssOut << std::endl;
		ssOut << sHTML;
	}

	return ssOut.str();
}

void HttpServer::serve_forever()
{
	ip::tcp::endpoint endpoint{ ip::tcp::v4(), m_port };
	ip::tcp::acceptor acceptor{ m_io_service, endpoint };

	acceptor.listen();
	accept_and_run(acceptor, m_io_service);

#ifdef HTTP_SERVER_MULTI_THREADED
	{
		const std::size_t thread_pool_size_ = boost::thread::hardware_concurrency();

		std::cout << "HTTP Server (" << thread_pool_size_ << " Threads) waiting for requests on port " << m_port << std::endl;

		// Create a pool of threads to run all of the io_services.
		std::vector<boost::shared_ptr<boost::thread> > threads;
		for (std::size_t i = 0; i < thread_pool_size_; ++i)
		{
			boost::shared_ptr<boost::thread> thread(new boost::thread([this]() {m_io_service.run(); }));
			threads.push_back(thread);
		}

		// Wait for all threads in the pool to exit.
		for (std::size_t i = 0; i < threads.size(); ++i)
			threads[i]->join();
	}
#else
	std::cout << "HTTP Server (Single Thread) waiting for requests on port " << m_port << std::endl;

	m_io_service.run();
#endif 
}

std::shared_ptr<Session> HttpServer::CreateSession()
{
	return std::make_shared<Session>(m_io_service, this); // TODO Possible lifetime issue if we destroy HttpServer while requests are being processed
}

void HttpResponse::addLine(const std::string& line)
{
	if (method.empty())
	{
		// First line
		std::stringstream ssRequestLine(line);
		ssRequestLine >> method;
		ssRequestLine >> url;
		ssRequestLine >> version;
	}
	else
	{
		// Split Header Line
		std::stringstream ssHeader(line);
		std::string headerName;
		std::getline(ssHeader, headerName, ':');
		std::string value;
		std::getline(ssHeader, value);
		boost::algorithm::to_lower(headerName);
		boost::trim(value);
		headers[headerName] = value;
	}
}

void HttpResponse::addContent(const std::string& str)
{
	content = str;
}

void HttpResponse::read(const std::string& everything)
{
	// Read header line by line, then content

	std::string line, ignore;
	std::stringstream stream{ everything };

	headers.clear();
	content.clear();

	while (1)
	{
		std::getline(stream, line, '\r');
		std::getline(stream, ignore, '\n');

		addLine(line);

		if (line.empty())
			break;
	}

	if (has_chunk_encoding())
	{
		while (1)
		{
			std::getline(stream, line, '\r');
			std::getline(stream, ignore, '\n');

			if (line.empty())
				break;

			size_t current_len = content.size();
			int len = std::stoul(line, nullptr, 16);
			if (!len)
				break;

			content.resize(current_len + len);
			stream.read(&content[current_len], len);

			std::getline(stream, ignore, '\n');
		}
	}
	else
	{ 
		// Rest of the stream is the content
		int pos = stream.tellg();
		content.assign(everything.begin() + pos, everything.end());
	}
}

size_t HttpResponse::content_length()
{
	auto request = headers.find("content-length");
	if (request != headers.end())
	{
		std::stringstream ssLength(request->second);
		int content_length;
		ssLength >> content_length;
		return content_length;
	}
	return 0;
}

bool HttpResponse::has_chunk_encoding()
{
	auto request = headers.find("transfer-encoding");
	if (request != headers.end())
		return "chunked" == request->second;
	return false;
}