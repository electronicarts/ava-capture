//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, EventEmitter } from '@angular/core';

import { JobsService } from './jobs.service';

@Component({
  selector: 'job_block',
  template: require('./job_block.html')
})
export class JobBlock {

  @Input() data : any;
  @Input() detailed : Boolean;
  @Output() onGotoJob = new EventEmitter<number>();

  constructor(private jobsService: JobsService) {
      this.detailed = false;
  }

  gotoJob(jobid : number) {
    this.onGotoJob.emit(jobid);
  }

  restartJob(event, job_id, clone_job, use_same_machine) {

    this.jobsService.restartJob(job_id, clone_job, use_same_machine).subscribe(
        data => {},
        err => console.error(err),
        () => {}
      );

    event.preventDefault();
  }

  changePriority(job, value) {
    this.jobsService.changePriority(job.id, value).subscribe(
      data => {},
      err => console.error(err),
      () => {}
    ); 
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
