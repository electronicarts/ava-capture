//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

// capturearchive.service.ts
// Service for Farm Jobs

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, from } from 'rxjs';

@Injectable()
export class ArchiveService {

  constructor(public authHttp: HttpClient) {
  }

  importSession(project_id, files_to_upload) {

    var url = '/archive/import_session/' + project_id;

    // Create an Observable containing a Promise with an XMLHttpRequest
    return from(new Promise((resolve, reject) => {
        let formData: any = new FormData()
        let xhr = new XMLHttpRequest()

        for(var i = 0; i < files_to_upload.length; i++) {
            formData.append("userfile", files_to_upload[i], files_to_upload[i].name);
        }

        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    resolve(xhr.response)
                } else {
                    reject(xhr.response)
                }
            }
        }
        xhr.open("POST", url, true)
        xhr.send(formData)
    }));    
  }

  getExportLocation() : Observable<any> {
    return this.authHttp.get('/archive/get_export_path/');
  }

  deleteTakes(session_id : number, takeid_list : number[]) {
    var dataObj = {
      session_id: session_id,
      takeid_list : takeid_list,
    };
    return this.authHttp.post('/archive/delete_takes/', dataObj);
  }

  setSessionMasterColorchart(session_id : number, take_id : number) {
    var dataObj = {
      session_master_colorchart_id : take_id
    };
    return this.authHttp.patch('/archive/archive_session/' + session_id + '/', dataObj);    
  }

  setSessionMasterCalib(session_id : number, take_id : number) {
    var dataObj = {
      session_master_calib_id : take_id
    };
    return this.authHttp.patch('/archive/archive_session/' + session_id + '/', dataObj);    
  }

  setSessionNeutralTake(session_id : number, take_id : number) {
    var dataObj = {
      session_neutral_take_id : take_id
    };
    return this.authHttp.patch('/archive/archive_session/' + session_id + '/', dataObj);    
  } 

  setSessionFrontalCamera(session_id : number, cam_unique_id : string) {
    var dataObj = {
      session_id : session_id,
      cam_unique_id : cam_unique_id
    };
    return this.authHttp.post('/archive/set_frontal_cam/', dataObj);    
  }

  setTakesFlag(flag_name : string, takeid_list : number[]) {
    var dataObj = {
      take_ids : takeid_list,
      flag_name : flag_name,
      flag_set : true
    };
    return this.authHttp.post('/archive/set_take_flag/', dataObj);  
  }

  setTakeFlag(take_id : number, flag_name : string, flag_set : boolean) {
    var dataObj = {
      take_id : take_id,
      flag_name : flag_name,
      flag_set : flag_set
    };
    return this.authHttp.post('/archive/set_take_flag/', dataObj);    
  }

  getFarmNodes() : Observable<any> {
    return this.authHttp.get('/jobs/farm_nodes/');
 }
 
  createTakeThumbnailsJob(take_id : number) {
    var dataObj = {
      job_class : 'jobs.thumbnails.GenerateThumbnail',
      status: 'ready',
      req_gpu: false,
      req_version: 18,
      ext_take_id: take_id,
      ext_scan_assets_id: null,
      ext_tracking_assets_id: null
    };
    return this.authHttp.post('/jobs/farm_jobs/', dataObj);
  }

  createScanAssetThumbnailsJob(asset_id : number, frame_key : string = null) {
    var dataObj = {
      job_class : 'jobs.thumbnails.GenerateThumbnail',
      status: 'ready',
      req_gpu: false,
      req_version: 18,
      ext_take_id: null,
      ext_scan_assets_id: asset_id,
      ext_tracking_assets_id: null
    };
    if (frame_key) {
      dataObj['params'] = '{"frame_key":"'+frame_key+'"}';
    }
    return this.authHttp.post('/jobs/farm_jobs/', dataObj);
  }

  createTrackingAssetThumbnailsJob(asset_id : number, frame_key : string = null) {
    var dataObj = {
      job_class : 'jobs.thumbnails.GenerateThumbnail',
      status: 'ready',
      req_gpu: false,
      req_version: 18,
      ext_take_id: null,
      ext_scan_assets_id: null,
      ext_tracking_assets_id: asset_id
    };
    return this.authHttp.post('/jobs/farm_jobs/', dataObj);
  }

  createTrackingAsset(take_id : number, start_time : number, end_time : number) {
    var dataObj = {
      take_id : take_id,
      start_time : start_time,
      end_time : end_time
    };
    return this.authHttp.post('/archive/create_tracking_asset/', dataObj);
  }

  exportTakes(session_id, takeid_list : number[], export_path : string) {
    var dataObj = {
      session_id : session_id,
      takeid_list : takeid_list,
      export_path : export_path
    };
    return this.authHttp.post('/archive/export_takes/', dataObj);
  }

  getSession(session_id : number) {
    return this.authHttp.get('/archive/archive_session/' + session_id);
  }

  getTake(take_id : number) {
    return this.authHttp.get('/archive/take/' + take_id);
  }

  getProjects() {
    return this.authHttp.get('/archive/archive_projects/');
  }

  getProjectsTakes(project_id) {
    return this.authHttp.get('/archive/archive_project/' + project_id);
  }

  setStaticAssetFrame(asset_id : number, frame_type : string, frame_time: number) {
    var dataObj = {};
    dataObj[frame_type] = frame_time;
    return this.authHttp.patch('/archive/staticscanasset/' + asset_id + '/', dataObj);
  }

  setTrackingAssetFrame(asset_id : number, frame_type : string, frame_time: number) {
    var dataObj = {};
    dataObj[frame_type] = frame_time;
    return this.authHttp.patch('/archive/trackingasset/' + asset_id + '/', dataObj);
  }

}
