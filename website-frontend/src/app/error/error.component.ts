//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: '[error]',
  host: {
    class: 'error-page app'
  },
  template: require('./error.html')
})
export class ErrorComponent {
router: Router;

  constructor(router: Router) {
    this.router = router;
  }

  searchResult(): void {
    this.router.navigate(['/app', 'dashboard']);
  }

}
