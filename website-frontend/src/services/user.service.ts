//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

// user.service.ts
// Service for User Authentication

import { Injectable } from '@angular/core';
import { Http, Headers } from '@angular/http';
import { HttpClient } from '@angular/common/http';
import { Router, NavigationStart } from '@angular/router';
import { JwtHelperService } from '@auth0/angular-jwt';

import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export class UserModel
{
  username: '';
  first_name: '';
  last_name: '';
  gravatar: '';
  email: '';
  id: 0;
}

export class TokenModel
{
  token: '';
}

@Injectable()
export class UserService {
  private loggedIn = false;

  constructor(private http: Http, public authHttp: HttpClient, private router: Router) {
    this.loggedIn = !!localStorage.getItem('auth_token');
  }

  getCurrentUserID() {
    if (this.loggedIn) {
      return localStorage.getItem('last_user_id');
    } else {
      return '';
    }
  }

  getUserListDirect() {
    return this.authHttp.get('/accounts/all_users');
  }

  getCurrentUser() : Observable<UserModel> {
    return this.authHttp.get('/accounts/current_user').pipe(map(data => <UserModel>data));
  }

  refresh_token(current_token : String) {

    if (this.isLoggedIn()) {

      // This is one of the few places we will not be using HttpClient

      let headers = new Headers();
      headers.append('Content-Type', 'application/json');
      headers.append('Accept', 'application/json; indent=4, application/json, application/yaml, text/html, */*');

      return this.http
        .post(
          '/api-token-refresh/',
          JSON.stringify({ token : current_token }),
          { headers }
        )
        .pipe(
          map(res => res.json()),
          map(data => <TokenModel>data),
          map((res) => {
          if (res.token) {
            localStorage.setItem('auth_token', res.token);
            this.loggedIn = true;
            return true;
          } else {
            this.logout();
            return false;
          }
        }));
    }

  }

  refresh_token_if_needed() {

    // This is called when the user performs any action, to refresh the token
    // The token will only expire if the user performes no actions for a long time.
    // This should not be called for automatic page refreshes, only when the user clicks something.

    if (this.isLoggedIn()) {

      var token = localStorage.getItem('auth_token');
      if (token != null) {

        var jwtHelper = new JwtHelperService();
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

  set_token(username, token) {

    localStorage.setItem('auth_token', token);
    localStorage.setItem('last_user_id', username);

    if (!this.isLoggedIn()) {
      console.log('ERROR: Received new JWT token from /api-token-auth but it is already expired. Check server/client time not synchronized.');
      this.logout();
      return false;
    }

    this.loggedIn = true;

    return true;
  }

  login(username : string, password : string) {

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
      .pipe(
        map(res => res.json()),
        map(data => <TokenModel>data),
        map((res) => {
          if (res.token) {
            return this.set_token(username, res.token);
          } else {
            this.logout();
            return false;
          }
        }));
  }

  logout() {

    localStorage.removeItem('auth_token');
    localStorage.removeItem('last_user_id');
    this.loggedIn = false;

    this.http.get('/accounts/logout').subscribe();
  }

  isLoggedIn() {
    const jwtHelper = new JwtHelperService();
    const token = localStorage.getItem('auth_token');    
    return !jwtHelper.isTokenExpired(token);
  }
}

