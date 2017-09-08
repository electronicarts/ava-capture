//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Injectable } from '@angular/core';

@Injectable()
export class LoadDataEveryMs {

  subscription : any = null;
  timer_subscription : any= null;
  pause_count = 0;

  stored_ms = null;
  stored_observable_getter = null;
  stored_data_cb = null;
  stored_err_cb = null;

  constructor() {
  }

  subscribeDataChange(obs : any, next?: (value : any) => void, error?: (error : any) => void, complete?: () => void) {
    this.pause();
    obs.subscribe(next, error, () => {
      if (complete)
        complete();
      this.resume();
    });    
  }

  private pause() {
    this.pause_count++;
    if (this.pause_count==1) {
      this.release();
    }
  }

  private resume() {
    this.pause_count--;
    if (this.pause_count==0) {
      this.start(this.stored_ms, this.stored_observable_getter, this.stored_data_cb, this.stored_err_cb);
    }
  }

  start(ms : number, observable_getter : () => any, data_cb : any, err_cb = err => {}) {

    this.stored_ms = ms;
    this.stored_observable_getter = observable_getter;
    this.stored_data_cb = data_cb;
    this.stored_err_cb = err_cb;

    if (this.pause_count==0) {

      this.release();

      this.subscription = observable_getter().subscribe(
          data => {
            data_cb(data);

            this.timer_subscription = setTimeout(() => {
              this.start(ms, observable_getter, data_cb, err_cb);
            }, ms);
          },
          err => {

            err_cb(err);

            this.timer_subscription = setTimeout(() => {
              this.start(ms, observable_getter, data_cb, err_cb);
            }, ms);

          }
      );

    }
  }

  release() {
    if (this.timer_subscription) {
      clearTimeout(this.timer_subscription);
      this.timer_subscription = null;
    }

    if (this.subscription) {
      this.subscription.unsubscribe();
      this.subscription = null;
    }
  }
}
