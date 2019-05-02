//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {Component, ViewEncapsulation, Input, Output, EventEmitter} from '@angular/core';
import {Router, ActivatedRoute, Params, NavigationEnd} from '@angular/router';

import { JobsService } from './jobs.service';
import { LoadDataEveryMs } from '../../utils/reloader';

import { NotificationService } from '../notifications.service';

import {Pipe, PipeTransform} from '@angular/core';

declare var jQuery: any;

@Pipe({
  name: 'OnlyActivePipe'
})
export class OnlyActivePipe implements PipeTransform {

  transform(value, args?): Array<any> {
    var res = value;
    if (args) {
      res = value.filter(obj => { // filter active or pending
        return obj.active || obj.aws_instance_state=='pending';
      });
    }
    return res.sort(function(a, b) { // sort by machine_name
      return a.machine_name.toLowerCase().localeCompare(b.machine_name.toLowerCase());
    });  
  }
}

@Component({
  selector: '[farm_nodes_item]',
  template: require('./farm_nodes_item.html'),
  providers: [JobsService]
})
export class FarmNodesItem {
  @Input() group_key : string;
  @Input() group_val : any;
  
  @Output() onDisplayNodeDetails = new EventEmitter<number>();
  @Output() onJobDetails = new EventEmitter<any>();
  
  constructor(private notificationService: NotificationService, private jobsService: JobsService) {
  }

  trackByNodeId(index: number, farmnode) {
    return farmnode.id;
  }

  trackByContent(index: number, s) {
    return s;
  }

  displayJobDetails(event) {
    this.onJobDetails.emit(event);
  }

  displayNodeDetails(node_id) {
    this.onDisplayNodeDetails.emit(node_id);
  }

  startAWSInstance(event, node_id) {
    event.target.disabled = true;
    event.target.classList.add('btn-destructive');

    this.jobsService.startAWSInstance(node_id).subscribe(
        data => {},
        err => {this.notificationService.notifyError(`ERROR: Could not start AWS Instance (${err.status} ${err.statusText})`);},
        () => {

          setTimeout(() => {
            event.target.disabled = false;
            event.target.classList.remove('btn-destructive');
          }, 500);

        }
      );
  }

  reloadClient(event, node_id) {

    event.target.disabled = true;
    event.target.classList.add('btn-destructive');

    this.jobsService.reloadClient(node_id).subscribe(
        data => {},
        err => {this.notificationService.notifyError(`ERROR: Could not reload Client (${err.status} ${err.statusText})`);},
        () => {

          setTimeout(() => {
            event.target.disabled = false;
            event.target.classList.remove('btn-destructive');
          }, 500);

        }
      );
  }
}


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

  show_only_active : boolean = true;

  selected_job_id: number = 0;

  constructor(private notificationService: NotificationService, private jobsService: JobsService, private route: ActivatedRoute, router: Router) {
    this.router = router;
  }

  reloadClient(event, node_id) {

    event.target.disabled = true;
    event.target.classList.add('btn-destructive');

    this.jobsService.reloadClient(node_id).subscribe(
        data => {},
        err => {this.notificationService.notifyError(`ERROR: Could not reload Client (${err.status} ${err.statusText})`);},
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

  displayJobDetails(event) {
    this.selected_job_id = event;
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

          this.nodes_data.forEach((node_data) => {
            var group_name = node_data.group ? node_data.group : "No Group";
            if (!(group_name in nodes_by_group)) {
              nodes_by_group[group_name] = Array();
            }            
            nodes_by_group[group_name].push(node_data);
          });                    
          
          this.nodes_by_group = nodes_by_group;
        }, err => {}, 
      'getFarmNodes'); // cache key

  }

  ngOnDestroy(): void {
    this.loader.release();
  }

}
