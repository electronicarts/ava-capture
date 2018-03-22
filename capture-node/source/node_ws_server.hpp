// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include <memory>

#include <websocketpp/config/asio_no_tls.hpp>
#include <websocketpp/server.hpp>
typedef websocketpp::server<websocketpp::config::asio> ws_server;

class CaptureNode;
struct WSServerPrivate;

class WSServer
{
public:
	WSServer(int port);
	virtual ~WSServer();
	void serve_forever();
	void close();

protected:
	void send(websocketpp::connection_hdl hdl, const std::string& s);
	virtual void on_message(websocketpp::connection_hdl hdl, ws_server::message_ptr msg);

private:
	ws_server server;
};

class NodeWSServer : public WSServer
{
public:
	NodeWSServer(std::shared_ptr<CaptureNode> pNode, int port);
	virtual ~NodeWSServer();

protected:
	void on_message(websocketpp::connection_hdl hdl, ws_server::message_ptr msg) override;

private:
	std::shared_ptr<CaptureNode> m_node;
};
