//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Injectable } from '@angular/core';
import { Headers, Response } from '@angular/http';
import { AuthHttp, tokenNotExpired } from 'angular2-jwt';

import { Observable } from 'rxjs/Rx';

@Injectable()
export class NotificationService {

  notif_next_id : number = 1;
  notifications = [];
    
  constructor(public authHttp: AuthHttp) {
  }

  notifyError(msg : string) {
    this.addNotification("error", msg);
  }
  notifyWarning(msg : string) {
    this.addNotification("warning", msg);
  }
  notifyInfo(msg : string) {
    this.addNotification("info", msg);
  }

  dismissNotification(id: number) {
    // need to remove items in this array without replacing the array, as there will be subscriptions attached to the array
    for(var i = this.notifications.length - 1; i >= 0; i--) {
        if(this.notifications[i].id === id) {
            this.notifications.splice(i, 1);
            return;
        }
    }
  }

  private addNotification(class_name : string, msg : string) {
    var obj = {id:this.notif_next_id, class:class_name, msg:msg};
    this.notifications.push(obj);
    this.notif_next_id++;
  }

  getNotificationStream() {
    return Observable.of(this.notifications);
  }
 
}
