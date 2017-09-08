//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';

import { UserService } from "../../../services/user.service";
import { NotificationService } from '../../notifications.service';
import { CaptureService } from '../../capture/capture.service';

import { LoadDataEveryMs } from '../../../utils/reloader';

@Component({
  selector: 'navbar',
  template: require('./navbar.html'),
  providers: [NotificationService, CaptureService]
})
export class NavbarComponent {

  user = {first_name: '', last_name: '', gravatar: '', email: ''};

  seed_white = require("../../../assets/images/Symbol_white.png");

  notif_subscription = null;
  current_notifications = [];

  current_page_index = 0;

  loader = new LoadDataEveryMs();

  constructor(private userService: UserService, private notificationService: NotificationService, private router: Router, private captureService: CaptureService) {
    router.events.subscribe((val) => {
        if (val instanceof NavigationEnd) {
            // Notification each time the route changes, so that we can set our style accordingly
            if (val.urlAfterRedirects === '/app/frontpage')
                this.current_page_index = 1;
            else if (val.urlAfterRedirects.startsWith('/app/capture'))
                this.current_page_index = 2;
            else if (val.urlAfterRedirects.startsWith('/app/review'))
                this.current_page_index = 3;
            else if (val.urlAfterRedirects.startsWith('/app/pipeline'))
                this.current_page_index = 4;
            else if (val.urlAfterRedirects.startsWith('/app/farm'))
                this.current_page_index = 5;
            else 
                this.current_page_index = 0;
        }
    });
  }
  
  test() {
    // Example to send notifications
    this.notificationService.notifyError("TEST asdkas asdkjh");
    this.notificationService.notifyWarning("TEST warning asdkas asdkjh");
    this.notificationService.notifyInfo("TEST info asdkas asdkjh");
  }

  dismissNotif(id: number) {
    this.notificationService.dismissNotification(id);
  }

  trackById(index: number, something : any) {
    return something.id;
  }
  
  loadUserInfo() {

    this.userService.getCurrentUser().subscribe(
        data => {
          this.user = data;
        },
        err => {
          console.error(err)
        },
        () => console.log('done')
      );
  }

  ngOnInit(): void {

    // Get user name from server
    this.loadUserInfo();

    // Subscription to notification service
    this.notif_subscription = this.notificationService.getNotificationStream().subscribe(
        data => {
          this.current_notifications = data;
        }
      );

      // Subscription only to detect if we are logged out
    this.loader.start(15000, () => { return this.captureService.getSystemInformation(); }, data => {
          // NOTE: We are not doing anything at the moment with the data we recieve, this subscription
          // is used only to check if we are still logged in.
        }, err => {

          // Unauthorized access check, we only need to do this at a single location, if we become
          // unauthorized (because the token expired), the error woll be detected here and we will be redirected 
          // to the login page. 

          // There are two ways the JWT can expire, on the frontend (Angular2-jwt) or on the server (Django Rest Jwt returns 401)

          if (err.status === 401 || err.message === 'No JWT present or has expired') { // TODO With new version of angular2-jwt use isinstanceof AuthError
            this.router.navigate(['/login']);
          }

        });      
  }

  ngOnDestroy(): void {
    if (this.notif_subscription) {
      this.notif_subscription.unsubscribe();
      this.notif_subscription = null;
    }

    this.loader.release();
  }

}
