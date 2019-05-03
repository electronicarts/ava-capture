//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

// logged-in.guard.ts
// Prevent page access if the user is not logged in

import { Injectable } from '@angular/core';
import { Router, CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { UserService } from '../services/user.service';

@Injectable()
export class LoggedInGuard implements CanActivate {
  constructor(private user: UserService, private router: Router) {}

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    if (this.user.isLoggedIn())
        return true;
    this.router.navigate(['/login'], {queryParams: { returnUrl: state.url}});
    return false;

  }
}
