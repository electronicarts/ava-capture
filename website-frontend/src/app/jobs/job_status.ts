//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input } from '@angular/core';

@Component({
  selector: 'job_status',
  template: require('./job_status.html')
})
export class JobStatus {

  @Input() status : String;

}
