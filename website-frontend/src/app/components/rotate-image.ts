//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, ElementRef, EventEmitter } from '@angular/core';

@Component({
  selector: 'rotate_img',
  template: `<div style="white-space: nowrap; display: inline-block;" [style.height.px]="_divHeight">
              <div *ngIf="angle==90 || angle==270" style="display: inline-block; vertical-align: middle; width:1px;" [style.height.px]="width"></div>
              <img 
               style="vertical-align:middle;"
               (load)="newImageLoaded()"
               (click)="imgclick($event)"
               [width]="width" 
               [src]="src"
               [class.rotate-90]="angle==90"
               [class.rotate-180]="angle==180"
               [class.rotate-270]="angle==270">
             </div>`
})
export class RotateImage {

  @Input() src : any;
  @Input() width : any = null;
  @Input() angle : number = 0;
  @Output() click = new EventEmitter<any>();

  private _divHeight:number = null;

  divHeight():number {
    var imgElems = this.el.nativeElement.getElementsByTagName('img');
    if (imgElems.length > 0) {
      var img = imgElems[0];
      if (img) {
        if (img.naturalWidth>0) {
          var naturalWidth = this.width ? this.width : img.naturalWidth;
          var naturalHeight = this.width ? (this.width * img.naturalHeight / img.naturalWidth) : img.naturalHeight;
          if (this.angle==90 || this.angle==270)
            return naturalWidth;
          return naturalHeight;
        }
      }
    }
    return null;
  }

  el : ElementRef;

  constructor(el: ElementRef) {
    this.el = el;
  }  

  imgclick(event : any) {
    this.click.emit(event);
  }

  updateDimensions(): void {
    this._divHeight = this.divHeight();
  }

  newImageLoaded(): void {
    this.updateDimensions();
  }

  ngOnInit(): void {
    this.updateDimensions();
  }

  ngOnChanges() {
    this.updateDimensions();
  }
}
