//the logic behind msgpack conversions

//from_msgpack -> whatever it returns it as

//whatever it returns it as -> msgpack

#include <iostream>
#include <iterator>
#include <utility>
#include <vector>
#include <map>
#include "../../protocols/msgpack23/msgpack23.h"

/*
Metadata structure:


{"implant_uuid":"uuid", ...}
*/


/**
 * @brief creates a msgpack metadata object. 
 * @param metadata: A map of <std::string, std::string>, each item is a metadata field. Ex, hostname=myhostname
 * @param response_buffer: A vector in which to hold the response bytes
 * @return 0 success, 1 fail
 */
int create_metadata(std::map<std::string, std::string> metadata, std::vector<unsigned char>& response_buffer) {
    //std::map<std::string, int> const original{ {"apple", 1}, {"banana", 2} };

    //check vector length > 0:
    if (metadata.size() < 0) {
        //no metadata, something went wrong
        return 1;
    }

    //Debug print:
    std::cout << "Metadata:" << std::endl;
    for (auto const& [key, value] : metadata) {
        std::cout << key << ": " << value << '\n';
    }

    msgpack23::Packer packer{ std::back_inserter(response_buffer) };
    //and pack it
    packer(metadata);

    return 0;
}

//Don't think we'll need an unpack metadata

/*
Task request structure

{task_uuid: <some_uuid>, implant_uuid: <intended_target>, "task":{"taskname":"somename" "args":{"arg1":"value1"}}}

*/

int create_task_request() {
    return 0;
}

/*
Task response structure

{"task_uuid":"1234", "implant_uuid": 9999, "result":{"data_type":"text", "data":"somedomain\bob"}}

*/

int create_task_response() {
    return 0;

}