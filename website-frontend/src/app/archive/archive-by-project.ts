//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, ViewChild } from '@angular/core';
import { Router, ActivatedRoute, Params, NavigationEnd } from '@angular/router';

import { ArchiveService } from './capturearchive.service';
import { LoadDataEveryMs } from '../../utils/reloader';

import { SetFrameDialog } from './set-frame-dialog';

import { NotificationService } from '../notifications.service';

var $ = require("jquery");

@Component({
  selector: 'archive-by-project',
  template: require('./archive-by-project.html'),
  providers: [ArchiveService, SetFrameDialog]
})
export class ArchiveByProjectPage {

  @ViewChild('setframedialog')
  public setframedialogComponent : SetFrameDialog;
    
  router: Router;
  loader = new LoadDataEveryMs();
  project_data : any = null;
  project_id = 0;
  loading : boolean = true;

  all_takes : number[] = [];

  show_empty_takes = false;

  selected_job_id: number = 0;

  icon_movie = require("../../assets/images/ava_movie.svg");
  icon_single = require("../../assets/images/ava_single.svg");
  icon_burst = require("../../assets/images/ava_multi.svg");
  icon_scan = require("../../assets/images/ava_scan.svg");
  
  scan_frame_list = [
    {'name':'NeutralStart', 'key':'take_neutral_start_time'},
    {'name':'PatternStart', 'key':'take_pattern_start_time'},
    {'name':'MixedW', 'key':'take_mixed_w_time'},
    {'name':'PatternEnd', 'key':'take_pattern_last_time'},
    {'name':'NeutralEnd', 'key':'take_neutral_end_time'}];

  track_frame_list = [
    {'name':'Start', 'key':'start_time'},
    {'name':'End', 'key':'end_time'}];     

  import_session_project_id = 0;
  import_session_error = null;
  import_session_files = [];

  working : boolean = false;
      
  constructor(private notificationService: NotificationService, private archiveService: ArchiveService, private route: ActivatedRoute, router: Router) {
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

  scanAssetThumbfile(front_path : string, framerate : number, frame_time : number) {
    var frame_index = Math.floor(frame_time * framerate);
    return front_path.replace("_front_", "_f"+frame_index+"_");
  }

  trackingAssetThumbfile(asset_id : number, framerate : number, frame_time : number) {
    var frame_index = Math.floor(frame_time * framerate);
    return 'track' + asset_id + '_f' + frame_index + '.jpg';
  }
  
  trackById(index: number, something : any) {
    return something.id;
  }

  editFrameRange(asset : any, frame_name : string, frame_key : string, frame_time : number) {
    this.setframedialogComponent.show('tracking', asset, frame_name, frame_key, frame_time);
  }

  editFrameNumber(asset : any, frame_name : string, frame_key : string, frame_time : number) {
    this.setframedialogComponent.show('scan', asset, frame_name, frame_key, frame_time);
  }

  toggleTakeFlag(event, take, which) {
    
    var flag_set = event.target.checked;
    this.loader.subscribeDataChange(
      this.archiveService.setTakeFlag(take.id, which,flag_set ),
      data => {
        // change done, update data
        if (flag_set)
          take.flag = which;
        else
          take.flag = "none";
      },
      err => {
        this.notificationService.notifyError(`ERROR: Could not set Take flag (${err.status} ${err.statusText})`);
      }
    );
  }
    
  ngOnInit(): void {

    // Get Session Dd from URL
    this.route.params.forEach((params: Params) => {

      var new_project_id = +params['id']; // (+) converts string 'id' to a number

      if (this.project_id != new_project_id) {
        this.project_id = new_project_id;
        this.project_data = null;
        this.loading = true;

        this.loader.start(3000, () => { return this.archiveService.getProjectsTakes(this.project_id); }, (data : any) => {
          
            this.project_data = data;
            this.loading = false;

            // Find frontal camera in each take
            for (var i = 0, leni = this.project_data.sessions.length; i < leni; i++) {
              var session = this.project_data.sessions[i];
              for (var j = 0, lenj = session.shots.length; j < lenj; j++) {
                var shot = session.shots[j];
                for (var k = 0, lenk = shot.takes.length; k < lenk; k++) {
                  var take = shot.takes[k];
                  var frontal_camera = null;
                  for (var l = 0, lenl = take.cameras.length; l < lenl; l++) {
                    if (take.cameras[l].unique_id == take.frontal_cam_uid) {
                      frontal_camera = take.cameras[l];
                      break;
                    }
                  }
                  take.frontal_camera = frontal_camera;
                }
              }
            }
        }, err => {
          this.loading = false;
        }, 
        'archive_getProjectsTakes_' + this.project_id); // cache key
          
      }

    });

  }

  ngOnDestroy(): void {
    this.loader.release();
  }

}
