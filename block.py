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
from util import short_hex, long_hex
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
    print "BLOCK "+long_hex(hash256[::-1])
    print "Next block: "+long_hex(hashNext[::-1])
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

  n_blockindex = 0

  key_prefix = "\x0ablockindex"
  cursor = db.cursor()
  (key, value) = cursor.set_range(key_prefix)

  while key.startswith(key_prefix):
    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_string()
    hash256 = kds.read_bytes(32)
    hash_hex = long_hex(hash256[::-1])
    block_data = _deserialize_block_index(vds)

    if (hash_hex.startswith(block_hash) or short_hex(hash256[::-1]).startswith(block_hash)):
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

  if pattern == "NONSTANDARD_CSCRIPTS": # Hack to look for non-standard transactions
    search_odd_scripts(datadir, cursor, block_data)
    return

  while True:
    block_string = _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'],
                               block_data['hash256'], block_data['hashNext'], False)
    
    if re.search(pattern, block_string) is not None:
      print "MATCH: Block height: "+str(block_data['nHeight'])
      print block_string

    if block_data['nHeight'] == 0:
      break
    block_data = read_block(cursor, block_data['hashPrev'])
    
def search_odd_scripts(datadir, cursor, block_data):
  """ Look for non-standard transactions """
  while True:
    block_string = _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'],
                               block_data['hash256'], block_data['hashNext'], False)
    
    found_nonstandard = False
    for m in re.finditer("'TxIn:(.*?)'", block_string):
      s = m.group(1)
      if re.match(r'\s*COIN GENERATED coinbase:\w+$', s): continue
      if re.match(r'.*sig: \d+:\w+...\w+ \d+:\w+...\w+$', s): continue
      if re.match(r'.*sig: \d+:\w+...\w+$', s): continue
      print "Nonstandard TxIn: "+s
      found_nonstandard = True
      break

    for m in re.finditer("'TxOut:(.*?)'", block_string):
      s = m.group(1)
      if re.match(r'.*Script: DUP HASH160 \d+:\w+...\w+ EQUALVERIFY CHECKSIG$', s): continue
      if re.match(r'.*Script: \d+:\w+...\w+ CHECKSIG$', s): continue
      print "Nonstandard TxOut: "+s
      found_nonstandard = True
      break

    if found_nonstandard:
      print "NONSTANDARD TXN: Block height: "+str(block_data['nHeight'])
      print block_string

    if block_data['nHeight'] == 0:
      break
    block_data = read_block(cursor, block_data['hashPrev'])
  
def check_block_chain(db_env):
  """ Make sure hashPrev/hashNext pointers are consistent through block chain """
  db = _open_blkindex(db_env)

  kds = BCDataStream()
  vds = BCDataStream()
  
  # Read the hashBestChain record:
  cursor = db.cursor()
  (key, value) = cursor.set_range("\x0dhashBestChain")
  vds.write(value)
  hashBestChain = vds.read_bytes(32)

  back_blocks = []

  block_data = read_block(cursor, hashBestChain)

  while block_data['nHeight'] > 0:
    back_blocks.append( (block_data['nHeight'], block_data['hashMerkle'], block_data['hashPrev'], block_data['hashNext']) )
    block_data = read_block(cursor, block_data['hashPrev'])

  back_blocks.append( (block_data['nHeight'], block_data['hashMerkle'], block_data['hashPrev'], block_data['hashNext']) )
  genesis_block = block_data
  
  print("check block chain: genesis block merkle hash is: %s"%(block_data['hashMerkle'][::-1].encode('hex_codec')))

  while block_data['hashNext'] != ('\0'*32):
    forward = (block_data['nHeight'], block_data['hashMerkle'], block_data['hashPrev'], block_data['hashNext'])
    back = back_blocks.pop()
    if forward != back:
      print("Forward/back block mismatch at height %d!"%(block_data['nHeight'],))
      print(" Forward: "+str(forward))
      print(" Back: "+str(back))
    block_data = read_block(cursor, block_data['hashNext'])
