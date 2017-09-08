//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

// jobs.service.ts
// Service for Farm Jobs

import { Injectable } from '@angular/core';
import { Headers, Response } from '@angular/http';
import { AuthHttp, tokenNotExpired } from 'angular2-jwt';

@Injectable()
export class JobsService {  

  constructor(public authHttp: AuthHttp) {
  }

  getFarmNodes() {
     return this.authHttp.get('/jobs/farm_nodes/').map(res => res.json());
  }

  getFarmGroups() {
     return this.authHttp.get('/jobs/farm_groups/').map(res => res.json());
  }

  getFarmJobs(filter_search : string, filter_status : string, limit_count : number) {
     var url = '/jobs/farm_jobs/?limit=' + limit_count;
     if (filter_status && filter_status != 'all') {
       url += '&status=' + filter_status;
     }
     if (filter_search) {
       url += '&search=' + filter_search;
     }
     return this.authHttp.get(url).map(res => res.json());
  }

  getFarmJobDetails(jobid) {
     return this.authHttp.get('/jobs/farm_job/' + jobid).map(res => res.json());
  }

  getNodeDetails(nodeid) {
     return this.authHttp.get('/jobs/farm_node/' + nodeid).map(res => res.json());
  }

  changePriority(job_id, value) {
    var dataObj = {};
    dataObj['priority'] = value;
    return this.authHttp.patch('/jobs/farm_jobs/' + job_id + '/', dataObj);    
  }

  killJob(job_id) {
    var dataObj = {
      job_id : job_id
    };
    return this.authHttp.post('/jobs/kill_job/', dataObj);
  }

  deleteJob(job_id) {
    var dataObj = {
      job_id : job_id
    };
    return this.authHttp.post('/jobs/delete_job/', dataObj);
  }

  restartJob(job_id, clone_job, use_same_machine) {
    var dataObj = {
      job_id : job_id,
      clone_job: clone_job,
      use_same_machine: use_same_machine
    };
    return this.authHttp.post('/jobs/restart_job/', dataObj);
  }

  reloadClient(node_id) {
    var dataObj = {
      node_id : node_id,
    };
    return this.authHttp.post('/jobs/reload_client/', dataObj);
  }

}
