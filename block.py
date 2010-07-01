#
# Code for dumping a single block, given its ID (hash)
#

from bsddb.db import *
import logging
import os.path
import sys
import time

from BCDataStream import *
from base58 import public_key_to_bc_address
from util import short_hex
from deserialize import *

def _read_CDiskTxPos(stream):
  n_file = stream.read_uint32()
  n_block_pos = stream.read_uint32()
  n_tx_pos = stream.read_uint32()
  return (n_file, n_block_pos, n_tx_pos)

def _dump_block(datadir, nFile, nBlockPos, hash256, hashNext):
  blockfile = open(os.path.join(datadir, "blk%04d.dat"%(nFile,)), "rb")
  ds = BCDataStream()
  ds.map_file(blockfile, nBlockPos)
  print "BLOCK "+hash256.encode('hex_codec')
  print "Next block: "+hashNext.encode('hex_codec')
  print deserialize_Block(ds)
  ds.close_file()
  blockfile.close()

def dump_block(datadir, db_env, block_hash):
  """ Dump a block, given hexadecimal hash-- either the full hash
      OR a short_hex version of the it.
  """
  db = DB(db_env)
  try:
    r = db.open("blkindex.dat", "main", DB_BTREE, DB_THREAD|DB_RDONLY)
  except DBError:
    r = True

  if r is not None:
    logging.error("Couldn't open blkindex.dat/main.  Try quitting any running Bitcoin apps.")
    sys.exit(1)

  kds = BCDataStream()
  vds = BCDataStream()

  n_tx = 0
  n_blockindex = 0

  key_prefix = "\x0ablockindex"+(block_hash[0:4].decode('hex_codec'))
  cursor = db.cursor()
  (key, value) = cursor.set_range(key_prefix)

  while key.startswith(key_prefix):
    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_string()
    hash256 = kds.read_bytes(32)
    version = vds.read_int32()
    hashNext = vds.read_bytes(32)
    nFile = vds.read_uint32()
    nBlockPos = vds.read_uint32()
    nHeight = vds.read_int32()

    b_version = vds.read_int32()
    hashPrev = vds.read_bytes(32)
    hashMerkle = vds.read_bytes(32)
    nTime = vds.read_int32()
    nBits = vds.read_int32()
    nNonce = vds.read_int32()

    if (hash256.encode('hex_codec')).startswith(block_hash) or short_hex(hash256).startswith(block_hash):
      _dump_block(datadir, nFile, nBlockPos, hash256, hashNext)

    (key, value) = cursor.next()

  db.close()

