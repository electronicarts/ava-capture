// stdafx.h : include file for standard system include files,
// or project specific include files that are used frequently, but
// are changed infrequently
//

#pragma once

#ifndef _WIN32_WINNT		// Allow use of features specific to Windows XP or later.                   
#define _WIN32_WINNT 0x0501	// Change this to the appropriate value to target other versions of Windows.
#endif						


#include <stdio.h>

#ifdef WIN32
// win32 only
#include <tchar.h>
#include <windows.h>
#include <conio.h>
#include <process.h>
#else
// linux
#define _tmain(a,b) main(a,b)
#define _TCHAR char
#define _getch()
#endif



// TODO: reference additional headers your program requires here
