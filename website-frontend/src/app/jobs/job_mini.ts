//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, EventEmitter } from '@angular/core';
import {Router, NavigationEnd} from '@angular/router';

@Component({
  selector: 'job_label',
  template: require('./job_mini.html')
})
export class JobLabel {

  @Input() job : any;

  show_image : boolean = false;

  toggleImage() {
    this.show_image = !this.show_image;
  }

}

@Component({
  selector: 'job_label_list',
  template: require('./job_mini_list.html')
})
export class JobLabelList {

  @Input() jobs : any;

  trackById(job : any) {
    return job.id;
  }

}
