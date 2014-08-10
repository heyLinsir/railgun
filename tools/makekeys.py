#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# @file: tools/makekeys.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Contributors:
#   public@korepwx.com   <public@korepwx.com>
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# This file is released under BSD 2-clause license.

import os
import string
import random

import nacl.secret


# make a new randomized key
def make_key(n):
    alphabet = string.letters + string.digits + string.punctuation
    return ''.join([
        random.choice(alphabet)
        for i in xrange(n)
    ])


# make a new keyfile
def create_keyfile(keyfile, keysize=32):
    dpath = os.path.dirname(keyfile)
    if (not os.path.isdir(dpath)):
        os.makedirs(dpath, 0700)
    with open(keyfile, 'wb') as f:
        f.write("%s\n" % make_key(keysize))
    os.chmod(keyfile, 0700)


create_keyfile('keys/commKey.txt', keysize=nacl.secret.SecretBox.KEY_SIZE)
create_keyfile('keys/webKey.txt')
