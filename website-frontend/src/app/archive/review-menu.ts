//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {Component, ViewEncapsulation} from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';

import { CaptureService } from '../capture/capture.service';

@Component({
  selector: 'review_menu_page',
  template: `
    <div class="section_select">
        <ul>
            <li>
                <a [class.selected]="current_page_index==1" [routerLink]=" ['/app/review/project'] ">Project Overview</a>                
            </li>
            <li>
                <a [class.selected]="current_page_index==2" [routerLink]=" ['/app/review/session'] ">Session Details</a>
            </li>
        </ul>
    </div>

    <router-outlet></router-outlet>
  `,
  encapsulation: ViewEncapsulation.None,
  providers: [CaptureService]
})
export class ReviewMenuPage {

  current_page_index = 0;
  
  constructor(private router: Router, private captureService: CaptureService) {
    router.events.subscribe((val) => {
        if (val instanceof NavigationEnd) {
            // Notification each time the route changes, so that we can set our style accordingly
            if (val.urlAfterRedirects.startsWith('/app/review/project'))
                this.current_page_index = 1;
            else if (val.urlAfterRedirects.startsWith('/app/review/session'))
                this.current_page_index = 2;
            else 
                this.current_page_index = 0;
        }
    });
  }

}
