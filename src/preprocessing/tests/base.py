import os
from unittest import TestCase


class BaseTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.resource_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
