//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule }      from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule, Routes } from '@angular/router';
import { HttpModule, Http } from '@angular/http';

import { AuthModule } from '../auth.module';

import { CoreModule } from './core/core.module';
import { LoginModule } from './login/login.module';
import { ErrorModule } from './error/error.module';

import { LoginComponent } from './login/login.component';
import { ErrorComponent } from './error/error.component';

import { AppComponent }  from './app.component';

import { UserService } from '../services/user.service';
import { ConfigService } from '../services/config.service';
import { LoggedInGuard } from '../utils/logged-in.guard';

const appRoutes: Routes = [
  { path: 'error', component: ErrorComponent},
  { path: 'login', component: LoginComponent},
  {
    path: '',
    redirectTo: '/app/frontpage',
    pathMatch: 'full'
  },
  { path: '**', redirectTo: '/app/frontpage' },
];

@NgModule({
  imports:      [ 
    BrowserModule, 
    HttpModule,
    AuthModule,
    CoreModule,
    LoginModule,
    ErrorModule,
    RouterModule.forRoot(appRoutes, { useHash: true }) ],
  providers: [ UserService, LoggedInGuard, ConfigService ],
  declarations: [ AppComponent ],
  bootstrap:    [ AppComponent ]
})
export class AppModule { }
