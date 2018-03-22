// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#include <functional>

#include "node_ws_server.hpp"
#include "capturenode.hpp"
#include "base64.hpp"

#include <boost/algorithm/string.hpp>

WSServer::WSServer(int port)
{
    server.init_asio();
    server.set_message_handler(std::bind(&WSServer::on_message, this, std::placeholders::_1, std::placeholders::_2));
    server.listen(port);
    server.start_accept();   
}

WSServer::~WSServer()
{
}

void WSServer::serve_forever()
{
    server.run();
}
	
void WSServer::close()
{
    //std::cout << "WEBSOCKET> Shutting down" << std::endl;

    server.stop_listening();
    server.stop();
}

void WSServer::on_message(websocketpp::connection_hdl hdl, ws_server::message_ptr msg)
{
    //std::cout << "WEBSOCKET> message:" << msg->get_payload() << std::endl;
}

void WSServer::send(websocketpp::connection_hdl hdl, const std::string& s)
{
    server.send(hdl, s, websocketpp::frame::opcode::text);
}

NodeWSServer::NodeWSServer(std::shared_ptr<CaptureNode> pNode, int port)
  : WSServer(port), m_node(pNode)
{
}

NodeWSServer::~NodeWSServer()
{
}

void NodeWSServer::on_message(websocketpp::connection_hdl hdl, ws_server::message_ptr msg)
{
    //std::cout << "WEBSOCKET> message:" << msg->get_payload() << std::endl;

	std::vector<std::string> paths;
	boost::split(paths, msg->get_payload(), boost::is_any_of("/"), boost::token_compress_on);

    if (paths.size()<3 || msg->get_opcode()!=websocketpp::frame::opcode::text)
        return;

    if (paths[0]=="capture")
    {
        std::string camUniqueId = paths[1];
        std::string action = paths[2];

        auto cam = m_node->cameraById(camUniqueId.c_str());
        if (!cam.get())
            return;

        if (action=="large_preview")
        {
            std::vector<unsigned char> buf;
            if (cam->get_large_preview_image(buf))
            {
        	    send(hdl, base64encode(buf));
            }
        }
        else if (action=="preview")
        {
            std::vector<unsigned char> buf;
            bool is_histogram = false;
            if (cam->get_preview_image(buf), &is_histogram)
            {
        	    send(hdl, camUniqueId + ";" + base64encode(buf));
            }
        }
    }
}
