#
# Code for dumping a single block, given its ID (hash)
#

from bsddb.db import *
import logging
import os.path
import re
import sys
import time

from BCDataStream import *
from base58 import public_key_to_bc_address
from util import short_hex
from deserialize import *

def _open_blkindex(db_env):
  db = DB(db_env)
  try:
    r = db.open("blkindex.dat", "main", DB_BTREE, DB_THREAD|DB_RDONLY)
  except DBError:
    r = True
  if r is not None:
    logging.error("Couldn't open blkindex.dat/main.  Try quitting any running Bitcoin apps.")
    sys.exit(1)
  return db

def _read_CDiskTxPos(stream):
  n_file = stream.read_uint32()
  n_block_pos = stream.read_uint32()
  n_tx_pos = stream.read_uint32()
  return (n_file, n_block_pos, n_tx_pos)

def _dump_block(datadir, nFile, nBlockPos, hash256, hashNext, do_print=True):
  blockfile = open(os.path.join(datadir, "blk%04d.dat"%(nFile,)), "rb")
  ds = BCDataStream()
  ds.map_file(blockfile, nBlockPos)
  block_string = deserialize_Block(ds)
  ds.close_file()
  blockfile.close()
  if do_print:
    print "BLOCK "+hash256.encode('hex_codec')
    print "Next block: "+hashNext.encode('hex_codec')
    print block_string
  return block_string

def _deserialize_block_index(vds):
  result = {}
  result['version'] = vds.read_int32()
  result['hashNext'] = vds.read_bytes(32)
  result['nFile'] = vds.read_uint32()
  result['nBlockPos'] = vds.read_uint32()
  result['nHeight'] = vds.read_int32()

  result['b_version'] = vds.read_int32()
  result['hashPrev'] = vds.read_bytes(32)
  result['hashMerkle'] = vds.read_bytes(32)
  result['nTime'] = vds.read_int32()
  result['nBits'] = vds.read_int32()
  result['nNonce'] = vds.read_int32()
  return result

def dump_block(datadir, db_env, block_hash):
  """ Dump a block, given hexadecimal hash-- either the full hash
      OR a short_hex version of the it.
  """
  db = _open_blkindex(db_env)

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
    block_data = _deserialize_block_index(vds)

    if (hash256.encode('hex_codec')).startswith(block_hash) or short_hex(hash256).startswith(block_hash):
      print "Block height: "+str(block_data['nHeight'])
      _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'], hash256, block_data['hashNext'])

    (key, value) = cursor.next()

  db.close()

def read_block(db_cursor, hash):
  (key,value) = db_cursor.set_range("\x0ablockindex"+hash)
  vds = BCDataStream()
  vds.clear(); vds.write(value)
  block_data = _deserialize_block_index(vds)
  block_data['hash256'] = hash
  return block_data

def dump_block_n(datadir, db_env, block_number):
  """ Dump a block given block number (== height, genesis block is 0)
  """
  db = _open_blkindex(db_env)

  kds = BCDataStream()
  vds = BCDataStream()
  
  # Read the hashBestChain record:
  cursor = db.cursor()
  (key, value) = cursor.set_range("\x0dhashBestChain")
  vds.write(value)
  hashBestChain = vds.read_bytes(32)

  block_data = read_block(cursor, hashBestChain)

  while block_data['nHeight'] > block_number:
    block_data = read_block(cursor, block_data['hashPrev'])

  print "Block height: "+str(block_data['nHeight'])
  _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'], block_data['hash256'], block_data['hashNext'])

def search_blocks(datadir, db_env, pattern):
  """ Dump a block given block number (== height, genesis block is 0)
  """
  db = _open_blkindex(db_env)
  kds = BCDataStream()
  vds = BCDataStream()
  
  # Read the hashBestChain record:
  cursor = db.cursor()
  (key, value) = cursor.set_range("\x0dhashBestChain")
  vds.write(value)
  hashBestChain = vds.read_bytes(32)

  block_data = read_block(cursor, hashBestChain)
  while True:
    block_string = _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'],
                               block_data['hash256'], block_data['hashNext'], False)
    
    if re.search(pattern, block_string) is not None:
      print "MATCH: Block height: "+str(block_data['nHeight'])
      print block_string

    if block_data['nHeight'] == 0:
      break
    block_data = read_block(cursor, block_data['hashPrev'])
    

  
