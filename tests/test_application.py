#
#   Testing if whole application is starting and ending correctly
#

from unittest import TestCase

import preparation
import app


class TestMainWindow(TestCase):

    app = None
    win = None

    def setUp(self):
        self.app, self.win = app.get_main_app()

    def tearDown(self):
        self.win.close()
        self.app.quit()

    def test_noop(self):
        pass
