// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

#include <memory>

#include "httpserver.hpp"

class CaptureNode;

class NodeHttpServer : public HttpServer
{
public:
	NodeHttpServer(std::shared_ptr<CaptureNode> pNode, int port);
	virtual ~NodeHttpServer();

protected:
	virtual std::string handleRequest(std::shared_ptr<Session> session) override;

	std::string getStatusPage(std::shared_ptr<Session> request);
	std::string getCamerasPage(std::shared_ptr<Session> request);
	std::string getCameraPage(std::shared_ptr<Session> request, const std::vector<std::string>& paths);
	std::string postParameterSet(std::shared_ptr<Session> request, const std::vector<std::string>& paths);

private:
	std::shared_ptr<CaptureNode> m_node;
};
