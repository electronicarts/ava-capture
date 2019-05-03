//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule }      from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule } from '@angular/router';
import { FormsModule }   from '@angular/forms';

import { AssetsByProjectPage }  from './assets-by-project';
import { AssetsProjectsPage } from './../assets/assets-projects';
import { AssetService }  from './assets.service';
import { PipelinePage} from './pipeline';

import { JobsListModule }  from '../jobs/jobs.module';

import { LaunchJobDialog }  from './launch-job-dialog';

import { OnlyBestPipe }  from './assets-by-project';
import { FilterBySessionAndName }  from './assets-by-project';

import { CommonModule }  from '../common.module';

@NgModule({
  imports:      [ BrowserModule, RouterModule, JobsListModule, FormsModule, CommonModule ],
  declarations: [ AssetsByProjectPage, AssetsProjectsPage, LaunchJobDialog, PipelinePage, OnlyBestPipe, FilterBySessionAndName ],
  bootstrap:    [ AssetsByProjectPage ]
})
export class AssetsModule { }
