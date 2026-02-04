#include "c2.h"
#include "../protocols/json/json.h"
#include "../data/msgpack/msgpack.h"
// ======================================================================================
// 0. STATIC MEMBER DEFINITIONS
// ======================================================================================
std::map<InMethod, IngressFunc> C2Implant::s_ingress_map;
std::map<OutMethod, EgressFunc> C2Implant::s_egress_map;
std::map<std::string, InMethod> C2Implant::s_in_resolver;
std::map<std::string, OutMethod> C2Implant::s_out_resolver;


// ======================================================================================
// 2. STRATEGIES (Jinja Generated)
// ======================================================================================

// --- Ingress Strategies ---

nlohmann::json get_HTTP(std::string implant_uuid) {
    std::cout << "[HTTP GET] Checking for orders for UUID: " << implant_uuid << "...\n";
    return nullptr; // No orders

}

nlohmann::json get_DNS(std::string implant_uuid) {
    std::cout << "[DNS TXT] Querying for orders...\n";
    return nullptr; // No orders
}

// --- Egress Strategies ---
// Note: These must match EgressFunc signature: (uuid, text, task_id)

void post_NTP(std::string implant_uuid, std::string text_data, std::string task_uuid) {
    std::cout << "[NTP] Smuggling data inside timestamp fields.\n";
    std::cout << "      ID: " << implant_uuid << " | Task: " << task_uuid << "\n";
    std::cout << "      Data: " << text_data << "\n";

}

void post_ICMP(std::string implant_uuid, std::string text_data, std::string task_uuid) {
    std::cout << "[ICMP] Packing data into ping payload: " << text_data << "\n";
}

// ======================================================================================
// 3. CLASS IMPLEMENTATION
// ======================================================================================

//jinja this
void C2Implant::init() {
    // Mapping Enums to Functions
    s_ingress_map[InMethod::HTTP] = get_HTTP;
    s_ingress_map[InMethod::DNS] = get_DNS;

    s_egress_map[OutMethod::NTP] = post_NTP;
    s_egress_map[OutMethod::ICMP] = post_ICMP;

    // Optional: Populate resolvers
    // s_in_resolver["http"] = InMethod::HTTP;
}

int C2Implant::register_implant(InMethod registration_method) {
    // Get the strategy
    if (s_ingress_map.find(registration_method) == s_ingress_map.end()) {
        std::cerr << "[-] Strategy not found for registration.\n";
        return -1;
    }

    // Call strategy with "Zero UUID" for registration
    nlohmann::json implant_uuid_data = s_ingress_map[registration_method]("00000000-0000-0000-0000-000000000000");

    // 3. Extract UUID
    if (implant_uuid_data.contains("implant_uuid")) {
        implant_uuid_ = implant_uuid_data["implant_uuid"];
        std::cout << "[+] Registered! Implant UUID: " << implant_uuid_ << std::endl;
        return 1;
    }

    std::cerr << "[-] Failed to register implant. Exiting." << std::endl;
    return -1;
}

void C2Implant::cycle(InMethod get, OutMethod post) {
    std::cout << "[*] Starting C2 Cycle Loop...\n";

    while (true) {
        // 1. Check for Strategy Existence
        if (s_ingress_map.find(get) == s_ingress_map.end() || s_egress_map.find(post) == s_egress_map.end()) {
            std::cerr << "[-] Invalid strategies selected.\n";
            return;
        }

        // 2. GET Task
        nlohmann::json task_data = s_ingress_map[get](implant_uuid_);

        // 3. Validation
        bool bIsValidTask = !task_data.is_null()
            && task_data.contains("task_uuid")
            && task_data["task_uuid"].is_string();

        if (bIsValidTask) {
            std::string task_uuid = task_data["task_uuid"];
            std::cout << "[+] Received Task: " << task_uuid << std::endl;

            // Execute Actions (Mocked)
            std::string text_data = "If you see this it means the implant is talking to you";

            // Prepare Response
            std::vector<uint8_t> task_response_as_msgpack;
            create_task_response(implant_uuid_, task_uuid, text_data, task_response_as_msgpack);

            // POST Response
            s_egress_map[post](implant_uuid_, text_data, task_uuid);
        }
        else {
            std::cout << "[.] No task or empty response. Sleeping..." << std::endl;
        }

        // finally, Sleep
        this->sleep_implant();
    }
}

void C2Implant::sleep_implant() {
    // Using standard cross-platform sleep for safety.
    // Replace with Sleep(5000) if you specifically need the WinAPI hook.
    std::this_thread::sleep_for(std::chrono::milliseconds(5000));
}