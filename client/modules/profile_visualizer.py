import tomllib


def http_view(toml_string: str) -> list:
    """
    On the wire string output of HTTP comms representation
    """
    output = []

    try:
        data = tomllib.loads(toml_string)
    except Exception as e:
        raise e

    profile_name = data.get("profile", {}).get("name", "Unknown")
    output.append(f"\n[*] Loaded Profile: {profile_name}")
    output.append("=" * 60)

    # ==========================================
    # HTTP GET (BEACON)
    # ==========================================
    get_config = data.get("http", {}).get("get", {})
    get_client = get_config.get("client", {})

    get_method = get_config.get("method", "GET")
    get_uri = get_config.get("uri", "/")
    get_query = ""

    get_params = get_client.get("parameters", [])
    if get_params:
        param_strings = [f"{list(p.keys())[0]}={list(p.values())[0]}" for p in get_params]
        get_query = "?" + "&".join(param_strings)

    output.append("=== HTTP GET (Beacon Check-in) ===")
    # output.append("--- ON THE WIRE ---")
    output.append("```")
    output.append(f"{get_method} {get_uri}{get_query} HTTP/1.1")

    for header in get_client.get("headers", []):
        for k, v in header.items():
            output.append(f"{k}: {v}")

    output.append("")
    output.append(get_client.get("body", "<EMPTY BODY>"))
    output.append("```")

    output.append("-" * 19)

    output.append("[*] <METADATA> Transforms:")
    transforms = get_client.get("metadata", {}).get("transforms", [])
    if not transforms:
        output.append("  -> (No transforms)")
    for step in transforms:
        val = step.get("val")
        output.append(f"  -> {step['op']}" + (f" (value: '{val}')" if val is not None else ""))

    output.append("=" * 60)

    # ==========================================
    # HTTP POST (EXFIL)
    # ==========================================
    post_config = data.get("http", {}).get("post", {})
    post_client = post_config.get("client", {})

    post_method = post_config.get("method", "POST")
    post_uri = post_config.get("uri", "/")
    post_query = ""

    post_params = post_client.get("parameters", [])
    if post_params:
        param_strings = [f"{list(p.keys())[0]}={list(p.values())[0]}" for p in post_params]
        post_query = "?" + "&".join(param_strings)

    output.append("=== HTTP POST (Data Exfiltration) ===")
    output.append("```")
    output.append(f"{post_method} {post_uri}{post_query} HTTP/1.1")

    for header in post_client.get("headers", []):
        for k, v in header.items():
            output.append(f"{k}: {v}")

    output.append("")
    output.append(post_client.get("body", "<EMPTY BODY>"))
    output.append("```")
    output.append("-" * 19)

    output.append("[*] <CLIENT_ID> Transforms:")
    id_transforms = post_client.get("id", {}).get("transforms", [])
    if not id_transforms:
        output.append("  -> (No transforms)")
    for step in id_transforms:
        val = step.get("val")
        output.append(f"  -> {step['op']}" + (f" (value: '{val}')" if val is not None else ""))

    output.append("\n[*] <OUTPUT> Transforms:")
    output_transforms = post_client.get("output", {}).get("transforms", [])
    if not output_transforms:
        output.append("  -> (No transforms)")
    for step in output_transforms:
        val = step.get("val")
        output.append(f"  -> {step['op']}" + (f" (value: '{val}')" if val is not None else ""))

    output.append("=" * 60)

    return output
    # return "\n".join(output)
