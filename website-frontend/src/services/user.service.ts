//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

// user.service.ts
// Service for User Authentication

import { Injectable } from '@angular/core';
import { Http, Headers, Response } from '@angular/http';
import { Router, NavigationStart } from '@angular/router';
import { AuthHttp, tokenNotExpired, JwtHelper } from 'angular2-jwt';

@Injectable()
export class UserService {
  private loggedIn = false;

  constructor(private http: Http, public authHttp: AuthHttp, private router: Router) {
    this.loggedIn = !!localStorage.getItem('auth_token');

    router.events.subscribe((val) => {

      if (val instanceof NavigationStart) {

        // Every time the route changes, from a user action, check if the JWT Token needs a refresh
        this.refresh_token_if_needed();

      }

    });

  }

  getUserListDirect() {
    return this.authHttp.get('/accounts/all_users').map(res => res.json());
  }

  getCurrentUser() {
    return this.authHttp.get('/accounts/current_user').map(res => res.json());
  }

  refresh_token(current_token : String) {

    if (this.isLoggedIn()) {

      // This is one of the few places we will not be using authHttp

      let headers = new Headers();
      headers.append('Content-Type', 'application/json');
      headers.append('Accept', 'application/json; indent=4, application/json, application/yaml, text/html, */*');

      return this.http
        .post(
          '/api-token-refresh/',
          JSON.stringify({ token : current_token }),
          { headers }
        )
        .map(res => res.json())
        .map((res) => {
          if (res.token) {
            localStorage.setItem('auth_token', res.token);
            this.loggedIn = true;
            return true;
          } else {
            this.logout();
            return false;
          }
        });
    }

  }

  refresh_token_if_needed() {

    // This is called when the user performs any action, to refresh the token
    // The token will only expire if the user performes no actions for a long time.
    // This should not be called for automatic page refreshes, only when the user clicks something.

    if (this.isLoggedIn()) {

      var token = localStorage.getItem('auth_token');
      if (token != null) {

        var jwtHelper = new JwtHelper();
        var secondsOffset = 3600 / 2; // Number of seconds until the Token will expire

        if (jwtHelper.isTokenExpired(token, secondsOffset)) {

          // Token will expire in less than secondsOffset seconds, refresh

          this.refresh_token(token).subscribe(
            result => {},
            err => {}
          );

        }
      }

    }

  }

  login(username : String, password : String) {

    // This is one of the few places we will not be using authHttp

    let headers = new Headers();
    headers.append('Content-Type', 'application/json');
    headers.append('Accept', 'application/json; indent=4, application/json, application/yaml, text/html, */*');

    return this.http
      .post(
        '/api-token-auth/',
        JSON.stringify({ username, password }),
        { headers }
      )
      .map(res => res.json())
      .map((res) => {
        if (res.token) {
          localStorage.setItem('auth_token', res.token);
          this.loggedIn = true;
          return true;
        } else {
          this.logout();
          return false;
        }
      });
  }

  logout() {
    this.http.get('/accounts/logout').subscribe();

    localStorage.removeItem('auth_token');
    this.loggedIn = false;
  }

  isLoggedIn() {
    return tokenNotExpired('auth_token'); // JWT
  }
}

