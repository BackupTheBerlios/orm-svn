#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -*- python -*-
#
#  File: conf.py
#  $Rev: 13 $
#  $Author: bsergean $
#  $Date: 2006-04-07 23:02:21 -0700 (Fri, 07 Apr 2006) $
#
#*****************************************************************************
# prefix is the directory prefix for the future downloaded media
# it can also be set with the ORMDIR env variable
# with bash: export ORMPREFIX=/home/mp3
# 
# settings format: <filename prefix>='<url>',
# <filename prefix> will be used to create the dir where each podcast are put
# ormMainDir is the prefix dir where the podcast specific dirs are created
#
# You can use a sharp (#) to comment a line
#
# Example:
#
# prefix = '/home/mp3'
# prefix = dict(
# orm='http://podcast.rtl.fr/onrefaitlematch.xml',
# )
#
# files will be created as /home/mp3/orm/orm-2006-03-21.mp3
# for the 2006-03-21 podcast
#*****************************************************************************

import os
import sys

# default dir on some platforms, see below for tuning
if sys.platform == 'darwin':
    prefix = os.path.expanduser('~/Desktop')
elif sys.platform == 'win32':
    prefix = 'C:/tmp'
else: # Unix ?
    prefix = os.path.expanduser('~')

prefix = os.environ.get('ORMDIR', prefix)

########
#
#  !!!! Dont touch anything before above :) !!!!
#
########

# if you want to tune it, uncomment here:
# prefix = '/home/mp3'
# prefix = '/perso/mp3/Divers/Divers - Divers'

# The main parameter
podcasts = dict(
#orm='http://podcast.rtl.fr/onrefaitlematch.xml',
#masque='http://radiofrance-podcast.net/podcast/rss_14007.xml',
#coffe='http://radiofrance-podcast.net/podcast/rss_10031.xml',
#fouduroi='http://radiofrance-podcast.net/podcast/rss_10048.xml',
#leplustot='http://radiofrance-podcast.net/podcast/rss_10030.xml',

test='http://marge1/~bsergean/pod.xml',
#test2='http://marge1/~bsergean/pod2.xml',
#test3='http://marge1/~bsergean/pod3.xml',
)
