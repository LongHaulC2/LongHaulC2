#include <string>
#include "core/settings.h"


int set_comms_get_strategy(std::string strategy_name) {
	SettingsManager::instance().set("comms_get_function", strategy_name);
	return 0;
}

int set_comms_post_strategy(std::string strategy_name) {
	SettingsManager::instance().set("comms_post_function", strategy_name);
	return 0;
}
