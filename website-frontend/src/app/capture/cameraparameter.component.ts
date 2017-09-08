//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, ViewChild, EventEmitter } from '@angular/core';

@Component({
  selector: 'cam-param',
  template: `{{name}}: 
    <span *ngIf="disabled">
      {{value | number}} {{unit}}
    </span>
    <span *ngIf="!disabled && !(edit_visible || editAlwaysVisible)">
      <a (click)="showEdit()">{{value | number}} {{unit}}</a>
    </span>
    <span *ngIf="!disabled && (edit_visible || editAlwaysVisible)">
      <input #param_edit_box type="number" [min]="min" [max]="max" [(ngModel)]="new_value" [disabled]="disabled">
      <button [disabled]="disabled" (click)="changevalue()">Change</button>
    </span>`
})
export class CameraParameterValueComponent {
  @Input() name: string;
  @Input() unit: string;
  @Input() value: number;
  @Input() min: number;
  @Input() max: number;
  @Input() disabled: boolean;
  @Input() editAlwaysVisible: boolean;
  @Output() onChanged = new EventEmitter<number>();
  @ViewChild('param_edit_box') param_edit_box;

  private edit_visible = false;
  private new_value = 0;

  showEdit() {
    this.new_value = this.value;
    this.edit_visible = true;
  }

  changevalue() {
    this.onChanged.emit(this.new_value);
    this.edit_visible = false;
  }
}
