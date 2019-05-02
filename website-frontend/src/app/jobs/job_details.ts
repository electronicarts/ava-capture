//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input } from '@angular/core';
import {ActivatedRoute, Params} from '@angular/router';

import { JobsService } from './jobs.service';
import { LoadDataEveryMs } from '../../utils/reloader';

@Component({
  selector: 'job_details',
  template: require('./job_details.html'),
  providers: [JobsService]
})
export class JobDetailsPage {

  @Input()
  jobid = 0;

  job_data : any = null;
  loading : boolean = true;

  loader = new LoadDataEveryMs();

  constructor(private jobsService: JobsService, private route: ActivatedRoute) {
  }

  gotoJob(jobid : number) {
    this.jobid = jobid;
    this.ngOnChanges();
  }

  trackByJobId(index: number, job : any) {
    return job.id;
  }

  ngOnChanges() : void {

    if (this.jobid>0) {
      this.loading = true;
      this.loader.start(3000, () => { return this.jobsService.getFarmJobDetails(this.jobid); }, data => {
            this.job_data = data;
            this.loading = false;
          }, err => {
            this.job_data = null;
            this.loading = false;
          });
    }

  }

  ngOnInit(): void {

  }

  ngOnDestroy(): void {

      this.loader.release();

  }

}
