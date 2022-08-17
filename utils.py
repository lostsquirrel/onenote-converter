import os
import pathlib
import app_config
from dotenv import dotenv_values


def load_env_file():
    current_path = pathlib.Path(__file__).parent.resolve()
    env_path = os.path.join(current_path, '.env')
    config = dotenv_values(env_path)
    for x in vars(app_config):
        if x.isupper():
            x = x.strip()
            if x in config:
                setattr(app_config, x, config[x].strip())
