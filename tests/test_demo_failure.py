import unittest
class BrokenTest(unittest.TestCase):
    def test_demo_failure(self):
        self.assertEqual(1, 2, 'intentional CI test failure')
