// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include <memory>

#include <boost/thread/thread.hpp>

#ifdef USE_TLS_WEBSOCKET
	#include <websocketpp/config/asio.hpp>
#else
	#include <websocketpp/config/asio_no_tls.hpp>
#endif
#include <websocketpp/server.hpp>


class CaptureNode;
struct WSServerPrivate;

#ifdef USE_TLS_WEBSOCKET
	typedef websocketpp::server<websocketpp::config::asio_tls> serverT;
#else
	typedef websocketpp::server<websocketpp::config::asio> serverT;
#endif

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
	virtual void on_message(websocketpp::connection_hdl hdl, serverT::message_ptr msg);

private:
	serverT server;
	boost::thread runner;
};

class NodeWSServer : public WSServer
{
public:
	NodeWSServer(std::shared_ptr<CaptureNode> pNode, int port);
	virtual ~NodeWSServer();

protected:
	void on_message(websocketpp::connection_hdl hdl, serverT::message_ptr msg) override;

private:
	std::shared_ptr<CaptureNode> m_node;
};
