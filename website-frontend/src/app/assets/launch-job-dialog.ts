//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, EventEmitter, ElementRef } from '@angular/core';
import { AssetService } from './assets.service';

var $ = require("jquery");

@Component({
  selector: 'launch-job-dialog',
  template: require('./launch-job-dialog.html')
})
export class LaunchJobDialog {

  jobclass : string;
  use_gpu : boolean = true;
  asset_id = 0;
  params_to_show = []

  params = {resolution:4096, meshfile:"", color_matrix:""};

  el: ElementRef;

  constructor(el: ElementRef, private assetService: AssetService) {
      this.el = el;
  }

  show(asset_id : number, jobclass : string) {
    this.jobclass = jobclass;
    this.asset_id = asset_id;
    this.params.resolution = 4096;
    this.params.meshfile = '';
    this.params.color_matrix = '';
    this.use_gpu = true;

    // Choose parameters to show depending on the job_class
    this.params_to_show = [];
    if (this.jobclass == 'jobs.lightstage.Geometry')
      this.params_to_show = ['resolution', 'meshfile'];
    if (this.jobclass == 'jobs.lightstage.Textures')
      this.params_to_show = ['resolution', 'color_matrix'];

    // Show dialog
    ($(this.el.nativeElement).find('div:first')).addClass('modal-dialog-container-show');
  }

  onCancelLaunchJob() {
    ($(this.el.nativeElement).find('div:first')).removeClass('modal-dialog-container-show');
  }

  onLaunchJob(event) {

    event.target.disabled = true;
    event.target.classList.add('btn-destructive');

    var params_str = JSON.stringify(this.params);

    this.assetService.createAssetJob(this.asset_id, this.jobclass, params_str, this.use_gpu).subscribe(
        data => {},
        err => console.error(err),
        () => {

          setTimeout(() => {

            event.target.disabled = false;
            event.target.classList.remove('btn-destructive');

            ($(this.el.nativeElement).find('div:first')).removeClass('modal-dialog-container-show');

          }, 500);

        }
      );
    
  }

}
