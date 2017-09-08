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
export class AssetService {

  constructor(public authHttp: AuthHttp) {
  }  

  createAssetJob(scan_asset_id : number, jobclass : string, params : string, use_gpu : boolean) {
    var dataObj = {
      job_class : jobclass,
      status: 'ready',
      params : params,
      req_gpu: use_gpu,
      req_version: 18,
      ext_take_id: null,
      ext_scan_assets_id: scan_asset_id,
      ext_tracking_assets_id: null
    };
    return this.authHttp.post('/jobs/farm_jobs/', dataObj);
  }

  createTrackingAssetJob(tracking_asset_id : number, jobclass : string, params : string, use_gpu : boolean, node_name : string) {
    var dataObj = {
      job_class : jobclass,
      status: 'ready',
      params : params,
      req_gpu: use_gpu,
      req_version: 18,
      ext_take_id: null,
      ext_scan_assets_id: null,
      ext_tracking_assets_id: tracking_asset_id,
      node_name: node_name
    };
    return this.authHttp.post('/jobs/farm_jobs/', dataObj);
  }

  getProjects() {
    return this.authHttp.get('/archive/archive_projects/').map(res => res.json());
  }

  getProjectsAssets(project_id) {
    return this.authHttp.get('/archive/asset_projects/' + project_id).map(res => res.json());
  }

}
