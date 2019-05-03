//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component } from '@angular/core';
import { Router, ActivatedRoute, Params } from '@angular/router';

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
  returnUrl : string = null;

  use_ldap = true;
  use_oauth2 = process.env.AUTH_URL && process.env.AUTH_CLIENT_ID && process.env.AUTH_REDIRECT_URI;

  img_ea_logo = require("../../assets/images/EA_logo_logotype-700x303.png");
  img_seed_logo = require("../../assets/images/Seed_Logo_with_Text.png");

  btn_google_signin_normal_web = require("../../assets/images/btn_google_signin_dark_normal_web.png");

  constructor(private userService: UserService, private router: Router, private route: ActivatedRoute, private config : ConfigService) {
    this.support_email = config.supportEmail;
  }

  initiateGoogleAuth() {

    if (!this.use_oauth2)
      return;

    this.login_failed_message = false;
    
    const AUTH_STATE_original_url = window.location.href.split('#', 1)
    const AUTH_STATE_redirect_anchor = '/auth';
    const AUTH_STATE_token = '00000000'; // TODO

    var url = process.env.AUTH_URL + '?' +
      'client_id='+process.env.AUTH_CLIENT_ID+'&' +
      'response_type=code&' +
      'scope=openid%20email&' +
      'redirect_uri='+process.env.AUTH_REDIRECT_URI+'&' +
      'state=security_token%3D'+AUTH_STATE_token+'%26url%3D'+AUTH_STATE_original_url+'%26anchor%3D'+AUTH_STATE_redirect_anchor+'&' +
      'nonce=xxxxxxxx-xxxxxxxx-xxxxxxxxx&' +
      'hd=ea.com';

    // Redirect to Authentication Service
    window.location.href = url;
  }

  ngOnInit() {
    // Log out when visiting this page
    this.userService.logout();

    this.route.queryParams.subscribe((params: Params) => {
      this.returnUrl = params['returnUrl'] || '/app/dashboard';
    });
          
  }

  onSubmit(form: any) {

    this.userService.login(this.username, this.password).subscribe(
        result => {

          if (result) {

            // Login OK
            this.login_failed_message = false;
            this.router.navigateByUrl(this.returnUrl);
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
