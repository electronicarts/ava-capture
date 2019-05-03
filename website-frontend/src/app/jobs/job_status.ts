//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input } from '@angular/core';

@Component({
  selector: 'job_status',
  template: require('./job_status.html')
})
export class JobStatus {

  @Input() status : String;

}
