//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Pipe, PipeTransform } from '@angular/core';

@Pipe({name: 'duration'})
export class DurationPipe implements PipeTransform {

  duration_string(ds, de): string {
    var seconds = (de.getTime() - ds.getTime()) / 1000;
    var days = Math.floor(seconds / 3600 / 24);
    var hours = Math.floor(seconds / 3600);
    var minutes = Math.floor((seconds) / 60);

    if (days > 1) {
      return days + ' days';
    }

    if (hours > 1) {
      var rmin = Math.round(minutes - (hours * 60));
      return hours + ' hours ' + rmin + ' minutes';
    }

    if (minutes > 1) {
      var rsec = Math.round(seconds - (minutes * 60));
      return minutes + ' minutes ' + rsec + ' seconds';
    }

    return Math.round(seconds) + ' seconds';
  }

  transform(end_time: any, start_time: any): string {

    if (end_time && !start_time) {
      // No second time specified, use current time
      var ds = new Date(end_time);
      var de = new Date();
      return this.duration_string(ds, de);
    }

    if (start_time && end_time) {
      // Two times specified
      var ds = new Date(start_time);
      var de = new Date(end_time);
      return this.duration_string(ds, de);
    }

    return '';
  }
}
