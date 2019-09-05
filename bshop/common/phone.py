import phonenumbers
from common import exceptions


def parse_phone(phone, default_country="CN"):

    try:
        p = phonenumbers.parse(phone, default_country)
    except phonenumbers.phonenumberutil.NumberParseException:
        raise exceptions.InvalidPhone

    if p.country_code == 86 and len(str(p.national_number)) != 11:
        raise exceptions.InvalidPhone
    phone = phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.E164)
    return phone
