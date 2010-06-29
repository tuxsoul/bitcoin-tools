#
# Code for parsing the blkindex.dat file
#

from bsddb.db import *
import logging
from operator import itemgetter
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

def dump_blockindex(db_env, owner=None, n_to_dump=1000):
  db = DB(db_env)
  r = db.open("blkindex.dat", "main", DB_BTREE, DB_THREAD|DB_RDONLY)
  if r is not None:
    logging.error("Couldn't open blkindex.dat/main")
    sys.exit(1)

  kds = BCDataStream()
  vds = BCDataStream()

  wallet_transactions = []

  for (i, (key, value)) in enumerate(db.items()):
    if i > n_to_dump:
      break

    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_string()

    if type == "owner":
      k_hash160 = kds.read_bytes(20)
      k_pos = _read_CDiskTxPos(vds)

      type_v = vds.read_string()
      if type_v == "owner":
        v_hash160 = kds.read_bytes(20)
        v_pos = _read_CDiskTxPos(kds)
        height = kds.read_int32()
      else:
        logging.warn("tx owner, unknown value type: %s"%(type_v,))
        continue
      print("TxOwner(%s: %d %d %d) for %s, at (%d %d %d) height %d"%
            (hash_160_to_bc_address(k_hash160), k_pos[0], k_pos[1], k_pos[2],
             hash_160_to_bc_address(v_hash160), v_pos[0], v_pos[1], v_pos[2], height))
    elif type == "tx":
      hash256 = kds.read_bytes(32)
      version = vds.read_uint32()
      tx_pos = _read_CDiskTxPos(vds)
      print("Tx(%s:%d %d %d)"%((short_hex(hash256),)+tx_pos))
      n_tx_out = vds.read_compact_size()
      for i in range(0,n_tx_out):
        tx_out = _read_CDiskTxPos(vds)
        if tx_out[0] != 0xffffffffL:
          print("  ==> TxOut(%d %d %d)"%tx_out)
      
    else:
      logging.warn("blkindex: type %s"%(type,))
      continue

  db.close()

