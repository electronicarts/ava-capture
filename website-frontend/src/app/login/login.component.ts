//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component } from '@angular/core';
import { Router } from '@angular/router';

import { UserService } from '../../services/user.service';
import { ConfigService } from  '../../services/config.service';

@Component({
  selector: '[login]',
  host: {
    class: 'login-page app'
  },
  template: require('./login.html')
})
export class LoginComponent {

  username = '';
  password = '';
  login_failed_message = false;
  support_email = null;

  img_ea_logo = require("../../assets/images/EA_logo_logotype-700x303.png");
  img_seed_logo = require("../../assets/images/Seed_Logo_with_Text.png");

  constructor(private userService: UserService, private router: Router, private config : ConfigService) {
    // Log out when visiting this page
    this.userService.logout();

    this.support_email = config.supportEmail;
  }

  onSubmit(form: any) {

    this.userService.login(this.username, this.password).subscribe(
        result => {

          if (result) {
            // Login OK
            this.login_failed_message = false;
            this.router.navigate(['/app', 'dashboard']);
          } else {
            // Login Failed
            console.log('Login Failed');
            this.login_failed_message = true;
          }
        },
        err => {
            // Login Failed
            console.log('Login Failed');
            this.login_failed_message = true;
        }
    );
  }
}
