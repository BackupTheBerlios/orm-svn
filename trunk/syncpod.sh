#!/usr/bin/bash
# -*- coding: iso-8859-1 -*-
# -*- python -*-
#
#  File: syncpod.sh
#  $Rev: 17 $
#  $Author: bsergean $
#  $Date: 2006-04-08 20:05:37 -0400 (Sat, 08 Apr 2006) $
#
#*****************************************************************************
#
# See LICENSE file for licensing and to see where does some code come from
#
#*****************************************************************************
# Should (not tested, be really carefull !!) sync your ipod with 
# not functional yet.

# tune me
export ORMDIR=$HOME
export IPOD_MOUNTPOINT=/mnt/ipod

# add the new song
python orm.py 2> /dev/null | awk -F: '$1 ~ /new/ {print $2}' | xargs gnupod_addsong.pl