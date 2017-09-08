// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include <memory>
#include <boost/asio.hpp>

class HttpServer;

class HttpResponse
{
public:
	HttpResponse() {}

	void addLine(const std::string& line); // read a single header line
	void addContent(const std::string& str); // read the content string

	void read(const std::string& everything); // read the while HTTP message (header + content)

	size_t content_length();
	bool has_chunk_encoding();

	std::string method;
	std::string url;
	std::string version;
	std::map<std::string, std::string> headers;
	std::string content;
};

class Session
{
public:
	Session(boost::asio::io_service& io_service, HttpServer* server) : socket(io_service), server(server) {
	}
	~Session() {
	}

	static void run(std::shared_ptr<Session> session);
	boost::asio::ip::tcp::socket socket;

	HttpResponse request;

private:
	static void read_next_headers(std::shared_ptr<Session> session);
	static void read_content(std::shared_ptr<Session> session, size_t len);
	static void read_request(std::shared_ptr<Session> session);

	boost::asio::streambuf buff;
	HttpServer* server;
};

class HttpServer
{
public:
	HttpServer(int port);
	virtual ~HttpServer();
	void serve_forever();
	void close();

	// To be overloaded in server implementations
	virtual std::string handleRequest(std::shared_ptr<Session> session);

protected:
	std::shared_ptr<Session> CreateSession();
private:
	void accept_and_run(boost::asio::ip::tcp::acceptor& acceptor, boost::asio::io_service& io_service);
private:
	unsigned short m_port;
	boost::asio::io_service m_io_service;
};
