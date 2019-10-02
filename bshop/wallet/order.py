from user_center.provider import get_open_id


def wechat_create_order(provider, code, amount):
    open_id = get_open_id(provider, code)


def alipay_create_order(code, amount):
    pass
