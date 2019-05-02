//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, EventEmitter } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { JobsService } from './jobs.service';

@Component({
  selector: 'job_infopanel',
  template: require('./job_infopanel.html'),
  providers: [JobsService]
})
export class JobInfoPanel {

  @Input() job_id : number = 0;
  @Output() onHideJobDetails = new EventEmitter<void>();
  
  constructor(private jobsService: JobsService) {
  }  

  hideJobDetails() {
    this.job_id = 0;
    this.onHideJobDetails.emit();
  }

  displayJobDetails(jobid) {
    this.job_id = jobid;
  }
        
}
