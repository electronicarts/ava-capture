//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

// capturearchive.service.ts
// Service for Farm Jobs

import { Injectable } from '@angular/core';
import { Headers, Response } from '@angular/http';
import { AuthHttp, tokenNotExpired } from 'angular2-jwt';

import { Observable } from 'rxjs/Rx';

@Injectable()
export class ArchiveService {

  constructor(public authHttp: AuthHttp) {
  }

  importSession(project_id, files_to_upload) {

    var url = '/archive/import_session/' + project_id;

    // Create an Observable containing a Promise with an XMLHttpRequest
    return Observable.fromPromise(new Promise((resolve, reject) => {
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

  getExportLocation() {
    return this.authHttp.get('/archive/get_export_path/').map(res => res.json());
  }

  deleteTakes(takeid_list : number[]) {
    var dataObj = {
      takeid_list : takeid_list,
    };
    return this.authHttp.post('/archive/delete_takes/', dataObj);
  }

  setSessionFrontalCamera(session_id : number, cam_unique_id : string) {
    var dataObj = {
      session_id : session_id,
      cam_unique_id : cam_unique_id
    };
    return this.authHttp.post('/archive/set_frontal_cam/', dataObj);    
  }

  setTakeFlag(take_id : number, flag_name : string, flag_set : boolean) {
    var dataObj = {
      take_id : take_id,
      flag_name : flag_name,
      flag_set : flag_set
    };
    return this.authHttp.post('/archive/set_take_flag/', dataObj);    
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

  createTrackingAsset(take_id : number, calib_file : string, start_time : number, end_time : number) {
    var dataObj = {
      take_id : take_id,
      calib_file : calib_file,
      start_time : start_time,
      end_time : end_time
    };
    return this.authHttp.post('/archive/create_tracking_asset/', dataObj);
  }

  exportTakes(takeid_list : number[], export_path : string) {
    var dataObj = {
      takeid_list : takeid_list,
      export_path : export_path
    };
    return this.authHttp.post('/archive/export_takes/', dataObj);
  }

  getSession(session_id : number) {
    return this.authHttp.get('/archive/archive_session/' + session_id).map(res => res.json());
  }

  getTake(take_id : number) {
    return this.authHttp.get('/archive/take/' + take_id).map(res => res.json());
  }

  getProjects() {
    return this.authHttp.get('/archive/archive_projects/').map(res => res.json());
  }

  getProjectsTakes(project_id) {
    return this.authHttp.get('/archive/archive_project/' + project_id).map(res => res.json());
  }

}
