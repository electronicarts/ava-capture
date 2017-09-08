//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import {Component, ViewEncapsulation} from '@angular/core';
import {Router, NavigationEnd} from '@angular/router';

import { ArchiveService } from './capturearchive.service';

import { LoadDataEveryMs } from '../../utils/reloader';

@Component({
  selector: 'pipeline',
  template: `
    <div class="section_select">
        <div>
            <span class="label">Projects:</span>
            <select [(ngModel)]="current_project" (ngModelChange)="onChangeProject($event)">
              <option value="0">Please select a Project</option>
              <option *ngFor="let prj of project_data; trackBy:trackById" value="{{prj.id}}">
                {{prj.name}}
              </option>
            </select>
        </div>
        <div>        
            <span class="label">Session:</span>
            <select [(ngModel)]="current_session" (ngModelChange)="onChangeSession($event)">
              <option value="0">Please select a Session</option>
              <option *ngFor="let sess of session_data; trackBy:trackById" value="{{sess.id}}">
                {{sess.name}}
              </option>
            </select>            
        </div>
    </div>

    <section class="content">
      <router-outlet></router-outlet>
    </section>
  `,
  encapsulation: ViewEncapsulation.None,
  providers: [ArchiveService]
})
export class ReviewSessionPage {

  current_project = 0;
  current_session = 0;
  project_data = [];
  session_data = [];

  loader = new LoadDataEveryMs();

  constructor (private router: Router, private archiveService: ArchiveService) {
    this.router = router;

    router.events.subscribe((val) => {
        if (val instanceof NavigationEnd) {
            // Notification each time the route changes, so that we can change the select dropdown
            if (val.urlAfterRedirects.startsWith('/app/review/session/archive-session/')) {

              // Need to find this session in all projects, to select project and session
              var session_id = Number(val.urlAfterRedirects.split('/')[5]);

              // this.current_project = 
              // this.current_session = 
            }
        }
    });

  }

  trackById(obj : any) {
    return obj.id;
  }

  onChangeProject(event) {

    this.current_session = 0;
    if (this.current_project>0) {
      // Find project with this ID
      for (var i = 0, leni = this.project_data.length; i < leni; i++) {
        if (this.project_data[i].id == this.current_project) {
          this.session_data = this.project_data[i].sessions;

          this.onChangeSession(null);
          return;
        }
      }
    }
    
    this.session_data = [];
  }

  onChangeSession(event) {
    if (this.current_session > 0) {
      this.router.navigate(['app', 'review', 'session', 'archive-session', this.current_session]);
    } else {
      this.router.navigate(['app', 'review', 'session']);     
    }
  }

  ngOnInit() {

    this.loader.start(3000, () => { return this.archiveService.getProjects(); }, (data : any) => {
          this.project_data = data.results;
        });
    
  }

  ngOnDestroy() {
    this.loader.release();
  }

}
