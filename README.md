# LongHaulC2
C2 Aimed at Long Haul Management

# Goals:
Replace other  C2's as a long haul, Red Team/Offensive management C2. A "guardian"/"maintain access"/"Oh shit my shell got detected" solution.

## Things  I would like: 
 - Malleable C2 interopability (use CS's malleable C2 capabilities/scripts)
 - Good management capabilites (likely an API exposed from server, and a good management frontend)


# Implementation  Details:


#### Comms:
 - MessagaePack: Simple, easy to parse, JSON like, binary encoded structure. 


#### Agent:
 - C++

 Primary platform: Windows first, but linux would be useful for long  term. Make the beacon source  as 
 platform agnostic as possible/have compile options (ex, win_func.cpp, lin_func.cpp)

#### Server:
 - Python
    - Flexibility with dynamic restarts, faster dev time, and flask-restx.