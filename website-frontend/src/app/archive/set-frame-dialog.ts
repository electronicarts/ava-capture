//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, EventEmitter, ElementRef } from '@angular/core';
import { ArchiveService } from './capturearchive.service';

var $ = require("jquery");

@Component({
  selector: 'set-frame-dialog',
  template: require('./set-frame-dialog.html')
})
export class SetFrameDialog {

  asset_type : string = null;
  asset_data : any = null;
  take_data : any = null;
  frame_name : string;
  frame_key : string;
  frame_time : number;
  frame_frame : number;
  fps : number = 30;
  duration_frame : number = 1000.0;

  el: ElementRef;

  constructor(el: ElementRef, private archiveService: ArchiveService) {
      this.el = el;
  }

  videoLoaded() {
    var video = (<any>document.getElementById('setFrameVideo0'));
    if (video) {
      this.duration_frame = (video.duration * this.fps) - 1;     
    }
  }

  find_cam(cameras, selected_cam_name) {
    for (var i = 0, leni = cameras.length; i < leni; i++) {
      if (cameras[i].unique_id == selected_cam_name) {
        return cameras[i];
      }
    }
    return null;
  }

  onChangeFrame() {
    var video = (<any>document.getElementById('setFrameVideo0'));
    if (video) {     
      this.frame_time = this.frame_frame / this.fps;
      // In Chrome, this will only work if the webserver supports "206 Partial Content"
      video.currentTime = this.frame_time;
    }   
  }
  
  show(asset_type : string, asset: any, frame_name : string, frame_key: string, frame_time : number) {
    this.asset_type = asset_type;
    this.asset_data = asset;
    this.frame_name = frame_name;
    this.frame_key = frame_key;
    this.frame_time = frame_time;
    this.take_data = null;
    this.frame_frame = frame_time * this.fps;

    // Show dialog
    ($(this.el.nativeElement).find('div:first')).addClass('modal-dialog-container-show');
  
    this.archiveService.getTake(this.asset_data.take_id).subscribe(
      data => {
          this.take_data = data;

          if (this.take_data.frontal_cam_uid) {
              // search for this camera in the take info, to get fps from frontal camera (used for preview)
              var cam : any = this.find_cam(this.take_data.cameras, this.take_data.frontal_cam_uid);
              if (cam) {
                  this.fps = cam.framerate;
                  this.frame_frame = frame_time * this.fps;
              }
          }
      },
      err => console.error(err),
      () => {}
  );
}

  onCancel() {
    // Hide dialog
    ($(this.el.nativeElement).find('div:first')).removeClass('modal-dialog-container-show');
  }

  onClear(event) {
    // Clear the value (set to Null in database)

    event.target.disabled = true;

    if (this.asset_type == 'scan') {

      this.archiveService.setStaticAssetFrame(this.asset_data.id, this.frame_key, null).subscribe(
        data => {},
        err => console.error(err),
        () => {

          setTimeout(() => {

            event.target.disabled = false;

            ($(this.el.nativeElement).find('div:first')).removeClass('modal-dialog-container-show');

          }, 500);

        }
      );
      
    }
    if (this.asset_type == 'tracking') {
      
      this.archiveService.setTrackingAssetFrame(this.asset_data.id, this.frame_key, null).subscribe(
        data => {},
        err => console.error(err),
        () => {

          setTimeout(() => {

            event.target.disabled = false;

            ($(this.el.nativeElement).find('div:first')).removeClass('modal-dialog-container-show');

          }, 500);

        }
      );

    }

  }

  onSetFrame(event) {

    event.target.disabled = true;
    event.target.classList.add('btn-destructive');

    if (this.asset_type == 'scan') {

      this.archiveService.setStaticAssetFrame(this.asset_data.id, this.frame_key, this.frame_time).subscribe(
        data => {},
        err => console.error(err),
        () => {

          // Also launch thumbnails job in bg
          this.archiveService.createScanAssetThumbnailsJob(this.asset_data.id, this.frame_key).subscribe(data=>{});

          setTimeout(() => {

            event.target.disabled = false;
            event.target.classList.remove('btn-destructive');

            ($(this.el.nativeElement).find('div:first')).removeClass('modal-dialog-container-show');

          }, 500);

        }
      );

    }      
    if (this.asset_type == 'tracking') {

      this.archiveService.setTrackingAssetFrame(this.asset_data.id, this.frame_key, this.frame_time).subscribe(
        data => {},
        err => console.error(err),
        () => {

          // Also launch thumbnails job in bg
          this.archiveService.createTrackingAssetThumbnailsJob(this.asset_data.id, this.frame_key).subscribe(data=>{});

          setTimeout(() => {

            event.target.disabled = false;
            event.target.classList.remove('btn-destructive');

            ($(this.el.nativeElement).find('div:first')).removeClass('modal-dialog-container-show');

          }, 500);

        }
      );

    }      
    
  }

}
