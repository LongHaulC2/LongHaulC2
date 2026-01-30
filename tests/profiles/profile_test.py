from mpp import *

mp = MalleableProfile("./bing_getonly.profile")


def clean_string(s):
    """
    Removes specific delimiter artifacts from a string.
    Adjust the replace logic below if you strictly want to delete them
    instead of unescaping them.
    """
    if isinstance(s, str):
        # This unescapes \" to ", which is usually the intent for C2 profiles.
        # If you strictly want to DELETE the characters, change '"' to ''
        return s.replace('\\"', '"').replace('"\\', '"')
    return s


def clean_ast(node):
    """
    Recursively traverses the AST and cleans 'value' and 'key' fields.
    """
    # 1. Handle Dictionary (recurse into values)
    if isinstance(node, dict):
        for key, value in node.items():
            clean_ast(value)

    # 2. Handle List (recurse into items)
    elif isinstance(node, list):
        for item in node:
            clean_ast(item)

    # 3. Handle 'Block' objects (recurse into the 'data' attribute)
    elif hasattr(node, "data") and isinstance(node.data, list):
        clean_ast(node.data)

    # 4. Handle 'Option' and 'Statement' objects (clean the 'value' and 'key')
    # We check for 'value' attribute which both Option and Statement have.
    elif hasattr(node, "value"):
        # Clean the value
        node.value = clean_string(node.value)

        # Statements also have a 'key' attribute (e.g., header name)
        if hasattr(node, "key") and node.key:
            node.key = clean_string(node.key)


# Run the cleaning function on the profile root
clean_ast(mp.profile)

# Verify the output
print(mp.profile)
