from django.test import TestCase

from common import exceptions
from common.phone import parse_phone


class CommonTestCase(TestCase):
    def test_parse_phone(self):
        parse_phone("+8613812345678")
        parse_phone("13812345678")

        with self.assertRaises(exceptions.InvalidPhone):
            parse_phone("13812345678", default_country=None)
            parse_phone("bad string")
