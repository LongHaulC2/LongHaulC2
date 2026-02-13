#include <windows.h>
#include <iostream>
#include "../data/structs.h"
#include "cd.h"
/*
Minimal example of a command module. 
*/

ModuleResult cd(std::string pathname) {
	BOOL result = SetCurrentDirectory(
		pathname.c_str()
	);

	//failure. confusing, sorry. TLDR, return value is non-zero here. Thanks windows. 
	//https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setcurrentdirectory
	if (result == 0) {
		//if 0, it means somethign failed, so call getlasterror to see what that is. 
		// no data to send back
		return { "", GetLastError()};
	}
	//on success return ERROR_SUCCESS
	// no data to send back
	return { "", ERROR_SUCCESS };


}