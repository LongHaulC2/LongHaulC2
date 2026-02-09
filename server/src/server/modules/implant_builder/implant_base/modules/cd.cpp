#include <windows.h>
#include <iostream>
/*
Minimal example of a command module. 
*/

int cd(std::string pathname) {
	BOOL result = SetCurrentDirectory(
		pathname.c_str()
	);
	return int(result);
}