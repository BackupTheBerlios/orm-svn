#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -*- python -*-
#
#  File: orm.py
#  $Rev$
#  $Author$
#  $Date$
#
#*****************************************************************************
#
# See LICENSE file for licensing and to see where does some code come from
#
#*****************************************************************************
# !! orm podcatcher !!
# the name is taken from 'On Refaiiiiiiiiiit le match sur RTL'
# norm.py needs python 2.4
# orm.py should work with old python
#
# Features:
# - if file already exists dont download it
# - fetch several podcast
#
# Todo:
# - plug to GNUPod
# bash-3.00$ ORMDIR=/tmp python orm.py 2> /dev/null
# notnew     :/tmp/test/test-2006-03-21.mp3
#
# To import the new podcast:

# - Unit Testing.
#     Create a test.py file, a make test directive, put rss files with link on local dummy file:///files in
#     a test dir.
#     Get http server code from /usr/lib/python2.4/pydoc.py to start a webserver.
# - multiple date parsing schemes
# - write file mp3 tag
# - error handling
# - dont work if there are several podcast the same day => just add hour:minutes to the filename
# - create a thread for each download (see norm.py)
# - print server information
# - bad xml should yield errors
#
# Bugs:
# - Missing features ?
# - and others, send me an email (see LICENSE)
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

if sys.platform == 'win32':
	outfd = open('C:/tmp/message', 'w')
else:
	outfd = sys.stderr
	outfd = open('/tmp/message', 'w')
def log(msg):
	# we have to cast some type ('instance',
	# the error message from an exception), to print it
	outfd.write(str(msg) + '\n')
	outfd.flush()

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
	log("%s: %s\nFrom %s" % (os.path.basename(sys.argv[0]),
				 msg,
				 _functionId(1)))
	sys.exit(1)

class UrlCheckError(Exception):
	pass

def checkUrl(url, verbose):
	""" http://www.voidspace.org.uk/python/articles/urllib2.shtml """
	if verbose: log('checking url ...%s' % url)

	if not len(url):
		raise UrlCheckError, 'checkUrl: void url' 

	req = urllib2.Request(url)
	try:
		handle = urllib2.urlopen(req)
	except IOError:
		if verbose: log('... Error')
		raise UrlCheckError, 'checkUrl ' + url + ' : the requested url was not found' 
	else:
		if verbose: log('... OK')
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

class myURLOpener(urllib.FancyURLopener):
    """Create sub-class in order to overide error 206.  This error means a
       partial file is being sent,
       which is ok in this case.  Do nothing with this error.
    """
    def http_error_206(self, url, fp, errcode, errmsg, headers, data=None):
        pass

class UrlGrabError(Exception):
	pass

def urlGrab(url, dlFile, progressfunction, verbose = True):
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
				if verbose: log("File already downloaded")
		else:
			if verbose: log('download complete')
			webPage.close()
			outputFile.close()
			return 'old'

		# actually download the stuff
		totalSize = existSize + remoteFileSize
		numBytes = existSize
		while loop:
			data = webPage.read(8192)
			if not data:
				break
			outputFile.write(data)
			numBytes = numBytes + len(data)
			if callable(progressfunction):
				progressfunction(numBytes, totalSize)

	except UrlCheckError, error:
		errorMsg = 'urlGrab: Cannot fetch podcast media: %s\n' % (error)
		raise UrlGrabError, errorMsg
	else:
		webPage.close()
		outputFile.close()
		return 'new'

class dateObjFromStringError: pass
def dateObjFromString(text):
	""" http://pleac.sourceforge.net/pleac_python/datesandtimes.html """
        formats = [
        '%A %d %B %Y %Hh%M', # equipetv
        '%a, %d %b %Y %H:%M:%S PDT', # orm
        '%a, %d %b %Y %H:%M:%S +0200', # radio france
        ]
        for f in formats:
            try: 
	        timeobject = time.strptime(text, f)
                parsed = True
            except (ValueError): pass
        
        if not parsed:
            raise dateObjFromStringError

        return timeobject
        
class dateSortedMp3Lister(SGMLParser):
	"""
	The xml file is an <item> tag flat sibling

	<item>
		<title>Saccomano et son �quipe de sp�cialistes</title>
		<itunes:author>RTL.fr</itunes:author>
		<itunes:subtitle>L'�mission du 13/03/06</itunes:subtitle>
		<itunes:summary>Saccomano et son �quipe de sp�cialistes</itunes:summary>
		<itunes:category text="International">
			<itunes:category text="French"/>
		</itunes:category>
		<itunes:category text="News"/>
		<itunes:category text="Public Radio"/>
		<itunes:explicit>no</itunes:explicit>
		<itunes:keywords>RTL podcast</itunes:keywords>
		<description>Saccomano et son �quipe de sp�cialistes</description>
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
                self.contentType = ''

	def start_pubdate(self, attrs):
		self.handlePubDate = True
	def end_pubdate(self):
		self.handlePubDate = False

	def start_enclosure(self, attrs):
		# maybe there's a nicer way of getting the attribute.
		for attr in attrs:
			if attr[0] == "url":
				self.curUrl = attr[1]
                        if attr[0] == 'type':
                                self.contentType = attr[1]

	def start_item(self, attrs): pass
	def end_item(self):
		if self.curLastDate > self.lastDate:
			self.lastDate = self.curLastDate
			self.url = self.curUrl

	def handle_data(self, text):
		if self.handlePubDate:
                        try:
			        self.curLastDate = dateObjFromString(text)
                        except (dateObjFromStringError):
                                self.curLastDate = dateSortedMp3Lister.DC

def transferProgressHook(curbytes, total):
	if curbytes > total:
		sys.stderr.write('\rProgress: %s/%s\r' % (format_number(total), format_number(total)))
	else:
		sys.stderr.write('\rProgress: %s/%s' % (format_number(curbytes), format_number(total)))
		sys.stderr.flush()
		sys.stderr.write('\r' + ' ' * 80)

class podcastHandler:

	def __init__(self, prefix, filenamePrefix, podurl, transferProgressHook, verbose = True):
		self.verbose = verbose
		self.prefix = prefix
		self.filenamePrefix = filenamePrefix
		self.transferProgressHook = transferProgressHook
		self.podurl = podurl
		self.error = False
		self.errorMsg = ""

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
			# FIXME: bug here, we should have html = html.replace
			html.replace('pubDate','pubdate')
			htmlFD.close()
		
			self.htmlFD = StringIO.StringIO(html)
			
		except UrlCheckError, error:
			self.error = True
			self.errorMsg = '\nUrl check error %s\n' % (error)
			if self.verbose: log(self.errorMsg)

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

		# we try with the file extension:
		import urlparse
		path = urlparse.urlparse(self.parser.url)[2]
		ext = os.path.splitext(path)[1]
		if not len(ext):
			# try with mime: guess_extension returns None when it fails
			import mimetypes
			ext = mimetypes.guess_extension(self.parser.contentType)
			if not ext:
				# we fall back to our set of extension
				exts = {'audio/mpeg': '.mp3', 'video/mp4': '.mp4', 'video/mov': '.m4v'}
				ext = exts.get(self.parser.contentType, '.mp3') # there's only pirated music on the web :)
                
		dirName = os.path.join(self.prefix, self.filenamePrefix)
		if self.verbose: log('downloading[%s] %s\n' % (self.filenamePrefix, self.parser.url))
		output = self.filenamePrefix + '-' + time.strftime('%Y-%m-%d', self.parser.lastDate) + ext
		self.absoutput = os.path.join(dirName, output)
		try:
			self.absoutput = '%s:%s' % (urlGrab(self.parser.url, self.absoutput,
							    self.transferProgressHook, self.verbose),
						    self.absoutput)
			
		except UrlGrabError, error:
			self.error = False # leave a chance
			self.errorMsg = error
			if self.verbose: log(self.errorMsg)

	def download(self):
		self.getPodcastAndPreprocessIt()
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
                # fixme: Need to fix this for windows
                if sys.platform == 'win32':
                        _err_exit('configFilename default path not handled under Windows')
		configFilename = os.path.expanduser('~/.orm')
		if not os.path.exists(configFilename):
			raise SettingsError, 'no ~/.orm file: execute make install from the orm install root directory'
				
		code = open(configFilename).read() # FIXME: error handling
		if not len(code):
			raise SettingsError, 'Empty ~/.orm file: execute make install from the orm install root directory'
		
		confmodule = importCode(code, 'conf')

		if not hasattr(confmodule,'prefix'):
			raise SettingsError, 'missing prefix variable in the ~/.orm file'
                    
                if not hasattr(confmodule,'podcasts'):
			raise SettingsError, 'missing podcasts variable in the ~/.orm file'

		self.prefix = confmodule.prefix
		self.podcasts = confmodule.podcasts

if __name__ == "__main__":
	try:
		# complicatedFunctionFromTheFuture()
		verbose = True
		if verbose: log('Micoud est nul')
		s = settings()
		if verbose: log('orm prefix: %s' % s.prefix)
		
		for f, url in s.podcasts.iteritems():
			# create the podcast dir
			dirName = os.path.join(s.prefix, f)

			if not os.path.exists(dirName):
				try:
					os.makedirs(dirName)
				except OSError, error:
					raise SettingsError, "%s\nCannot create %s" % (error, dirName)

			downloader = podcastHandler(s.prefix, f, url, transferProgressHook, verbose)
			downloader.download()
			if not downloader.error:
				print downloader.absoutput

		if verbose: log('\nnul. completement nul')

	except SettingsError, e:
		_err_exit('Error: %s\n' % (e))

	except (KeyboardInterrupt):
		_err_exit("\nMais pourquoi. Pourquoi ?\n")

