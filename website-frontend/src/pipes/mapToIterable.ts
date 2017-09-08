//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

// http://stackoverflow.com/questions/31490713/iterate-over-typescript-dictionary-in-angular-2

import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'mapToIterable'
})
export class MapToIterable {
  transform(dict: Object): Array<any> {
    var a = [];
    for (var key in dict) {
      if (dict.hasOwnProperty(key)) {
        a.push({key: key, val: dict[key]});
      }
    }
    return a;
  }
}

