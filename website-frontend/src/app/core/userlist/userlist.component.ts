//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, OnInit } from '@angular/core';
import { UserService } from '../../../services/user.service';
import { LoadDataEveryMs } from '../../../utils/reloader';

@Component({
  selector: 'userlist',
  template: require('./userlist.html'),
  providers: [UserService]
})
export class UserlistComponent {

  loader = new LoadDataEveryMs();
  users = null;

  constructor(private userService: UserService) {
  }

  loadUserList() {

    this.loader.start(5000, () => { return this.userService.getUserListDirect(); }, data => {
          this.users = data;
        });
  }

   trackById(index: number, user) {
     return user.id;
   }

  ngOnInit(): void {

    this.loadUserList();
  }

  ngOnDestroy(): void {

    this.loader.release();

  }
}
