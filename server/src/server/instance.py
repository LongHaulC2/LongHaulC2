from dotenv import dotenv_values

# load dotenv
env_config = dotenv_values(".env")  # returns a dict
print(env_config)
