#
# Misc util routines
#

def long_hex(bytes):
  return bytes.encode('hex_codec')

def short_hex(bytes):
  t = bytes.encode('hex_codec')
  if len(t) < 11:
    return t
  return t[0:4]+"..."+t[-4:]

