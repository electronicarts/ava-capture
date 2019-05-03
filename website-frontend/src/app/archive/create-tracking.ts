//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {Component, ElementRef} from '@angular/core';
import {Router, ActivatedRoute, Params, NavigationEnd} from '@angular/router';
import {Location} from '@angular/common';

import { ArchiveService } from './capturearchive.service';

var $ = require("jquery");

@Component({
  selector: 'create-tracking',
  template: require('./create-tracking.html'),
  providers: [ArchiveService]
})
export class CreateTrackingPage {

  error_message = null;

  ct_take_id = null;
  ct_take_info : any = null;
  ct_start_time = 0.0;
  ct_start_frame = 0;
  ct_end_time = 0.0;
  ct_end_frame = 0;
  ct_fps = 30;
  ct_duration = 100;

  location = null;
  messages : string = "";

  working = false;

  constructor(el: ElementRef, private archiveService: ArchiveService, private route: ActivatedRoute, router: Router, private _location: Location) {
      this.location = _location;
  }

  trackById(index: number, something : any) {
    return something.id;
  }

  onChangeStartFrame() {

    this.messages = "";

    var video = (<any>document.getElementById('createTrackingAssetModalVideo0'));
    this.ct_duration = (video.duration * this.ct_fps) - 1;

    this.ct_start_time = this.ct_start_frame / this.ct_fps;
    video.currentTime = this.ct_start_time;
  }

  onChangeEndFrame() {

    this.messages = "";

    var video = (<any>document.getElementById('createTrackingAssetModalVideo1'));
    this.ct_duration = (video.duration * this.ct_fps) - 1;

    this.ct_end_time = this.ct_end_frame / this.ct_fps;
    video.currentTime = this.ct_end_time;
  }

  onCancel() {
      this._location.back();
  }

  onCreateTrackingAsset(quit : boolean) {

      this.working = true;

      this.archiveService.createTrackingAsset(this.ct_take_info.id, this.ct_start_time, this.ct_end_time).subscribe(
        data => {
          this.working = false;
          if (quit) {
            this._location.back();
          } else {
            this.messages = "Range created from frame #" + this.ct_start_frame + " to frame #" + this.ct_end_frame + ".";
            this.ct_start_frame = this.ct_end_frame;
            this.onChangeStartFrame()
            this.updateData();
          }          
        },
        err => {
          this.working = false;
          this.error_message = err;
        },
        () => {}
      );

  }

  find_cam(cameras, selected_cam_name) {
    for (var i = 0, leni = cameras.length; i < leni; i++) {
      if (cameras[i].unique_id == selected_cam_name) {
        return cameras[i];
      }
    }
    return null;
  }

  updateData() {
    this.archiveService.getTake(this.ct_take_id).subscribe(
      data => {
          this.ct_take_info = data;

          if (this.ct_take_info.frontal_cam_uid) {
              // search for this camera in the take info, to get fps from frontal camera (used for preview)
              var cam : any = this.find_cam(this.ct_take_info.cameras, this.ct_take_info.frontal_cam_uid);
              if (cam) {
                  this.ct_fps = cam.framerate;
              }
          }

      },
      err => console.error(err),
      () => {}
    );
  }

  ngOnInit(): void {

    // Get Take Id from URL
    this.route.params.forEach((params: Params) => {

        this.ct_take_id = +params['id'];
        this.updateData();
    });

  }

  ngOnDestroy(): void {
  }
}
