import unittest
import app_config


class AppConfigTest(unittest.TestCase):

    def test_prop(self):
        for x in dir(app_config):
            print(x)

    def test_prop_var(self):
        for x in vars(app_config):
            print(x)
