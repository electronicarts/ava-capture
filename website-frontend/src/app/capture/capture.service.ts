//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

// capture.service.ts
// Service for Live Capture

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

@Injectable()
export class CaptureService {

  constructor(public authHttp: HttpClient) {
  }

  setCameraROIPercent(camera_id : number, percent : number, loc_id : number) {
    var dataObj = {
      camera_id : camera_id,
      loc_id : loc_id,
      percent : percent
    };
    return this.authHttp.post('/capture/camera_set_roi/', dataObj);
  }

  setCameraROI(camera_id : number, values : number[], loc_id : number) {
    var dataObj = {
      camera_id : camera_id,
      loc_id : loc_id,
      x : values[0],
      y : values[1],
      w : values[2],
      h : values[3]
    };
    return this.authHttp.post('/capture/camera_set_roi/', dataObj);
  }

  sendMessageToNodes(location_id : number, message : string) {
    var dataObj = {
      location_id : location_id,
      message: message,
    };
    return this.authHttp.post('/capture/message/', dataObj);
  }

  resetCameraROI(camera_id : number, loc_id : number) {
    var dataObj = {
      camera_id : camera_id,
      loc_id : loc_id,
    };
    return this.authHttp.post('/capture/camera_reset_roi/', dataObj);
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
    return this.authHttp.post('/capture/stop_recording/', dataObj);
  }

  recordImageBurst(location_id : number, session_id : number, shot_name : string, burst_length: number, burst_is_scan : boolean) {
    var dataObj = {
      location : location_id,
      session_id : session_id,
      shot : shot_name,
      burst_length : burst_length,
      burst_is_scan : burst_is_scan
    };
    return this.authHttp.post('/capture/record_single_image/', dataObj);
  }

  recordSingleImage(location_id : number, session_id : number, shot_name : string) {
    var dataObj = {
      location : location_id,
      session_id : session_id,
      shot : shot_name
    };
    return this.authHttp.post('/capture/record_single_image/', dataObj);
  }

  nextCaptureShot(shot_name : string, location_id : number) : Observable<any> {
    var dataObj = {
      name : shot_name
    };
    return this.authHttp.post('/capture/new_shot/' + location_id, dataObj);
  }

  newCaptureSession(location_id : number, new_session_name : string, existing_project : number, new_project_name : string) : Observable<any> {
    var dataObj = {
      name : new_session_name
    };
    if (existing_project>0) {
      dataObj['project_id'] = existing_project;
    }
    if (new_project_name!='') {
      dataObj['project_name'] = new_project_name;
    }
    return this.authHttp.post('/capture/new_session/' + location_id, dataObj);
  }

  getSystemInformation() {
    return this.authHttp.get('/capture/locations/');
  }

  getLocationName(location_id : number) : Observable<string> {
    return this.authHttp.get('/capture/location/' + location_id, {responseType: 'text'}).pipe(map(data => <string>data));
  }

  getLocationConfig(location_id : number) {
    return this.authHttp.get('/capture/location_config/' + location_id);
  }

  getCameraDetailsDirect(location_id : number) {
    return this.authHttp.get('/capture/cameras_detailed/' + location_id);
  }

  getSingleCameraDetailsDirect(location_id : number, camera_id : number) {
    return this.authHttp.get('/capture/camera_detailed/' + location_id + '/' + camera_id);
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
