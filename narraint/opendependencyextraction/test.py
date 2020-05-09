import re

NUMBER_FIX_REGEX = re.compile(r"\d*,\d*")


test = "asdfasdf 324,231324 adsfasdf"

if NUMBER_FIX_REGEX.findall(test):
    print('hist')