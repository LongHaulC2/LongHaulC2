'''
Test template generation for the implants.

Steps:


1: Python logic for which options, files needed etc.
2. Format code blocks with data (callback, transforms, data location, etc)
3. Paste into build files (ex, [[http_get_block]])



'''







from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pathlib import Path
# 1. Setup Jinja with C++ safe delimiters
env = Environment(
    loader=FileSystemLoader('.'),
    # distinct brackets to avoid C++ conflicts
    block_start_string='[%',
    block_end_string='%]',
    variable_start_string='[[',
    variable_end_string=']]',
    comment_start_string='[#',
    comment_end_string='#]',
    # clean up whitespace so generated code looks pro
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=StrictUndefined # Fail fast if a var is missing
)

# test workflow here
OUTPUT_DIR = Path("./templates/output")
CODE_DIR = Path("implant_base")
TEMPLATE_DIR = Path("./templates")

#pretend malc2 settings ig
#Step 2: Format blocks....
with open(str(TEMPLATE_DIR / "wininet_http_get.j2"), "r") as http_get_file:
    # settings here
    context = {
        "client_metadata_http_header": True,
        
        "client_metadata_header": "utmcc",

        "client_metadata_http_print": None

    }

    t = http_get_file.read()
    http_comms_template = env.from_string(t)
    # can also use env.get_tempalte for a file 
    rendered_code = http_comms_template.render(**context)

    with open(str(OUTPUT_DIR / "wininet_http_get.cpp"), "w") as output:
        output.write(rendered_code)



# step 3... paste into build files.
'''
Open file (ex, comms.h)

template render (http_get_block/whatever else) 

save back to that file

'''