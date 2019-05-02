//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {Component, ViewEncapsulation} from '@angular/core';
import { Router, ActivatedRoute, Params } from '@angular/router';

import { JobsService } from './jobs.service';
import { NotificationService } from '../notifications.service';
import { LoadDataEveryMs } from '../../utils/reloader';

declare var jQuery: any;

@Component({
  selector: 'jobs_running',
  template: require('./jobs_running.html'),
  encapsulation: ViewEncapsulation.None,
  providers: [JobsService]
})
export class JobsRunningPage {

  loader = new LoadDataEveryMs();

  jobs_data = null;
  selected_job_id = 0;

  filter_limit : number = 30;
  filter_search : string = null;
  filter_status : string = 'all';

  constructor(private notificationService: NotificationService, private jobsService: JobsService, private route: ActivatedRoute) {
  }

  hideJobDetails() {
    this.selected_job_id = 0;
  }

  displayJobDetails(jobid) {
    this.selected_job_id = jobid;
  }

  restartJob(event, job_id, clone_job, use_same_machine) {

    this.jobsService.restartJob(job_id, clone_job, use_same_machine).subscribe(
        data => {},
        err => { this.notificationService.notifyError(`ERROR: Could not restart job (${err.status} ${err.statusText})`); }
      );

    event.preventDefault();
  }

  trackByJobId(index: number, farmjob) {
    return farmjob.id;
  }

  ngOnInit(): void {

    let searchInput = jQuery('#table-search-input');
    searchInput
      .focus((e) => {
      jQuery(e.target).closest('.input-group').addClass('focus');
    })
      .focusout((e) => {
      jQuery(e.target).closest('.input-group').removeClass('focus');
    });

    this.loader.start(3000, () => { return this.jobsService.getFarmJobs(this.filter_search, this.filter_status, this.filter_limit); }, data => {
          this.jobs_data = data.results;
        }, err=>{},
      'getFarmNodes_'+this.filter_search+this.filter_status+this.filter_limit); // cache_key

  }

  ngOnDestroy(): void {

    this.loader.release();

  }

}
