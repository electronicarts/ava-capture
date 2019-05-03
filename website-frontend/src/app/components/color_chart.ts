//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, ElementRef, EventEmitter } from '@angular/core';
import { ActivatedRoute, Params } from '@angular/router';
import { ArchiveService } from './../archive/capturearchive.service';

class RGBColor {
  r : number = 0;
  g : number = 0;
  b : number = 0;
  constructor(r, g, b) {
    this.r = r;
    this.g = g;
    this.b = b;
  }
  css() {
    return "rgb(" + this.r + "," + this.g + "," + this.b + ")";
  }
}

class ChartCorner {
  x : number = 0;
  y : number = 0;
  color : RGBColor;
  radius : number = 5;
  constructor(x, y, color) {
    this.x = x;
    this.y = y;
    this.color = color;
  }
  isInside(pt) {
    return !(pt.x<this.x-this.radius || pt.x>this.x+this.radius || pt.y<this.y-this.radius || pt.y>this.y+this.radius);
  }
  draw(ctx) {
    ctx.fillStyle='#FFFFFF';
    ctx.fillRect(this.x-this.radius-2,this.y-this.radius-2,10+4,10+4);
    ctx.fillStyle='#000000';
    ctx.fillRect(this.x-this.radius-1,this.y-this.radius-1,10+2,10+2);
    
    ctx.fillStyle=this.color.css();
    ctx.fillRect(this.x-this.radius,this.y-this.radius,10,10);
  }
}

@Component({
  selector: 'colorcharteditor',
  template: `<canvas 
    (mousedown)="onMouseDown($event);" 
    (mousemove)="onMouseMove($event);"
    (mouseup)="onMouseUp($event);"
    id="myCanvas"></canvas>`
})
export class ColorChartEditor {

  @Input() width : number;
  @Input() height : number;
  @Input() originalwidth : number;
  @Input() originalheight : number;
  @Input() img : string;
  @Output() coordinates = new EventEmitter<Array<number>>();

  el: ElementRef;
  imageObj = null;
  zoom_factor = 1.0;

  // Color chart data (order of corners Black-White-DarkSkin-Turquoise, clockwise from upper-left)
  chartCorners = [ 
    new ChartCorner(10, 10, new RGBColor(0,0,0)), 
    new ChartCorner(30, 10, new RGBColor(255,255,255)), 
    new ChartCorner(30, 30, new RGBColor(116,81,67)), 
    new ChartCorner(10, 30, new RGBColor(92,190,172))];

  // Mouse interaction
  moving = -1;

  constructor(el: ElementRef) {
    this.el = el;
  }

  getCanvas() {
    return this.el.nativeElement.getElementsByTagName('canvas')[0];
  }

  resizeCanvas() {
    var canvas = this.getCanvas();
    canvas.width  = this.width;
    canvas.height = this.height; 
    canvas.style.width  = this.width + 'px';
    canvas.style.height = this.height + 'px';
    this.draw();
  }

  getMousePos(canvas, event) {
    var rect = canvas.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    }
  }

  onMouseDown(ev) {
    var mousePos = this.getMousePos(this.getCanvas(), ev);
    for (var i = 0; i < this.chartCorners.length; i++) { 
      if (this.chartCorners[i].isInside(mousePos)) {
        this.moving = i;
      }
    }

  }

  emitCornerList() {
    var cornerList = [];
    this.chartCorners.forEach((element) => {
      cornerList.push({
        x: element.x/this.zoom_factor,
        y: element.y/this.zoom_factor
      });
    });
    this.coordinates.emit(cornerList); 
  }

  onMouseMove(ev) {
    if (this.moving >= 0) {
      var mousePos = this.getMousePos(this.getCanvas(), ev);

      this.chartCorners[this.moving].x = mousePos.x;
      this.chartCorners[this.moving].y = mousePos.y;

      this.draw();
      this.emitCornerList();
    }
  }

  onMouseUp(ev) {
    this.moving = -1;
  } 

  draw() {
    var canvas = this.getCanvas();
    var context = canvas.getContext('2d');

    if (this.imageObj) {

      var horizontal_zoom = canvas.width/this.originalwidth;
      var vertical_zoom = canvas.height/this.originalheight;

      this.zoom_factor = Math.min(horizontal_zoom, vertical_zoom);

      context.drawImage(this.imageObj, 0, 0, this.originalwidth*this.zoom_factor, this.originalheight*this.zoom_factor);
    }

    context.beginPath();
    context.moveTo(this.chartCorners[this.chartCorners.length-1].x, this.chartCorners[this.chartCorners.length-1].y);
    this.chartCorners.forEach((element) => {
      context.lineTo(element.x, element.y);
    });
    context.strokeStyle="black";
    context.stroke();

    this.chartCorners.forEach((element) => {
      element.draw(context);
    });

  }

  ngOnInit() {
    this.resizeCanvas();
  }  
  
  ngOnChanges() {

    var canvas = this.getCanvas();
    var context = canvas.getContext('2d');
    var imageObj = new Image();
    imageObj.onload = () => {
      this.imageObj = imageObj;
      this.draw();
    };
    imageObj.src = this.img;

  }  

  ngOnDestroy() {
  }
  
}

@Component({
  selector: 'color_chart',
  template: require('./color_chart.html'),
  providers: [ArchiveService, ColorChartEditor]
})
export class ColorChart {
  @Input() takeid : any;

  take = null;
  coordinates = "";

  constructor(private route: ActivatedRoute, private archiveService: ArchiveService) {
  }

  ngOnInit() {
  }  
  
  ngOnChanges() {

    //console.log(this.takeid);
    this.archiveService.getTake(this.takeid).subscribe(
      data => {
        //console.log(data);
        this.take = data;
      },
      err => {},
      () => {},
    );

  }  

  ngOnDestroy() {
  }
  
}

@Component({
  template: `<div *ngIf="takeid">
              <div>Page wrapper for color chart editor for Take #{{takeid}}</div>
              <div><color_chart [takeid]="takeid"></color_chart></div>
             </div>`
})
export class ColorChartPage {

  takeid = null;

  constructor(private route: ActivatedRoute, private archiveService: ArchiveService) {
  }

  ngOnInit(): void {

    // Get Take Id from URL
    this.route.params.forEach((params: Params) => {
      this.takeid = +params['id'];
    });

  }

  ngOnDestroy(): void {
  }
}
