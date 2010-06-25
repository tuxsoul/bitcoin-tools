Run    dbdump.py --help    for usage.  Database files are opened read-only, but
you might want to backup your Bitcoin wallet.dat file just in case.

Requires the pycrypto library from  http://www.dlitz.net/software/pycrypto/
to translate public keys into human-friendly Bitcoin addresses.

TODO: anybody want to volunteer to write code to dump out sections of the blkindex.dat/blk000n.dat block data files?
It should be fairly straightforward to reverse engineer from the Bitcoin source...

