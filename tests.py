import time
import unittest

from web import CrappyCache


class TestCache(unittest.TestCase):

    def test_setget(self):

        cc = CrappyCache()
        cc["key"] = "val"

        self.assertEqual("val", cc["key"])

    def test_expiration(self):

        cc = CrappyCache(expiration=2)
        cc["key"] = "val"

        self.assertEqual("val", cc["key"])

        time.sleep(3)

        self.assertIsNone(cc["key"])


if __name__ == '__main__':
    unittest.main()
