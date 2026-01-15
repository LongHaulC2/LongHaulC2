// Implant_v01.cpp : Defines the entry point for the application.
//
#include <iostream>

#include "Implant_v01.h"
#include "lifecycle/register.h"

int temp_loop() {
    while (1) {
        //HTTP_GET

        //ACTIONS

        //HTTP_POST

        //SLEEP
        return 0;

    }
}

#include <iostream>
#include <iterator>
#include <utility>
#include <vector>
#include <map>
#include "protocols/msgpack/msgpack23.h"

int test_pack() {
    std::map<std::string, int> const original{ {"apple", 1}, {"banana", 2} };

    std::vector<unsigned char> data{};
    msgpack23::Packer packer{ std::back_inserter(data) };
    packer(original);

    std::map<std::string, int> unpacked;
    msgpack23::Unpacker unpacker{ data };
    unpacker(unpacked);

    for (auto const& [key, value] : unpacked) {
        std::cout << key << ": " << value << '\n';
    }
}

int main()
{
    std::cout << "hello" << std::endl;
    //register_implant();
    test_pack();
    //loop

    return 0;
}
