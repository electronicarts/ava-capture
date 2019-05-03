//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, ViewChild, EventEmitter } from '@angular/core';

import { CaptureService } from './capture.service';
import { ImageZoomComponent } from './imagezoom.component';

import {$WebSocket, WebSocketSendMode, WebSocketConfig} from 'angular2-websocket/angular2-websocket';

export interface ImageLoader {
  stop();
  next();
}

export class UrlImageLoader implements ImageLoader {

  // Simple image loader class. Construct with ip and camera uid, the callback will be 
  // called each time an image is recieved.

  cb: (string) => void;
  cam_ip : string;
  cam_uid : string;
  counter = 0;
  active = false;

  constructor(cam_ip : string, cam_uid : string, cb : (string) => void) {
    this.cam_ip = cam_ip;
    this.cam_uid = cam_uid;
    this.cb = cb;
    this.active = true;
  }
  
  fetch() {
    if (this.active) {
      // Retrieving new imge

      this.counter++;    
      var url = 'http://'+this.cam_ip+':8080/camera/'+this.cam_uid+'/large_preview/' + this.counter;
      this.cb(url);
    }
  }

  next() {
    // This will be called when we are ready for a new image
    setTimeout(() => {
      if (this.active) {
        this.fetch();
      }
    }, 30); // wait at least 30 ms between images
  }

  stop() {
    this.active = false;
  }
}

export class WSImageLoader implements ImageLoader {

  // Simple image loader class. Construct with ip and camera uid, the callback will be 
  // called each time an image is recieved.

  cb: (string) => void;
  cam_ip : string;
  cam_uid : string;
  cam_machine_name : string;
  active = false;
  ws : any = null;

  constructor(cam_ip : string, cam_machine_name : string, cam_uid : string, cb : (string) => void) {
    this.cam_ip = cam_ip;
    this.cam_machine_name = cam_machine_name;
    this.cam_uid = cam_uid;
    this.cb = cb;
    this.active = true;

    const webSocketConfig = {reconnectIfNotNormalClose: true} as WebSocketConfig;
    if (location.protocol=="https:") {
      this.ws = new $WebSocket("wss://"+cam_machine_name+":9003", null, webSocketConfig);
    } else {
        this.ws = new $WebSocket("ws://"+cam_ip+":9002", null, webSocketConfig);
    }      

    this.ws.onMessage(
      (msg: MessageEvent)=> {
        this.cb("data:image/jpg;base64,"+msg.data);
      },
      {autoApply: false}
    ); 
  }
  
  fetch() {
    if (this.active) {
      this.ws.send("capture/"+this.cam_uid+"/large_preview").subscribe();
    }
  }

  next() {
    // This will be called when we are ready for a new image
    setTimeout(() => {
      if (this.active) {
        this.fetch();
      }
    }, 30); // wait at least 30 ms between images
  }

  stop() {
    this.active = false;
  }
}

@Component({
  selector: 'zoomview-selector',
  template: require('./zoomview.html'),
  providers: [CaptureService]
})
export class ZoomViewComponent {

  @ViewChild(ImageZoomComponent)
  public imagezoom : ImageZoomComponent;

  constructor(private captureService: CaptureService) {
  }

  public camera_id = 0;
  public cam_model : string = '';
  public cam_unique_id : string = '';
  public cam_version : string = '';
  public cam_ip : string = '';
  public cam_machine_name : string = '';
  public cam_rotation : number = 0;

  visible = false;

  imageLoader : ImageLoader = null;

  startImageLoader() {

    this.imageLoader = new WSImageLoader(this.cam_ip, this.cam_machine_name, this.cam_unique_id, (url : string) => {
      if (this.visible && this.imagezoom) {
        this.imagezoom.setImageSrc(url, this.cam_rotation, () => {
          // Callback when the image was used 
          if (this.imageLoader) {
            this.imageLoader.next();
          }
        });  
      } else {
        // Image was not used but we ask for a next one anyway
        if (this.imageLoader) {
          this.imageLoader.next();
        }
    }
    });

    this.imageLoader.next();
  }

  setROIPercent(value : number) {
    this.captureService.setCameraROIPercent(this.camera_id, value, -1).subscribe(
        data => { },
        err => console.error(err),
        () => {}
      );
  }

  setROI(values : number[]) {
    this.captureService.setCameraROI(this.camera_id, values, -1).subscribe(
        data => { },
        err => console.error(err),
        () => {}
      );
  }

  resetROI() {
    this.captureService.resetCameraROI(this.camera_id, -1).subscribe(
        data => { },
        err => console.error(err),
        () => {}
      );
  }

  public isVisible(): boolean {return this.visible;}

  public show(camera): void {

    this.camera_id = camera.id;
    this.cam_model = camera.model;
    this.cam_unique_id = camera.unique_id;
    this.cam_version = camera.version;
    this.cam_ip = camera.ip_address;
    this.cam_machine_name = camera.machine_name;
    this.cam_rotation = camera.rotation;

    if (this.imagezoom)
      this.imagezoom.resetView();
    this.startImageLoader();
    this.visible = true;
  }

  public hide(): void {

    if (this.imageLoader) {
      this.imageLoader.stop();
      this.imageLoader = null;  
    }

    if (this.imagezoom)
      this.imagezoom.clear();

    this.visible = false;
    this.camera_id = 0;
  }

  ngOnInit(): void {
  }

  ngOnDestroy(): void {
    this.hide();
  }

}
