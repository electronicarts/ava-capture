//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {Component} from '@angular/core';
import {Router, ActivatedRoute, Params, NavigationEnd} from '@angular/router';

import { AssetService } from './assets.service';
import { CoreComponent } from '../core/core.component';

@Component({
  selector: 'assets-projects',
  template: require('./assets-projects.html'),
  providers: [AssetService]
})
export class AssetsProjectsPage {

  router: Router;
  project_data : any = null;
  projects_subscription = null;

  constructor(private assetService: AssetService, private route: ActivatedRoute, router: Router, private coreComponent: CoreComponent) {
    this.router = router;
  }

  trackByProjectId(index: number, project : any) {
    return project.id;
  }

  trackBySessionId(index: number, session : any) {
    return session.id;
  }

  ngOnInit(): void {

    this.projects_subscription = this.coreComponent.getProjectsStream().subscribe(
      data => {
        this.project_data = data;
      }
    );

  }

  ngOnDestroy(): void {
    if (this.projects_subscription) {
      this.projects_subscription.unsubscribe();
    }
  }
}
