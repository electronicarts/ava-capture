//
// Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
//

import { NgModule }      from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule }   from '@angular/forms';

import { LoginComponent }  from './login.component';
import { AuthComponent }  from './auth.component';

@NgModule({
  imports:      [ BrowserModule, FormsModule ],
  declarations: [ LoginComponent, AuthComponent ],
  bootstrap:    [ LoginComponent ]
})
export class LoginModule { }
