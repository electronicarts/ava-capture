//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {Component} from '@angular/core';
import {Router, ActivatedRoute, Params, NavigationEnd} from '@angular/router';

import { ArchiveService } from './capturearchive.service';
import { CoreComponent } from '../core/core.component';

var $ = require("jquery");

@Component({
  selector: 'archive-by-session',
  template: require('./archive-by-session.html'),
  providers: [ArchiveService]
})
export class ArchivesPage {

  router: Router;
  projects_subscription = null;
  project_data : any = null;

  import_session_project_id = 0;
  import_session_error = null;
  import_session_files = [];

  working : boolean = false;

  constructor(private archiveService: ArchiveService, private route: ActivatedRoute, router: Router, private coreComponent: CoreComponent) {
    this.router = router;
  }

  fileChangeEvent(event) {
    this.import_session_files = event.target.files;
  }

  onClickImport(target_project_id) {
    this.import_session_project_id = target_project_id;
    this.import_session_error = null;
    (<any>$('#importSessionModal')).addClass('modal-dialog-container-show');
  }

  onCancelImportSessionFromJSON() {
    (<any>$('#importSessionModal')).removeClass('modal-dialog-container-show');
  }

  onImportSessionFromJSON() {

    this.working = true;

    this.archiveService.importSession(this.import_session_project_id, this.import_session_files).subscribe(
      data => {
        (<any>$('#importSessionModal')).removeClass('modal-dialog-container-show');
        this.working = false;
      },
      err => {
        this.import_session_error = err; // Display Error text
        $('#textareaID').focus();
        this.working = false;
      },
      () => {}
    );    
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
