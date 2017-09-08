//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import {Component} from '@angular/core';
import {Router, ActivatedRoute, Params, NavigationEnd} from '@angular/router';

import { ArchiveService } from './capturearchive.service';
import { LoadDataEveryMs } from '../../utils/reloader';

@Component({
  selector: 'archive-projects',
  template: require('./archive-projects.html'),
  providers: [ArchiveService]
})
export class ArchiveProjectsPage {

  router: Router;
  loader = new LoadDataEveryMs();
  project_data : any = null;

  constructor(private archiveService: ArchiveService, private route: ActivatedRoute, router: Router) {
    this.router = router;
  }

  trackByProjectId(index: number, project : any) {
    return project.id;
  }

  trackBySessionId(index: number, session : any) {
    return session.id;
  }

  ngOnInit(): void {

    this.loader.start(3000, () => { return this.archiveService.getProjects(); }, (data : any) => {
          this.project_data = data.results;
        });

  }

  ngOnDestroy(): void {
    this.loader.release();
  }
}
