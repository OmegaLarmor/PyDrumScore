import unittest
from drumscore.test.test_base import TestBase

# pylint: disable = missing-function-docstring, missing-class-docstring
class TestUtilities(TestBase):

    def test_text_feature(self):
        self.base_test_song("song_text")

    def test_tempo_feature(self):
        self.base_test_song("song_tempo_change")

if __name__ == '__main__':
    unittest.main()
