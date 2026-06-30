import tomllib


def raw_view(toml_string: str) -> list:
    """Return a list of text lines representing the raw profile wire format."""
    output = []

    try:
        data = tomllib.loads(toml_string)
    except Exception as e:
        raise e

    profile_name = data.get("profile", {}).get("name", "Unknown")
    output.append(f"\n[*] Loaded Profile: {profile_name}")
    output.append("=" * 60)

    raw = data.get("raw", {})
    if not raw:
        output.append("(no [raw] section found)")
        return output

    def _describe_transforms(transforms: list) -> list[str]:
        lines = []
        for step in transforms:
            val = step.get("val")
            lines.append(
                f"  -> {step['op']}"
                + (
                    f" (val: '{val[:40]}...')"
                    if val and len(val) > 40
                    else (f" (val: '{val}')" if val is not None else "")
                )
            )
        return lines

    # GET block
    get_block = raw.get("get", {})
    if get_block:
        output.append("=== RAW GET (Beacon Check-in) ===")
        output.append(f"  proto : {get_block.get('proto', 'tcp').upper()}")
        output.append(f"  body  : {get_block.get('body', '<METADATA>')}")

        meta_transforms = get_block.get("client", {}).get("metadata", {}).get("transforms", [])
        output.append("")
        output.append("[*] Client Metadata Transforms:")
        if meta_transforms:
            output.extend(_describe_transforms(meta_transforms))
        else:
            output.append("  -> (none)")

        server_transforms = get_block.get("server", {}).get("output", {}).get("transforms", [])
        server_body = get_block.get("server", {}).get("body", "<OUTPUT>")
        output.append("")
        output.append("[*] Server Response:")
        output.append(f"  body  : {server_body}")
        if server_transforms:
            output.append("  transforms:")
            output.extend(_describe_transforms(server_transforms))
        output.append("=" * 60)

    # POST block
    post_block = raw.get("post", {})
    if post_block:
        output.append("=== RAW POST (Data Exfil) ===")
        output.append(f"  proto : {post_block.get('proto', 'tcp').upper()}")
        output.append(f"  body  : {post_block.get('body', '<OUTPUT>')}")

        output_transforms = post_block.get("client", {}).get("output", {}).get("transforms", [])
        output.append("")
        output.append("[*] Client Output Transforms:")
        if output_transforms:
            output.extend(_describe_transforms(output_transforms))
        else:
            output.append("  -> (none)")

        server_body = post_block.get("server", {}).get("body", "")
        output.append("")
        output.append("[*] Server ACK:")
        output.append(f"  body  : {repr(server_body)}")
        output.append("=" * 60)

    return output
