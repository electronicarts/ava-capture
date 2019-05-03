//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {Component, ElementRef} from '@angular/core';
import {Router, ActivatedRoute, Params, NavigationEnd} from '@angular/router';
import { Pipe, PipeTransform } from '@angular/core';

import { ArchiveService } from './capturearchive.service';
import { LoadDataEveryMs } from '../../utils/reloader';
import { NotificationService } from '../notifications.service';

var $ = require("jquery");

@Pipe({
  name: 'NFirstPipe'
})
export class NFirstPipe implements PipeTransform {

  transform(value, count : number): Array<any> {
    return value.slice(0, count);  
  }
}

@Component({
  selector: 'archive-session',
  template: require('./archive-session.html'),
  providers: [ArchiveService]
})
export class ArchiveSessionPage {

  router: Router;
  session_id = 0;
  loader = new LoadDataEveryMs();
  session_data : any = null;
  selected_takes = new Set();
  selected_size : number = 0;
  all_takes : number[] = [];
  all_cam_uid : string[] = [];

  export_location = '';
  export_location_suggestions = ['\\\\seed.la.ad.ea.com\\rfs1\\avacapture','/cloud/s3/seed-ava-capture-e1','/cloud/gcs/seed-ava-capture-us'];
  export_missing_nodes = [];
  
  selected_job_id: number = 0;

  loading : boolean = true;

  el : ElementRef;

  exporting_count = 0;
  error_message = "";

  showCompleteTakes = new Set();

  icon_movie = require("../../assets/images/ava_movie.svg");
  icon_single = require("../../assets/images/ava_single.svg");
  icon_burst = require("../../assets/images/ava_multi.svg");
  icon_scan = require("../../assets/images/ava_scan.svg");

  constructor(el: ElementRef, private notificationService: NotificationService, private archiveService: ArchiveService, private route: ActivatedRoute, router: Router) {
    this.el = el;
    this.router = router;
  }

  showCompleteTake(take_id: number) {
    this.showCompleteTakes.add(take_id);
  }

  ifCompleteTakeShown(take_id: number) {
    return this.showCompleteTakes.has(take_id);;
  }

  onChangeMasterColorchart(take_id) {
    this.archiveService.setSessionMasterColorchart(this.session_id, take_id ).subscribe(
      data => {
      },
      err => {this.notificationService.notifyError(`ERROR: Could not change Master Color Chart (${err.status} ${err.statusText})`);},
      () => {}
    );
  }

  onChangeMasterCalib(take_id) {
    this.archiveService.setSessionMasterCalib(this.session_id, take_id ).subscribe(
      data => {
      },
      err => {this.notificationService.notifyError(`ERROR: Could not change Master Calib (${err.status} ${err.statusText})`);},
      () => {}
    );
  }

  onChangeNeutralTake(take_id) {
    this.archiveService.setSessionNeutralTake(this.session_id, take_id ).subscribe(
      data => {
      },
      err => {this.notificationService.notifyError(`ERROR: Could not change Neutral Take (${err.status} ${err.statusText})`);},
      () => {}
    );
  }

  onChangeFrontalCamera(unique_id) {
    this.archiveService.setSessionFrontalCamera(this.session_id, unique_id ).subscribe(
        data => {
        },
        err => {this.notificationService.notifyError(`ERROR: Could not change Frontal Camera (${err.status} ${err.statusText})`);},
        () => {}
      );
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
      err => { this.notificationService.notifyError(`ERROR: Could not set Take flag (${err.status} ${err.statusText})`); }
    );
  }
  
  toggleTakeSelection(take_id : number) {
    if (this.selected_takes.has(take_id)) {
      this.selected_takes.delete(take_id);
    } else {
      this.selected_takes.add(take_id);
    }
    this.recomputeSelectedSize();
  }

  createTakeThumbnailJob(event : any, take_id : number) {

    event.target.disabled = true;
    event.target.classList.add('btn-destructive');

    this.archiveService.createTakeThumbnailsJob(take_id).subscribe(
        data => {},
        err => { this.notificationService.notifyError(`ERROR: Could not create job (${err.status} ${err.statusText})`); },
        () => {

          setTimeout(() => {
            event.target.disabled = false;
            event.target.classList.remove('btn-destructive');
          }, 500);

        }
      );

  }

  onCancelExport() {
    (<any>$('#exportTakesModal')).removeClass('modal-dialog-container-show');
  }

  exportNextInArray(arr, end_callback, fail_callback) {

    this.exporting_count = arr.length;
    if (this.exporting_count == 0) {
      end_callback();      
      return;
    }

    var this_item = arr.pop();
    
    this.archiveService.exportTakes(this.session_id, [this_item], this.export_location).subscribe(
      data => {
        this.exportNextInArray(arr, end_callback, fail_callback);
      },
      err => {
        fail_callback("ERROR: Something went wrong");
      },
      () => {}
    );
  }

  recomputeSelectedSize() {
    // Create list of all required nodes for this export
    var selected_size = 0;
    if (this.session_data && this.session_data.shots) {
      for (var i = 0, leni = this.session_data.shots.length; i < leni; i++) {
        for (var j = 0, lenj = this.session_data.shots[i].takes.length; j < lenj; j++) {
          if (this.selected_takes.has(this.session_data.shots[i].takes[j].id)) {
            // This take is going to be exported
            console.log(this.session_data.shots[i].takes[j].total_size);
            selected_size = selected_size + this.session_data.shots[i].takes[j].total_size;
          }
        }
      }
    }
    this.selected_size = selected_size;
  }

  onQueueExport() {
      // List of take IDs in this.selected_takes

      var what_we_need_to_export = Array.from(this.selected_takes.values());
      this.error_message = "";
      this.exporting_count = what_we_need_to_export.length;
      this.exportNextInArray(what_we_need_to_export, () => {
        // End Callback
        this.selected_takes.clear(); // clear selection after export is queued
        this.selected_size = 0;
        (<any>$('#exportTakesModal')).removeClass('modal-dialog-container-show');
      }, (msg) => {
        // Fail Callback
        console.log(msg);
        this.error_message = msg;
      });
  }

  onCancelDelete() {
    (<any>$('#deleteTakesModal')).removeClass('modal-dialog-container-show');
  }

  onQueueDelete() {
      // List of take IDs in this.selected_takes

      this.archiveService.deleteTakes(this.session_id, Array.from(this.selected_takes.values())).subscribe(
        data => {
          this.selected_takes.clear(); // clear selection after delete is queued
          this.selected_size = 0;

          (<any>$('#deleteTakesModal')).removeClass('modal-dialog-container-show');
        },
        err => {
          this.notificationService.notifyError(`ERROR: Could not delete takes (${err.status} ${err.statusText})`);
          console.log('TODO removeTakes ERROR'); // Display error message
        },
        () => {}
      );
  }

  onSelectAllFromFlag(flag_name) {
    var selection = []
    if (this.session_data && this.session_data.shots) {
      for (var i = 0, leni = this.session_data.shots.length; i < leni; i++) {
        for (var j = 0, lenj = this.session_data.shots[i].takes.length; j < lenj; j++) {
          if (this.session_data.shots[i].takes[j].flag == flag_name) {
            selection.push( this.session_data.shots[i].takes[j].id);
          }          
        }
      }
    }
    this.selected_takes = new Set(selection);
    this.recomputeSelectedSize();
  }

  onSelectAllTakes() {
    this.selected_takes = new Set(this.all_takes);
    this.recomputeSelectedSize();
  }

  onSelectNoneTakes() {
    this.selected_takes.clear();
    this.selected_size = 0;
  }

  onExportSelected() {

    this.export_missing_nodes = [];

    this.archiveService.getExportLocation().subscribe(
      data => {
          this.export_location = data.path;
        }
    );

    if (this.selected_takes.size > 0) {

      // Create list of all required nodes for this export
      var all_nodes = new Set();
      if (this.session_data && this.session_data.shots) {
        for (var i = 0, leni = this.session_data.shots.length; i < leni; i++) {
          for (var j = 0, lenj = this.session_data.shots[i].takes.length; j < lenj; j++) {
            if (this.selected_takes.has(this.session_data.shots[i].takes[j].id)) {
              // This take is going to be exported
              var cameras = this.session_data.shots[i].takes[j].cameras;
              for (var c = 0, lenc = cameras.length; c < lenc; c++) {
                all_nodes.add(cameras[c].machine_name);
              }
            }
          }
        }
      }

      // Get Current list of Job Clients
      this.archiveService.getFarmNodes().subscribe(
        data => {

          // Remove machines that are currently active
          for (var i = 0, leni = data.results.length; i < leni; i++) {
            if (data.results[i].active) {
              all_nodes.delete(data.results[i].machine_name);
            }
          }

          // all_nodes is now the list of missing nodes
          this.export_missing_nodes = Array.from(all_nodes.values());
        }
      );          
      
      // Display dialog with Export Location (UNC Path) input
      (<any>$('#exportTakesModal')).addClass('modal-dialog-container-show');
    }
  }

  onBestSelected() {
    if (this.selected_takes.size > 0) {

      this.archiveService.setTakesFlag('best', Array.from(this.selected_takes.values())).subscribe(
        data => {
          this.selected_takes.clear(); // clear selection after delete is queued
          this.selected_size = 0;

          (<any>$('#deleteTakesModal')).removeClass('modal-dialog-container-show');
        },
        err => {
          this.notificationService.notifyError(`ERROR: Could not delete takes (${err.status} ${err.statusText})`);
          console.log('TODO removeTakes ERROR'); // Display error message
        },
        () => {}
      );
    }
  }

  onRemoveSelected() {
    if (this.selected_takes.size > 0) {
      // Display dialog with Dete Confirmation
      (<any>$('#deleteTakesModal')).addClass('modal-dialog-container-show');
    }
  }

  trackByString(index: number, name : any) {
    return name;
  }

  trackByShotId(index: number, shot : any) {
    return shot.id;
  }

  trackByTakeId(index: number, take : any) {
    return take.id;
  }

  trackByCameraId(index: number, cam : any) {
    return cam.id;
  }

  ngOnInit(): void {

    // Get Session Dd from URL
    this.route.params.forEach((params: Params) => {

      this.session_id = +params['id']; // (+) converts string 'id' to a number

      this.loading = true;

      this.onSelectNoneTakes();
      this.showCompleteTakes.clear();

      // Main data stream for this session
      this.loader.start(3000, () => { return this.archiveService.getSession(this.session_id); }, (data : any) => {

              this.session_data = data;
              this.loading = false;

              var all_takes = [];
              var all_cameras = new Set();

              if (this.session_data && this.session_data.shots) {
                for (var i = 0, leni = this.session_data.shots.length; i < leni; i++) {
                  for (var j = 0, lenj = this.session_data.shots[i].takes.length; j < lenj; j++) {

                    var take = this.session_data.shots[i].takes[j];
                    var frontal_camera = null;
  
                    all_takes.push(take.id);

                    for (var k = 0, lenk = take.cameras.length; k < lenk; k++) {
                      all_cameras.add(take.cameras[k].unique_id);

                      if (take.cameras[k].unique_id == take.frontal_cam_uid) {
                        frontal_camera = take.cameras[k];
                      }                      
                    }

                    take.frontal_camera = frontal_camera;
                  }
                }
              }

              this.all_takes = all_takes;
              this.all_cam_uid = Array.from(all_cameras.values());

          }, err => {
            this.loading = false;
          },
        'archive_getSession' + this.session_id); // cache key

    });

  }

  ngOnDestroy(): void {
    this.loader.release();
  }
}
