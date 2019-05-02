//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, EventEmitter } from '@angular/core';
import { ActivatedRoute, Params } from '@angular/router';

import { JobsService } from './jobs.service';
import { LoadDataEveryMs } from '../../utils/reloader';

declare var jQuery: any;

@Component({
    selector: 'job_output',
    template: `
      <div class="console_output">
      <span id="console_output_div"></span>
      <div style="padding: 6px; font-size: 1.5rem;" *ngIf="status=='running'"><i class="fa fa-spinner fa-pulse fa-fw"></i></div>
      </div>
    `,
    providers: [JobsService]
  })
  export class JobOutputComponent {
    @Input() job_id : number;
    @Output() onContentAdded = new EventEmitter<void>();
    @Output() onBeforeContentAdded = new EventEmitter<void>();

    loader = new LoadDataEveryMs();
    offset : number = 0;
    status : string = "";

    constructor(private jobsService: JobsService) {
    }

    // TODO Call clear() if job_id changes

    clear() {
      jQuery('#console_output_div').empty();
      this.offset = 0;
    }

    ngOnInit(): void {

        this.loader.start(1000, () => { return this.jobsService.getFarmJobOutput(this.job_id, this.offset); }, data => {
          this.status = data.status;
          if (data.length>0) {
            this.offset += data.length;
            this.onBeforeContentAdded.emit();
            jQuery('#console_output_div').append(data.content);
            this.onContentAdded.emit();
          }
        }, err=>{
          this.status = "error";
        },);

    }

    ngOnDestroy(): void {
        this.loader.release();
    }

}

@Component({
  selector: 'job_output_page',
  template: `
    <div>Output of Job #{{job_id}}</div>
    <div *ngIf="job_id>0"><job_output (onBeforeContentAdded)="onBeforeContentAdded()" (onContentAdded)="onContentAdded()" [job_id]="job_id"></job_output></div>
  `,
  providers: [JobsService]
})
export class JobOutputPage {

    job_id : number = 0;
    snappedToBottom: boolean = true;
    animating: boolean = false;
    needToScroll: boolean = false;

    constructor(private route: ActivatedRoute) {
    }

    onBeforeContentAdded() {
      this.needToScroll = this.snappedToBottom;
    }

    onContentAdded() {
      // Scroll to bottom of page
      if (this.needToScroll) {
        this.animating = true;
        jQuery("html, body").animate({ scrollTop: jQuery(document).height()-jQuery(window).innerHeight() + 40 }, 400, () => {
          this.animating = false;
        }); 
      }
    }

    ngOnInit(): void {
        // Get Take Id from URL
        this.route.params.forEach((params: Params) => {
            this.job_id = +params['id'];
        });
        
        jQuery(window).scroll(() => {
          if(jQuery(window).scrollTop() + jQuery(window).height() + 10 >= jQuery(document).height()) {
              this.snappedToBottom = true;
            } else {
            if (!this.animating) {
              this.snappedToBottom = false;
            }
          }
       });
    }
}
