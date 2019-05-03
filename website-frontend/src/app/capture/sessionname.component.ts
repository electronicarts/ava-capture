//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, Output, ViewChild, EventEmitter, ElementRef } from '@angular/core';

var $ = require("jquery");

@Component({
  selector: 'session-name',
  template: `{{name}}: 
    <span>
      <input [readonly]="!_has_new_value" class="form-control form-control-dark" #param_edit_box type="text" [(ngModel)]="_current_value">
      <button class="btn btn-xs btn-primary" [disabled]="disabled || _has_new_value" (click)="createNewName()">New</button>
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

  el: ElementRef;

  constructor(el: ElementRef) {
    this.el = el;
  }

  createNewName() {
    this.value = '-new-';
    this.onNew.emit(this._current_value);

    // Set keyboard focus on the edit box
    setTimeout(() => {
      ($(this.el.nativeElement).find('input:first')).focus();
      ($(this.el.nativeElement).find('input:first')).select();
    }, 500);
  }
}
