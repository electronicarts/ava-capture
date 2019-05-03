//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {Component, ViewEncapsulation} from '@angular/core';
import {Router, NavigationEnd} from '@angular/router';

import { ArchiveService } from './capturearchive.service';
import { CoreComponent } from '../core/core.component';

@Component({
  selector: 'pipeline',
  template: `
    <div class="section_select">
        <div *ngIf="!loading">
            <span class="label">Projects:</span>
            <select [(ngModel)]="current_project" (ngModelChange)="onChangeProject($event)">
              <option value="0">Please select a Project</option>
              <option *ngFor="let prj of project_data; trackBy:trackById" value="{{prj.id}}">
                {{prj.name}}
              </option>
            </select>
        </div>
        <div *ngIf="!loading">        
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
  projects_subscription = null;
  loading : boolean = true;

  session_id_from_url : number = null;

  constructor (private router: Router, private archiveService: ArchiveService, private coreComponent: CoreComponent) {
    this.router = router;

    router.events.subscribe((val) => {
        if (val instanceof NavigationEnd) {
            // Notification each time the route changes, so that we can change the select dropdown
            if (val.urlAfterRedirects.startsWith('/app/review/session/archive-session/')) {

              // Need to find this session in all projects, to select project and session
              this.session_id_from_url = Number(val.urlAfterRedirects.split('/')[5]);

              // Find session with this ID
              this.setSessionFromId(this.session_id_from_url);
            }
        }
    });

  }

  setSessionFromId(session_id) {
    for (var i = 0, leni = this.project_data.length; i < leni; i++) {
      for (var j = 0, lenj = this.project_data[i].sessions.length; j < lenj; j++) {
        if (this.project_data[i].sessions[j].id == session_id) {
          this.session_id_from_url = null;
          this.current_project = this.project_data[i].id;
          this.session_data = this.project_data[i].sessions;
          this.current_session = session_id;
          this.coreComponent.setCurrentSession(session_id);
          return;
        }
      }              
    }              
  }

  trackById(obj : any) {
    return obj.id;
  }

  onChangeProject(event) {

    this.current_session = 0;
    this.session_id_from_url = null;
    //this.router.navigate(['app', 'review', 'session']);  
    this.coreComponent.setCurrentSession(0);
    
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

    this.projects_subscription = this.coreComponent.getProjectsStream().subscribe(
      data => {
        this.project_data = data;
        this.loading = false;
        
        if (this.session_id_from_url)
          this.setSessionFromId(this.session_id_from_url);

        if (this.coreComponent.getCurrentSession()>0 && this.current_session != this.coreComponent.getCurrentSession()) {
          this.router.navigate(['app', 'review', 'session', 'archive-session', this.coreComponent.getCurrentSession()]);
        }     
      }
    );
    
  }

  ngOnDestroy() {
    if (this.projects_subscription) {
      this.projects_subscription.unsubscribe();
    }
  }

}
