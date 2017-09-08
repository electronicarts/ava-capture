//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule }      from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule, Routes } from '@angular/router';
import { LoggedInGuard } from '../../utils/logged-in.guard';

import { CoreComponent }  from './core.component';
import { NavbarComponent } from './navbar/navbar.component';
import { SidebarComponent } from './sidebar/sidebar.component';
import { UserlistComponent } from './userlist/userlist.component';

import { FrontpageModule } from '../frontpage/frontpage.module';
import { ArchivesModule } from '../archive/archive.module';
import { AssetsModule } from '../assets/assets.module';
import { CaptureModule } from '../capture/capture.module';
import { JobsModule } from '../jobs/jobs.module';

import { FrontpageComponent } from '../frontpage/frontpage.component';

import { LiveCapturePage } from './../capture/live';
import { CapturePageSelect } from './../capture/capture_select';
import { PipelinePage} from './../assets/pipeline';
import { LightstageControlPage } from './../capture/lightstage_control';
import { FarmNodePage } from './../jobs/farm_node';
import { JobDetailsPage } from './../jobs/job_details';
import { FarmNodesPage } from './../jobs/farm_nodes';
import { JobsRunningPage } from './../jobs/jobs_running';
import { JobsPageSelect } from './../jobs/jobs_page_select';
import { ArchivesPage } from './../archive/archive-by-session';
import { AssetsByProjectPage } from './../assets/assets-by-project';
import { ArchiveByProjectPage } from './../archive/archive-by-project';
import { AssetsProjectsPage } from './../assets/assets-projects';
import { ArchiveSessionPage } from './../archive/archive-session';
import { ArchiveProjectsPage } from './../archive/archive-projects';
import { CreateTrackingPage } from './../archive/create-tracking';
import { ReviewMenuPage } from './../archive/review-menu';
import { ReviewProjectPage } from './../archive/review-project-select';
import { ReviewSessionPage } from './../archive/review-session-select';

const coreRoutes: Routes = [
  {
    path: 'app',
    component: CoreComponent,
    children: [
      { path: 'frontpage', component: FrontpageComponent, canActivate: [LoggedInGuard]},
      { path: 'lightstage-control', component: LightstageControlPage, canActivate: [LoggedInGuard] },
      { path: 'farm-node/:id', component: FarmNodePage, canActivate: [LoggedInGuard] },
      { path: 'job_details/:id', component: JobDetailsPage, canActivate: [LoggedInGuard] },
      { path: 'archive-by-session', component: ArchivesPage, canActivate: [LoggedInGuard] },
      { path: 'archive-projects', component: ArchiveProjectsPage, canActivate: [LoggedInGuard] },      
      { path: 'archive-session/create-tracking/:id', component: CreateTrackingPage, canActivate: [LoggedInGuard] },
      { path: 'assets-projects', component: AssetsProjectsPage, canActivate: [LoggedInGuard] },      
      { path: 'review', component: ReviewMenuPage, canActivate: [LoggedInGuard], children: [
        { path: 'project', component: ReviewProjectPage, canActivate: [LoggedInGuard], children: [
          { path: 'archive-by-project/:id', component: ArchiveByProjectPage, canActivate: [LoggedInGuard] }
        ] },
        { path: 'session', component: ReviewSessionPage, canActivate: [LoggedInGuard], children: [
          { path: 'archive-session/:id', component: ArchiveSessionPage, canActivate: [LoggedInGuard] }
        ] }
      ] },
      { path: 'capture', component: CapturePageSelect, canActivate: [LoggedInGuard], children: [
        { path: 'live-capture/:id', component: LiveCapturePage, canActivate: [LoggedInGuard] },
      ]},
      { path: 'farm', component: JobsPageSelect, canActivate: [LoggedInGuard], children: [
        { path: 'jobs-running', component: JobsRunningPage, canActivate: [LoggedInGuard] },
        { path: 'farm-nodes', component: FarmNodesPage, canActivate: [LoggedInGuard] },
      ]
      },
      { path: 'pipeline', component: PipelinePage, canActivate: [LoggedInGuard], children: [
        { path: 'assets-by-project/:id', component: AssetsByProjectPage, canActivate: [LoggedInGuard] },
      ]},
      { path: 'userlist', component: UserlistComponent, canActivate: [LoggedInGuard] }
    ]
  }
];

@NgModule({
  imports:      [ 
    BrowserModule, 
    FrontpageModule,
    ArchivesModule, AssetsModule, CaptureModule, JobsModule,
    RouterModule.forRoot(coreRoutes) ],
  declarations: [ CoreComponent, NavbarComponent, SidebarComponent, UserlistComponent ],
  bootstrap:    [ CoreComponent ]
})
export class CoreModule { }
