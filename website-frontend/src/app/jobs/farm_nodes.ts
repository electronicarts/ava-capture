//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import {Component, ViewEncapsulation} from '@angular/core';
import {Router, ActivatedRoute, Params, NavigationEnd} from '@angular/router';

import { JobsService } from './jobs.service';
import { LoadDataEveryMs } from '../../utils/reloader';

declare var jQuery: any;

@Component({
  selector: 'farm_nodes',
  template: require('./farm_nodes.html'),
  encapsulation: ViewEncapsulation.None,
  providers: [JobsService]
})
export class FarmNodesPage {

  router: Router;
  selected_node_id = 0;
  loader = new LoadDataEveryMs();

  nodes_data = null;
  nodes_by_group = {};

  constructor(private jobsService: JobsService, private route: ActivatedRoute, router: Router) {
    this.router = router;
  }

  reloadClient(event, node_id) {

    event.target.disabled = true;
    event.target.classList.add('btn-destructive');

    this.jobsService.reloadClient(node_id).subscribe(
        data => {},
        err => console.error(err),
        () => {

          setTimeout(() => {
            event.target.disabled = false;
            event.target.classList.remove('btn-destructive');
          }, 500);

        }
      );
  }

  trackByNodeId(index: number, farmnode) {
    return farmnode.id;
  }

  hideNodeDetails() {
    this.selected_node_id = 0;
  }

  displayNodeDetails(nodeid) {
    this.selected_node_id = nodeid;
  }

  ngOnInit(): void {

    let searchInput = jQuery('#table-search-input');
    searchInput
      .focus((e) => {
      jQuery(e.target).closest('.input-group').addClass('focus');
    })
      .focusout((e) => {
      jQuery(e.target).closest('.input-group').removeClass('focus');
    });

    this.loader.start(3000, () => { return this.jobsService.getFarmNodes(); }, data => {
          this.nodes_data = data.results;

          // Sort Nodes by Groups
          var nodes_by_group = {};

          data.results.forEach((node_data) => {
            var group_name = node_data.group ? node_data.group : "No Group";
            if (!(group_name in nodes_by_group)) {
              nodes_by_group[group_name] = Array();
            }            
            nodes_by_group[group_name].push(node_data);
          });                    
          
          this.nodes_by_group = nodes_by_group;
        });

  }

  ngOnDestroy(): void {
    this.loader.release();
  }

}
