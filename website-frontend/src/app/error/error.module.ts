//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule }      from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { ErrorComponent }  from './error.component';

@NgModule({
  imports:      [ BrowserModule ],
  declarations: [ ErrorComponent ],
  bootstrap:    [ ErrorComponent ]
})
export class ErrorModule { }
