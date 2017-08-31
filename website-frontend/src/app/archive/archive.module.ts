//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule }      from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule } from '@angular/router';
import { FormsModule }   from '@angular/forms';

import { ArchivesPage }  from './archive-by-session';
import { ArchiveSessionPage }  from './archive-session';
import { ArchiveProjectsPage }  from './archive-projects';
import { ArchiveByProjectPage }  from './archive-by-project';
import { CreateTrackingPage }  from './create-tracking';

import { ReviewMenuPage } from './review-menu';
import { ReviewProjectPage } from './review-project-select';
import { ReviewSessionPage } from './review-session-select';

import { JobsListModule }  from '../jobs/jobs.module';
import { CommonModule }  from '../common.module';

import { VideoPlaceholder }  from './video-placeholder';
import { FrameTimeDisplay } from './frametime-display';

import { SetFrameDialog }  from './set-frame-dialog';

@NgModule({
  imports:      [ BrowserModule, FormsModule, RouterModule, JobsListModule, CommonModule ],
  declarations: [ ArchivesPage, ArchiveSessionPage, ArchiveByProjectPage, ArchiveProjectsPage, 
                  CreateTrackingPage, VideoPlaceholder, FrameTimeDisplay, 
                  ReviewMenuPage, ReviewProjectPage, ReviewSessionPage, SetFrameDialog ],
  bootstrap:    [ ArchivesPage ]
})
export class ArchivesModule { }
