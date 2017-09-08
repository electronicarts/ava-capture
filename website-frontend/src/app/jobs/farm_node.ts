//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input } from '@angular/core';
import { Router, ActivatedRoute, Params } from '@angular/router';

import { JobsService } from './jobs.service';
import { LoadDataEveryMs } from '../../utils/reloader';

@Component({
  selector: 'farm_node',
  template: require('./farm_node.html'),
  providers: [JobsService]
})
export class FarmNodePage {

  @Input()
  nodeid = 0;

  node_data = null;
  loader = new LoadDataEveryMs();

  constructor(private jobsService: JobsService, private route: ActivatedRoute) {
  }

  ngOnChanges() : void {

    this.loader.start(3000, () => { return this.jobsService.getNodeDetails(this.nodeid); }, data => {
          this.node_data = data;
        });

  }

  ngOnInit(): void {
  }

  ngOnDestroy(): void {
    this.loader.release();
  }

}
