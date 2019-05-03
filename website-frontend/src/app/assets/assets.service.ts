//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

// capturearchive.service.ts
// Service for Farm Jobs

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable()
export class AssetService {

  constructor(public authHttp: HttpClient) {
  }  

  createAssetJob(scan_asset_id : number, jobclass : string, params : string, use_gpu : boolean, node_name : string, tags : string[] = []) {
    var dataObj = {
      job_class : jobclass,
      status: 'ready',
      params : params,
      req_gpu: use_gpu,
      req_version: 18,
      ext_take_id: null,
      ext_scan_assets_id: scan_asset_id,
      ext_tracking_assets_id: null,
      node_name: node_name,
      tags: tags
    };
    return this.authHttp.post('/jobs/farm_jobs/', dataObj);
  }

  createTakeJob(take_id : number, jobclass : string, params : string, use_gpu : boolean, node_name : string, tags : string[] = [])
  {
    var dataObj = {
      job_class : jobclass,
      status: 'ready',
      params : params,
      req_gpu: use_gpu,
      req_version: 18,
      ext_take_id: take_id,
      ext_scan_assets_id: null,
      ext_tracking_assets_id: null,
      node_name: node_name,
      tags: tags
    };
    return this.authHttp.post('/jobs/farm_jobs/', dataObj);
  }

  createTrackingAssetJob(tracking_asset_id : number, jobclass : string, params : string, use_gpu : boolean, node_name : string, tags : string[] = []) {
    var dataObj = {
      job_class : jobclass,
      status: 'ready',
      params : params,
      req_gpu: use_gpu,
      req_version: 18,
      ext_take_id: null,
      ext_scan_assets_id: null,
      ext_tracking_assets_id: tracking_asset_id,
      node_name: node_name,
      tags: tags
    };
    return this.authHttp.post('/jobs/farm_jobs/', dataObj);
  }

  getProjects() {
    return this.authHttp.get('/archive/archive_projects/');
  }

  getProjectsAssets(project_id) {
    return this.authHttp.get('/archive/asset_projects/' + project_id);
  }

}
