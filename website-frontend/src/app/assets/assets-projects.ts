//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import {Component} from '@angular/core';
import {Router, ActivatedRoute, Params, NavigationEnd} from '@angular/router';

import { AssetService } from './assets.service';
import { LoadDataEveryMs } from '../../utils/reloader';

@Component({
  selector: 'assets-projects',
  template: require('./assets-projects.html'),
  providers: [AssetService]
})
export class AssetsProjectsPage {

  router: Router;
  loader = new LoadDataEveryMs();
  project_data : any = null;

  constructor(private assetService: AssetService, private route: ActivatedRoute, router: Router) {
    this.router = router;
  }

  trackByProjectId(index: number, project : any) {
    return project.id;
  }

  trackBySessionId(index: number, session : any) {
    return session.id;
  }

  ngOnInit(): void {

    this.loader.start(3000, () => { return this.assetService.getProjects(); }, (data : any) => {
          this.project_data = data.results;
        });

  }

  ngOnDestroy(): void {
    this.loader.release();
  }
}
