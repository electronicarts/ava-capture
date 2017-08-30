//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, Subject } from 'rxjs/Rx';

import { LoadDataEveryMs } from '../../utils/reloader';

import { ArchiveService } from '../archive/capturearchive.service';

@Component({
  selector: '[core]',
  template: require('./core.html'),
  providers: [ArchiveService]
})
export class CoreComponent {

  loader = new LoadDataEveryMs();
  subject = new Subject<any>();
  last_projects = [];
  
  constructor(router: Router, private archiveService: ArchiveService) {
  }

  getProjectsStream() {
    return this.subject.startWith(this.last_projects);
  }  

  ngOnInit() {
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
