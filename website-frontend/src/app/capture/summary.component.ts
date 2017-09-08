//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//


import { Component } from '@angular/core';

@Component({
  selector: 'summary-selector',
  template: require('./summary.html')
})
export class SummaryComponent {

  public visible = false;
  public content = null;

  public show(): void {
    this.visible = true;
  }
  public hide(): void {
    this.visible = false;
    this.content = null;
  }
}
