import graphene


class Result(graphene.ObjectType):
    success = graphene.Boolean()
    message = graphene.String()


class PageInfo(graphene.ObjectType):
    start_cursor = graphene.String(default_value="")
    end_cursor = graphene.String(default_value="")
    has_next_page = graphene.Boolean(default_value=False)
    has_prev_page = graphene.Boolean(default_value=False)
    total_count = graphene.Int(default_value=0)


class EnumChoice(graphene.Enum):
    @classmethod
    def values(cls):
        choices = []
        for _, v in cls.__enum__.__members__.items():
            choices.append(v.value)
        return choices


class LoginProvider(EnumChoice):
    WECHAT = "WECHAT"
    ALIPAY = "ALIPAY"


class FiatCurrency(EnumChoice):
    USD = "USD"
    CNY = "CNY"


# https://pay.weixin.qq.com/wiki/doc/api/wxa/wxa_api.php?chapter=9_2
class OrderState(EnumChoice):
    SUCCESS = "SUCCESS"
    NOTPAY = "NOTPAY"
    USERPAYING = "USERPAYING"
    REFUND = "REFUND"
    PAYERROR = "PAYERROR"


class Amount(graphene.ObjectType):
    amount = graphene.String()
    sign = graphene.String()
    unit = graphene.String()

    @classmethod
    def from_json(cls, d):
        return cls(amount=d["amount"], sign=d["sign"], unit=d["unit"])
