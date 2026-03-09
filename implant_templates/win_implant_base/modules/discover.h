#pragma once

#include "data/structs.h"
#include "_debug/debug.h"

//idea, name this "neighbor discovery" or something, for each enightbor, addd it to a map of ipand mac,and send back in data. 
// this allows for better parsing/neighbor discovery/a consistent return so the server knows how to handle it, and pass to neo4j.
ModuleResult passive_arp_discovery();