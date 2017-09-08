//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'videoplaceholder',
  template: `<div style="display: inline-block; vertical-align:top;">
              <video *ngIf="showing" width="{{width}}" autoplay loop>
               <source src="{{src}}" type="video/mp4">
              </video>
              <div [style.width.px]="width" *ngIf="!showing">
               <button style="width:100%; height:100%;" (click)="clickToShow()" type="button" class="btn btn-default"> 
                <i class="fa fa-play-circle-o" aria-hidden="true"></i>
               </button>
              </div>
             </div>`
})
export class VideoPlaceholder {

  @Input() src : any;
  @Input() width : number = 180;

  showing : boolean = false;

  constructor() {
  }

  clickToShow() {
    this.showing = true;
  }

}
