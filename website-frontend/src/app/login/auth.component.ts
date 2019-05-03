//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component } from '@angular/core';
import { Router, ActivatedRoute, Params } from '@angular/router';
import { UserService } from '../../services/user.service';

@Component({
  selector: '[auth]',
  template: `Authentication`,
  providers: [UserService]
})
export class AuthComponent {

   constructor(private activatedRoute: ActivatedRoute, private userService: UserService, private router: Router) {
   }

  ngOnInit() {

    this.activatedRoute.queryParams.subscribe(params => {
        
        // Use the JWT token we recieved
        
        const token = params['token'];
        const userid = params['userid'];

        localStorage.setItem('auth_token', token);
        localStorage.setItem('last_user_id', userid);

        if (this.userService.set_token(userid, token)) {
            this.router.navigateByUrl('/app/dashboard');
        } else {
            // Error with token
            console.log('Token Failure');
            this.userService.logout();
        }
        
      });
    }         
  }
