//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {$WebSocket, WebSocketSendMode, WebSocketConfig} from 'angular2-websocket/angular2-websocket';

export class NodeLink
{
    node_id : number = -1;
    node_ptr : any = null;
    ws : any = null;
    camera_list = Array();
    cache = {};

    constructor(node : any) {
        // Initialize and create one websocket
        this.node_id = node.id;
        this.node_ptr = node;

        const webSocketConfig = {reconnectIfNotNormalClose: true} as WebSocketConfig;
        if (location.protocol=="https:") {
            this.ws = new $WebSocket("wss://"+node.machine_name+":9003", null, webSocketConfig);
        } else {
            this.ws = new $WebSocket("ws://"+node.ip_address+":9002", null, webSocketConfig);
        }      

        this.ws.onMessage(
            (msg: MessageEvent)=> {
                var res = msg.data.split(";", 2);
                if (res.length==2) {
                    this.got_preview_image(res[0], res[1]);
                }
            },
            {autoApply: false}
          ); 
          this.ws.onOpen(
            (msg: Event)=> {
                console.log("Websocket Connected!");
                // Communication channel open, start requesting thumbnails
                this.camera_list.forEach(cam => {
                    this.ws.send("capture/"+cam+"/preview").subscribe();
                });
            },
            {autoApply: false}
          ); 
          this.ws.onClose(
            (msg: CloseEvent)=> {
                console.log("Websocket closed");
            },
            {autoApply: false}
          ); 
    }

    private got_preview_image(unique_id, image_b64) {

        // Update node data with new image
        var framerate = 0;
        this.node_ptr.camera_details.some(cam => {
            if (cam.unique_id == unique_id) {
                cam.jpeg_thumbnail = image_b64;
                framerate = cam.effective_fps;
                this.cache[cam.unique_id] = image_b64;
                return true; // stops iterating
            }
            return false; // continue iteration
        });

        // after a delay, request next image
        var delay_ms = Math.max(Math.min(1000.0 / framerate, 1000), 10);
        setTimeout(() => {
            if (this.camera_list.indexOf(unique_id)>=0) {
                this.ws.send("capture/"+unique_id+"/preview").subscribe();
            }
        }, delay_ms);
    }

    set_camera_list(node, camera_list) {
        this.node_ptr = node;
        if (this.node_ptr.camera_details) {
            this.node_ptr.camera_details.forEach(cam => {
                if (cam.unique_id in this.cache) {
                    cam.jpeg_thumbnail = this.cache[cam.unique_id];
                }
            });        
        }
        this.camera_list = camera_list;
    }

    release() {
        this.camera_list = Array();
        if (this.ws) {
            this.ws.close(false);
        }
    }
}

export class LiveNodeLink
{
    location_id : number = -1;
    node_map = new Map();

    constructor() {
    }

    set_location(loc_id) {
        if (loc_id != this.location_id) {
            this.release(); 
            this.location_id = loc_id;
        }
    }

    release() {
        this.node_map.forEach(element => {
            element.release();
        });
        this.node_map.clear();
    }

    update_from_nodes(nodes : any) {
        if (nodes) {
            var node_id_list = Array();
            nodes.forEach(node => {
                node_id_list.push(node.id);
                if (!this.node_map.has(node.id)) {
                    this.node_map.set(node.id, new NodeLink(node));
                }
                var cams = Array();
                node.cameras.forEach(cam => {
                    cams.push(cam.unique_id);
                });
                this.node_map.get(node.id).set_camera_list(node, cams);
            });
            var to_delete = Array();
            this.node_map.forEach(element => {
                if (node_id_list.indexOf(element.node_id)<0) {
                    to_delete.push(element.node_id);
                }
            });
            to_delete.forEach(id => {
                this.node_map.get(id).release();
                this.node_map.delete(id);
            });
        }
    }
}

