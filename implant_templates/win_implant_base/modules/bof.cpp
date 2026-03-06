extern "C" { //tldr, compield in c, so we need to use those names, not the c++ mangled ones
    #include "libs/bof_launcher_api.h"
}
#include "data/structs.h"
#include <vector>
#include <iostream>
#include <windows.h>

ModuleResult run_bof(std::vector<uint8_t> bof_bytes, const std::string& bof_args) {

    if (bofLauncherInit() < 0) {
        //std::cout << "Bof init occured" << std::endl;
        return { "", ERROR_INTERNAL_ERROR };

    }

    BofObjectHandle bof_handle;
    if (bofObjectInitFromMemory(bof_bytes.data(), bof_bytes.size(), &bof_handle) < 0) {
        // handle the error
        //std::cout << "Bof init from mem occured" << std::endl;
        return { "", ERROR_BAD_FORMAT };
    }


    //args
    BofArgs* args0 = NULL;
    if (bofArgsInit(&args0) < 0) {
        std::cout << "Bof args err" << std::endl;
        return { "", ERROR_OUTOFMEMORY };


    }
    bofArgsBegin(args0);
    bofArgsAdd(args0, (unsigned char*)bof_args.c_str(), bof_args.size()); 
    bofArgsEnd(args0);


    // Execute
    BofContext* context = NULL;
    if (bofObjectRun(bof_handle, (unsigned char*)bofArgsGetBuffer(args0), bofArgsGetBufferSize(args0), &context) < 0) {
        //std::cout << "Bof run err occured" << std::endl;
        return { "", ERROR_INTERNAL_ERROR };
    }

    // Get output
    std::string bof_str_output{};
    DWORD status{};
    const char* output = bofContextGetOutput(context, NULL);
    if (output) {
        bof_str_output = std::string(output); // thsi copies the data into our str, so no need to worry about the context free
        status = ERROR_SUCCESS;
    }
    else {
        bof_str_output = "";
        status = ERROR_UNIDENTIFIED_ERROR;

    }
    
    bofArgsRelease(args0);
    bofContextRelease(context);

    return { bof_str_output, status };


}