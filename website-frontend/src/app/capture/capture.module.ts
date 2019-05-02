//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule }      from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule } from '@angular/router';
import { FormsModule }   from '@angular/forms';

import { CommonModule }  from '../common.module';

import { LiveCapturePage }  from './live';
import { LightstageControlPage } from './lightstage_control';
import { ImageZoomComponent }  from './imagezoom.component';
import { SessionNameComponent }  from './sessionname.component';
import { TimerDisplayComponent }  from './timer-display.component';
import { ZoomViewComponent }  from './zoomview.component';
import { CameraParameterValueComponent }  from './cameraparameter.component';
import { SummaryComponent, SortBy }  from './summary.component';
import { CapturePageSelect } from './../capture/capture_select';

@NgModule({
  imports:      [ BrowserModule, RouterModule, FormsModule, CommonModule ],
  declarations: [ LiveCapturePage, LightstageControlPage, ImageZoomComponent, SessionNameComponent, 
    TimerDisplayComponent, ZoomViewComponent, CameraParameterValueComponent, SummaryComponent, SortBy, CapturePageSelect ],
  bootstrap:    [ LiveCapturePage ]
})
export class CaptureModule { }
