//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, ViewChild } from '@angular/core';
import { Router, ActivatedRoute, Params, NavigationEnd } from '@angular/router';

import { LaunchJobDialog } from './launch-job-dialog';

import { AssetService } from './assets.service';
import { LoadDataEveryMs } from '../../utils/reloader';

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

  constructor(private assetService: AssetService, private route: ActivatedRoute, router: Router) {
    this.router = router;
  }

  onCreateJob(event : any, asset_id : number, jobclass : string) {
    this.launchJobComponent.show(asset_id, jobclass);
  }

  createStaticAssetJob(event : any, asset_id : number, job_class : string, need_gpu : boolean) {

    event.target.disabled = true;
    event.target.classList.add('btn-destructive');
    
    this.assetService.createAssetJob(asset_id, job_class, null, need_gpu).subscribe(
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

  createTrackingAssetJob(event : any, asset_id : number, job_class : string, need_gpu : boolean, node_name : string) {

    event.target.disabled = true;
    event.target.classList.add('btn-destructive');
    
    this.assetService.createTrackingAssetJob(asset_id, job_class, null, need_gpu, node_name).subscribe(
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

  trackByProjectId(index: number, project : any) {
    return project.id;
  }

  trackByAssetId(index: number, asset : any) {
    return asset.id;
  }

  ngOnInit(): void {

    // Get Session Dd from URL
    this.route.params.forEach((params: Params) => {

      this.project_id = +params['id']; // (+) converts string 'id' to a number

        this.loader.start(3000, () => { return this.assetService.getProjectsAssets(this.project_id); }, (data : any) => {

                this.project_data = data;

            });

    });

  }

  ngOnDestroy(): void {
    this.loader.release();
  }
}
