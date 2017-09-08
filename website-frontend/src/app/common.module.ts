//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule }      from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { DataSizePipe }  from '../pipes/data-size.pipe';
import { DurationPipe } from '../pipes/duration-pipe';
import { TimeAgoPipe } from '../pipes/ago-pipe';
import { ContainsPipe } from '../pipes/contains-pipe';
import { MapToIterable } from '../pipes/mapToIterable';

import { RotateImage } from './components/rotate-image';

@NgModule({
  imports:      [ BrowserModule ],
  declarations: [ DataSizePipe, DurationPipe, TimeAgoPipe, ContainsPipe, RotateImage, MapToIterable ],
  exports:      [ DataSizePipe, DurationPipe, TimeAgoPipe, ContainsPipe, RotateImage, MapToIterable ]
})
export class CommonModule { }
