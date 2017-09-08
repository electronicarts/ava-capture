//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

// capture.service.ts
// Service for Live Capture

import { Injectable } from '@angular/core';
import { AuthHttp } from 'angular2-jwt';

@Injectable()
export class CaptureService {

  constructor(public authHttp: AuthHttp) {
  }

  setCameraROI(camera_id : number, values : number[]) {
    var dataObj = {
      camera_id : camera_id,
      x : values[0],
      y : values[1],
      w : values[2],
      h : values[3]
    };
    return this.authHttp.post('/capture/camera_set_roi/' + camera_id, dataObj);
  }

  resetCameraROI(camera_id : number) {
    var dataObj = {
      camera_id : camera_id,
    };
    return this.authHttp.post('/capture/camera_reset_roi/' + camera_id, dataObj);
  }

  startRecording(location_id : number, session_id : number, shot_name : string) {
    var dataObj = {
      location : location_id,
      session_id : session_id,
      shot : shot_name
    };
    return this.authHttp.post('/capture/start_recording/', dataObj);
  }

  stopRecording(location_id : number) {
    var dataObj = {
      location : location_id,
    };
    return this.authHttp.post('/capture/stop_recording/', dataObj).map(res => res.json());
  }

  recordSingleImage(location_id : number, session_id : number, shot_name : string) {
    var dataObj = {
      location : location_id,
      session_id : session_id,
      shot : shot_name
    };
    return this.authHttp.post('/capture/record_single_image/', dataObj).map(res => res.json());
  }

  nextCaptureShot(location_id : number) {
    var dataObj = {
      name : 'todo'
    };
    return this.authHttp.post('/capture/new_shot/' + location_id, dataObj);
  }

  newCaptureSession(location_id : number, new_session_name : string) {
    var dataObj = {
      name : new_session_name
    };
    return this.authHttp.post('/capture/new_session/' + location_id, dataObj).map(res => res.json());
  }

  getSystemInformation() {
    return this.authHttp.get('/capture/locations/').map(res => res.json());
  }

  getLocationName(location_id : number) {
    return this.authHttp.get('/capture/location/' + location_id).map(res => res.text());
  }

  getLocationConfig(location_id : number) {
    return this.authHttp.get('/capture/location_config/' + location_id).map(res => res.json());
  }

  getCameraDetailsDirect(location_id : number) {
    return this.authHttp.get('/capture/cameras_detailed/' + location_id).map(res => res.json());
  }

  getSingleCameraDetailsDirect(location_id : number, camera_id : number) {
    return this.authHttp.get('/capture/camera_detailed/' + location_id + '/' + camera_id).map(res => res.json());
  }

  setCameraParameter(location_id : number, cam_id : number, parameter_name : string, value : number) {
    var dataObj = {
      cam_id : cam_id,
      parameter_name : parameter_name,
      value : value
    };
    return this.authHttp.post('/capture/camera_parameter/' + location_id, dataObj);
  }

  setLocationOptions(location_id : number, dataObj) {
    return this.authHttp.post('/capture/location_config/' + location_id, dataObj);
  }

  toggleUsingSync(camId : number) {
    var dataObj = {
      camera_id : camId,
    };
    return this.authHttp.post('/capture/toggle_using_sync/', dataObj);
  }

  toggleCapturing(camId : number) {
    var dataObj = {
      camera_id : camId,
    };
    return this.authHttp.post('/capture/toggle_capturing/', dataObj);
  }

  closeNode(nodeId : number) {
    var dataObj = {
      node_id : nodeId,
    };
    return this.authHttp.post('/capture/close_node/', dataObj);
  }

  setCameraRotation(camera_id : number, angle : number) {
    var dataObj = {
      camera_id : camera_id,
      angle : angle,
    };
    return this.authHttp.post('/capture/set_camera_rotation/', dataObj);
  }

}
