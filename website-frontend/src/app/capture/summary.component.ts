//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//


import { Component, Input } from '@angular/core';
import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'SortBy'
})
export class SortBy implements PipeTransform {
  transform(values, key): Array<any> {
    var res = values;
    return res.sort(function(a, b) {
      return a[key].toLowerCase().localeCompare(b[key].toLowerCase());
    });  
  }
}

@Component({
  selector: 'summary-selector',
  template: require('./summary.html')
})
export class SummaryComponent {

  @Input() content : any = null;

  getBgColor(delta, fps) {
    if (delta > 1.0/fps*1.05 || delta < 1.0/fps*0.95) { // if more than 5% difference
      return '#692828';
    } else if  (delta > 1.0/fps*1.01 || delta < 1.0/fps*0.99) { // between 1% and 5R
      return '#4d4d19';
    } else {
      return '#1e451e';
    }    
  }
  
}
