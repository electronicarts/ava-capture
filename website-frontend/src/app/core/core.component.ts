//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component } from '@angular/core';
import { Router } from '@angular/router';

import { LoadDataEveryMs } from '../../utils/reloader';

import { ArchiveService } from '../archive/capturearchive.service';

import { Subject } from 'rxjs';
import { startWith } from 'rxjs/operators';

@Component({
  selector: '[core]',
  template: require('./core.html'),
  providers: [ArchiveService]
})
export class CoreComponent {

  loader = new LoadDataEveryMs();
  subject = new Subject<any>();
  last_projects = [];

  current_project : number = 0;
  current_session : number = 0;
  current_location : number = 0;
  
  constructor(router: Router, private archiveService: ArchiveService) {
  }

  setCurrentProject(id) {
    this.current_project = id;

    localStorage.setItem('ui_current_project_id',id);
  }

  getCurrentProject() {
    return this.current_project;
  }

  setCurrentSession(id) {
    this.current_session = id;

    localStorage.setItem('ui_current_session_id',id);
  }

  getCurrentSession() {
    return this.current_session;
  }

  setCurrentLocation(id) {
    this.current_location = id;

    localStorage.setItem('ui_current_location_id',id);
  }

  getCurrentLocation() {
    return this.current_location;
  }

  getProjectsStream() {
    return this.subject.pipe(startWith(this.last_projects));
  }  

  ngOnInit() {

    this.current_project = Number(localStorage.getItem('ui_current_project_id'));
    this.current_session = Number(localStorage.getItem('ui_current_session_id'));
    this.current_location = Number(localStorage.getItem('ui_current_location_id'));
    
    this.loader.start(10000, () => { return this.archiveService.getProjects(); }, (data : any) => {
      // TODO Only if changed?
      this.last_projects = data.results;  
      this.subject.next(data.results); // forwards to all observers subscribed to this subject
    });
  }
    
  ngOnDestroy() {
    this.loader.release();  
  }
      
}
