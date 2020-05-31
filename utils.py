import pickle
import time
import os
import re
import platform

def detect_platform():
    p = 'Unknown'
    if platform.platform().find('Windows') != -1:
        p = 'Windows'
    elif platform.platform().find('Linux') != -1:
        p = 'Linux'
    return p

def list2csv(l):
    csv = ''
    for item in l:
        csv += str(item) + ','
    csv = csv[:-1]
    return csv


def remove_blank_in_endpoint(string):
    length = len(string)

    first_index = 0
    for i in range(length):
        if is_blank(string[first_index]):
            first_index += 1
        else:
            break

    last_index = length - 1
    for i in range(length):
        if is_blank(string[last_index]):
            last_index -= 1
        else:
            break
    last_index += 1
    return string[first_index:last_index]

def is_blank(ch):
    blank_ch = [' ', '\t', '\n']
    if ch in blank_ch:
        return True
    else:
        return False
