//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, ViewChild } from '@angular/core';
import { Router, ActivatedRoute, Params } from '@angular/router';

import { CaptureService } from './capture.service';
import { UserService } from '../../services/user.service';

import { TimerDisplayComponent } from './timer-display.component';
import { SummaryComponent } from './summary.component';
import { SessionNameComponent } from './sessionname.component';
import { ZoomViewComponent } from './zoomview.component';

import { LoadDataEveryMs } from '../../utils/reloader';

var $ = require("jquery");

@Component({
  selector: 'live',
  template: require('./live.html'),
  providers: [CaptureService, UserService]
})
export class LiveCapturePage {

  @ViewChild(SummaryComponent)
  public summary : SummaryComponent;

  @ViewChild(ZoomViewComponent)
  public zoomview : ZoomViewComponent;

  @ViewChild(TimerDisplayComponent)
  public timerdisplay : TimerDisplayComponent;

  @ViewChild('shot')
  public shotNameComponent : SessionNameComponent;

  capturenodes = [];
  capturecameras = [];
  counter = 1;
  counter_session = Math.random();

  recording = false;
  recording_single = false;

  read_access = true;
  write_access = false;
  load_failed = false;

  location_id = 0;
  location_name = '';

  hardware_sync_frequency = null;
  pulse_duration = null;
  external_sync = 0;
  show_focus_peak = false;
  show_overexposed = false;
  show_histogram = false;
  bitdepth_avi = 8;
  bitdepth_single = 8;

  loader = new LoadDataEveryMs();

  project_id = 0;
  project_name = '';
  session_id = 0;
  session_name = '';
  shot_id = 0;
  shot_name = '';
  next_take = 1;

  create_session_name = '';
  create_session_error = null;

  camera_models = [];
  camera_count = 0;
  batch_target = 'all';

  syncs_found = 0;

  node_to_close = 0;
  node_to_close_name : string = null;

  available_freqs = [10, 20, 24, 30, 40, 50, 60, 70, 72, 80, 90, 100, 120];

  thumbnail_preview_fps = 5;

  camera_view_mode = 0;

  show_camera_list = false;

  constructor(private captureService: CaptureService, private route: ActivatedRoute, private userService: UserService) {
  }

  toggle_view_cameras_per_node() {
    this.camera_view_mode = (this.camera_view_mode+1)%3;
  }

  batch_camera(callbackFn) {
    if (this.capturenodes) {
      this.capturenodes.forEach(node => {
        node.camera_details.forEach(camera => {
          if (this.batch_target === 'all' || camera.model === this.batch_target) {
            callbackFn(camera);
          }
        });
      });
    }
  }

  batch_syncEnable(value) {
    // Set value on all cameras matching
    this.batch_camera(camera => {
      if (Boolean(camera.using_hardware_sync) !== Boolean(value)) {
        this.onToggleUsingSync(camera.id);
      }
    });
  }

  batch_setExposure(value) {
    // Set value on all cameras matching
    this.batch_camera(camera => {
      this.onChangeCameraParameter(value, 'exposure', camera.id);
    });
  }

  batch_setGain(value) {
    // Set value on all cameras matching
    this.batch_camera(camera => {
      this.onChangeCameraParameter(value, 'gain', camera.id);
    });
  }

  trackByNodeId(index: number, node) {
    return node.id;
  }

  trackByCameraId(index: number, cam) {
    return cam.id;
  }

  trackByDriveRoot(index: number, drive) {
    return drive.root;
  }

  onToggleUsingSync(camId) {
    this.loader.subscribeDataChange(
      this.captureService.toggleUsingSync(camId),
      data => {},
      err => console.error(err)
    );
  }

  onToggleCapturing(camId) {
    this.loader.subscribeDataChange(
      this.captureService.toggleCapturing(camId),
      data => {},
      err => console.error(err)
    );
  }

  onCameraRotateLeft(camera) {

    var rot = (camera.rotation + 270) % 360;

    this.loader.subscribeDataChange(
      this.captureService.setCameraRotation(camera.id, rot),
      data => {
        camera.rotation = rot;
      },
      err => console.error(err)
    );
  }

  onCameraRotateRight(camera) {

    var rot = (camera.rotation + 90) % 360;

    this.loader.subscribeDataChange(
      this.captureService.setCameraRotation(camera.id, rot),
      data => {
        camera.rotation = rot;
      },
      err => console.error(err)
    );

  }

  onDisplayCloseNodeModal(nodeId, node_name) {
    this.node_to_close = nodeId;
    this.node_to_close_name = node_name;
    (<any>$('#restartNodeModal')).addClass('modal-dialog-container-show');
  }

  onCancelCloseNode() {
    (<any>$('#restartNodeModal')).removeClass('modal-dialog-container-show');
  }

  onCloseNode() {
    this.captureService.closeNode(this.node_to_close).subscribe(
        data => {
          (<any>$('#restartNodeModal')).removeClass('modal-dialog-container-show');
        },
        err => console.error(err),
        () => {}
      );
  }

  onStartRecording() {
    if (this.recording || this.recording_single)
      return;

    if (this.zoomview)
      this.zoomview.hide();

    this.captureService.startRecording(this.location_id, this.session_id, this.shotNameComponent.value).subscribe(
        data => {
          this.recording = true;
          this.timerdisplay.start();
        },
        err => console.error(err),
        () => {}
      );

      this.userService.refresh_token_if_needed();
  }

  onStopRecording() {
    this.timerdisplay.pause();
    this.captureService.stopRecording(this.location_id).subscribe(
        data => {
          this.recording = false;

          this.summary.content = data;
          this.summary.show();

          this.timerdisplay.clear();
        },
        err => console.error(err),
        () => {}
      );

      this.userService.refresh_token_if_needed();
  }

  onSinglePhotoRecording() {
    this.recording_single = true;
    this.captureService.recordSingleImage(this.location_id, this.session_id, this.shotNameComponent.value).subscribe(
        data => {

          this.summary.content = data;
          this.summary.show();

        },
        err => console.error(err),
        () => {
          this.recording_single = false;
        }
      );

      this.userService.refresh_token_if_needed();
  }

  onNextCaptureShot() {
      this.captureService.nextCaptureShot(this.location_id).subscribe(
        data => {

          this.shot_id = 0;
          this.shot_name = '-new-';
          this.next_take = 1;

        },
        err => console.error(err),
        () => {}
      );
  }

  onShowCreateSessionDialog() {
    this.create_session_name = '';
    this.create_session_error = null;

    (<any>$('#createSessionModal')).addClass('modal-dialog-container-show');
  }

  onCancelCreateNewSession() {
    (<any>$('#createSessionModal')).removeClass('modal-dialog-container-show');
  }

  onCreateNewSession() {

    this.captureService.newCaptureSession(this.location_id, this.create_session_name).subscribe(
      data => {

        this.session_id = data.session_id;
        this.session_name = data.session_name;

        this.shot_id = 0;
        this.shot_name = '-new-';
        this.next_take = 1;

        (<any>$('#createSessionModal')).removeClass('modal-dialog-container-show');

      },
      err => {
        this.create_session_error = err.text(); // Display Error text
        $('#textareaID').focus();
      },
      () => {}
    );

  }

  enableZoonView(camera) {
    this.zoomview.show(camera);
  }

  onChangeCameraParameter(value, parameter, cam_id) {
    this.captureService.setCameraParameter(
          this.location_id,
          cam_id,
          parameter,
          value
          ).subscribe(
        data => console.log('done set camera parameter'), // TODO: We recieve the actual new value here (it could be clamped)
        err => console.error(err),
        () => {}
      );
  }

  onChangeLocationSyncOption(value) {       

    var dataObj = {
      location : this.location_id,
      frequency : this.hardware_sync_frequency,
      pulse_duration : this.pulse_duration,
      external_sync : this.external_sync==1
    };

    this.captureService.setLocationOptions(this.location_id, dataObj).subscribe(
        data => {},
        err => console.error(err),
        () => {}
      );

      this.userService.refresh_token_if_needed();
  }

  onChangeLocationOption(value) {       

    var dataObj = {
      location : this.location_id,
      display_focus_peak : this.show_focus_peak,
      display_overexposed : this.show_overexposed,
      display_histogram : this.show_histogram,
      bitdepth_avi : Number(this.bitdepth_avi),
      bitdepth_single : Number(this.bitdepth_single)     
    };

    this.captureService.setLocationOptions(this.location_id, dataObj).subscribe(
        data => {},
        err => console.error(err),
        () => {}
      );

      this.userService.refresh_token_if_needed();
  }

  within_percent(value, reference, percent) {
    // returns true if value is within percent% of reference
    return Math.abs(value - reference) * 100 / reference < percent;
  }

  loadCaptureNodes(location_id) {

    this.cancelSubscriptions();

    this.loader.start(1000, () => { return this.captureService.getCameraDetailsDirect(location_id); }, data => {

        this.load_failed = false;
        this.read_access = data.read_access;
        this.write_access = data.write_access;

        this.project_id = data.project_id;
        this.project_name = data.project_id ? data.project_name : '';
        this.session_id = data.session_id;
        this.session_name = data.session_name;
        this.shot_id = data.shot_id;
        this.shot_name = data.shot_name;
        this.next_take = data.next_take;

        this.show_focus_peak = data.location.show_focus_peak;
        this.show_overexposed = data.location.show_overexposed;
        this.show_histogram = data.location.show_histogram;
        this.bitdepth_avi = data.location.bitdepth_avi;
        this.bitdepth_single = data.location.bitdepth_single;
        
        this.hardware_sync_frequency = data.location.hardware_sync_frequency;
        this.pulse_duration = data.location.pulse_duration;
        this.external_sync = data.location.external_sync?1:0;

        this.capturenodes = data.nodes;
        this.capturenodes['counter'] = this.counter++;

        // Update list of unique camera models
        var updated_camera_count = 0;
        var updated_syncs_found = 0;
        var all_capturecameras = [];
        if (this.capturenodes) {
          this.capturenodes.forEach(node => {
            if (node.sync_found && node.active)
              updated_syncs_found++;
            if (node.camera_details) {
              node.camera_details.forEach(camera => {
                updated_camera_count++;
                all_capturecameras.push(camera);
                if (this.camera_models.indexOf(camera.model) < 0) {
                  this.camera_models.push(camera.model);
                }
              });
            }
          });
        }
        this.camera_count = updated_camera_count;
        this.syncs_found = updated_syncs_found;
        this.capturecameras = all_capturecameras;

      }, err => {

        if (err.status === 403) {
          this.load_failed = false;
          this.read_access = false;
          this.write_access = false;
        } else {
          this.load_failed = true;
        }

        this.capturenodes = [];
        this.capturecameras = [];
      });

  }

  ngOnInit(): void {

    // When Session modal dialog is displayed, focus on the text box
    $('#createSessionModal').on('shown.bs.modal', function () {
        $('#textareaID').focus();
    });

    // Get Location id from URL
    this.route.params.forEach((params: Params) => {

      this.location_id = +params['id']; // (+) converts string 'id' to a number

      this.captureService.getLocationName(this.location_id).subscribe(
          data => {
            this.location_name = data;
          },
          err => {
            this.location_name = 'error';
            console.error(err);
          },
          () => {}
        );

      this.cancelSubscriptions();
      if (this.summary)
        this.summary.hide();
      if (this.zoomview)
        this.zoomview.hide();

      // Get list of nodes
      this.loadCaptureNodes(this.location_id);

    });

  }

  cancelSubscriptions() {
    this.loader.release();
  }

  ngOnDestroy(): void {
    this.cancelSubscriptions();
  }

}
