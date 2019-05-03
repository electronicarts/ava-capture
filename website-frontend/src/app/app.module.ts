//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule, ErrorHandler } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule, Routes, Router, NavigationStart, NavigationEnd } from '@angular/router';

import { JwtModule } from '@auth0/angular-jwt';

import { HttpModule } from '@angular/http';
import { HttpClientModule } from '@angular/common/http';

import { CoreModule } from './core/core.module';
import { LoginModule } from './login/login.module';
import { ErrorModule } from './error/error.module';

import { LoginComponent } from './login/login.component';
import { AuthComponent } from './login/auth.component';
import { ErrorComponent } from './error/error.component';

import { AppComponent }  from './app.component';

import { UserService } from '../services/user.service';
import { ConfigService } from '../services/config.service';
import { LoggedInGuard } from '../utils/logged-in.guard';

import { NotificationService } from './notifications.service';

export function tokenGetter() {
  return localStorage.getItem('auth_token');
}

const appRoutes: Routes = [
  { path: 'error', component: ErrorComponent},
  { path: 'login', component: LoginComponent},
  { path: 'auth', component: AuthComponent},
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
    CoreModule,
    LoginModule,
    ErrorModule,
    RouterModule.forRoot(appRoutes, { useHash: true }),
    HttpClientModule,
    JwtModule.forRoot({
      config: {
        tokenGetter: tokenGetter,
        headerName: 'Authorization',
        authScheme: 'JWT '
        //,
        //whitelistedDomains: ['localhost:3001'],
        //blacklistedRoutes: [/.*\/accounts\/logout/]
      }
    }) ],
  providers: [ NotificationService, UserService, LoggedInGuard, ConfigService ],
  declarations: [ AppComponent ],
  bootstrap:    [ AppComponent ]
})
export class AppModule { 

  constructor(private router: Router, private userService : UserService) {

    router.events.subscribe((val) => {

      if (val instanceof NavigationStart) {

        // /login is the only url outside of our authentication, do not refresh the token if we go there, in fact, 
        // logout() will be called in the constructor of /login
        if (val.url != '/login') {

          // Every time the route changes, from a user action, check if the JWT Token needs a refresh
          userService.refresh_token_if_needed();        
        }

      }

    });

  }

}
