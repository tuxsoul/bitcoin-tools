#
# Code for parsing transactions from the blkindex.dat file
#

from bsddb.db import *
import logging
from operator import itemgetter
import sys
import time

from BCDataStream import *
from base58 import public_key_to_bc_address, bc_address_to_hash_160
from util import short_hex
from deserialize import *

def _read_CDiskTxPos(stream):
  n_file = stream.read_uint32()
  n_block_pos = stream.read_uint32()
  n_tx_pos = stream.read_uint32()
  return (n_file, n_block_pos, n_tx_pos)

def dump_transactions(db_env, owner=None):
  db = DB(db_env)
  r = db.open("blkindex.dat", "main", DB_BTREE, DB_THREAD|DB_RDONLY)
  if r is not None:
    logging.error("Couldn't open blkindex.dat/main")
    sys.exit(1)

  kds = BCDataStream()
  vds = BCDataStream()

  cursor = db.cursor()
  
  start_key = "\x05owner"
  owner = None
  if owner is not None:
    owner_hash = bc_address_to_hash_160(owner) 
    start_key += owner_hash
  else:
    owner_hash = None

  try:
    (key, value) = cursor.set_range(start_key)
  except DBNotFoundError:
    print("No transactions for owner "+owner)
    return

  kds.clear(); kds.write(key)
  vds.clear(); vds.write(value)
  type = kds.read_string()

  while type == "owner":
      hash160 = kds.read_bytes(20)
      pos = _read_CDiskTxPos(vds)
      height = kds.read_int32()
      if owner_hash is not None and owner_hash != hash160:
        break
      print("TxOwner(%s: %d %d %d) height %d"%
            (hash_160_to_bc_address(hash160), pos[0], pos[1], pos[2], height))
      try:
        (key,value) = cursor.next()
        kds.clear(); kds.write(key)
        vds.clear(); vds.write(value)
        type = kds.read_string()
      except DBNotFoundError:
        break

  cursor.close()
  db.close()

