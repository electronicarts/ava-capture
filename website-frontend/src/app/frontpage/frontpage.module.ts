//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule }      from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule } from '@angular/router';

import { FrontpageComponent, OnlyActivePipe }  from './frontpage.component';

import { CommonModule }  from '../common.module';

import { JobsListModule }  from '../jobs/jobs.module';

@NgModule({
  imports:      [ BrowserModule, RouterModule, CommonModule, JobsListModule ],
  declarations: [ FrontpageComponent, OnlyActivePipe ],
  bootstrap:    [ FrontpageComponent ]
})
export class FrontpageModule { }
