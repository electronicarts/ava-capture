//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { Component, Input, ElementRef } from '@angular/core';

var $ = require("jquery");

@Component({
  selector: 'copy-path',
  template: `<div class="clipboard-path">
        <input type="text" [style.width]="width" [value]="cleanPath()" readonly>
        <button (click)="copyToClipboard($event)"><i class="fa fa-copy"></i></button>
    </div>`
})
export class CopyPath {

  @Input() path : string;
  @Input() width : string = "200px";

  el : ElementRef;

  constructor(el: ElementRef) {
    this.el = el;
  }

  getOS() {
    var userAgent = window.navigator.userAgent,
        platform = window.navigator.platform,
        macosPlatforms = ['Macintosh', 'MacIntel', 'MacPPC', 'Mac68K'],
        windowsPlatforms = ['Win32', 'Win64', 'Windows', 'WinCE'],
        iosPlatforms = ['iPhone', 'iPad', 'iPod'],
        os = null;
  
    if (macosPlatforms.indexOf(platform) !== -1) {
      os = 'Mac OS';
    } else if (iosPlatforms.indexOf(platform) !== -1) {
      os = 'iOS';
    } else if (windowsPlatforms.indexOf(platform) !== -1) {
      os = 'Windows';
    } else if (/Android/.test(userAgent)) {
      os = 'Android';
    } else if (!os && /Linux/.test(platform)) {
      os = 'Linux';
    }
  
    return os;
  }
  
  cleanPath() {
    var value = this.path;

    // Convert path to UNC representation

    if (value.startsWith("/mnt/")) {
      // Convert to UNC
      value = value.replace("/mnt/", "\\\\");
    }
    if (value.startsWith("\\\\")) {
      // Use backslash
      value = value.replace(/\//g, "\\");
    }

    return value;
  }

  copyToClipboard(event) {
    var input = $(this.el.nativeElement).find('input');
    input.focus();
    input.select();
    try {
      var successful = document.execCommand('copy');
      if (!successful) {
        throw new Error('copy command was unsuccessful');
      }
    }
    catch (err) {
      alert('please press Ctrl/Cmd+C to copy');
    }    
  }
}
