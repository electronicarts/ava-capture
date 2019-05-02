//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, OnInit } from '@angular/core';
import { Router, NavigationEnd} from '@angular/router';
import { Location } from '@angular/common';

import { UserService, UserModel } from '../../../services/user.service';
import { CaptureService } from '../../capture/capture.service';

import { LoadDataEveryMs } from '../../../utils/reloader';

var $ = require("jquery");

@Component({
  selector: 'sidebar',
  template: require('./sidebar.html'),
  providers: [UserService, CaptureService]
})
export class SidebarComponent {

  router: Router;
  location: Location;
  user : UserModel = new UserModel();;

  capture_locations = [];
  nb_running_jobs = 0;
  nb_queued_jobs = 0;
  nb_farmnodes_active = 0;

  img_lightstage = require("../../../assets/images/lightstage.png");

  loader = new LoadDataEveryMs();

  constructor(router: Router, location: Location, private userService: UserService, private captureService: CaptureService) {
    this.router = router;
    this.location = location;
  }

  loadActiveCameraCount() {

    this.loader.start(3000, () => { return this.captureService.getSystemInformation(); }, data => {
          this.capture_locations = data.locations;
          this.nb_running_jobs = data.nb_running_jobs;
          this.nb_queued_jobs = data.nb_queued_jobs;
          this.nb_farmnodes_active = data.nb_farmnodes_active;
        }, err => {

          // Unauthorized access check, we only need to do this at a single location, if we become
          // unauthorized (because the token expired), the error woll be detected here and we will be redirected 
          // to the login page. 

          // There are two ways the JWT can expire, on the frontend (Angular2-jwt) or on the server (Django Rest Jwt returns 401)

          if (err.status === 401 || err.message === 'No JWT present or has expired') { // TODO With new version of angular2-jwt use isinstanceof AuthError
            this.router.navigate(['/login'], {queryParams: { returnUrl: this.router.url}});
          }

        });
  }

  loadUserInfo() {
    this.userService.getCurrentUser().subscribe(
        data => {

        this.user = data;

        },
        err => console.error(err),
        () => console.log('loadUserInfo done')
      );
  }

  trackByLocId(index: number, loc) {
    return loc.id;
  }

  ngOnInit(): void {

    // Get user name from server
    this.loadUserInfo();
    this.loadActiveCameraCount();
  }

  ngOnDestroy(): void {

    this.loader.release();

  }
}
