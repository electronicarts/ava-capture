// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include <memory>

#include <boost/thread/thread.hpp>

#include <websocketpp/config/asio.hpp>
#include <websocketpp/config/asio_no_tls.hpp>
#include <websocketpp/server.hpp>

class CaptureNode;
struct WSServerPrivate;

namespace strategy 
{
	class Secure 
	{
	public:
		typedef websocketpp::server<websocketpp::config::asio_tls> serverT;
	};
	class Normal 
	{
	public:
		typedef websocketpp::server<websocketpp::config::asio> serverT;
	};
}

template <class S>
class WSServer
{
public:
	WSServer(int port);
	virtual ~WSServer();
	void serve_forever();
	void serve_forever_in_thread();
	void close();

protected:
	void send(websocketpp::connection_hdl hdl, const std::string& s);
	virtual void on_message(websocketpp::connection_hdl hdl, typename S::serverT::message_ptr msg);
	
private:	
	void extra_init(int port);

private:
	typename S::serverT server;
	boost::thread runner;
};

template <class S>
class NodeWSServer : public WSServer<S>
{
public:
	NodeWSServer(std::shared_ptr<CaptureNode> pNode, int port);
	virtual ~NodeWSServer();

protected:
	void on_message(websocketpp::connection_hdl hdl, typename S::serverT::message_ptr msg) override;

private:
	std::shared_ptr<CaptureNode> m_node;
};
