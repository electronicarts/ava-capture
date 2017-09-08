//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, ViewChild } from '@angular/core';
import { Router, ActivatedRoute, Params, NavigationEnd } from '@angular/router';

import { ArchiveService } from './capturearchive.service';
import { LoadDataEveryMs } from '../../utils/reloader';

@Component({
  selector: 'archive-by-project',
  template: require('./archive-by-project.html'),
  providers: [ArchiveService]
})
export class ArchiveByProjectPage {

  router: Router;
  loader = new LoadDataEveryMs();
  project_data : any = null;
  project_id = 0;

  selected_takes : number[] = [];
  all_takes : number[] = [];
  
  constructor(private archiveService: ArchiveService, private route: ActivatedRoute, router: Router) {
    this.router = router;
  }

  thumbfile(front_path, suffix) {
    return front_path.replace("_front_", "_"+suffix+"_");
  }

  trackById(index: number, something : any) {
    return something.id;
  }

  toggleBestTake(event, take) {

    var flag_set = event.target.checked;
    this.loader.subscribeDataChange(
      this.archiveService.setTakeFlag(take.id, "best",flag_set ),
      data => {
        // change done, update data
        if (flag_set)
          take.flag = "best";
        else
          take.flag = "none";
      },
      err => console.error(err)
    );
  }

  toggleBadTake(event, take) {
    var flag_set = event.target.checked;
    this.loader.subscribeDataChange(
      this.archiveService.setTakeFlag(take.id, "bad",flag_set ),
      data => {
        // change done, update data
        if (flag_set)
          take.flag = "bad";
        else
          take.flag = "none";
      },
      err => console.error(err)
    );
  }

  ngOnInit(): void {

    // Get Session Dd from URL
    this.route.params.forEach((params: Params) => {

      this.project_id = +params['id']; // (+) converts string 'id' to a number

        this.loader.start(3000, () => { return this.archiveService.getProjectsTakes(this.project_id); }, (data : any) => {

                this.project_data = data;

                // Find frontal camera in each take
                for (var i = 0, leni = this.project_data.sessions.length; i < leni; i++) {
                  var session = this.project_data.sessions[i];
                  for (var j = 0, lenj = session.shots.length; j < lenj; j++) {
                    var shot = session.shots[j];
                    for (var k = 0, lenk = shot.takes.length; k < lenk; k++) {
                      var take = shot.takes[k];
                      var frontal_camera = null;
                      for (var l = 0, lenl = take.cameras.length; l < lenl; l++) {
                        if (take.cameras[l].unique_id == take.frontal_cam_uid) {
                          frontal_camera = take.cameras[l];
                          break;
                        }
                      }
                      take.frontal_camera = frontal_camera;
                    }
                  }
                }
            });

    });

  }

  ngOnDestroy(): void {
    this.loader.release();
  }
}
