//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import {Component, ElementRef} from '@angular/core';
import {Router, ActivatedRoute, Params, NavigationEnd} from '@angular/router';

import { ArchiveService } from './capturearchive.service';
import { LoadDataEveryMs } from '../../utils/reloader';

var $ = require("jquery");

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
  selected_takes : number[] = [];
  all_takes : number[] = [];
  export_location = '';
  all_cam_uid : string[] = [];

  el : ElementRef;

  constructor(el: ElementRef, private archiveService: ArchiveService, private route: ActivatedRoute, router: Router) {
    this.el = el;
    this.router = router;
  }

  onChangeFrontalCamera(unique_id) {
    this.archiveService.setSessionFrontalCamera(this.session_id, unique_id ).subscribe(
        data => {
        },
        err => console.error(err),
        () => {}
      );
  }

  toggleBestTake(event, take) {

    var flag_set = event.target.checked;
    this.loader.subscribeDataChange(
      this.archiveService.setTakeFlag(take.id, "best",flag_set ),
      data => {
        // change done, update data
        if (flag_set)
          take.flag = "best";
        else
          take.flag = "none";
      },
      err => console.error(err)
    );
  }

  toggleBadTake(event, take) {
    var flag_set = event.target.checked;
    this.loader.subscribeDataChange(
      this.archiveService.setTakeFlag(take.id, "bad",flag_set ),
      data => {
        // change done, update data
        if (flag_set)
          take.flag = "bad";
        else
          take.flag = "none";
      },
      err => console.error(err)
    );
  }

  toggleTakeSelection(take_id : number) {
    var idx = this.selected_takes.indexOf(take_id);
    if (idx > -1) {
      this.selected_takes.splice(idx, 1);
    } else {
      this.selected_takes.push(take_id);
    }
  }

  createTakeThumbnailJob(event : any, take_id : number) {

    event.target.disabled = true;
    event.target.classList.add('btn-destructive');

    this.archiveService.createTakeThumbnailsJob(take_id).subscribe(
        data => {},
        err => console.error(err),
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

  onQueueExport() {
      // List of take IDs in this.selected_takes

      this.archiveService.exportTakes(this.selected_takes, this.export_location).subscribe(
        data => {
          this.selected_takes = []; // clear selection after export is queued

          (<any>$('#exportTakesModal')).removeClass('modal-dialog-container-show');
        },
        err => {
          console.log('TODO exportTakes ERROR'); // Display error message
        },
        () => {}
      );
  }

  onCancelDelete() {
    (<any>$('#deleteTakesModal')).removeClass('modal-dialog-container-show');
  }

  onQueueDelete() {
      // List of take IDs in this.selected_takes

      this.archiveService.deleteTakes(this.selected_takes).subscribe(
        data => {
          this.selected_takes = []; // clear selection after delete is queued

          (<any>$('#deleteTakesModal')).removeClass('modal-dialog-container-show');
        },
        err => {
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
    this.selected_takes = selection;
  }

  onSelectAllTakes() {
    this.selected_takes = this.all_takes;
  }

  onSelectNoneTakes() {
    this.selected_takes = [];
  }

  onExportSelected() {

    this.archiveService.getExportLocation().subscribe(
      data => {
          this.export_location = data.path;
        },
        err => {
        },
        () => {}
    );

    if (this.selected_takes.length > 0) {
      // Display dialog with Export Location (UNC Path) input
      (<any>$('#exportTakesModal')).addClass('modal-dialog-container-show');
    }
  }

  onRemoveSelected() {
    if (this.selected_takes.length > 0) {
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

        this.loader.start(3000, () => { return this.archiveService.getSession(this.session_id); }, (data : any) => {

                this.session_data = data;

                var all_takes = [];
                var all_cameras = new Set();

                if (this.session_data && this.session_data.shots) {
                  for (var i = 0, leni = this.session_data.shots.length; i < leni; i++) {
                    for (var j = 0, lenj = this.session_data.shots[i].takes.length; j < lenj; j++) {
                      all_takes.push( this.session_data.shots[i].takes[j].id);

                      for (var k = 0, lenk = this.session_data.shots[i].takes[j].cameras.length; k < lenk; k++) {
                        all_cameras.add(this.session_data.shots[i].takes[j].cameras[k].unique_id);
                      }
                    }
                  }
                }

                this.all_takes = all_takes;
                this.all_cam_uid = Array.from(all_cameras.values());

            });

    });

  }

  ngOnDestroy(): void {
    this.loader.release();
  }
}
