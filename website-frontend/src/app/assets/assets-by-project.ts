//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, ViewChild } from '@angular/core';
import { Pipe, PipeTransform } from '@angular/core';
import { Router, ActivatedRoute, Params, NavigationEnd } from '@angular/router';

import { LaunchJobDialog } from './launch-job-dialog';

import { AssetService } from './assets.service';
import { LoadDataEveryMs } from '../../utils/reloader';

import { NotificationService } from '../notifications.service';

@Pipe({
  name: 'OnlyBestPipe'
})
export class OnlyBestPipe implements PipeTransform {

  transform(value, args?): Array<any> {
    var res = value;
    if (args) {
      res = value.filter(obj => { // filter best/calib
        return obj.take_flag=='best' || obj.take_flag=='calib' || obj.take_flag=='colorchart';
      });
    }
    return res;  
  }
}

@Pipe({
  name: 'FilterBySessionAndName'
})
export class FilterBySessionAndName implements PipeTransform {

  filter_prop(obj, name, search) {
    if (obj.hasOwnProperty(name))
    {
      var test = obj[name].toLowerCase().includes(search);
      return obj[name].toLowerCase().includes(search);
    }
    return false;
  }

  transform(values, session_id : number, search_string : string): Array<any> {
    search_string = search_string.toLocaleLowerCase();
    var res = values;
    if (search_string) {
      res = values.filter(obj => {
        return this.filter_prop(obj,'name',search_string) || this.filter_prop(obj,'take_name',search_string) || this.filter_prop(obj,'shot_name',search_string);
      });
    }
    return res;  
  }
}

@Component({
  selector: 'assets-by-project',
  template: require('./assets-by-project.html'),
  providers: [AssetService]
})
export class AssetsByProjectPage {

  @ViewChild('launchjobdialog')
  public launchJobComponent : LaunchJobDialog;

  router: Router;
  loader = new LoadDataEveryMs();
  project_data : any = null;
  project_id = 0;

  loading = true;

  selected_job_id: number = 0;

  desired_fragment = null;

  filter_search = '';
  filter_session = '';

  constructor(private notificationService: NotificationService, private assetService: AssetService, private route: ActivatedRoute, router: Router) {
    this.router = router;
  }

  scanAssetHasSequence(asset) {
    return asset.take_neutral_start_time != null && 
          asset.take_neutral_end_time != null && 
          asset.take_mixed_w_time != null && 
          asset.take_pattern_start_time != null && 
          asset.take_pattern_last_time != null;
  }

  trackingAssetIsValid(asset) {
    return asset.start_time != null && 
          asset.end_time != null;
  }

  scanAssetDuration(asset) {
    return asset.take_neutral_end_time - asset.take_neutral_start_time;
  }

  trackingAssetDuration(asset) {
    return asset.end_time - asset.start_time;
  }

  onCreateJob(event : any, jobclass : string, options : any[], take_id : number = null, asset_id : number = null, tracking_asset_id : number = null, tags : any[]) {
    this.launchJobComponent.show(jobclass, options, take_id, asset_id, tracking_asset_id, tags);
  }

  createStaticAssetJob(event : any, asset_id : number, job_class : string, tags : string[] = [], options : any[] = []) {

    // need_gpu is obsolete, use tags
    var need_gpu = false;

    if (options.length>0)
      return this.onCreateJob(event, job_class, options, null, asset_id, null, tags);

    event.target.disabled = true;
    event.target.classList.add('btn-running');
    
    this.assetService.createAssetJob(asset_id, job_class, null, need_gpu, null, tags).subscribe(
        data => {},
        err => {
          this.notificationService.notifyError(`ERROR: Could not create ${job_class} (${err.status} ${err.statusText})`);
        },
        () => {

          setTimeout(() => {
            event.target.disabled = false;
            event.target.classList.remove('btn-running');
          }, 500);

        }
      );

    event.preventDefault();      
  }

  createTakeJob(event : any, take_id : number, job_class : string, tags : string[] = [], options : any[] = []) {

    // need_gpu is obsolete, use tags
    var need_gpu = false;

    event.target.disabled = true;
    event.target.classList.add('btn-running');

    if (options.length>0)
      return this.onCreateJob(event, job_class, options, take_id, null, null, tags);   
    
    this.assetService.createTakeJob(take_id, job_class, null, need_gpu, null, tags).subscribe(
        data => {},
        err => {
          this.notificationService.notifyError(`ERROR: Could not create ${job_class} (${err.status} ${err.statusText})`);
        },
        () => {

          setTimeout(() => {
            event.target.disabled = false;
            event.target.classList.remove('btn-running');
          }, 500);

        }
      );

    event.preventDefault();
  }

  createTrackingAssetJob(event : any, asset_id : number, job_class : string, tags : string[] = [], options : any[] = []) {

    // need_gpu is obsolete, use tags
    var need_gpu = false;

    event.target.disabled = true;
    event.target.classList.add('btn-running');
    
    if (options.length>0)
      return this.onCreateJob(event, job_class, options, null, null, asset_id, tags);
    
    this.assetService.createTrackingAssetJob(asset_id, job_class, null, need_gpu, null, tags).subscribe(
        data => {},
        err => {
          this.notificationService.notifyError(`ERROR: Could not create ${job_class} (${err.status} ${err.statusText})`);
        },
        () => {

          setTimeout(() => {
            event.target.disabled = false;
            event.target.classList.remove('btn-running');
          }, 500);

        }
      );

    event.preventDefault();
  }

  trackByProjectId(index: number, project : any) {
    return project.id;
  }

  trackByAssetId(index: number, asset : any) {
    return asset.id;
  }

  trackById(index: number, asset : any) {
    return asset.id;
  }
  
  tryScrollToFragment() {
    // If we were waiting for this fragment to load, and it is loaded, scroll to it
    if (this.desired_fragment) {
      const element = document.querySelector('#' + this.desired_fragment);
      if (element) {
        element.scrollIntoView(true);
        this.desired_fragment = null;
      }  
    }
  }

  ngAfterContentChecked() {
    // If we were waiting for this fragment to load, and it is loaded, scroll to it
    this.tryScrollToFragment();
  }

  ngOnInit(): void {

    // inside in ngOnInit()
    this.route.fragment.subscribe(f => {
      // Store desired fragment for later, when the content is finished loading
      this.desired_fragment = f;
      this.tryScrollToFragment();
    });

    // Get Session Dd from URL
    this.route.params.forEach((params: Params) => {      

      var new_project_id = +params['id']; // (+) converts string 'id' to a number

      if (this.project_id != new_project_id) {
        this.project_id = new_project_id;
        this.project_data = null;
        this.loading = true;

        this.loader.start(3000, () => { return this.assetService.getProjectsAssets(this.project_id); }, (data : any) => {
          
            this.project_data = data;
            this.loading = false;
  
            // Find frontal camera in each take
            for (var i = 0, leni = this.project_data.calibration_takes.length; i < leni; i++) {
              var take = this.project_data.calibration_takes[i];
              var frontal_camera = null;
              for (var l = 0, lenl = take.cameras.length; l < lenl; l++) {
                if (take.cameras[l].unique_id == take.frontal_cam_uid) {
                  frontal_camera = take.cameras[l];
                  break;
                }
              }
              take.frontal_camera = frontal_camera;
            }      
            
            // Find frontal camera in each take
            for (var i = 0, leni = this.project_data.colorchart_takes.length; i < leni; i++) {
              var take = this.project_data.colorchart_takes[i];
              var frontal_camera = null;
              for (var l = 0, lenl = take.cameras.length; l < lenl; l++) {
                if (take.cameras[l].unique_id == take.frontal_cam_uid) {
                  frontal_camera = take.cameras[l];
                  break;
                }
              }
              take.frontal_camera = frontal_camera;
            }            

            // Find frontal camera in each take
            for (var i = 0, leni = this.project_data.single_frame_takes.length; i < leni; i++) {
              var take = this.project_data.single_frame_takes[i];
              var frontal_camera = null;
              for (var l = 0, lenl = take.cameras.length; l < lenl; l++) {
                if (take.cameras[l].unique_id == take.frontal_cam_uid) {
                  frontal_camera = take.cameras[l];
                  break;
                }
              }
              take.frontal_camera = frontal_camera;
            }     
            

          }, err => {
            this.loading = false;
          }, 
            'getProjectsAssets_'+this.project_id); // cache key
                  
      }

    });
  }

  ngOnDestroy(): void {
    this.loader.release();
  }
}
