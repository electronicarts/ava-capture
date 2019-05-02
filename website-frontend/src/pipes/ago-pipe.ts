//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Pipe, PipeTransform } from '@angular/core';

@Pipe({name: 'timeago'})
export class TimeAgoPipe implements PipeTransform {
  transform(value: any): string {

    if (value) {
      var ds = new Date(value);
      var de = new Date();

      var seconds = (de.getTime() - ds.getTime()) / 1000;
      var days = Math.floor(seconds / 3600 / 24);
      var hours = Math.floor(seconds / 3600);
      var minutes = Math.floor((seconds) / 60);

      if (days > 1) {
        return days + ' days ago';
      }

      if (hours > 1) {
        return hours + ' hours ago';
      }

      if (minutes > 1) {
        return minutes + ' minutes ago';
      }

      if (seconds > 30) {
        return Math.round(seconds) + ' seconds ago';
      }

      return 'just now';
    }

    return '';
  }
}
