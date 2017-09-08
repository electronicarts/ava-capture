//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: '[core]',
  template: require('./core.html')
})
export class CoreComponent {
  
  constructor(router: Router) {
  }

}
