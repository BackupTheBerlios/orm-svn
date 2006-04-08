#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -*- python -*-
#
#  $HeadURL$
#  $Rev$
#  $Author$
#  $Date$
#
#*****************************************************************************
#
#  Copyright (c) 2006 Benjamin Sergeant (bsergean at gmail dot com)
#
#  progress bar code stolen from yum:
#  http://linux.duke.edu/projects/yum/
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
# standalone podcast downloader
# the name is taken from 'On Refaiiiiiiiiiit le match sur RTL'
# tested on Linux with python 2.4 but should work with older versions
#
# Features:
# - if file already exists dont download it
# - fetch several podcast
# - dont create anything on your disk apart from the downloaded podcasts
#
# Todo:
# - error handling
# - detect extension file (.aac ?) for creating the correct filename
# - dont work if there are several podcast the same day
# - create a thread for each download (progress method then ?)
# - print server information
# - bad xml should yield errors
#
# Bugs:
# - When download is canceled by KeyInterupt the message 'filename' saved is
#   printed
#*****************************************************************************

__version__ = "orm 0.1"

import sys
import os
import urllib
import time
from sgmllib import SGMLParser
import StringIO
import urllib2

try: import locale; locale.setlocale(locale.LC_ALL, "")
except: pass

# see http://www.nedbatchelder.com/blog/200410.html#e20041003T074926
def _functionId(nFramesUp):
        """ Create a string naming the function n frames up on the stack.
        """
        co = sys._getframe(nFramesUp+1).f_code
        return "%s (%s @ %d)" % (co.co_name, co.co_filename, co.co_firstlineno)

def notYetImplemented():
        """ Call this function to indicate that a method isn't implemented yet.
        """
        raise Exception("Not yet implemented: %s" % _functionId(1))

def complicatedFunctionFromTheFuture():
        notYetImplemented()

def _err_exit(msg):
	""" to exit from program on an error with a formated message """
	sys.stderr.write("%s: %s\nFrom %s\n" % (os.path.basename(sys.argv[0]),
					      msg,
					      _functionId(1)))
	sys.exit(1)

class UrlCheckError(Exception):
	pass

def checkUrl(url, verbose):
	""" http://www.voidspace.org.uk/python/articles/urllib2.shtml """
	if verbose: print 'checking url ...', url

	if not len(url):
		raise UrlCheckError, 'checkUrl: void url' 

	req = urllib2.Request(url)
	try:
		handle = urllib2.urlopen(req)
	except IOError:
		if verbose: print '... Error'
		raise UrlCheckError, 'checkUrl ' + url + ' : the requested url was not found'
	else:
		if verbose: print '... OK'
		handle.close()

def format_number(number, SI=0, space=' '):
	"""(yum) Turn numbers into human-readable metric-like numbers"""
	symbols = ['', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
	# (none), kilo, mega, giga, tera, peta, exa, zetta, yotta

	if SI: step = 1000.0
	else: step = 1024.0

	thresh = 999
	depth = 0

	# we want numbers between
	while number > thresh:
		depth  = depth + 1
		number = number / step

	# just in case someone needs more than 1000 yottabytes!
	diff = depth - len(symbols) + 1
	if diff > 0:
		depth = depth - diff
		number = number * thresh**depth

	if type(number) == type(1) or type(number) == type(1L):
		format = '%i%s%s'
	elif number < 9.95:
		# must use 9.95 for proper sizing.  For example, 9.99 will be
		# rounded to 10.0 with the .1f format string (which is too long)
		format = '%.1f%s%s'
	else:
		format = '%.0f%s%s'

	return(format % (number, space, symbols[depth]))

def transferProgressHook(curbytes, total):
	if curbytes > total:
		sys.stdout.write('\rProgress: %s/%s\r' % (format_number(total), format_number(total)))
	else:
		sys.stdout.write('\rProgress: %s/%s' % (format_number(curbytes), format_number(total)))
		sys.stdout.flush()
		sys.stdout.write('\r' + ' ' * 80)

class myURLOpener(urllib.FancyURLopener):
    """Create sub-class in order to overide error 206.  This error means a
       partial file is being sent,
       which is ok in this case.  Do nothing with this error.
    """
    def http_error_206(self, url, fp, errcode, errmsg, headers, data=None):
        pass

class UrlGrabError(Exception):
	pass

def urlGrab(url, dlFile, progressfunction = transferProgressHook, verbose = True):
	loop = 1
	
	existSize = 0
	myUrlclass = myURLOpener()
	if os.path.exists(dlFile):
		outputFile = open(dlFile,"ab")
		existSize = os.path.getsize(dlFile)
                #If the file exists, then only download the remainder
		myUrlclass.addheader("Range","bytes=%s-" % (existSize))
	else:
		outputFile = open(dlFile,"wb")

	try:
		checkUrl(url, verbose)
		webPage = myUrlclass.open(url)

                # If the file exists, but we already have the
		# whole thing, don't download again
		if webPage.headers.has_key('Content-Length'):
			remoteFileSize = int(webPage.headers['Content-Length'])
			if remoteFileSize == existSize:
				loop = 0
				# FIXME: looks like we never go
				# here but don't download a file twice either ...
				if verbose: print "File already downloaded"
		else:
			if verbose: print 'download complete'
			webPage.close()
			outputFile.close()
			return

		# actually download the stuff
		totalSize = existSize + remoteFileSize
		numBytes = existSize
		while loop:
			data = webPage.read(8192)
			if not data:
				break
			outputFile.write(data)
			numBytes = numBytes + len(data)
			progressfunction(numBytes, totalSize)

	except UrlCheckError, error:
		errorMsg = 'urlGrab: Cannot fetch podcast media: %s\n' % (error)
		raise UrlGrabError, errorMsg
	else:
		webPage.close()
		outputFile.close()

def dateObjFromString(text):
	""" http://pleac.sourceforge.net/pleac_python/datesandtimes.html """
	# we get rid of the last token which differ depending on podcasts
	# and give the rest to strptime
	return time.strptime((' ').join(text.split()[0:-1]), '%a, %d %b %Y %H:%M:%S')

class dateSortedMp3Lister(SGMLParser):
	"""
	The xml file is an <item> tag flat sibling

	<item>
		<title>Saccomano et son équipe de spécialistes</title>
		<itunes:author>RTL.fr</itunes:author>
		<itunes:subtitle>L'émission du 13/03/06</itunes:subtitle>
		<itunes:summary>Saccomano et son équipe de spécialistes</itunes:summary>
		<itunes:category text="International">
			<itunes:category text="French"/>
		</itunes:category>
		<itunes:category text="News"/>
		<itunes:category text="Public Radio"/>
		<itunes:explicit>no</itunes:explicit>
		<itunes:keywords>RTL podcast</itunes:keywords>
		<description>Saccomano et son équipe de spécialistes</description>
		<enclosure url="http://blabla.html" length="2870" type="audio/mpeg"/>
		<guid>
			http://blabla.html
		</guid>
		<link>http://www.rtl.fr/</link>
		<author>webmaster@rtl.fr</author>
		<pubDate>Tue, 14 Mar 2006 17:00:04 PDT</pubDate>
	</item>
	"""

	DC = (0, 0, 0,    0, 0, 0,    0, 0, 0)

	def reset(self):
		SGMLParser.reset(self)
		self.handlePubDate = False
		#self.lastDate = dateObjFromString(dateSortedMp3Lister.DC)
		#self.curLastDate = dateObjFromString(dateSortedMp3Lister.DC)
		self.lastDate = dateSortedMp3Lister.DC
		self.curLastDate = dateSortedMp3Lister.DC
		
		self.url = ''
		self.curUrl = ''

	def start_pubdate(self, attrs):
		self.handlePubDate = True
	def end_pubdate(self):
		self.handlePubDate = False

	def start_enclosure(self, attrs):
		# maybe there's a nicer way of getting the attribute.
		for attr in attrs:
			if attr[0] == "url":
				self.curUrl = attr[1]
				break

	def start_item(self, attrs): pass
	def end_item(self):
		if self.curLastDate > self.lastDate:
			self.lastDate = self.curLastDate
			self.url = self.curUrl

	def handle_data(self, text):
		if self.handlePubDate:
			self.curLastDate = dateObjFromString(text)

class podcastHandler:

	def __init__(self, prefix, filenamePrefix, podurl, verbose = True):
		self.verbose = verbose
		self.prefix = prefix
		self.filenamePrefix = filenamePrefix
		self.podurl = podurl
		self.error = False
		self.errorMsg = ""
		self.getPodcastAndPreprocessIt()

	def getPodcastAndPreprocessIt(self):
		"""
		fetch the podcast.xml file and 'sed' him like
		sed 's/pubDate/pubdate/g' < onrefaitlematch.xml
		since sgmllib cannot lookup pubDate tag start (bug ??)
		"""
		try:
			checkUrl(self.podurl, self.verbose)
			htmlFD = urllib.urlopen(self.podurl)

			# sed
			html = htmlFD.read()
			html.replace('pubDate','pubdate')
			htmlFD.close()
		
			self.htmlFD = StringIO.StringIO(html)
			
		except UrlCheckError, error:
			self.error = True
			self.errorMsg = '\nUrl check error %s\n' % (error)
			if self.verbose: print self.errorMsg

	def parsePC(self):
		"""
		Parse the podcast and download the mp3.
		"""
		if self.error: return
		
		self.parser = dateSortedMp3Lister()
		self.parser.feed(self.htmlFD.read())
		self.parser.close()

	def downloadContent(self):
		if self.error: return
		
		dirName = os.path.join(self.prefix, self.filenamePrefix)
		if self.verbose: print 'downloading[%s] %s\n' % (self.filenamePrefix, self.parser.url)
		output = self.filenamePrefix + '-' + time.strftime('%Y-%m-%d', self.parser.lastDate) + '.mp3'
		try:
			urlGrab(self.parser.url,
				os.path.join(dirName, output),
				transferProgressHook, self.verbose)
		except UrlGrabError, error:
			self.error = False # leave a chance
			self.errorMsg = error
			if self.verbose: print self.errorMsg

	def download(self):
		if not self.error and not self.htmlFD.closed:
			self.parsePC()
			self.downloadContent()
			self.htmlFD.close()

def importCode(code, name):
	import new
	module = new.module(name)
	exec code in module.__dict__
	return module

# FIXME: minor case class name
class SettingsError(Exception):
	pass

class settings:

	def __init__(self):

		# we need to find from where we were started
		# we cheat for now, just take the hard coded path
		# configFilename = '/home/bsergean/src/Prog/orm/trunk/conf.py'
		configFilename = os.path.expanduser('~/.orm')
		if not os.path.exists(configFilename):
			raise SettingsError, 'no ~/.orm file: execute make install from the orm install root directory'
				
		code = open(configFilename).read() # FIXME: error handling
		if not len(code):
			raise SettingsError, 'Empty ~/.orm file: execute make install from the orm install root directory'
		
		confmodule = importCode(code, 'conf')

		if not hasattr(confmodule,'ormMainDir') or \
		       not hasattr(confmodule,'ormPodcastSettings'):
			raise SettingsError, 'Corrupted ~/.orm file: repare or get a new one by executing make install from the orm install root directory'

		self.ormMainDir = confmodule.ormMainDir
		self.ormPodcastSettings = confmodule.ormPodcastSettings

		settingsFD = StringIO.StringIO(self.ormPodcastSettings)

		self.podcasts = {}
		for line in settingsFD.readlines():
			line = line.strip()
			if not len(line) or line.startswith('#'):
				continue
			tokens = line.split(',')
			if len(tokens) != 2:
				continue
			filenamePrefix = tokens[0]
			podurl = tokens[1]

			# create the podcast dir
			dirName = os.path.join(self.ormMainDir, filenamePrefix)

			if not os.path.exists(dirName):
				try:
					os.makedirs(dirName)
				except OSError, error:
					_err_exit("%s\nCannot create %s: Exiting\n" % (error, dirName))

			self.podcasts[filenamePrefix] = podurl

		settingsFD.close()

if __name__ == "__main__":
	try:
		# complicatedFunctionFromTheFuture()
		verbose = True
		if verbose: print 'Micoud est nul'

		s = settings()
		
		for k, v in s.podcasts.iteritems():
			downloader = podcastHandler(prefix = s.ormMainDir,
				                    filenamePrefix = k,
						    podurl = v,
						    verbose = verbose)
			downloader.download()

		if verbose: print 'nul. completement nul'

	except SettingsError, e:
		_err_exit('Error: %s\n' % (e))

	except (KeyboardInterrupt):
		_err_exit("\nMais pourquoi. Pourquoi ?\n")

