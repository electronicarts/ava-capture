//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {Component, ViewEncapsulation} from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';

import { CaptureService } from '../capture/capture.service';

import { LoadDataEveryMs } from '../../utils/reloader';

@Component({
  selector: 'jobs_page_select',
  template: `
    <!-- Header for Farm page, to select between Machine and Jobs view -->
    <div class="section_select">
        <ul>
            <li>
                <a [class.selected]="current_page_index==1" [routerLink]=" ['/app/farm/farm-nodes'] ">
                <span class="badge badge-default" [class.badge-success]="nb_farmnodes_active>0">{{nb_farmnodes_active}}</span>
                Farm Machines</a>                
            </li>
            <li>
                <a [class.selected]="current_page_index==2" [routerLink]=" ['/app/farm/jobs-running'] ">
                <span class="badge badge-default" [class.badge-warning]="nb_queued_jobs>0">{{nb_queued_jobs}}</span> 
                <span class="badge badge-default" [class.badge-info]="nb_running_jobs>0">{{nb_running_jobs}}</span>
                Farm Jobs</a>
            </li>
        </ul>
    </div>

    <section class="content">
      <router-outlet></router-outlet>
    </section>
  `,
  encapsulation: ViewEncapsulation.None,
  providers: [CaptureService]
})
export class JobsPageSelect {

  current_page_index = 0;

  nb_running_jobs = 0;
  nb_queued_jobs = 0;
  nb_farmnodes_active = 0;
  
  loader = new LoadDataEveryMs();

  constructor(private router: Router, private captureService: CaptureService) {
    router.events.subscribe((val) => {
        if (val instanceof NavigationEnd) {
            // Notification each time the route changes, so that we can set our style accordingly
            if (val.urlAfterRedirects === '/app/farm/jobs-running')
                this.current_page_index = 2;
            else if (val.urlAfterRedirects === '/app/farm/farm-nodes')
                this.current_page_index = 1;
            else 
                this.current_page_index = 0;
        }
    });
  }

  ngOnInit() {

      this.loader.start(5000, () => { return this.captureService.getSystemInformation(); }, data => {
          this.nb_running_jobs = data.nb_running_jobs;
          this.nb_queued_jobs = data.nb_queued_jobs;
          this.nb_farmnodes_active = data.nb_farmnodes_active;
        }, err => {}, 
    'getSystemInformation');    // cache key
    
  }

  ngOnDestroy() {
      this.loader.release();
  }

}
