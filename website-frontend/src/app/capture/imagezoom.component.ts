//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import {Component, ViewEncapsulation, Output, EventEmitter} from '@angular/core';

@Component({
  selector: 'imagezoom-selector',
  encapsulation: ViewEncapsulation.None,
  template: require('./imagezoom.html')
})
export class ImageZoomComponent {

  @Output() onSetROI = new EventEmitter<number[]>();
  @Output() onSetROIPercent = new EventEmitter<number>();
  @Output() onResetROI = new EventEmitter<void>();  

  my_canvas = null;
  my_ctx = null;
  my_image = null;

  scale_factor = 1.0;
  mouseIsDown = false;
  lastX = 0;
  lastY = 0;
  offsetX = 0;
  offsetY = 0;

  roiVisible = false;
  roiOffsetX = 0;
  roiOffsetY = 0;
  roiWidth = 0;
  roiHeight = 0;
  loading_image = false;

  rotation_angle = 0;

  lastFullWidth = 0;
  lastFullHeight = 0;

  resetROI() {
    this.roiVisible = false;
    this.roiOffsetX = 100;
    this.roiOffsetY = 200;
    this.roiWidth = 400;
    this.roiHeight = 600;

    this.onResetROI.emit();    
  }

  defineROITemplate(event, template_index) {
    this.roiVisible = false;
    if (this.my_image) {
      var W = this.lastFullWidth;
      var H = this.lastFullHeight;

      switch (template_index) {
        case 0: // Crop Center 95%
          this.onSetROIPercent.emit(95);
          break;
        case 1: // Crop Center 90%
          this.onSetROIPercent.emit(90);
          break;
        case 2: // Crop Center 50%
          this.onSetROIPercent.emit(50);
          break;
        case 3: // Crop Center 30%
          this.onSetROIPercent.emit(30);
          break;
        case 4: // Crop Center 15%
          this.onSetROIPercent.emit(15);
          break;
        case 5: // Make Square
          var d = Math.min(W,H);
          this.onSetROI.emit([(W-d)/2,(H-d)/2,d,d]);
          break;
      }
    }

    event.preventDefault();
  }

  defineROI() {
    this.resetROI();
    this.roiVisible = true;
  }

  setROI() {
    var values = [this.roiOffsetX,this.roiOffsetY,this.roiWidth,this.roiHeight];
    this.onSetROI.emit(values);
    this.roiVisible = false;
  }

  render(timestamp) {

    if (this.my_ctx && !this.loading_image && this.my_image) {

        this.my_canvas.width = window.innerWidth;
        this.my_canvas.height = window.innerHeight;

        this.my_ctx.resetTransform();
        this.my_ctx.fillStyle="#303030";
        this.my_ctx.fillRect(0, 0, this.my_canvas.width, this.my_canvas.height);

        // Draw main image from camera
        this.my_ctx.translate(this.my_canvas.width / 2, this.my_canvas.height / 2);
        this.my_ctx.translate(this.offsetX, this.offsetY);

        // Width/height after rotation
        var rotatedWidth = this.my_image.naturalWidth;
        var rotatedHeight = this.my_image.naturalHeight;
        if (this.rotation_angle==90 || this.rotation_angle==270) {
          rotatedWidth = this.my_image.naturalHeight;
          rotatedHeight = this.my_image.naturalWidth;
        }

        // Scale image to fit in window
        var window_scale = this.my_canvas.width / rotatedWidth; // Fit width
        if (this.my_canvas.height/this.my_canvas.width < rotatedHeight/rotatedWidth)
          window_scale = this.my_canvas.height / rotatedHeight; // Fit height

        // center, rotate, scale
        this.my_ctx.scale(this.scale_factor * window_scale, this.scale_factor * window_scale);
        this.my_ctx.rotate(this.rotation_angle*Math.PI/180.0);
        this.my_ctx.translate(-this.my_image.naturalWidth / 2, -this.my_image.naturalHeight / 2);
        this.my_ctx.drawImage(this.my_image, 0, 0);

        // Draw ROI Box
        if (this.roiVisible) {
          this.my_ctx.strokeStyle="#FF0000";
          this.my_ctx.strokeRect(this.roiOffsetX,this.roiOffsetY,this.roiOffsetX+this.roiWidth,this.roiOffsetY+this.roiHeight);
        }

        // Draw small image in corner
        if (this.my_canvas.width > 400) {
          this.my_ctx.resetTransform();
          switch (this.rotation_angle) {
            case 90:
              this.my_ctx.translate(this.my_canvas.width, 0);
              this.my_ctx.rotate(this.rotation_angle*Math.PI/180.0);
              this.my_ctx.scale(200 / this.my_image.naturalHeight, 200 / this.my_image.naturalHeight);
              break;
            case 180:
              this.my_ctx.translate(this.my_canvas.width, 200*this.my_image.naturalHeight/this.my_image.naturalWidth);
              this.my_ctx.rotate(this.rotation_angle*Math.PI/180.0);
              this.my_ctx.scale(200 / this.my_image.naturalWidth, 200 / this.my_image.naturalWidth);
              break;
            case 270:
              this.my_ctx.translate(this.my_canvas.width - 200, 200*this.my_image.naturalWidth/this.my_image.naturalHeight);
              this.my_ctx.rotate(this.rotation_angle*Math.PI/180.0);
              this.my_ctx.scale(200 / this.my_image.naturalHeight, 200 / this.my_image.naturalHeight);
              break;
            default:
              this.my_ctx.translate(this.my_canvas.width - 200, 0);
              this.my_ctx.rotate(this.rotation_angle*Math.PI/180.0);
              this.my_ctx.scale(200 / this.my_image.naturalWidth, 200 / this.my_image.naturalWidth);
              break;
          }
          this.my_ctx.drawImage(this.my_image, 0, 0);
        }
    }
  }

  resetView() {
    this.scale_factor = 1.0;
    this.offsetX = 0;
    this.offsetY = 0;
    window.requestAnimationFrame((timestamp) => {this.render(timestamp);});
  }

  mouseDownFunc(event) {

    this.mouseIsDown = true;
    this.lastX = event.clientX;
    this.lastY = event.clientY;

    event.preventDefault();
  }

  mouseUpFunc(event) {
    this.mouseIsDown = false;
    event.preventDefault();
  }

  mouseMoveFunc(event) {

    if (!this.mouseIsDown) return;

    var offsetX = event.clientX - this.lastX;
    var offsetY = event.clientY - this.lastY;
    this.lastX = event.clientX;
    this.lastY = event.clientY;

    this.offsetX += offsetX;
    this.offsetY += offsetY;
    window.requestAnimationFrame((timestamp) => {this.render(timestamp);});

    event.preventDefault();
  }

  mouseWheelFunc(event) {

    this.scale_factor *= Math.pow(1.1, event.wheelDelta / 120);
    this.scale_factor = Math.min(10.0, this.scale_factor);
    this.scale_factor = Math.max(0.5, this.scale_factor);
    window.requestAnimationFrame((timestamp) => {this.render(timestamp);});

    event.preventDefault();
  }

  setImageSrc(src, rotation_angle, loading_done) {

    if (!this.my_image) {
        this.my_canvas = document.getElementById('draw_canvas');

        if (!this.my_canvas)
          return;

        this.my_ctx = this.my_canvas.getContext('2d');
        this.my_image = new Image();
        this.rotation_angle = rotation_angle;

        this.my_canvas.onmousedown = (event) => { this.mouseDownFunc(event); };
        this.my_canvas.onmouseup = (event) => { this.mouseUpFunc(event); };
        this.my_canvas.onmouseout = (event) => { this.mouseUpFunc(event); }; // unless we can capture mouse?
        this.my_canvas.onmousemove = (event) => { this.mouseMoveFunc(event); };
        this.my_canvas.onmousewheel = (event) => { this.mouseWheelFunc(event); };

        this.my_image.onload = () => { 

          this.loading_image = false;
          if (this.my_image) {
            this.lastFullWidth = this.my_image.naturalWidth;
            this.lastFullHeight = this.my_image.naturalHeight;
          }

          window.requestAnimationFrame((timestamp) => {this.render(timestamp);});
          loading_done(); 
        };
    }

    if (this.my_image) {
        this.loading_image = true;
        this.my_image.src = src;
    }
  }

  clear() {
    this.my_image = null;
  }

  ngOnInit(): void {
  }

  ngOnDestroy(): void {
    this.my_ctx = null;
  }

}
