// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include "server_uplink.hpp"
#include "capturenode.hpp"
#include "httpserver.hpp"
#include "base64.hpp"
#include "json.hpp"

#include <boost/bind.hpp>
#include <boost/asio.hpp>
#include <boost/asio/ssl.hpp>
#include <boost/thread/thread.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/filesystem.hpp>
#include <boost/lexical_cast.hpp>

#include <iostream>
#include <iomanip>

#include <type_traits>

const int CODE_VERSION = 1057;

template <bool isHttps>
class HttpContext
{
public:
	HttpContext(boost::asio::io_service& io_service,
		boost::asio::ssl::context& context,
		boost::asio::ip::tcp::resolver::iterator endpoint_iterator,
		std::string raw_request)
		: socket_(io_service, context), raw(raw_request)
	{
		socket_.set_verify_mode(boost::asio::ssl::verify_peer);
		socket_.set_verify_callback(
			boost::bind(&HttpContext::verify_certificate, this, _1, _2));

		boost::asio::async_connect(socket_.lowest_layer(), endpoint_iterator,
			boost::bind(&HttpContext::handle_connect, this,
				boost::asio::placeholders::error));
	}

	HttpContext(boost::asio::io_service& io_service,
			boost::asio::ip::tcp::resolver::iterator endpoint_iterator,
			std::string raw_request)
			: socket_(io_service), raw(raw_request)
	{
		boost::asio::async_connect(socket_.lowest_layer(), endpoint_iterator,
			boost::bind(&HttpContext::handle_connect, this,
				boost::asio::placeholders::error));
	}

	bool verify_certificate(bool preverified,
		boost::asio::ssl::verify_context& ctx)
	{
		// The verify callback can be used to check whether the certificate that is
		// being presented is valid for the peer. For example, RFC 2818 describes
		// the steps involved in doing this for HTTPS. Consult the OpenSSL
		// documentation for more details. Note that the callback is called once
		// for each certificate in the certificate chain, starting from the root
		// certificate authority.

		//// In this example we will simply print the certificate's subject name.
		//char subject_name[256];
		//X509* cert = X509_STORE_CTX_get_current_cert(ctx.native_handle());
		//X509_NAME_oneline(X509_get_subject_name(cert), subject_name, 256);
		//std::cout << "Verifying " << subject_name << "\n";

		//return preverified;		
		return true; // TODO Certificate verification
	}

	void handle_connect(const boost::system::error_code& error);

	void handle_handshake(const boost::system::error_code& error)
	{
		if (!error)
		{
			size_t request_length = raw.length();

			boost::asio::async_write(socket_,
				boost::asio::buffer(raw.c_str(), request_length),
				boost::bind(&HttpContext::handle_write, this,
					boost::asio::placeholders::error,
					boost::asio::placeholders::bytes_transferred));
		}
		else
		{
			std::cerr << "Handshake failed: " << error.message() << "\n";
		}
	}

	void handle_write(const boost::system::error_code& error, size_t bytes_transferred)
	{
		if (!error)
		{
			boost::asio::async_read(socket_,
				//boost::asio::buffer(reply_, sizeof(reply_)),
				reply_,
				boost::bind(&HttpContext::handle_read, this,
					boost::asio::placeholders::error,
					boost::asio::placeholders::bytes_transferred));
		}
		else
		{
			std::cerr << "Write failed: " << error.message() << "\n";
		}
	}

	void handle_read(const boost::system::error_code& error, size_t bytes_transferred)
	{
		if (bytes_transferred)
			response << &reply_;
	}

	std::string get_response() const 
	{
		return response.str();
	}

private:
	typedef typename std::conditional<isHttps, boost::asio::ssl::stream<boost::asio::ip::tcp::socket>, boost::asio::ip::tcp::socket>::type socket_t;
	socket_t socket_;
	boost::asio::streambuf reply_;
	std::string raw;
	std::stringstream response;
};

template<> void HttpContext<true>::handle_connect(const boost::system::error_code& error)
{
	if (!error)
	{
		socket_.async_handshake(boost::asio::ssl::stream_base::client,
			boost::bind(&HttpContext::handle_handshake, this,
				boost::asio::placeholders::error));
	}
	else
	{
		std::cout << "Connect failed: " << error.message() << "\n";
	}
}

template<> void HttpContext<false>::handle_connect(const boost::system::error_code& error)
{
	handle_handshake(error);
}

struct HttpRequest
{
	HttpRequest() {
		url = "/";
		method = "POST";
		payload = "";
		accept_type = "application/json, text/html, text/plain";
		content_type = "application/json";
	}

	std::string url;
	std::string method;
	std::string payload;
	std::string server;
	std::string port;
	std::string username;
	std::string password;
	std::string accept_type;
	std::string content_type;
};

class HttpsClient
{
public:
	HttpsClient(const HttpRequest& req)
	{
		// Build HTTP Request 
		std::stringstream ss;
		ss << req.method << " " << req.url << " HTTP/1.1\r\nHost: " << req.server << "\r\nConnection: close\r\n";
		if (req.payload.length() > 0)
			ss << "content-length: " << req.payload.length() << "\r\n";
		ss << "Content-Type: " << req.content_type << "\r\n";
		ss << "Accept: " << req.accept_type << "\r\n";
		ss << "Authorization: Basic " << base64encode(req.username + ":" + req.password) << "\r\n";
		ss << "\r\n" << req.payload;

		// std::cout << "DEBUG HTTP REQUEST: " << ss.str() << std::endl;

		boost::asio::io_service io_service;
		boost::asio::ip::tcp::resolver resolver(io_service);
		boost::asio::ip::tcp::resolver::query query(req.server, req.port);
		boost::asio::ip::tcp::resolver::iterator iterator = resolver.resolve(query);

		if (req.port == "443")
		{
			boost::asio::ssl::context ctx(boost::asio::ssl::context::sslv23);
			ctx.set_default_verify_paths();
			HttpContext<true> c(io_service, ctx, iterator, ss.str());

			io_service.run();
			response = c.get_response();
		}
		else
		{
			HttpContext<false> c(io_service, iterator, ss.str());

			io_service.run();
			response = c.get_response();
		}
	}

	std::string response;
};

ServerUplink::ServerUplink(std::shared_ptr<CaptureNode> pNode,
	const char * SERVER, int PORT, const char * USERNAME, const char * PASSWORD, const char * GIT_REVISION) 
	: running(false), m_node(pNode), m_server(SERVER), m_port(boost::lexical_cast<std::string>(PORT)), 
	  m_username(USERNAME), m_password(PASSWORD), m_build_version(GIT_REVISION)
{
	std::cout << "Code Version: " << CODE_VERSION << std::endl;

	// Find IP Address and Machine Name (to reach server)
	try {
		boost::asio::io_service io_service;
		boost::asio::ip::tcp::resolver resolver(io_service);
		boost::asio::ip::tcp::resolver::query query(boost::asio::ip::tcp::v4(), m_server, m_port);
		boost::asio::ip::tcp::resolver::iterator endpoints = resolver.resolve(query);
		boost::asio::ip::tcp::endpoint ep = *endpoints; // first endpoint
		boost::asio::ip::tcp::socket socket(io_service);
		socket.connect(ep);
		boost::asio::ip::address addr = socket.local_endpoint().address();

		running = true;

		m_ip_address = addr.to_string();
		m_machine_name = boost::asio::ip::host_name();

		// Launch thread to ping server every few seconds
		m_thread = boost::thread([this]() {uplinkThread(); });
	}
	catch (boost::system::system_error se)
	{
		std::cerr << "==================================================================" <<  std::endl;
		std::cerr << "  ERROR: Could not connect to server " << m_server << ":" << m_port << std::endl;
		std::cerr << "==================================================================" << std::endl;
	}
}

ServerUplink::~ServerUplink()
{
	if (running)
	{
		running = false;

		m_thread.interrupt(); // kill the sleep_for()
		m_thread.join();

		{
			rapidjson::Document d;
			d.SetObject();
			d.AddMember("machine_name", rapidjson::Value(m_machine_name.c_str(), d.GetAllocator()), d.GetAllocator());
			d.AddMember("ip_address", rapidjson::Value(m_ip_address.c_str(), d.GetAllocator()), d.GetAllocator());

			rapidjson::StringBuffer buffer;
			rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
			d.Accept(writer);

			// Send final update
			HttpRequest req;
			FillRequest(req);
			req.url = "/capture/node_shutdown/";
			req.payload = buffer.GetString();
			HttpsClient client(req);
		}
	}
}

void ServerUplink::FillRequest(HttpRequest& req)
{
	req.server = m_server;
	req.port = m_port;
	req.username = m_username;
	req.password = m_password;
}

std::string ServerUplink::sendKeepalive(bool request_params)
{
	if (!running)
		return std::string();

	rapidjson::Document d;
	d.SetObject();
	d.AddMember("machine_name", rapidjson::Value(m_machine_name.c_str(), d.GetAllocator()), d.GetAllocator());
	d.AddMember("build_version", rapidjson::Value(m_build_version.c_str(), d.GetAllocator()), d.GetAllocator());
	
#ifdef WIN32
	d.AddMember("os", "windows", d.GetAllocator());	
#elif __linux__
	d.AddMember("os", "linux", d.GetAllocator());	
#endif

	d.AddMember("code_version", CODE_VERSION, d.GetAllocator());	
	d.AddMember("ip_address", rapidjson::Value(m_ip_address.c_str(), d.GetAllocator()), d.GetAllocator());
	d.AddMember("sync_found", m_node->sync_ok(), d.GetAllocator());
	if (request_params)
		d.AddMember("request_camera_params", true, d.GetAllocator());

	rapidjson::Value cam_array(rapidjson::kArrayType);
	for (auto c : m_node->cameraList())
	{
		rapidjson::Value strVal;
		strVal.SetString(c->unique_id().c_str(), d.GetAllocator());
		cam_array.PushBack(strVal, d.GetAllocator());
	}
	d.AddMember("cameras", cam_array, d.GetAllocator());

	rapidjson::Value drive_array(rapidjson::kArrayType);
	for (auto c : m_node->capture_folders())
	{
		boost::filesystem::path P(c.first);

		rapidjson::Value strVal;
		strVal.SetString(c.first.c_str(), d.GetAllocator());

		boost::filesystem::space_info si = boost::filesystem::space(P);

		rapidjson::Value driveinfo(rapidjson::kObjectType);
		driveinfo.AddMember("path", strVal, d.GetAllocator());
		strVal.SetString(P.parent_path().string().c_str(), d.GetAllocator());
		driveinfo.AddMember("root", strVal, d.GetAllocator());
		driveinfo.AddMember("bandwidth", c.second, d.GetAllocator()); // MB/s
		driveinfo.AddMember("available", si.available / 1024 / 1024, d.GetAllocator()); // MB
		driveinfo.AddMember("capacity", si.capacity / 1024 / 1024, d.GetAllocator()); // MB

		drive_array.PushBack(driveinfo, d.GetAllocator());
	}
	d.AddMember("drives", drive_array, d.GetAllocator());

	rapidjson::StringBuffer buffer;
	rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
	d.Accept(writer);

	HttpRequest req;
	FillRequest(req);
	req.url = "/capture/node_discover/";
	req.payload = buffer.GetString();
	HttpsClient client(req);

	if (request_params)
	{
		// Apply these parameters from client.response to m_node
		HttpResponse response;
		response.read(client.response);

		if (response.url == "200")
		{
			return response.content;
		}
		else
		{
			running = false;

			std::cerr << "ERROR : Received error from server:" << std::endl;
			std::cerr << response.method << " " << response.url  << " " << response.version << std::endl;
			std::cerr << response.content << std::endl;
		}
	}

	return std::string();
}

void ServerUplink::uplinkThread()
{
	while (running)
	{
		boost::this_thread::sleep_for(boost::chrono::seconds(40));

		// Send update every 40 seconds
		sendKeepalive();
	}
}

