//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  template: require('./frontpage.html')
})
export class FrontpageComponent {
  
  img_frostbite_logo_black = require("../../assets/images/frostbite_logo_black.png");

  constructor(router: Router) {
  }

}
