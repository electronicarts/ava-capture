//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Pipe, PipeTransform } from '@angular/core';

@Pipe({name: 'contains'})
export class ContainsPipe implements PipeTransform {
  transform(collection: any, value: any): boolean {
    return collection.includes(value);
  }
}
