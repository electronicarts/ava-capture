//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, EventEmitter, ElementRef } from '@angular/core';
import { AssetService } from './assets.service';
import { ColorChartEditor } from './../components/color_chart';
import { NotificationService } from '../notifications.service';

var $ = require("jquery");

@Component({
  selector: 'launch-job-dialog',
  template: require('./launch-job-dialog.html'),
  providers: [ColorChartEditor]
})
export class LaunchJobDialog {

  jobclass : string;
  take_id = 0;
  asset_id = 0;
  tracking_asset_id = 0;
  working = false;
  tags = []
  options = []

  el: ElementRef;

  constructor(el: ElementRef, private assetService: AssetService, private notificationService: NotificationService) {
      this.el = el;
  }

  hideDialog() {
    this.working = false;
    this.jobclass = '';
    this.take_id = 0;
    this.asset_id = 0;
    this.tracking_asset_id = 0;
    this.tags = []; 
    this.options = []; 
    ($(this.el.nativeElement).find('div:first')).removeClass('modal-dialog-container-show');
  }

  show(jobclass : string, options : any[], take_id : number = null, asset_id : number = null, tracking_asset_id : number = null, tags : any[]) {
    this.jobclass = jobclass;
    this.take_id = take_id;
    this.asset_id = asset_id;
    this.tracking_asset_id = tracking_asset_id;
    this.tags = tags;
    this.options = options;

    // Show dialog
    ($(this.el.nativeElement).find('div:first')).addClass('modal-dialog-container-show');
  }

  onCancelLaunchJob() {
    this.hideDialog();
  }

  trackByName(index: number, something : any) {
    return something.name;
  }

  dismissDialog() {
    setTimeout(() => {
      this.hideDialog();
    }, 500);
  }

  onLaunchJob(event) {

    this.working = true;

    // Build parameter string
    var params_dict = {};
    this.options.forEach((element) => {
      params_dict[element.name] = element.value;
    });
    var params_str = JSON.stringify(params_dict);

    // Launch job
    if (this.tracking_asset_id)
    {
      this.assetService.createTrackingAssetJob(this.tracking_asset_id, this.jobclass, params_str, false, null, this.tags).subscribe(
        data => {
          this.dismissDialog();
        },
        err => {
          this.notificationService.notifyError(`ERROR: Could not create ${this.jobclass} (${err.status} ${err.statusText})`);
          this.dismissDialog();
        }
      );
    }
    if (this.asset_id)
    {
      this.assetService.createAssetJob(this.asset_id, this.jobclass, params_str, false, null, this.tags).subscribe(
        data => {
          this.dismissDialog();
        },
        err => {
          this.notificationService.notifyError(`ERROR: Could not create ${this.jobclass} (${err.status} ${err.statusText})`);
          this.dismissDialog();
        }
      );
    }
    if (this.take_id)
    {
      this.assetService.createTakeJob(this.take_id, this.jobclass, params_str, false, null, this.tags).subscribe(
        data => {
          this.dismissDialog();
        },
        err => {
          this.notificationService.notifyError(`ERROR: Could not create ${this.jobclass} (${err.status} ${err.statusText})`);
          this.dismissDialog();
        }
      );
    }
  }
}
