//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule }      from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule } from '@angular/router';
import { FormsModule }   from '@angular/forms';

import { FarmNodesPage }  from './farm_nodes';
import { FarmNodePage }  from './farm_node';
import { JobDetailsPage }  from './job_details';
import { JobsPageSelect }  from './jobs_page_select';
import { JobsRunningPage }  from './jobs_running';
import { JobStatus }  from './job_status';
import { JobLabel, JobLabelList }  from './job_mini';
import { JobBlock }  from './job_block';

import { SearchPipe }  from './pipes/search-pipe';

import { CommonModule }  from '../common.module';

@NgModule({
  imports:      [ BrowserModule, RouterModule ],
  declarations: [ JobLabel, JobLabelList ],
  exports:      [ JobLabel, JobLabelList ],
  bootstrap:    [ ]
})
export class JobsListModule { }

@NgModule({
  imports:      [ BrowserModule, RouterModule, FormsModule, JobsListModule, CommonModule ],
  declarations: [ FarmNodesPage, FarmNodePage, JobsRunningPage, JobsPageSelect, JobDetailsPage, JobStatus, JobBlock, SearchPipe ],
  bootstrap:    [ FarmNodesPage ]
})
export class JobsModule { }

