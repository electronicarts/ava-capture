//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, ViewChild } from '@angular/core';

import { CaptureService } from './capture.service';
import { ImageZoomComponent } from './imagezoom.component';

@Component({
  selector: 'zoomview-selector',
  template: require('./zoomview.html'),
  providers: [CaptureService]
})
export class ZoomViewComponent {

  @ViewChild(ImageZoomComponent)
  public imagezoom : ImageZoomComponent;

  constructor(private captureService: CaptureService) {
  }

  public camera_id = 0;
  public cam_model : string = '';
  public cam_unique_id : string = '';
  public cam_version : string = '';
  public cam_ip : string = '';
  public cam_rotation : number = 0;

  counter = 0;
  visible = false;

  loadCameraData() {

    if (this.imagezoom) {
      this.counter++;

      var url = 'http://'+this.cam_ip+':8080/camera/'+this.cam_unique_id+'/large_preview/' + this.counter;

      this.imagezoom.setImageSrc(url, this.cam_rotation, () => {
        if (this.visible) {
          setTimeout(() => {
            this.loadCameraData();
          }, 30);
        }
      });
    } else {
      setTimeout(() => {
        this.loadCameraData();
      }, 50);
    }
  }

  setROI(values : number[]) {
    this.captureService.setCameraROI(this.camera_id, values).subscribe(
        data => { },
        err => console.error(err),
        () => {}
      );
  }

  resetROI() {
    this.captureService.resetCameraROI(this.camera_id).subscribe(
        data => { },
        err => console.error(err),
        () => {}
      );
  }

  public show(camera): void {

    this.camera_id = camera.id;
    this.cam_model = camera.model;
    this.cam_unique_id = camera.unique_id;
    this.cam_version = camera.version;
    this.cam_ip = camera.ip_address;
    this.cam_rotation = camera.rotation;

    if (this.imagezoom)
      this.imagezoom.resetView();
    this.loadCameraData();

    this.visible = true;
  }
  public hide(): void {

    if (this.imagezoom)
      this.imagezoom.clear();

    this.visible = false;
    this.camera_id = 0;
  }

  ngOnInit(): void {
  }

  ngOnDestroy(): void {
    this.hide();
  }

}
