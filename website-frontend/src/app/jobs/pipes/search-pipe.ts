//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {Pipe, PipeTransform} from '@angular/core';

@Pipe({
  name: 'SearchPipe'
})

export class SearchPipe implements PipeTransform {

  transform(value, args?): Array<any> {
    let searchText = new RegExp(args, 'ig');
    if (value) {
      return value.filter(farmnode => {
        if (farmnode.machine_name) {
          return farmnode.machine_name.search(searchText) !== -1;
        }
      });
    }
  }
}
