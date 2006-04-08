#*****************************************************************************
# ormMainDir is the directory prefix for the future downloaded media
# 
# settings format: <filename prefix>,<url>
# <filename prefix> will be used to create the dir where each podcast are put
# ormMainDir is the prefix dir where the podcast specific dirs are created
#
# You can use a sharp (#) to comment a line
#
# !! Warning !! - dont use comma (',') since it is the field separator
#               - dont add a backslash escape sequence for special characters
#                 if you have space in the ormMainDir directory
# Example:
#
# ormMainDir = '/home/mp3'
# ormPodcastSettings = """
# orm,http://podcast.rtl.fr/onrefaitlematch.xml
# """
#
# files will be created as /home/mp3/orm/orm-2006-03-21.mp3
# for the 2006-03-21 podcast
#*****************************************************************************

import os
import sys

# default dir on some platforms, see below for tuning
if sys.platform == 'darwin':
    ormMainDir = os.path.expanduser('~/Desktop')
elif sys.platform == 'win32':
    ormMainDir = 'C:/tmp'
else: # Unix ?
    ormMainDir = os.path.expanduser('~')

########
#
#  Dont touch anything before above :)
#
########

# if you want to tune it, uncomment here:
# ormMainDir = '/home/mp3'
# ormMainDir = '/perso/mp3/Divers/Divers - Divers'

# The main parameter
ormPodcastSettings = """

orm,http://podcast.rtl.fr/onrefaitlematch.xml
masque,http://radiofrance-podcast.net/podcast/rss_14007.xml
coffe,http://radiofrance-podcast.net/podcast/rss_10031.xml
fouduroi,http://radiofrance-podcast.net/podcast/rss_10048.xml
leplustot,http://radiofrance-podcast.net/podcast/rss_10030.xml

#test,http://marge1/~bsergean/pod.xml
#test2,http://marge1/~bsergean/pod2.xml
#test3,http://marge1/~bsergean/pod3.xml
"""
