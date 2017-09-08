//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, EventEmitter } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { JobsService } from './jobs.service';

@Component({
  selector: 'job_label',
  template: require('./job_mini.html'),
  providers: [JobsService]
})
export class JobLabel {

  @Input() job : any;
  @Input() show_link: boolean = true;
  @Input() minwidth: string = "340px";

  show_image : boolean = false;  

  constructor(private jobsService: JobsService) {
  }  

  toggleImage() {
    this.show_image = !this.show_image;
  }

  restartJob(event, job_id, clone_job, use_same_machine) {
    
    this.jobsService.restartJob(job_id, clone_job, use_same_machine).subscribe(
        data => {},
        err => console.error(err),
        () => {}
      );

    event.preventDefault();
  }

  killJob(event, job_id) {

    this.jobsService.killJob(job_id).subscribe(
        data => {},
        err => console.error(err),
        () => {}
      );
  }

  deleteJob(event, job_id) {

    this.jobsService.deleteJob(job_id).subscribe(
        data => {},
        err => console.error(err),
        () => {}
      );
  }

}

@Component({
  selector: 'job_label_list',
  template: require('./job_mini_list.html')
})
export class JobLabelList {

  @Input() jobs : any;

  trackById(job : any) {
    return job.id;
  }    

}
