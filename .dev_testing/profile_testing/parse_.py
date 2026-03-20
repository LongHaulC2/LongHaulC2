import tomllib

def test_parse_profile(toml_string: str):
    try:
        data = tomllib.loads(toml_string)
    except Exception as e:
        print(f"Failed to parse TOML: {e}")
        return

    profile_name = data.get('profile', {}).get('name', 'Unknown')
    print(f"\n[*] Loaded Profile: {profile_name}")
    print("=" * 60)

    # ==========================================
    # HTTP GET (BEACON)
    # ==========================================
    get_config = data.get('http', {}).get('get', {})
    get_client = get_config.get('client', {})
    
    # 1. Build URI with Parameters
    get_method = get_config.get('method', 'GET')
    get_uri = get_config.get('uri', '/')
    get_query = ""
    
    get_params = get_client.get('parameters', [])
    if get_params:
        param_strings = [f"{list(p.keys())[0]}={list(p.values())[0]}" for p in get_params]
        get_query = "?" + "&".join(param_strings)

    # 2. Print the Wire Format
    print("=== HTTP GET (Beacon Check-in) ===")
    print("--- ON THE WIRE ---")
    print(f"{get_method} {get_uri}{get_query} HTTP/1.1")
    
    for header in get_client.get('headers', []):
        for k, v in header.items():
            print(f"{k}: {v}")
    
    print() # Blank line separates headers from body in HTTP
    print(get_client.get('body', '<EMPTY BODY>'))
    print("-" * 19)

    # 3. Print Transforms
    print("[*] <METADATA> Transforms:")
    transforms = get_client.get('metadata', {}).get('transforms', [])
    if not transforms:
        print("  -> (No transforms)")
    for step in transforms:
        val = step.get('val')
        print(f"  -> {step['op']}" + (f" (value: '{val}')" if val is not None else ""))
    print("=" * 60)


    # ==========================================
    # HTTP POST (EXFIL)
    # ==========================================
    post_config = data.get('http', {}).get('post', {})
    post_client = post_config.get('client', {})
    
    # 1. Build URI with Parameters
    post_method = post_config.get('method', 'POST')
    post_uri = post_config.get('uri', '/')
    post_query = ""
    
    post_params = post_client.get('parameters', [])
    if post_params:
        param_strings = [f"{list(p.keys())[0]}={list(p.values())[0]}" for p in post_params]
        post_query = "?" + "&".join(param_strings)

    # 2. Print the Wire Format
    print("=== HTTP POST (Data Exfiltration) ===")
    print("--- ON THE WIRE ---")
    print(f"{post_method} {post_uri}{post_query} HTTP/1.1")
    
    for header in post_client.get('headers', []):
        for k, v in header.items():
            print(f"{k}: {v}")
    
    print()
    print(post_client.get('body', '<EMPTY BODY>'))
    print("-" * 19)

    # 3. Print Transforms
    print("[*] <CLIENT_ID> Transforms:")
    id_transforms = post_client.get('id', {}).get('transforms', [])
    if not id_transforms:
        print("  -> (No transforms)")
    for step in id_transforms:
        val = step.get('val')
        print(f"  -> {step['op']}" + (f" (value: '{val}')" if val is not None else ""))

    print("\n[*] <OUTPUT> Transforms:")
    output_transforms = post_client.get('output', {}).get('transforms', [])
    if not output_transforms:
        print("  -> (No transforms)")
    for step in output_transforms:
        val = step.get('val')
        print(f"  -> {step['op']}" + (f" (value: '{val}')" if val is not None else ""))
    print("=" * 60)


# Run the parser
with open("profile_def.toml", "r") as profile:
    test_parse_profile(profile.read())