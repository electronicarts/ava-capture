//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule } from '@angular/core';
import { Http, RequestOptions } from '@angular/http';
import { AuthHttp, AuthConfig } from 'angular2-jwt';

export function authHttpServiceFactory(http: Http, options: RequestOptions) {
  return new AuthHttp(new AuthConfig({
       headerName: 'Authorization',
       headerPrefix: 'JWT',
       tokenName: 'auth_token',
       globalHeaders: [
         {'Content-Type': 'application/json'},
         {'Accept': 'application/json; indent=4, application/json, application/yaml, text/html, */*'}],
       noJwtError: false,
       noTokenScheme: false
     }), http, options);
}

@NgModule({
  providers: [
    {
      provide: AuthHttp,
      useFactory: authHttpServiceFactory,
      deps: [Http, RequestOptions]
    }
  ]
})
export class AuthModule {}
