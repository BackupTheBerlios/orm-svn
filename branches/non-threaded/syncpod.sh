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
#  Copyright (c) 2006 Benjamin Sergeant (bsergean at gmail dot com)
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License version 2, as
#  published by the Free Software Foundation.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
#*****************************************************************************

#*****************************************************************************
# Should (not tested :) sync your ipod with 
# not functional yet.

# tune me
export ORMDIR=$HOME
export IPOD_MOUNTPOINT=/mnt/ipod

# add the new song
python orm.py 2> /dev/null | awk -F: '$1 ~ /new/ {print $2}' | xargs gnupod_addsong.pl