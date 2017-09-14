// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma warning(disable:4996)

#include "nodehttpserver.hpp"
#include "cameras.hpp"
#include "capturenode.hpp"
#include "base64.hpp"
#include "json.hpp"

#include <boost/algorithm/string.hpp>

#include <iostream>

#include <opencv2/imgproc.hpp>
#include <opencv2/opencv.hpp>

NodeHttpServer::NodeHttpServer(std::shared_ptr<CaptureNode> pNode, int port) : HttpServer(port), m_node(pNode)
{
}

NodeHttpServer::~NodeHttpServer()
{
}

std::string error500()
{
	std::stringstream ssOut;

	{
		std::string sHTML = "Server Error";
		ssOut << "HTTP/1.1 500 OK" << std::endl;
		ssOut << "content-type: text/html" << std::endl;
		ssOut << "content-length: " << sHTML.length() << std::endl;
		ssOut << std::endl;
		ssOut << sHTML;
	}

	return ssOut.str();
}

std::string error404()
{
	std::stringstream ssOut;

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

std::string simple200Json()
{
	std::stringstream ssOut;
	std::string sJSON = "{\"retcode\" : \"OK\"}";
	ssOut << "HTTP/1.1 200 OK" << std::endl;
	ssOut << "content-type: text/html" << std::endl;
	ssOut << "content-length: " << sJSON.length() << std::endl;
	ssOut << std::endl;
	ssOut << sJSON;
	return ssOut.str();
}

std::string summary200(shared_json_doc summary)
{
	// Create new json document, to contain summary from all cameras
	shared_json_doc doc(new rapidjson::Document());
	doc->SetObject();
	doc->AddMember("retcode", "OK", doc->GetAllocator());
	rapidjson::Value val(rapidjson::kObjectType);
	val.CopyFrom(*summary.get(), doc->GetAllocator());
	doc->AddMember("summary", val, doc->GetAllocator());

	// Serialize JSON
	rapidjson::StringBuffer buffer;
	rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
	doc->Accept(writer);

	{
		std::stringstream ssOut;
		ssOut << "HTTP/1.1 200 OK" << std::endl;
		ssOut << "content-type: application/json" << std::endl;
		ssOut << "content-length: " << buffer.GetSize() << std::endl;
		ssOut << std::endl;
		ssOut << buffer.GetString();
		return ssOut.str();
	}
}

std::string NodeHttpServer::getStatusPage(std::shared_ptr<Session> request)
{
	// Human-readable status page, displays node status and the list of cameras

	std::stringstream ssOut;

	{
		std::stringstream ssContent;
		ssContent << "<html><head><title>Capture Node Status Page</title></head>";
		ssContent << "<body><p>Camera List:</p>";
		ssContent << "<a href=\"/cameras\">cameras</a><table><tr>";
		if (m_node.get())
		{
			for (const std::shared_ptr<Camera>& cam : m_node->cameraList())
			{
				ssContent << "<td valign=\"top\">";
				ssContent << "Camera Unique ID : " << cam->unique_id() << "<br>";
				ssContent << "Camera Model : " << cam->model() << "<br>";
				ssContent << "Camera Width : " << cam->width() << "<br>";
				ssContent << "Camera Height : " << cam->height() << "<br>";
			//	html += 'Using hardware sync : %s<br>' % ('Yes' if cam.using_hardware_sync else 'No')
				ssContent << "<a href=\"/camera/" << cam->unique_id() << "/params\">Parameters</a><br>";
				ssContent << "Current Effective framerate : " << cam->effective_fps() << "<br>";

				std::map<std::string, CameraParameter> params = cam->params_list(); 
				for (auto p : params)
				{
					ssContent << "<a href=\"/camera/" << cam->unique_id()  << "/" << p.first << "\">" << p.first  << "</a> : " << cam->param_get(p.first.c_str()) << "<br>";
				}
				ssContent << "<a href=\"/camera/" << cam->unique_id()  << "/live\"><img width=\"" << cam->preview_width()  << "\" height=\"" << cam->preview_height()  << "\" src=\"/camera/" << cam->unique_id()  << "/preview\"></a><br>";

				//		if cam.has_lens_control() :
				//			html += '<a href="/camera/%s/autofocus">autofocus</a><br>' % cam.unique_id
				//		html += '<a href="/camera/%s/capture_image">capture one image</a><br>' % cam.unique_id
				//		html += '<a href="/camera/%s/start_recording">start_recording</a><br>' % cam.unique_id
				//		html += '<a href="/camera/%s/stop_recording">stop_recording</a><br>' % cam.unique_id
				//		html += '<a href="/camera/%s/start_capturing">start_capturing</a><br>' % cam.unique_id
				//		html += '<a href="/camera/%s/stop_capturing">stop_capturing</a><br>' % cam.unique_id

				ssContent << "</td>";
			}
		}
		ssContent << "</tr></table></body></html>";

		std::string sHTML = ssContent.str();

		ssOut << "HTTP/1.1 200 OK" << std::endl;
		ssOut << "content-type: text/html" << std::endl;
		ssOut << "content-length: " << sHTML.length() << std::endl;
		ssOut << std::endl;
		ssOut << sHTML;
	}

	return ssOut.str();
}

std::string NodeHttpServer::getCamerasPage(std::shared_ptr<Session> request)
{
	// Returns JSON content with the camera list

	std::stringstream ssOut;

	{
		rapidjson::Document d;
		d.SetArray();

		for (auto c : m_node->cameraList())
		{
			rapidjson::Value cam(rapidjson::kObjectType);

			cam.AddMember("unique_id", rapidjson::Value(c->unique_id().c_str(), d.GetAllocator()), d.GetAllocator());
			cam.AddMember("model", rapidjson::Value(c->model().c_str(), d.GetAllocator()), d.GetAllocator());
			cam.AddMember("version", rapidjson::Value(c->version().c_str(), d.GetAllocator()), d.GetAllocator());
			cam.AddMember("width", c->width(), d.GetAllocator());
			cam.AddMember("height", c->height(), d.GetAllocator());
			cam.AddMember("preview_width", c->preview_width(), d.GetAllocator());
			cam.AddMember("preview_height", c->preview_height(), d.GetAllocator());
			cam.AddMember("effective_fps", c->effective_fps(), d.GetAllocator());
			cam.AddMember("bpp", c->bpp(), d.GetAllocator());
			cam.AddMember("using_hardware_sync", c->using_hardware_sync(), d.GetAllocator());
			cam.AddMember("recording", c->recording(), d.GetAllocator());
			cam.AddMember("capturing", c->capturing(), d.GetAllocator());
			cam.AddMember("framerate", c->framerate(), d.GetAllocator());
			cam.AddMember("encoding_buffers_used", c->encoding_buffers_used(), d.GetAllocator());
			cam.AddMember("writing_buffers_used", c->writing_buffers_used(), d.GetAllocator());

			rapidjson::Value params(rapidjson::kObjectType);
			auto params_list = c->params_list();
			for (auto& p : params_list)
			{
				rapidjson::Value param_element(rapidjson::kObjectType);
				param_element.AddMember("value", c->param_get(p.first.c_str()), d.GetAllocator());
				param_element.AddMember("minimum", p.second.minimum, d.GetAllocator());
				param_element.AddMember("maximum", p.second.maximum, d.GetAllocator());
				param_element.AddMember("increment", p.second.increment, d.GetAllocator());

				rapidjson::Value strVal;
				strVal.SetString(p.first.c_str(), d.GetAllocator());

				params.AddMember(strVal, param_element, d.GetAllocator());
			}
			cam.AddMember("params", params, d.GetAllocator());

			// Encode Image as JPG
			std::vector<unsigned char> buf;
			bool is_histogram = false;
			if (c->get_preview_image(buf, &is_histogram))
			{ 
				cam.AddMember("jpeg_thumbnail", rapidjson::Value(base64encode(buf).c_str(), d.GetAllocator()), d.GetAllocator());
				cam.AddMember("jpeg_thumbnail_is_histogram", is_histogram, d.GetAllocator());
			}

			d.PushBack(cam, d.GetAllocator());
		}

		rapidjson::StringBuffer buffer;
		rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
		d.Accept(writer);

		ssOut << "HTTP/1.1 200 OK" << std::endl;
		ssOut << "content-type: application/json" << std::endl;
		ssOut << "content-length: " << buffer.GetSize() << std::endl;		
		ssOut << std::endl;
		ssOut << buffer.GetString();
	}

	return ssOut.str();
}

std::string NodeHttpServer::postParameterSet(std::shared_ptr<Session> request, const std::vector<std::string>& paths)
{
	// Handle POST request to change camera parameters (gain, framerate, etc)

	if (paths.size() != 4)
		return error500();

	std::string req_cam_id = paths[1];
	std::string req_what = paths[2];
	std::string req_value = paths[3];

	auto cam = m_node->cameraById(req_cam_id.c_str());
	if (!cam.get())
		return error500();

	cam->param_set(req_what.c_str(), ::atof(req_value.c_str()));

	auto params_list = cam->params_list();
	auto it = params_list.find(req_what);
	if (it == params_list.end())
		return error500();

	// Read parameter value to send reply
	std::stringstream ssOut;
	{
		rapidjson::Document d;
		d.SetObject();

		d.AddMember("value", cam->param_get(it->first.c_str()), d.GetAllocator());
		d.AddMember("minimum", it->second.minimum, d.GetAllocator());
		d.AddMember("maximum", it->second.maximum, d.GetAllocator());
		d.AddMember("increment", it->second.increment, d.GetAllocator());

		rapidjson::StringBuffer buffer;
		rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
		d.Accept(writer);

		ssOut << "HTTP/1.1 200 OK" << std::endl;
		ssOut << "content-type: application/json" << std::endl;
		ssOut << "content-length: " << buffer.GetSize() << std::endl;
		ssOut << std::endl;
		ssOut << buffer.GetString();
	}

	return ssOut.str();
}

std::string NodeHttpServer::getCameraPage(std::shared_ptr<Session> request, const std::vector<std::string>& paths)
{
	if (paths.size() < 3)
		return error500();

	std::string req_cam_id = paths[1];
	std::string req_what = paths[2];

	auto cam = m_node->cameraById(req_cam_id.c_str());
	if (!cam.get())
		return error500();

	if (req_what == "live")
	{
		{
			std::stringstream ssOut;

			ssOut << "HTTP/1.1 200 OK" << std::endl;
			ssOut << "content-type: text/html" << std::endl;
			ssOut << std::endl;
			ssOut << "<html><head><title>Live Camera Feed " << req_cam_id << "</title></head>\
				<body style=\"height:100%; margin:0;\"><div>Live Camera Feed " << req_cam_id << "</div>\
				<canvas id=\"my_canvas\" style=\"position:absolute; width:100%; height:100%;\">\
				</canvas>\
				<script language = \"JavaScript\">\
					var num = 0;\
					var canvas = document.getElementById('my_canvas');\
					var ctx = canvas.getContext('2d');\
					var img = new Image();\
					img.onload = function() {\
						ctx.drawImage(img, 0, 0, img.width, img.height, \
						0, 0, canvas.width, canvas.height);\
						window.setTimeout(function(){\
							img.src = \"/camera/" << req_cam_id << "/large_preview/\" + num;\
							num = num + 1;\
						}, 30);\
					};\
					img.onerror = function() {\
						window.setTimeout(function(){\
							img.src = \"/camera/" << req_cam_id << "/large_preview/\" + num;\
							num = num + 1;\
						}, 500);\
					};\
					img.onerror = function() {\
					};\
					img.src = \"/camera/" << req_cam_id << "/large_preview\";\
				</script>\
				</p>\
				</body></html>";

			return ssOut.str();
		}
	}
	else if (req_what == "preview")
	{
		// Encode Image as JPG
		std::vector<unsigned char> buf;
		if (cam->get_preview_image(buf))
		{
			std::stringstream ssOut;

			ssOut << "HTTP/1.1 200 OK" << std::endl;
			ssOut << "Content-Type: image/jpg" << std::endl;
			ssOut << "Content-Disposition: inline; filename=\"" << req_cam_id << "_live.jpg\"" << std::endl;
			ssOut << "Content-Length: " << buf.size() << std::endl;

			// Browsers should not cache this image, since this is the live feed from the camera
			ssOut << "Cache-Control: no-cache, no-store, must-revalidate" << std::endl;
			ssOut << "Pragma: no-cache" << std::endl;
			ssOut << "Expires: 0" << std::endl;

			ssOut << std::endl;
			ssOut.write(reinterpret_cast<char *>(&buf[0]), buf.size());

			return ssOut.str();
		}
	}
	else if (req_what == "large_preview")
	{
		// Encode Image as JPG
		std::vector<unsigned char> buf;
		if (cam->get_large_preview_image(buf))
		{
			std::stringstream ssOut;

			ssOut << "HTTP/1.1 200 OK" << std::endl;
			ssOut << "Content-Type: image/jpg" << std::endl;
			ssOut << "Content-Disposition: inline; filename=\"" << req_cam_id << "_live.jpg\"" << std::endl;
			ssOut << "Content-Length: " << buf.size() << std::endl;

			// Browsers should not cache this image, since this is the live feed from the camera
			ssOut << "Cache-Control: no-cache, no-store, must-revalidate" << std::endl;
			ssOut << "Pragma: no-cache" << std::endl;
			ssOut << "Expires: 0" << std::endl;

			ssOut << std::endl;
			ssOut.write(reinterpret_cast<char *>(&buf[0]), buf.size());

			return ssOut.str();
		}
	}

	return error404();
}

std::string NodeHttpServer::handleRequest(std::shared_ptr<Session> session)
{
	//std::cout << "DEBUG Node HTTP Server: " << session->request.method << " " << session->request.url << " " << session->request.version << std::endl;

	std::vector<std::string> paths;
	std::string urlp = boost::trim_left_copy_if(session->request.url, boost::is_any_of("/"));
	boost::split(paths, urlp, boost::is_any_of("/"), boost::token_compress_on);

	if (session->request.method == "GET")
	{
		if (session->request.url == "/")
			return getStatusPage(session);

		if (paths.size()>0 && paths[0]=="cameras")
			return getCamerasPage(session);

		if (paths.size()>0 && paths[0] == "camera")
			return getCameraPage(session, paths);
	}
	else if (session->request.method == "POST")
	{
		if (paths.size() > 0 && paths[0] == "close_node")
		{
			m_node->shutdown();

			return simple200Json();
		}
		else if (paths.size() == 3 && paths[0] == "camera" && paths[2] == "roi")
		{
			// Special case for Parameter ROI

			std::string req_cam_id = paths[1];
			auto cam = m_node->cameraById(req_cam_id.c_str());
			if (!cam.get())
				return error500();

			if (session->request.content.size())
			{
				// Parse JSON to get ROI

				rapidjson::Document d;
				d.Parse(session->request.content.c_str());

				int x = d["x"].GetInt();
				int y = d["y"].GetInt();
				int w = d["w"].GetInt();
				int h = d["h"].GetInt();

				cam->set_roi(x,y,x+w,y+h);
			}
			else
			{
				// Reset Camera ROI
				cam->reset_roi();
			}

			return simple200Json();
		}
		else if (paths.size() == 4 && paths[0] == "camera")
		{
			// Parameter setting
			return postParameterSet(session, paths);
		}
		else if (paths.size()>0 && paths[0] == "options")
		{
			m_node->setGlobalParams(session->request.content);

			return simple200Json();
		}
		else if (paths.size() > 1 && paths[0] == "toggle_using_sync")
		{
			std::string req_cam_id = paths[1];

			auto cam = m_node->cameraById(req_cam_id.c_str());
			if (!cam.get())
				return error500();

			bool newvalue = !cam->using_hardware_sync();
			if (paths.size() > 2)
				newvalue = paths[2] == "True";

			cam->set_hardware_sync(newvalue, m_node->global_framerate());

			return simple200Json();
		}
		else if (paths.size() > 1 && paths[0] == "toggle_capturing")
		{
			std::string req_cam_id = paths[1];

			auto cam = m_node->cameraById(req_cam_id.c_str());
			if (!cam.get())
				return error500();

			if (cam->capturing())
				cam->stop_capture();
			else
				cam->start_capture();

			return simple200Json();
		}

		// Steps for Single Shot
		else if (paths.size() > 0 && paths[0] == "all_prepare_single") // TODO take recieve folder name from server (timestamp+id)
		{
			m_node->prepare_single(1);
			return simple200Json();
		}
		else if (paths.size() > 0 && paths[0] == "all_start_single")
		{
			m_node->recording_trigger();
			return simple200Json();
		}
		else if (paths.size() > 0 && paths[0] == "all_finalize_single")
		{
			shared_json_doc summary = m_node->finalize_single();

			return summary200(summary);
		}

		// Steps for Multi Shot
		else if (paths.size() > 0 && paths[0] == "all_prepare_multi1") // TODO take recieve folder name from server (timestamp+id)
		{
			m_node->prepare_multi_stage1();
			return simple200Json();
		}
		else if (paths.size() > 0 && paths[0] == "all_prepare_multi2")
		{
			m_node->prepare_multi_stage2();
			return simple200Json();
		}
		else if (paths.size() > 0 && paths[0] == "all_start_multi")
		{
			m_node->recording_trigger();
			return simple200Json();
		}
		else if (paths.size() > 0 && paths[0] == "all_stop_recording")
		{
			shared_json_doc summary = m_node->stop_recording_all();

			return summary200(summary);
		}

		else if (paths.size() > 0 && paths[0] == "pause_sync")
		{
			m_node->pause_sync();
			return simple200Json();
		}
		else if (paths.size() > 0 && paths[0] == "resume_sync")
		{
			m_node->resume_sync(false);
			return simple200Json();
		}
	}

	// Request not handled, send 404

	std::cerr << "URL Not Found : " << session->request.url << std::endl;

	return error404();
}
