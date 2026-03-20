#include <iostream>
#include <string>
#include <vector>
#include <map>

// --- Signatures ---
// Input Strategy: Returns a command string (e.g., "exec whoami")
using IngressFunc = std::string(*)();

// Output Strategy: Takes the result string and sends it away
using EgressFunc = void (*)(std::string);

// --- Strategies - aka funcs to call that do data (Jinja generates these) ex, http_get, etc. append profile name on them?? not sure. ---

// Ingress: HTTP
std::string get_HTTP() {
    std::cout << "[HTTP GET] Checking for orders...\n";
    return "exec_calc"; // Simulated command received
}

std::string post_HTTP() {
    std::cout << "[HTTP GET] Checking for orders...\n";
    return "exec_calc"; // Simulated command received
}

//// Ingress: DNS TXT Records
//std::string get_DNS() {
//    std::cout << "[DNS TXT] Querying for orders...\n";
//    return ""; // No orders
//}

// Egress: NTP
void post_NTP(std::string data) {
    std::cout << "[NTP] Smuggling data inside timestamp fields: " << data << "\n";
}
//
//// Egress: ICMP (Ping)
//void post_ICMP(std::string data) {
//    std::cout << "[ICMP] Packing data into ping payload: " << data << "\n";
//}

// --- The Settings ---
// Jinja shuold populate this as well, based on profiles (can change these to HTTP_GET, DNS_GET, etc?)
enum class InMethod {
    HTTP, DNS
};
enum class OutMethod {
    NTP, ICMP
};

// --- The Dispatcher ---
class C2Agent {
public:
    //setup the maps to be used below
    static std::map<InMethod, IngressFunc> ingressMap;
    static std::map<OutMethod, EgressFunc> egressMap;

    static void init() {
        // Jinja populates this
        //settnig up mapping between which methods, and which funcs to call based on it
        ingressMap[InMethod::HTTP] = get_HTTP;
        //ingressMap[InMethod::DNS] = get_DNS; //extra options

        egressMap[OutMethod::NTP] = post_NTP;
        //egressMap[OutMethod::ICMP] = post_ICMP; //extra options
    }

    //wrapper of funcs to call, easier to do this, and just pass in the map of funcs
    static void cycle(InMethod in, OutMethod out) {
        // 1. GET Command
        std::string cmd = ingressMap[in]();

        if (cmd.empty()) return;

        // 2. Process (The actual work)
        std::string result = "Executed: " + cmd;

        // 3. POST Result (using a totally different protocol)
        egressMap[out](result);
    }
};

// Storage
std::map<InMethod, IngressFunc> C2Agent::ingressMap;
std::map<OutMethod, EgressFunc> C2Agent::egressMap;

int main() {
    C2Agent::init();

    //ex, start cycle, with 
    //GET on http, POST on NTP
    C2Agent::cycle(InMethod::HTTP, OutMethod::NTP);

    /*
    Add 2 commands. 

    strat-get: sets the get strat, i.e. `strat-get <name_of_strat>`
    strat-post: sets the post strat, i.e. `strat-post <name_of_strat>`
    
    For now, hardcoded logic is fine I guess. 

    */

    return 0;
}