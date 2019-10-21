from decimal import Decimal as _Decimal
from graphene import Decimal as OldDecimal


class Decimal(OldDecimal):
    @staticmethod
    def serialize(dec):
        if isinstance(dec, str):
            dec = _Decimal(dec)
            assert isinstance(
                dec, _Decimal
            ), 'Received not compatible Decimal "{}"'.format(repr(dec))
        return str(dec.normalize())
