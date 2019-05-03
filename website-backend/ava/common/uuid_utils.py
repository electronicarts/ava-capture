#
# Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved 
#


import uuid

# https://stackoverflow.com/questions/1181919/python-base-36-encoding/1181924
def base36encode(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    """Converts an integer to a base36 string."""
    if not isinstance(number, (int, long)):
        raise TypeError('number must be an integer')

    base36 = ''
    sign = ''

    if number < 0:
        sign = '-'
        number = -number

    if 0 <= number < len(alphabet):
        return sign + alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36

def uuid_node_base36():
    # Returns the computer's unique hardware address, encoded as base36
    return base36encode(uuid.getnode())
