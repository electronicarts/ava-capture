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
    </div>

    <section class="content">
      <router-outlet></router-outlet>
    </section>
  `,
  encapsulation: ViewEncapsulation.None,
  providers: [ArchiveService]
})
export class ReviewProjectPage {

  current_project = 0;
  project_data = [];

  loader = new LoadDataEveryMs();

  constructor (private router: Router, private archiveService: ArchiveService) {
    this.router = router;

    router.events.subscribe((val) => {
        if (val instanceof NavigationEnd) {
            // Notification each time the route changes, so that we can change the select dropdown
            if (val.urlAfterRedirects.startsWith('/app/review/project/archive-by-project')) {
              this.current_project = Number(val.urlAfterRedirects.split('/')[5]);
            }
        }
    });

  }

  trackById(obj : any) {
    return obj.id;
  }

  onChangeProject(event) {
    if (this.current_project > 0) {
      this.router.navigate(['app', 'review', 'project', 'archive-by-project', this.current_project]);
    } else {
      this.router.navigate(['app', 'review', 'project']);
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
