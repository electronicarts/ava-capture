//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { LoadDataEveryMs } from '../../utils/reloader';
import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'OnlyActivePipe'
})
export class OnlyActivePipe implements PipeTransform {

  transform(value): Array<any> {
    var res = value;
    if (value) {
      res = value.filter(obj => {
        return obj.active;
      }); 
    }
    return res;  
  }
}

@Component({
  template: require('./frontpage.html')
})
export class FrontpageComponent {
  
  data_active_farm_nodes = null;
  data_running_jobs = null;
  data_recent_finished_jobs = null;
  data_recent_capture_sessions = null;

  subscriptions = new Array<LoadDataEveryMs>();

  constructor(public authHttp: HttpClient) {
  }

  trackById(index: number, something : any) {
    return something.id;
  }
    
  getActiveFarmNodes() : Observable<any> {
    return this.authHttp.get('/jobs/farm_nodes/?status=accepting');
  }

  getRunningJobs() : Observable<any> {
    return this.authHttp.get('/jobs/farm_jobs/?status=running');
  }

  getRecentFinishedJobs(limit : number) : Observable<any> {
    return this.authHttp.get(`/jobs/recent_finished_jobs/?limit=${limit}`);
  }

  getRecentSessions(limit : number) : Observable<any> {
    return this.authHttp.get(`/archive/session/?ordering=-start_time&limit=${limit}`);
  }

  ngOnInit(): void {

    var loader = new LoadDataEveryMs();
    loader.start(3000, () => { return this.getActiveFarmNodes(); }, data => {
      this.data_active_farm_nodes = data;
    });
    this.subscriptions.push(loader);

    var loader = new LoadDataEveryMs();
    loader.start(3100, () => { return this.getRunningJobs(); }, data => {
      this.data_running_jobs = data;
    });
    this.subscriptions.push(loader);

    var loader = new LoadDataEveryMs();
    loader.start(3200, () => { return this.getRecentFinishedJobs(8); }, data => {
      this.data_recent_finished_jobs = data;
    });
    this.subscriptions.push(loader);

    var loader = new LoadDataEveryMs();
    loader.start(20000, () => { return this.getRecentSessions(8); }, data => {
      this.data_recent_capture_sessions = data;
    });
    this.subscriptions.push(loader);

  }

  ngOnDestroy(): void {
    while (this.subscriptions.length > 0) {
      this.subscriptions.pop().release();
    }
  }

}
