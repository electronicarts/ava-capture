//
// Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, ViewChild, EventEmitter } from '@angular/core';

@Component({
  selector: 'session-name',
  template: `{{name}}: 
    <span *ngIf="!_has_new_value">
      <b>{{_current_value}}</b>
      <button class="btn btn-xs btn-primary" [disabled]="disabled" (click)="createNewName()">New</button>
    </span>
    <span *ngIf="_has_new_value">
      <input class="form-control form-control-dark" #param_edit_box type="text" [(ngModel)]="_current_value">
    </span>`
})
export class SessionNameComponent {
  @Input() name: string;
  @Input()
    set value(name: string) {
        if (this._previous_value !== name) {
            this._current_value = name;
            this._has_new_value = (name === '-new-');
            this._previous_value = name;
        }
    }
    get value(): string { return this._current_value; }
  @Input() disabled: boolean;
  @Output() onNew = new EventEmitter<string>();
  @ViewChild('param_edit_box') param_edit_box;

  private _has_new_value = false;
  private _current_value = '';
  private _previous_value = '';

  createNewName() {
    this.value = '-new-';
    this.onNew.emit(this._current_value);
  }
}
