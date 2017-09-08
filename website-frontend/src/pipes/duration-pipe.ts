//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Pipe, PipeTransform } from '@angular/core';

@Pipe({name: 'duration'})
export class DurationPipe implements PipeTransform {
  transform(end_time: any, start_time: any): string {

    if (start_time && end_time) {
      var ds = new Date(start_time);
      var de = new Date(end_time);

      var seconds = (de.getTime() - ds.getTime()) / 1000;
      var days = Math.floor(seconds / 3600 / 24);
      var hours = Math.floor(seconds / 3600);
      var minutes = Math.floor((seconds) / 60);

      if (days > 1) {
        return days + ' days';
      }

      if (hours > 1) {
        return hours + ' hours';
      }

      if (minutes > 1) {
        return minutes + ' minutes';
      }

      return seconds + ' seconds';
    }

    return '';
  }
}
