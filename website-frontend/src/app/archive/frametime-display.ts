//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'frametime',
  template: `<span (click)="clickToggle();" *ngIf="showing_time" class="badge badge-pill badge-default">{{time | number:'1.1-1'}}s</span>
             <span (click)="clickToggle();" *ngIf="!showing_time" class="badge badge-pill badge-info">{{time*framerate}}</span>`
})
export class FrameTimeDisplay {

  @Input() time : number;
  @Input() framerate : number = 60;

  showing_time : boolean = true;

  constructor() {
  }

  clickToggle() {
    this.showing_time = !this.showing_time;
  }

}
