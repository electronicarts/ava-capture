//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {Component, ViewEncapsulation} from '@angular/core';
import {Router, NavigationEnd} from '@angular/router';

import { AssetService } from './assets.service';
import { CoreComponent } from '../core/core.component';

@Component({
  selector: 'pipeline',
  template: `
    <div class="section_select">
        <div *ngIf="!loading">
            Projects:
            <select [disabled]="project_data.length==0" [(ngModel)]="current_project" (ngModelChange)="onChangeProject($event)">
              <option value="0">Please select a Project</option>
              <option *ngFor="let prj of project_data; trackBy:trackById" value="{{prj.id}}">
                {{prj.name}}
              </option>
            </select>            
        </div>
    </div>

    <section class="content">
      <router-outlet></router-outlet>
    </section>
  `,
  encapsulation: ViewEncapsulation.None,
  providers: [AssetService]
})
export class PipelinePage {

  current_project = 0;

  project_data = [];
  projects_subscription = null;

  loading : boolean = true;

  projectIdFromUrl(url) {
    var arr = url.split(/[\/#]/); 
    if (arr.length<5)
      return 0;
    return Number(arr[4]);
  }

  constructor (private router: Router, private assetService: AssetService, private coreComponent: CoreComponent) {
    this.router = router;

    router.events.subscribe((val) => {
        if (val instanceof NavigationEnd) {
            // Notification each time the route changes, so that we can change the select dropdown
            if (val.urlAfterRedirects.startsWith('/app/pipeline/assets-by-project/')) {
              this.current_project = this.projectIdFromUrl(val.urlAfterRedirects);
              this.coreComponent.setCurrentProject(this.current_project);
            }
        }
    });

  }

  trackById(obj : any) {
    return obj.id;
  }

  onChangeProject(event) {
    if (this.current_project > 0) {
      this.router.navigate(['app', 'pipeline', 'assets-by-project', this.current_project]);
    }
  }

  ngOnInit() {

    this.current_project = this.projectIdFromUrl(this.router.url);
    if (this.current_project)
      this.coreComponent.setCurrentProject(this.current_project);

    this.projects_subscription = this.coreComponent.getProjectsStream().subscribe(
      data => {
        this.project_data = data;
        this.loading = false;

        if (this.coreComponent.getCurrentProject()>0 && this.current_project != this.coreComponent.getCurrentProject()) {
          this.router.navigate(['app', 'pipeline', 'assets-by-project', this.coreComponent.getCurrentProject()]); // , { fragment: this.route }
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
