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


class Exchange(EnumChoice):
    BINANCE = "binance"
    HUOBI = "huobipro"
    OKEX = "okex"


class FiatCurrency(EnumChoice):
    USD = "USD"
    CNY = "CNY"


class LabelType(EnumChoice):
    CURRENCY = "CURRENCY"
    EVENT = "EVENT"


class CredentialStatus(EnumChoice):
    NORMAL = "normal"
    ERROR = "error"


class DeviceType(EnumChoice):
    IOS = "ios"
    ANDROID = "android"


class Amount(graphene.ObjectType):
    amount = graphene.String()
    sign = graphene.String()
    unit = graphene.String()

    @classmethod
    def from_json(cls, d):
        return cls(amount=d["amount"], sign=d["sign"], unit=d["unit"])
