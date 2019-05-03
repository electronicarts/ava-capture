//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule }      from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule } from '@angular/router';
import { FormsModule }   from '@angular/forms';

import { FarmNodesPage, FarmNodesItem }  from './farm_nodes';
import { FarmNodePage }  from './farm_node';
import { JobDetailsPage }  from './job_details';
import { JobsPageSelect }  from './jobs_page_select';
import { JobsRunningPage }  from './jobs_running';
import { JobOutputPage, JobOutputComponent }  from './job_output';
import { JobStatus }  from './job_status';
import { JobLabel, JobLabelList }  from './job_mini';
import { JobInfoPanel }  from './job_infopanel';
import { JobBlock }  from './job_block';

import { SearchPipe }  from './pipes/search-pipe';
import { OnlyActivePipe }  from './farm_nodes';

import { CommonModule }  from '../common.module';

@NgModule({
  imports:      [ BrowserModule, RouterModule, CommonModule ],
  declarations: [ JobLabel, JobLabelList, JobStatus, JobBlock, JobInfoPanel, JobDetailsPage ],
  exports:      [ JobLabel, JobLabelList, JobStatus, JobBlock, JobInfoPanel, JobDetailsPage ],
  bootstrap:    [ ]
})
export class JobsListModule { }

@NgModule({
  imports:      [ BrowserModule, RouterModule, FormsModule, JobsListModule, CommonModule ],
  declarations: [ FarmNodesPage, FarmNodesItem, FarmNodePage, JobsRunningPage, JobOutputPage, JobOutputComponent, JobsPageSelect, SearchPipe, OnlyActivePipe ],
  bootstrap:    [ FarmNodesPage ]
})
export class JobsModule { }

