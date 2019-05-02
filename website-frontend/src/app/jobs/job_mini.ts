//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, EventEmitter } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { JobsService } from './jobs.service';
import { NotificationService } from '../notifications.service';

@Component({
  selector: 'job_label',
  template: require('./job_mini.html'),
  providers: [JobsService]
})
export class JobLabel {

  @Input() job : any;
  @Input() show_link: boolean = true;
  @Input() minwidth: string = "340px";
  @Output() onJobDetails = new EventEmitter<number>();

  show_image : boolean = false;  

  constructor(private notificationService: NotificationService, private jobsService: JobsService) {
  }  

  showJobDetails(jobid : number) {
    this.onJobDetails.emit(jobid);
  }  

  toggleImage() {
    this.show_image = !this.show_image;
  }

  restartJob(event, job_id, clone_job, use_same_machine) {
    
    this.jobsService.restartJob(job_id, clone_job, use_same_machine).subscribe(
        data => {},
        err => {
          this.notificationService.notifyError(`ERROR: Could not restart job (${err.status} ${err.statusText})`);
        }
      );

    event.preventDefault();
  }

  killJob(event, job_id) {

    this.jobsService.killJob(job_id).subscribe(
      data => {},
      err => {
        this.notificationService.notifyError(`ERROR: Could not kill job (${err.status} ${err.statusText})`);
      }
    );
  }

  deleteJob(event, job_id) {

    this.jobsService.deleteJob(job_id).subscribe(
      data => {},
      err => {
        this.notificationService.notifyError(`ERROR: Could not delete job (${err.status} ${err.statusText})`);
      }
      );
  }

}

@Component({
  selector: 'job_label_list',
  template: require('./job_mini_list.html')
})
export class JobLabelList {

  @Input() jobs : any;
  @Output() onJobDetails = new EventEmitter<number>();

  trackById(job : any) {
    return job.id;
  }

  displayJobDetails(id) {
    this.onJobDetails.emit(id);
  }

}
