//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, EventEmitter } from '@angular/core';

import { JobsService } from './jobs.service';
import { NotificationService } from '../notifications.service';

@Component({
  selector: 'job_block',
  template: require('./job_block.html')
})
export class JobBlock {

  @Input() data : any;
  @Input() detailed : Boolean;
  @Output() onGotoJob = new EventEmitter<number>();

  constructor(private notificationService: NotificationService, private jobsService: JobsService) {
      this.detailed = false;
  }

  gotoJob(jobid : number) {
    this.onGotoJob.emit(jobid);
  }

  restartChildJobs(event, job_id, use_same_machine) {
    
      this.jobsService.restartFailedChildJob(job_id, use_same_machine).subscribe(
        data => {},
        err => { this.notificationService.notifyError(`ERROR: Could not restart jobs (${err.status} ${err.statusText})`); }
        );
  
      event.preventDefault();
    }

  restartJob(event, job_id, clone_job, use_same_machine) {

    this.jobsService.restartJob(job_id, clone_job, use_same_machine).subscribe(
      data => {},
      err => { this.notificationService.notifyError(`ERROR: Could not restart job (${err.status} ${err.statusText})`); }
    );

    event.preventDefault();
  }

  changePriority(event, job, value) {
    
    this.jobsService.changePriority(job.id, value).subscribe(
      data => {
        job.priority = value;
      },
      err => { this.notificationService.notifyError(`ERROR: Could not change job priority (${err.status} ${err.statusText})`); }
    ); 

    event.preventDefault();
  }

  killJob(event, job_id) {

    this.jobsService.killJob(job_id).subscribe(
        data => {},
        err => { this.notificationService.notifyError(`ERROR: Could not kill job (${err.status} ${err.statusText})`); }
      );
  }

  deleteJob(event, job_id) {

    this.jobsService.deleteJob(job_id).subscribe(
        data => {},
        err => { this.notificationService.notifyError(`ERROR: Could not delete job (${err.status} ${err.statusText})`); }
      );
  }

}
