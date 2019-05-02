//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Injectable } from '@angular/core';
import { BaseRequestOptions } from '@angular/http'

@Injectable()
export class ExRequestOptions extends BaseRequestOptions  {
  constructor() {
    super();
    this.headers.append('X-CSRFToken', this.getCookie('csrftoken'));
  }

  getCookie(name : String) {
    let value = "; " + document.cookie;
    let parts = value.split("; " + name + "=");
    if (parts.length == 2) 
      return parts.pop().split(";").shift();
  }
}
