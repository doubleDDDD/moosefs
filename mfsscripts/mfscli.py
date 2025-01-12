#!/usr/bin/env python3

# Copyright (C) 2021 Jakub Kruszona-Zawadzki, Core Technology Sp. z o.o.
# 
# This file is part of MooseFS.
# 
# MooseFS is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 (only).
# 
# MooseFS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with MooseFS; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02111-1301, USA
# or visit http://www.gnu.org/licenses/gpl-2.0.html

PROTO_BASE = 0

VERSION = "3.0.116"

#some constants from MFSCommunication.h
CLTOMA_CSERV_LIST = (PROTO_BASE+500)
MATOCL_CSERV_LIST = (PROTO_BASE+501)
CLTOAN_CHART_DATA = (PROTO_BASE+506)
ANTOCL_CHART_DATA = (PROTO_BASE+507)
CLTOMA_SESSION_LIST = (PROTO_BASE+508)
MATOCL_SESSION_LIST = (PROTO_BASE+509)
CLTOMA_INFO = (PROTO_BASE+510)
MATOCL_INFO = (PROTO_BASE+511)
CLTOMA_FSTEST_INFO = (PROTO_BASE+512)
MATOCL_FSTEST_INFO = (PROTO_BASE+513)
CLTOMA_CHUNKSTEST_INFO = (PROTO_BASE+514)
MATOCL_CHUNKSTEST_INFO = (PROTO_BASE+515)
CLTOMA_CHUNKS_MATRIX = (PROTO_BASE+516)
MATOCL_CHUNKS_MATRIX = (PROTO_BASE+517)
CLTOMA_QUOTA_INFO = (PROTO_BASE+518)
MATOCL_QUOTA_INFO = (PROTO_BASE+519)
CLTOMA_EXPORTS_INFO = (PROTO_BASE+520)
MATOCL_EXPORTS_INFO = (PROTO_BASE+521)
CLTOMA_MLOG_LIST = (PROTO_BASE+522)
MATOCL_MLOG_LIST = (PROTO_BASE+523)
CLTOMA_CSSERV_COMMAND = (PROTO_BASE+524)
MATOCL_CSSERV_COMMAND = (PROTO_BASE+525)
CLTOMA_SESSION_COMMAND = (PROTO_BASE+526)
MATOCL_SESSION_COMMAND = (PROTO_BASE+527)
CLTOMA_MEMORY_INFO = (PROTO_BASE+528)
MATOCL_MEMORY_INFO = (PROTO_BASE+529)
CLTOMA_LIST_OPEN_FILES = (PROTO_BASE+532)
MATOCL_LIST_OPEN_FILES = (PROTO_BASE+533)
CLTOMA_LIST_ACQUIRED_LOCKS = (PROTO_BASE+534)
MATOCL_LIST_ACQUIRED_LOCKS = (PROTO_BASE+535)
CLTOMA_MASS_RESOLVE_PATHS = (PROTO_BASE+536)
MATOCL_MASS_RESOLVE_PATHS = (PROTO_BASE+537)
CLTOMA_SCLASS_INFO = (PROTO_BASE+542)
MATOCL_SCLASS_INFO = (PROTO_BASE+543)
CLTOMA_MISSING_CHUNKS = (PROTO_BASE+544)
MATOCL_MISSING_CHUNKS = (PROTO_BASE+545)

CLTOCS_HDD_LIST = (PROTO_BASE+600)
CSTOCL_HDD_LIST = (PROTO_BASE+601)

MFS_MESSAGE = 1

FEATURE_EXPORT_UMASK = 0
FEATURE_EXPORT_DISABLES = 1

MASKORGROUP = 4

MFS_CSSERV_COMMAND_REMOVE = 0
MFS_CSSERV_COMMAND_BACKTOWORK = 1
MFS_CSSERV_COMMAND_MAINTENANCEON = 2
MFS_CSSERV_COMMAND_MAINTENANCEOFF = 3
MFS_CSSERV_COMMAND_TMPREMOVE = 4

MFS_SESSION_COMMAND_REMOVE = 0

STATUS_OK = 0
ERROR_NOTFOUND = 41
ERROR_ACTIVE = 42

STATE_DUMMY = 0
STATE_LEADER = 1
STATE_ELECT = 2
STATE_FOLLOWER = 3
STATE_USURPER = 4

UNRESOLVED = "(unresolved)"

import socket
import struct
import time
import sys
import traceback
import os
import subprocess
import codecs
import json

cgimode = 1 if 'GATEWAY_INTERFACE' in os.environ else 0

try:
	xrange
except NameError:
	xrange = range

def myunicode(x):
	if sys.version_info[0]<3:
		return unicode(x)
	else:
		return str(x)

#parse parameters and auxilinary functions
if cgimode:
	# in CGI mode set default output encoding to utf-8 (our html page encoding)
	if sys.version_info[0]<3:
		sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
	elif sys.version_info[1]<7:
		sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
	else:
		sys.stdout.reconfigure(encoding='utf-8')

	try:
		import urllib.parse as xurllib
	except ImportError:
		import urllib as xurllib
	import cgi
	import cgitb

	cgitb.enable()

	fields = cgi.FieldStorage()

	try:
		if "masterhost" in fields:
			masterhost = fields.getvalue("masterhost")
		else:
			masterhost = 'mfsmaster'
	except Exception:
		masterhost = 'mfsmaster'
	try:
		masterport = int(fields.getvalue("masterport"))
	except Exception:
		masterport = 9421
	try:
		mastercontrolport = int(fields.getvalue("mastercontrolport"))
	except Exception:
		try:
			mastercontrolport = int(fields.getvalue("masterport"))-2
		except Exception:
			mastercontrolport = 9419
	try:
		if "mastername" in fields:
			mastername = fields.getvalue("mastername")
		else:
			mastername = 'MooseFS'
	except Exception:
		mastername = 'MooseFS'

#	thsep = ''
#	html_thsep = ''

	def htmlentities(str):
		return str.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace("'",'&apos;').replace('"','&quot;')

	def urlescape(str):
		return xurllib.quote_plus(str)

	def resolve(strip):
		try:
			return (socket.gethostbyaddr(strip))[0]
		except Exception:
			return UNRESOLVED

	def createlink(update):
		c = []
		for k in fields:
			if k not in update:
				c.append("%s=%s" % (k,urlescape(fields.getvalue(k))))
		for k,v in update.items():
			if v!="":
				c.append("%s=%s" % (k,urlescape(v)))
		return "mfs.cgi?%s" % ("&amp;".join(c))

	def createjslink(update):
		c = []
		for k in fields:
			if k not in update:
				c.append("%s=%s" % (k,urlescape(fields.getvalue(k))))
		for k,v in update.items():
			if v!="":
				c.append("%s=%s" % (k,urlescape(v)))
		return "mfs.cgi?%s" % ("&".join(c))

	def createorderlink(prefix,columnid):
		ordername = "%sorder" % prefix
		revname = "%srev" % prefix
		try:
			orderval = int(fields.getvalue(ordername))
		except Exception:
			orderval = 0
		try:
			revval = int(fields.getvalue(revname))
		except Exception:
			revval = 0
		return createlink({revname:"1"}) if orderval==columnid and revval==0 else createlink({ordername:str(columnid),revname:"0"})

	def createinputs(ignorefields):
		for k in fields:
			if k not in ignorefields:
				yield """<input type="hidden" name="%s" value="%s">""" % (k,htmlentities(fields.getvalue(k)))
		return

else: # CLI mode
	import getopt

	masterhost = 'mfsmaster'
	masterport = 9421
	mastercontrolport = 9419
	mastername = 'MooseFS'
	frameset = -1
	plaintextseparator = "\t"
	forceplaintext = 0
	colormode = 0
	donotresolve = 0
	sectionset = []
	sectionsubset = []
	clicommands = []

# order and data parameters
	IMorder = 0
	IMrev = 0
	MForder = 0
	MFrev = 0
	CSorder = 0
	CSrev = 0
	MBorder = 0
	MBrev = 0
	HDorder = 0
	HDrev = 0
	HDperiod = 0
	HDtime = 0
	HDaddrname = 1
	EXorder = 0
	EXrev = 0
	MSorder = 0
	MSrev = 0
	SCorder = 0
	SCrev = 0
	OForder = 0
	OFrev = 0
	OFsessionid = 0
	ALorder = 0
	ALrev = 0
	ALinode = 0
	MOorder = 0
	MOrev = 0
	MOdata = 0
	QUorder = 0
	QUrev = 0
	MCrange = 0
	MCcount = 25
	MCchdata = []
	CCrange = 0
	CCcount = 25
	CCchdata = []
	INmatrix = 0

	mcchartslist = [
			('ucpu',0,0,'User cpu usage'),
			('scpu',1,0,'System cpu usage'),
			('delete',2,1,'Number of chunk deletions'),
			('replicate',3,1,'Number of chunk replications'),
			('statfs',4,1,'Number of statfs operations'),
			('getattr',5,1,'Number of getattr operations'),
			('setattr',6,1,'Number of setattr operations'),
			('lookup',7,1,'Number of lookup operations'),
			('mkdir',8,1,'Number of mkdir operations'),
			('rmdir',9,1,'Number of rmdir operations'),
			('symlink',10,1,'Number of symlink operations'),
			('readlink',11,1,'Number of readlink operations'),
			('mknod',12,1,'Number of mknod operations'),
			('unlink',13,1,'Number of unlink operations'),
			('rename',14,1,'Number of rename operations'),
			('link',15,1,'Number of link operations'),
			('readdir',16,1,'Number of readdir operations'),
			('open',17,1,'Number of open operations'),
			('read',18,1,'Number of read operations'),
			('write',19,1,'Number of write operations'),
			('memoryrss',20,2,'Resident memory usage'),
			('prcvd',21,1,'Received packets'),
			('psent',22,1,'Sent packets'),
			('brcvd',23,1,'Received bytes'),
			('bsent',24,1,'Sent bytes'),
			('memoryvirt',25,2,'Virtual memory usage'),
			('usedspace',26,2,'RAW disk space usage'),
			('totalspace',27,2,'RAW disk space connected'),
			('create',28,1,'Number of chunk creation attempts'),
			('change',29,1,'Number of chunk internal operation attempts'),
			('delete_ok',30,1,'Number of successful chunk deletions'),
			('delete_err',31,1,'Number of unsuccessful chunk deletions'),
			('replicate_ok',32,1,'Number of successful chunk replications'),
			('replicate_err',33,1,'Number of unsuccessful chunk replications'),
			('create_ok',34,1,'Number of successful chunk creations'),
			('create_err',35,1,'Number of unsuccessful chunk creations'),
			('change_ok',36,1,'Number of successful chunk internal operations'),
			('change_err',37,1,'Number of unsuccessful chunk internal operations'),
			('cpu',100,0,'Cpu usage (total sys+user)')
	]
	mcchartsabr = {
			'delete':['del'],
			'replicate':['rep','repl'],
			'memoryrss':['memrss','rmem','mem'],
			'memoryvirt':['memvirt','vmem']
	}

	ccchartslist = [
			('ucpu',0,0,'User cpu usage'),
			('scpu',1,0,'System cpu usage'),
			('masterin',2,1,'Data received from master'),
			('masterout',3,1,'Data sent to master'),
			('csrepin',4,1,'Data received by replicator'),
			('csrepout',5,1,'Data sent by replicator'),
			('csservin',6,1,'Data received by csserv'),
			('csservout',7,1,'Data sent by csserv'),
			('hdrbytesr',8,5,'Bytes read (headers)'),
			('hdrbytesw',9,5,'Bytes written (headers)'),
			('hdrllopr',10,1,'Low level reads (headers)'),
			('hdrllopw',11,1,'Low level writes (headers)'),
			('databytesr',12,5,'Bytes read (data)'),
			('databytesw',13,5,'Bytes written (data)'),
			('datallopr',14,1,'Low level reads (data)'),
			('datallopw',15,1,'Low level writes (data)'),
			('hlopr',16,1,'High level reads'),
			('hlopw',17,1,'High level writes'),
			('rtime',18,4,'Read time'),
			('wtime',19,4,'Write time'),
			('repl',20,1,'Replicate chunk ops'),
			('create',21,1,'Create chunk ops'),
			('delete',22,1,'Delete chunk ops'),
			('version',23,1,'Set version ops'),
			('duplicate',24,1,'Duplicate ops'),
			('truncate',25,1,'Truncate ops'),
			('duptrunc',26,1,'Duptrunc (duplicate+truncate) ops'),
			('test',27,1,'Test chunk ops'),
			('load',28,3,'Server load'),
			('memoryrss',29,2,'Resident memory usage'),
			('memoryvirt',30,2,'Virtual memory usage'),
			('movels',31,1,'Low speed move ops'),
			('movehs',32,1,'High speed move ops'),
			('cpu',100,0,'Cpu usage (total sys+user)')
	]
	ccchartsabr = {
			'memoryrss':['memrss','rmem','mem'],
			'memoryvirt':['memvirt','vmem']
	}

	mccharts = {}
	cccharts = {}
	for name,no,mode,desc in mcchartslist:
		mccharts[name] = (no,mode,desc)
	for name,abrlist in mcchartsabr.items():
		for abr in abrlist:
			mccharts[abr] = mccharts[name]
	for name,no,mode,desc in ccchartslist:
		cccharts[name] = (no,mode,desc)
	for name,abrlist in ccchartsabr.items():
		for abr in abrlist:
			cccharts[abr] = cccharts[name]

	lastsval = ''
	lastorder = None
	lastrev = 0
	lastid = 0
	lastmode = None
	try:
		opts,args = getopt.getopt(sys.argv[1:],"hvH:P:S:C:f:ps:no:rm:i:a:b:c:d:28")
	except Exception:
		opts = [('-h',None)]
	for opt,val in opts:
		if val==None:
			val=""
		if opt=='-h':
			print("usage:")
			print("\t%s [-hpn28] [-H master_host] [-P master_port] [-f 0..3] -S(IN|IM|LI|IG|MU|IC|IL|MF|CS|MB|HD|EX|MS|RS|SC|OF|AL|MO|QU|MC|CC) [-s separator] [-o order_id [-r]] [-m mode_id] [i id] [-a count] [-b chart_data_columns] [-c count] [-d chart_data_columns]" % sys.argv[0])
			print("\t%s [-hpn28] [-H master_host] [-P master_port] [-f 0..3] -C(RC/ip/port|BW/ip/port|M[01]/ip/port|RS/sessionid)" % sys.argv[0])
			print("\t%s -v" % sys.argv[0])
			print("\ncommon:\n")
			print("\t-h : print this message and exit")
			print("\t-v : print version number and exit")
			print("\t-p : force plain text format on tty devices")
			print("\t-s separator : field separator to use in plain text format on tty devices (forces -p)")
			print("\t-2 : force 256-color terminal color codes")
			print("\t-8 : force 8-color terminal color codes")
			print("\t-H master_host : master address (default: mfsmaster)")
			print("\t-P master_port : master client port (default: 9421)")
			print("\t-n : do not resolve ip addresses (default when output device is not tty)")
			print("\t-f frame charset number : set frame charset to be displayed as table frames in ttymode")
			print("\t\t-f0 : use simple ascii frames '+','-','|' (default for non utf-8 encodings)")
			if (sys.stdout.encoding=='UTF-8' or sys.stdout.encoding=='utf-8'):
				if sys.version_info[0]<3:
					print("\t\t-f1 : use utf-8 frames: \xe2\x94\x8f\xe2\x94\xb3\xe2\x94\x93\xe2\x94\xa3\xe2\x95\x8b\xe2\x94\xab\xe2\x94\x97\xe2\x94\xbb\xe2\x94\x9b\xe2\x94\x81\xe2\x94\x83\xe2\x95\xb8\xe2\x95\xb9\xe2\x95\xba\xe2\x95\xbb")
					print("\t\t-f2 : use utf-8 frames: \xe2\x94\x8c\xe2\x94\xac\xe2\x94\x90\xe2\x94\x9c\xe2\x94\xbc\xe2\x94\xa4\xe2\x94\x94\xe2\x94\xb4\xe2\x94\x98\xe2\x94\x80\xe2\x94\x82\xe2\x95\xb4\xe2\x95\xb5\xe2\x95\xb6\xe2\x95\xb7")
					print("\t\t-f3 : use utf-8 frames: \xe2\x95\x94\xe2\x95\xa6\xe2\x95\x97\xe2\x95\xa0\xe2\x95\xac\xe2\x95\xa3\xe2\x95\x9a\xe2\x95\xa9\xe2\x95\x9d\xe2\x95\x90\xe2\x95\x91 (default for utf-8 encodings)")
				else:
					print("\t\t-f1 : use utf-8 frames: \u250f\u2533\u2513\u2523\u254b\u252b\u2517\u253b\u251b\u2501\u2503\u2578\u2579\u257a\u257b")
					print("\t\t-f2 : use utf-8 frames: \u250c\u252c\u2510\u251c\u253c\u2524\u2514\u2534\u2518\u2500\u2502\u2574\u2575\u2576\u2577")
					print("\t\t-f3 : use utf-8 frames: \u2554\u2566\u2557\u2560\u256c\u2563\u255a\u2569\u255d\u2550\u2551 (default for utf-8 encodings)")
			else:
				print("\t\t-f1 : use utf-8 frames (thick single)")
				print("\t\t-f2 : use utf-8 frames (thin single)")
				print("\t\t-f3 : use utf-8 frames (double - default for utf-8 encodings)")
			print("\nmonitoring:\n")
			print("\t-S data set : defines data set to be displayed")
			print("\t\t-SIN : show full master info")
			print("\t\t-SIM : show only masters states")
			print("\t\t-SLI : show only licence info")
			print("\t\t-SIG : show only general master (leader) info")
			print("\t\t-SMU : show only master memory usage")
			print("\t\t-SIC : show only chunks info (goal/copies matrices)")
			print("\t\t-SIL : show only loop info (with messages)")
			print("\t\t-SMF : show only missing chunks/files")
			print("\t\t-SCS : show connected chunk servers")
			print("\t\t-SMB : show connected metadata backup servers")
			print("\t\t-SHD : show hdd data")
			print("\t\t-SEX : show exports")
			print("\t\t-SMS : show active mounts")
			print("\t\t-SRS : show resources (storage classes,open files,acquired locks)")
			print("\t\t-SSC : show storage classes")
			print("\t\t-SOF : show only open files")
			print("\t\t-SAL : show only acquired locks")
			print("\t\t-SMO : show operation counters")
			print("\t\t-SQU : show quota info")
			print("\t\t-SMC : show master charts data")
			print("\t\t-SCC : show chunkserver charts data")
			print("\t-o order_id : sort data by column specified by 'order id' (depends on data set)")
			print("\t-r : reverse order")
			print("\t-m mode_id : show data specified by 'mode id' (depends on data set)")
			print("\t-i id : sessionid for -SOF or inode for -SAL")
			print("\t-a count : how many master chart entries should be shown")
			print("\t-b chart_data_columns : define master chart columns")
			print("\t-c count : how many chunkserver chart entries should be shown")
			print("\t-d chart_data_columns : define chunkserver chart columns (prefix with '+' for raw data, prefix with 'ip:[port:]' for server choice)")
			print("\t\tmaster charts columns:")
			for name,no,mode,desc in mcchartslist:
				if name in mcchartsabr:
					name = "%s,%s" % (name,",".join(mcchartsabr[name]))
				print("\t\t\t%s - %s" % (name,desc))
			print("\t\tchunkserver chart columns:")
			for name,no,mode,desc in ccchartslist:
				if name in ccchartsabr:
					name = "%s,%s" % (name,",".join(ccchartsabr[name]))
				print("\t\t\t%s - %s" % (name,desc))
			print("\ncommands:\n")
			print("\t-C command : perform particular command")
			print("\t\t-CRC/ip/port : remove given chunkserver from list of active chunkservers")
			print("\t\t-CBW/ip/port : send given chunkserver back to work (from grace state)")
			print("\t\t-CM1/ip/port : switch given chunkserver to maintenance mode")
			print("\t\t-CM0/ip/port : switch given chunkserver to standard mode (from maintenance mode)")
			print("\t\t-CRS/sessionid : remove given session")
			os._exit(0)
		elif opt=='-v':
			print("version: %s" % VERSION)
			os._exit(0)
		elif opt=='-2':
			colormode = 2
		elif opt=='-8':
			colormode = 1
		elif opt=='-p':
			forceplaintext = 1
		elif opt=='-s':
			plaintextseparator = val
			forceplaintext = 1
		elif opt=='-n':
			donotresolve = 1
		elif opt=='-f':
			frameset = int(val)
		elif opt=='-H':
			masterhost = val
		elif opt=='-P':
			masterport = int(val)
		elif opt=='-S':
			lastsval = val
			if 'IN' in val:
				sectionset.append("IN")
				sectionsubset.append("IM")
				sectionsubset.append("LI")
				sectionsubset.append("IG")
				sectionsubset.append("MU")
				sectionsubset.append("IC")
				sectionsubset.append("IL")
				sectionsubset.append("MF")
				if lastmode!=None:
					INmatrix = lastmode
				if lastorder!=None:
					IMorder = lastorder
				if lastrev:
					IMrev = 1
			if 'IM' in val:
				sectionset.append("IN")
				sectionsubset.append("IM")
				if lastorder!=None:
					IMorder = lastorder
				if lastrev:
					IMrev = 1
			if 'LI' in val:
				sectionset.append("IN")
				sectionsubset.append("LI")
			if 'IG' in val:
				sectionset.append("IN")
				sectionsubset.append("IG")
			if 'MU' in val:
				sectionset.append("IN")
				sectionsubset.append("MU")
			if 'IC' in val:
				sectionset.append("IN")
				sectionsubset.append("IC")
				if lastmode!=None:
					INmatrix = lastmode
			if 'IL' in val:
				sectionset.append("IN")
				sectionsubset.append("IL")
			if 'MF' in val:
				sectionset.append("IN")
				sectionsubset.append("MF")
				if lastorder!=None:
					MForder = lastorder
				if lastrev:
					MFrev = 1
			if 'CS' in val:
				sectionset.append("CS")
				sectionsubset.append("CS")
				if lastorder!=None:
					CSorder = lastorder
				if lastrev:
					CSrev = 1
			if 'MB' in val:
				sectionset.append("CS")
				sectionsubset.append("MB")
				if lastorder!=None:
					MBorder = lastorder
				if lastrev:
					MBrev = 1
			if 'HD' in val:
				sectionset.append("HD")
				if lastorder!=None:
					HDorder = lastorder
				if lastrev:
					HDrev = 1
				if lastmode!=None:
					if lastmode>=0 and lastmode<6:
						HDperiod,HDtime = divmod(lastmode,2)
			if 'EX' in val:
				sectionset.append("EX")
				if lastorder!=None:
					EXorder = lastorder
				if lastrev:
					EXrev = 1
			if 'MS' in val:
				sectionset.append("MS")
				if lastorder!=None:
					MSorder = lastorder
				if lastrev:
					MSrev = 1
			if 'MO' in val:
				sectionset.append("MO")
				if lastorder!=None:
					MOorder = lastorder
				if lastrev:
					MOrev = 1
				if lastmode!=None:
					MOdata = lastmode
			if 'RS' in val:
				sectionset.append("RS")
				sectionsubset.append("SC")
				sectionsubset.append("OF")
				sectionsubset.append("AL")
			if 'SC' in val:
				sectionset.append("RS")
				sectionsubset.append("SC")
				if lastorder!=None:
					SCorder = lastorder
				if lastrev:
					SCrev = 1
			if 'OF' in val:
				sectionset.append("RS")
				sectionsubset.append("OF")
				if lastorder!=None:
					OForder = lastorder
				if lastrev:
					OFrev = 1
				if lastid:
					OFsessionid = lastid
			if 'AL' in val:
				sectionset.append("RS")
				sectionsubset.append("AL")
				if lastorder!=None:
					ALorder = lastorder
				if lastrev:
					ALrev = 1
				if lastid:
					ALinode = lastid
			if 'QU' in val:
				sectionset.append("QU")
				if lastorder!=None:
					QUorder = lastorder
				if lastrev:
					QUrev = 1
			if 'MC' in val:
				sectionset.append("MC")
				if lastmode!=None:
					MCrange = lastmode
			if 'CC' in val:
				sectionset.append("CC")
				if lastmode!=None:
					CCrange = lastmode
			lastorder = None
			lastrev = 0
			lastmode = None
		elif opt=='-o':
			if 'IM' in lastsval:
				IMorder = int(val)
			if 'MF' in lastsval:
				MForder = int(val)
			if 'CS' in lastsval:
				CSorder = int(val)
			if 'MB' in lastsval:
				MBorder = int(val)
			if 'HD' in lastsval:
				HDorder = int(val)
			if 'EX' in lastsval:
				EXorder = int(val)
			if 'MS' in lastsval:
				MSorder = int(val)
			if 'MO' in lastsval:
				MOorder = int(val)
			if 'SC' in lastsval:
				SCorder = int(val)
			if 'OF' in lastsval:
				OForder = int(val)
			if 'AL' in lastsval:
				ALorder = int(val)
			if 'QU' in lastsval:
				QUorder = int(val)
			if lastsval=='':
				lastorder = int(val)
		elif opt=='-r':
			if 'IM' in lastsval:
				IMrev = 1
			if 'MF' in lastsval:
				MFrev = 1
			if 'CS' in lastsval:
				CSrev = 1
			if 'MB' in lastsval:
				MBrev = 1
			if 'HD' in lastsval:
				HDrev = 1
			if 'EX' in lastsval:
				EXrev = 1
			if 'MS' in lastsval:
				MSrev = 1
			if 'MO' in lastsval:
				MOrev = 1
			if 'SC' in lastsval:
				SCrev = 1
			if 'OF' in lastsval:
				OFrev = 1
			if 'AL' in lastsval:
				ALrev = 1
			if 'QU' in lastsval:
				QUrev = 1
			if lastsval=='':
				lastrev = 1
		elif opt=='-m':
			if 'HD' in lastsval:
				d = int(val)
				if d>=0 and d<6:
					HDperiod,HDtime = divmod(d,2)
			if 'MO' in lastsval:
				MOdata = int(val)
			if 'IN' in lastsval or 'IC' in lastsval:
				INmatrix = int(val)
			if 'MC' in lastsval:
				MCrange = int(val)
			if 'CC' in lastsval:
				CCrange = int(val)
			if lastsval=='':
				lastmode = int(val)
		elif opt=='-i':
			if 'OF' in lastsval:
				OFsessionid = int(val)
			if 'AL' in lastsval:
				ALinode = int(val)
			if lastsval=='':
				lastid = int(val)
		elif opt=='-a':
			MCcount = int(val)
		elif opt=='-b':
			for x in val.split(','):
				x = x.strip()
				if ':' in x:
					xs = x.split(':')
					if len(xs)==2:
						chhost = xs[0]
						chport = 9421
						x = xs[1]
					elif len(xs)==3:
						chhost = xs[0]
						chport = int(xs[1])
						x = xs[2]
					else:
						print("Unknown chart name: %s" % x)
						os._exit(0)
				else:
					chhost = None
					chport = None
				if x[0]=='+':
					x = x[1:]
					rawmode = 1
				else:
					rawmode = 0
				if x in mccharts:
					MCchdata.append((chhost,chport,mccharts[x][0],mccharts[x][1],mccharts[x][2],rawmode))
				else:
					print("Unknown master chart name: %s" % x)
					os._exit(0)
		elif opt=='-c':
			CCcount = int(val)
		elif opt=='-d':
			for x in val.split(','):
				x = x.strip()
				if ':' in x:
					xs = x.split(':')
					if len(xs)==2:
						chhost = xs[0]
						chport = 9422
						x = xs[1]
					elif len(xs)==3:
						chhost = xs[0]
						chport = int(xs[1])
						x = xs[2]
					else:
						print("Unknown chart name: %s" % x)
						os._exit(0)
				else:
					chhost = None
					chport = None
				if x[0]=='+':
					x = x[1:]
					rawmode = 1
				else:
					rawmode = 0
				if x in cccharts:
					if chhost==None or chport==None:
						print("in chunkserver chart data server ip/host must be specified")
						os._exit(0)
					CCchdata.append((chhost,chport,cccharts[x][0],cccharts[x][1],cccharts[x][2],rawmode))
				else:
					print("Unknown chunkserver chart name: %s" % x)
					os._exit(0)
		elif opt=='-C':
			clicommands.append(val)

	if sectionset==[] and clicommands==[]:
		print("Specify data to be shown (option -S) or command (option -C). Use '-h' for help.")
		os._exit(0)

	ttymode = 1 if forceplaintext==0 and os.isatty(1) else 0
	if ttymode:
		try:
			import curses
			curses.setupterm()
			if curses.tigetnum("colors")>=256:
				colors256 = 1
			else:
				colors256 = 0
		except Exception:
			colors256 = 1 if 'TERM' in os.environ and '256color' in os.environ['TERM'] else 0
		# colors: 0 - white,1 - red,2 - orange,3 - yellow,4 - green,5 - cyan,6 - blue,7 - violet,8 - gray
		CSI="\x1B["
		if colors256:
			ttyreset=CSI+"0m"
			colorcode=[CSI+"38;5;196m",CSI+"38;5;208m",CSI+"38;5;226m",CSI+"38;5;34m",CSI+"38;5;30m",CSI+"38;5;19m",CSI+"38;5;55m",CSI+"38;5;244m"]
		else:
			ttysetred=CSI+"31m"
			ttysetyellow=CSI+"33m"
			ttysetgreen=CSI+"32m"
			ttysetcyan=CSI+"36m"
			ttysetblue=CSI+"34m"
			ttysetmagenta=CSI+"35m"
			ttyreset=CSI+"0m"
			# no orange - use red, no gray - use white
			colorcode=[ttysetred,ttysetred,ttysetyellow,ttysetgreen,ttysetcyan,ttysetblue,ttysetmagenta,""]
	else:
		colorcode=["","","","","","","",""]

	if ttymode and (sys.stdout.encoding=='UTF-8' or sys.stdout.encoding=='utf-8'):
		if frameset>=0 and frameset<=3:
			tabbleframes=frameset
		else:
			tabbleframes=0
	else:
		tabbleframes=0

	# terminal encoding mambo jumbo (mainly replace unicode chars that can't be printed with '?' instead of throwing exception)
	term_encoding = sys.stdout.encoding
	if term_encoding==None:
		term_encoding = 'utf-8'
	if sys.version_info[0]<3:
		sys.stdout = codecs.getwriter(term_encoding)(sys.stdout,'replace')
		sys.stdout.encoding = term_encoding
	elif sys.version_info[1]<7:
		sys.stdout = codecs.getwriter(term_encoding)(sys.stdout.detach(),'replace')
		sys.stdout.encoding = term_encoding
	else:
		sys.stdout.reconfigure(errors='replace')

	# lines prepared for JSON output (force utf-8):
	#if sys.version_info[0]<3:
	#	sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
	#elif sys.version_info[1]<7:
	#	sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
	#else:
	#	sys.stdout.reconfigure(encoding='utf-8')

	# frames:
	#  +-----+-----+-----+-----+
	#  |     |     |     |     |
	#  |     |     |     |  |  |
	#  |  +- | -+- | -+  |  +- |
	#  |  |  |  |  |  |  |  |  |
	#  |     |     |     |     |
	#  +-----+-----+-----+-----+
	#  |     |     |     |     |
	#  |  |  |  |  |  |  |  |  |
	#  | -+- | -+  |  +- | -+- |
	#  |  |  |  |  |     |     |
	#  |     |     |     |     |
	#  +-----+-----+-----+-----+
	#  |     |     |     |     |
	#  |  |  |     |  |  |     |
	#  | -+  | -+- |  +  | -+  |
	#  |     |     |  |  |     |
	#  |     |     |     |     |
	#  +-----+-----+-----+-----+
	#  |     |     |     |     |
	#  |  |  |     |     |     |
	#  |  +  |  +- |  +  |  +  |
	#  |     |     |  |  |     |
	#  |     |     |     |     |
	#  +-----+-----+-----+-----+
	#  

	class Tabble:
		Needseparator = 0
		def __init__(self,title,ccnt,defattr=""):
			if tabbleframes==1:
				if sys.version_info[0]<3:
					self.frames = ['\xe2\x94\x8f', '\xe2\x94\xb3', '\xe2\x94\x93', '\xe2\x94\xa3', '\xe2\x95\x8b', '\xe2\x94\xab', '\xe2\x94\x97', '\xe2\x94\xbb', '\xe2\x94\x9b', '\xe2\x94\x81', '\xe2\x94\x83', '\xe2\x95\xb8', '\xe2\x95\xb9', '\xe2\x95\xba', '\xe2\x95\xbb', ' ']
				else:
					self.frames = ['\u250f', '\u2533', '\u2513', '\u2523', '\u254b', '\u252b', '\u2517', '\u253b', '\u251b', '\u2501', '\u2503', '\u2578', '\u2579', '\u257a', '\u257b', ' ']
			elif tabbleframes==2:
				if sys.version_info[0]<3:
					self.frames = ['\xe2\x94\x8c', '\xe2\x94\xac', '\xe2\x94\x90', '\xe2\x94\x9c', '\xe2\x94\xbc', '\xe2\x94\xa4', '\xe2\x94\x94', '\xe2\x94\xb4', '\xe2\x94\x98', '\xe2\x94\x80', '\xe2\x94\x82', '\xe2\x95\xb4', '\xe2\x95\xb5', '\xe2\x95\xb6', '\xe2\x95\xb7', ' ']
				else:
					self.frames = ['\u250c', '\u252c', '\u2510', '\u251c', '\u253c', '\u2524', '\u2514', '\u2534', '\u2518', '\u2500', '\u2502', '\u2574', '\u2575', '\u2576', '\u2577', ' ']
			elif tabbleframes==3:
				if sys.version_info[0]<3:
					self.frames = ['\xe2\x95\x94', '\xe2\x95\xa6', '\xe2\x95\x97', '\xe2\x95\xa0', '\xe2\x95\xac', '\xe2\x95\xa3', '\xe2\x95\x9a', '\xe2\x95\xa9', '\xe2\x95\x9d', '\xe2\x95\x90', '\xe2\x95\x91', ' ', '\xe2\x95\x91', ' ', '\xe2\x95\x91', ' ']
				else:
					self.frames = ['\u2554', '\u2566', '\u2557', '\u2560', '\u256c', '\u2563', '\u255a', '\u2569', '\u255d', '\u2550', '\u2551', ' ', '\u2551', ' ', '\u2551', ' ']
			else:
				self.frames = ['+','+','+','+','+','+','+','+','+','-','|',' ','|',' ','|',' ']
			self.title = title
			self.ccnt = ccnt
			self.head = []
			self.body = []
			self.defattrs = []
			self.cwidth = []
			for _ in range(ccnt):
				self.defattrs.append(defattr)
				self.cwidth.append(0)
		def combineattr(self,attr,defattr):
			attrcolor = ""
			for c in ("0","1","2","3","4","5","6","7","8"):
				if c in defattr:
					attrcolor = c
			for c in ("0","1","2","3","4","5","6","7","8"):
				if c in attr:
					attrcolor = c
			attrjust = ""
			for c in ("l","L","r","R","c","C"):
				if c in defattr:
					attrjust = c
			for c in ("l","L","r","R","c","C"):
				if c in attr:
					attrjust = c
			return attrcolor+attrjust
		def header(self,*rowdata):
			ccnt = 0
			for celldata in rowdata:
				if type(celldata)==tuple:
					if len(celldata)==3:
						ccnt+=celldata[2]
					else:
						if celldata[0]!=None:
							cstr = myunicode(celldata[0])
							if len(cstr) > self.cwidth[ccnt]:
								self.cwidth[ccnt] = len(cstr)
						ccnt+=1
				else:
					if celldata!=None:
						cstr = myunicode(celldata)
						if len(cstr) > self.cwidth[ccnt]:
							self.cwidth[ccnt] = len(cstr)
					ccnt+=1
			if ccnt != self.ccnt:
				raise IndexError
			self.head.append(rowdata)
		def defattr(self,*rowdata):
			if len(rowdata) != self.ccnt:
				raise IndexError
			self.defattrs = rowdata
		def append(self,*rowdata):
			ccnt = 0
			rdata = []
			for celldata in rowdata:
				if type(celldata)==tuple:
					if celldata[0]!=None:
						cstr = myunicode(celldata[0])
					else:
						cstr = ""
					if len(celldata)==3:
						rdata.append((cstr,self.combineattr(celldata[1],self.defattrs[ccnt]),celldata[2]))
						ccnt+=celldata[2]
					else:
						if len(cstr) > self.cwidth[ccnt]:
							self.cwidth[ccnt] = len(cstr)
						if len(celldata)==2:
							rdata.append((cstr,self.combineattr(celldata[1],self.defattrs[ccnt])))
						else:
							rdata.append((cstr,self.defattrs[ccnt]))
						ccnt+=1
				else:
					if celldata!=None:
						cstr = myunicode(celldata)
						if len(cstr) > self.cwidth[ccnt]:
							self.cwidth[ccnt] = len(cstr)
						rdata.append((cstr,self.defattrs[ccnt]))
					else:
						rdata.append(celldata)
					ccnt+=1
			if ccnt != self.ccnt:
				raise IndexError
			self.body.append(rdata)
		def attrdata(self,cstr,cattr,cwidth):
			retstr = ""
			if "1" in cattr:
				retstr += colorcode[0]
				needreset = 1
			elif "2" in cattr:
				retstr += colorcode[1]
				needreset = 1
			elif "3" in cattr:
				retstr += colorcode[2]
				needreset = 1
			elif "4" in cattr:
				retstr += colorcode[3]
				needreset = 1
			elif "5" in cattr:
				retstr += colorcode[4]
				needreset = 1
			elif "6" in cattr:
				retstr += colorcode[5]
				needreset = 1
			elif "7" in cattr:
				retstr += colorcode[6]
				needreset = 1
			elif "8" in cattr:
				retstr += colorcode[7]
				needreset = 1
			else:
				needreset = 0
			if cstr=="--":
				retstr += " "+"-"*cwidth+" "
			elif cstr=="---":
				retstr += "-"*(cwidth+2)
			elif "L" in cattr or "l" in cattr:
				retstr += " "+cstr.ljust(cwidth)+" "
			elif "R" in cattr or "r" in cattr:
				retstr += " "+cstr.rjust(cwidth)+" "
			else:
				retstr += " "+cstr.center(cwidth)+" "
			if needreset:
				retstr += ttyreset
			return retstr
		def lines(self):
			outstrtab = []
			if ttymode:
				tabdata = []
				# upper frame
				tabdata.append((("---","",self.ccnt),))
				# title
				tabdata.append(((self.title,"",self.ccnt),))
				# header
				if len(self.head)>0:
					tabdata.append((("---","",self.ccnt),))
					tabdata.extend(self.head)
				# head and data separator
				tabdata.append((("---","",self.ccnt),))
				# data
				if len(self.body)==0:
					tabdata.append((("no data","",self.ccnt),))
				else:
					tabdata.extend(self.body)
				# bottom frame
				tabdata.append((("---","",self.ccnt),))
				# check col-spaned headers and adjust column widths if necessary
				for rowdata in tabdata:
					ccnt = 0
					for celldata in rowdata:
						if type(celldata)==tuple and len(celldata)==3 and celldata[0]!=None:
							cstr = myunicode(celldata[0])
							clen = len(cstr)
							cwidth = sum(self.cwidth[ccnt:ccnt+celldata[2]])+3*(celldata[2]-1)
							if clen > cwidth:
								add = clen - cwidth
								adddm = divmod(add,celldata[2])
								cadd = adddm[0]
								if adddm[1]>0:
									cadd+=1
								for i in range(celldata[2]):
									self.cwidth[ccnt+i] += cadd
							ccnt += celldata[2]
						else:
							ccnt += 1
				separators = []
				# before tab - no separators
				seplist = []
				for i in range(self.ccnt+1):
					seplist.append(0)
				separators.append(seplist)
				for rowdata in tabdata:
					seplist = [1]
					for celldata in rowdata:
						if type(celldata)==tuple and len(celldata)==3:
							for i in range(celldata[2]-1):
								seplist.append(1 if celldata[0]=='---' else 0)
						seplist.append(1)
					separators.append(seplist)
				# after tab - no separators
				seplist = []
				for i in range(self.ccnt+1):
					seplist.append(0)
				separators.append(seplist)
				# add upper and lower separators:
				updownsep = [[a*2 + b for (a,b) in zip(x,y)] for (x,y) in zip(separators[2:],separators[:-2])]
				# create tabble
				for (rowdata,sepdata) in zip(tabdata,updownsep):
	#				print rowdata,sepdata
					ccnt = 0
					line = ""
					nsep = 0 #self.frames[10]
					for celldata in rowdata:
						cpos = ccnt
						cattr = ""
						if type(celldata)==tuple:
							if celldata[1]!=None:
								cattr = celldata[1]
							if len(celldata)==3:
								cwidth = sum(self.cwidth[ccnt:ccnt+celldata[2]])+3*(celldata[2]-1)
								ccnt+=celldata[2]
							else:
								cwidth = self.cwidth[ccnt]
								ccnt+=1
							cstr = celldata[0]
						else:
							cstr = celldata
							cwidth = self.cwidth[ccnt]
							ccnt+=1
						if cstr==None:
							cstr = ""
						cstr = myunicode(cstr)
						if cstr=="---":
							if nsep==0:
								line += self.frames[(13,6,0,3)[sepdata[cpos]]]
								#line += self.frames[(15,6,0,3)[sepdata[cpos]]]
							else:
								line += self.frames[(9,7,1,4)[sepdata[cpos]]]
							nsep = 1 #self.frames[4]
							for ci in range(cpos,ccnt-1):
								line += self.frames[9]*(self.cwidth[ci]+2)
								line += self.frames[(9,7,1,4)[sepdata[ci+1]]]
							line += self.frames[9]*(self.cwidth[ccnt-1]+2)
						else:
							if nsep==0:
								line += self.frames[(15,12,14,10)[sepdata[cpos]]]
								#line += self.frames[(15,10,10,10)[sepdata[cpos]]]
							else:
								line += self.frames[(11,8,2,5)[sepdata[cpos]]]
								#line += self.frames[(15,8,2,5)[sepdata[cpos]]]
							nsep = 0
							line += self.attrdata(cstr,cattr,cwidth)
					if nsep==0:
						line += self.frames[(15,12,14,10)[sepdata[ccnt]]]
						#line += self.frames[(15,10,10,10)[sepdata[ccnt]]]
					else:
						line += self.frames[(11,8,2,5)[sepdata[ccnt]]]
						#line += self.frames[(15,8,2,5)[sepdata[ccnt]]]
					outstrtab.append(line)
			else:
				for rowdata in self.body:
					row = []
					for celldata in rowdata:
						if type(celldata)==tuple:
							cstr = myunicode(celldata[0])
						elif celldata!=None:
							cstr = myunicode(celldata)
						else:
							cstr = ""
						row.append(cstr)
					outstrtab.append("%s:%s%s" % (self.title,plaintextseparator,plaintextseparator.join(row)))
			return outstrtab
		def __str__(self):
			if Tabble.Needseparator:
				sep = "\n"
			else:
				sep = ""
				Tabble.Needseparator = 1
			return sep+("\n".join(self.lines()))

	#x = Tabble("Test title",4)
	#x.header("column1","column2","column3","column4")
	#x.append("t1","t2","very long entry","test")
	#x.append(("r","r3"),("l","l2"),"also long entry","test")
	#print x
	#
	#x = Tabble("Very long tabble title",2)
	#x.defattr("l","r")
	#x.append("key","value")
	#x.append("other key",123)
	#y = []
	#y.append(("first","1"))
	#y.append(("second","4"))
	#x.append(*y)
	#print x
	#
	#x = Tabble("Tabble with complicated header",15,"r")
	#x.header(("","",4),("I/O stats last min","",8),("","",3))
	#x.header(("info","",4),("---","",8),("space","",3))
	#x.header(("","",4),("transfer","",2),("max time","",3),("# of ops","",3),("","",3))
	#x.header(("---","",15))
	#x.header("IP path","chunks","last error","status","read","write","read","write","fsync","read","write","fsync","used","total","used %")
	#x.append("192.168.1.102:9422:/mnt/hd4/",66908,"no errors","ok","19 MiB/s","27 MiB/s","263625 us","43116 us","262545 us",3837,3295,401,"1.0 TiB","1.3 TiB","76.41%")
	#x.append("192.168.1.102:9422:/mnt/hd5/",67469,"no errors","ok","25 MiB/s","29 MiB/s","340303 us","89168 us","223610 us",2487,2593,366,"1.0 TiB","1.3 TiB","75.93%")
	#x.append("192.168.1.111:9422:/mnt/hd5/",109345,("2012-10-12 07:27","2"),("damaged","1"),"-","-","-","-","-","-","-","-","1.2 TiB","1.3 TiB","87.18%")
	#x.append("192.168.1.211:9422:/mnt/hd5/",49128,"no errors",("marked for removal","4"),"-","-","-","-","-","-","-","-","501 GiB","1.3 TiB","36.46%")
	##x.append("192.168.1.111:9422:/mnt/hd5/",109345,("2012-10-12 07:27","2"),("damaged","1"),("","-",8),"1.2 TiB","1.3 TiB","87.18%")
	##x.append("192.168.1.211:9422:/mnt/hd5/",49128,"no errors",("marked for removal","4"),("","-",8),"501 GiB","1.3 TiB","36.46%")
	#x.append("192.168.1.229:9422:/mnt/hd10/","67969","no errors","ok","17 MiB/s","11 MiB/s","417292 us","76333 us","1171903 us","2299","2730","149","1.0 TiB","1.3 TiB","76.61%")
	#print x
	#
	#x = Tabble("Colors",1,"r")
	#x.append(("white","0"))
	#x.append(("red","1"))
	#x.append(("orange","2"))
	#x.append(("yellow","3"))
	#x.append(("green","4"))
	#x.append(("cyan","5"))
	#x.append(("blue","6"))
	#x.append(("magenta","7"))
	#x.append(("gray","8"))
	#print x
	#
	#x = Tabble("Adjustments",1)
	#x.append(("left","l"))
	#x.append(("right","r"))
	#x.append(("center","c"))
	#print x
	#
	#x = Tabble("Special entries",3)
	#x.defattr("l","r","r")
	#x.header("entry","effect","extra column")
	#x.append("-- ","--","")
	#x.append("--- ","---","")
	#x.append("('--','',2)",('--','',2))
	#x.append("('','',2)",('','',2))
	#x.append("('---','',2)",('---','',2))
	#x.append("('red','1')",('red','1'),'')
	#x.append("('orange','2')",('orange','2'),'')
	#x.append("('yellow','3')",('yellow','3'),'')
	#x.append("('green','4')",('green','4'),'')
	#x.append("('cyan','5')",('cyan','5'),'')
	#x.append("('blue','6')",('blue','6'),'')
	#x.append("('magenta','7')",('magenta','7'),'')
	#x.append("('gray','8')",('gray','8'),'')
	#x.append(('---','',3))
	#x.append("('left','l',2)",('left','l',2))
	#x.append("('right','r',2)",('right','r',2))
	#x.append("('center','c',2)",('center','c',2))
	#print x

	def resolve(strip):
		if donotresolve:
			return strip
		try:
			return (socket.gethostbyaddr(strip))[0]
		except Exception:
			return strip






# common auxilinary functions

def getmasteraddresses():
	m = []
	for mhost in masterhost.replace(';',' ').replace(',',' ').split():
		try:
			for i in socket.getaddrinfo(mhost,masterport,socket.AF_INET,socket.SOCK_STREAM,socket.SOL_TCP):
				if i[0]==socket.AF_INET and i[1]==socket.SOCK_STREAM and i[2]==socket.SOL_TCP:
					m.append(i[4])
		except Exception:
			pass
	return m

#def mysend(socket,msg):
#	totalsent = 0
#	while totalsent < len(msg):
#		sent = socket.send(msg[totalsent:])
#		if sent == 0:
#			raise RuntimeError("socket connection broken")
#		totalsent = totalsent + sent

#def myrecv(socket,leng):
#	if sys.version_info[0]<3:
#		msg = ''
#	else:
#		msg = bytes(0)
#	while len(msg) < leng:
#		chunk = socket.recv(leng-len(msg))
#		if len(chunk) == 0:
#			raise RuntimeError("socket connection broken")
#		msg = msg + chunk
#	return msg

def disablesmask_to_string(disables_mask):
	cmds = ["chown","chmod","symlink","mkfifo","mkdev","mksock","mkdir","unlink","rmdir","rename","move","link","create","readdir","read","write","truncate","setlength","appendchunks","snapshot","settrash","setsclass","seteattr","setxattr","setfacl"]
	l = []
	m = 1
	for cmd in cmds:
		if disables_mask & m:
			l.append(cmd)
		m <<= 1
	return ",".join(l)

def state_name(stateid):
	if stateid==STATE_DUMMY:
		return "DUMMY"
	elif stateid==STATE_USURPER:
		return "USURPER"
	elif stateid==STATE_FOLLOWER:
		return "FOLLOWER"
	elif stateid==STATE_ELECT:
		return "ELECT"
	elif stateid==STATE_LEADER:
		return "LEADER"
	else:
		return "???"

def state_color(stateid,sync):
	if stateid==STATE_DUMMY:
		return 8
	elif stateid==STATE_FOLLOWER or stateid==STATE_USURPER:
		if sync:
			return 5
		else:
			return 6
	elif stateid==STATE_ELECT:
		return 3
	elif stateid==STATE_LEADER:
		return 4
	else:
		return 1

def decimal_number(number,sep=' '):
	parts = []
	while number>=1000:
		number,rest = divmod(number,1000)
		parts.append("%03u" % rest)
	parts.append(str(number))
	parts.reverse()
	return sep.join(parts)

def humanize_number(number,sep='',suff='B'):
	number*=100
	scale=0
	while number>=99950:
		number = number//1024
		scale+=1
	if number<995 and scale>0:
		b = (number+5)//10
		nstr = "%u.%u" % divmod(b,10)
	else:
		b = (number+50)//100
		nstr = "%u" % b
	if scale>0:
		return "%s%s%si%s" % (nstr,sep,"-KMGTPEZY"[scale],suff)
	else:
		return "%s%s%s" % (nstr,sep,suff)

def timeduration_to_shortstr(timeduration):
	for l,s in ((86400,'d'),(3600,'h'),(60,'m'),(0,'s')):
		if timeduration>=l:
			if l>0:
				n = float(timeduration)/float(l)
			else:
				n = float(timeduration)
			rn = round(n,1)
			if n==round(n,0):
				return "%.0f%s" % (n,s)
			else:
				return "%s%.1f%s" % (("~" if n!=rn else ""),rn,s)
	return "???"

def timeduration_to_fullstr(timeduration):
	if timeduration>=86400:
		days,dayseconds = divmod(timeduration,86400)
		daysstr = "%u day%s, " % (days,("s" if days!=1 else ""))
	else:
		dayseconds = timeduration
		daysstr = ""
	hours,hourseconds = divmod(dayseconds,3600)
	minutes,seconds = divmod(hourseconds,60)
	if seconds==round(seconds,0):
		return "%u second%s (%s%u:%02u:%02u)" % (timeduration,("" if timeduration==1 else "s"),daysstr,hours,minutes,seconds)
	else:
		seconds,fracsec = divmod(seconds,1)
		return "%.3f seconds (%s%u:%02u:%02u.%03u)" % (timeduration,daysstr,hours,minutes,seconds,round(1000*fracsec,0))

def label_id_to_char(id):
	return chr(ord('A')+id)

def labelmask_to_str(labelmask):
	str = ""
	m = 1
	for i in xrange(26):
		if labelmask & m:
			str += label_id_to_char(i)
		m <<= 1
	return str

def labelmasks_to_str(labelmasks):
	if labelmasks[0]==0:
		return "*"
	r = []
	for labelmask in labelmasks:
		if labelmask==0:
			break
		r.append(labelmask_to_str(labelmask))
	return "+".join(r)


def print_exception():
	exc_type, exc_value, exc_traceback = sys.exc_info()
	try:
		if cgimode:
			print("""<table class="FR" cellspacing="0">""")
			print("""<tr><th>Oops!</th></tr>""")
			print("""<tr><td align="left"><b>An error has occurred. Check your MooseFS configuration and network connections. If you decide to seek support because of this error, please include the following traceback:</b>""")
			print("""<pre>""")
			print(traceback.format_exc().strip())
			print("""</pre></td></tr>""")
			print("""</table>""")
		elif ttymode:
			tab = Tabble("Exception Traceback",4)
			tab.header("file","line","in","text")
			tab.defattr("l","r","l","l")
			for d in traceback.extract_tb(exc_traceback):
				tab.append(d[0],d[1],d[2],repr(d[3]))
			tab.append(("---","",4))
			tab.append(("Error","c",4))
			tab.append(("---","",4))
			for d in traceback.format_exception_only(exc_type, exc_value):
				tab.append((repr(d.strip()),"",4))
			print("%s%s%s" % (colorcode[1],tab,ttyreset))
		else:
			print("""---------------------------------------------------------------- error -----------------------------------------------------------------""")
			print(traceback.format_exc().strip())
			print("""----------------------------------------------------------------------------------------------------------------------------------------""")
	except Exception:
		print(traceback.format_exc().strip())

def version_convert(version):
	if version>=(2,0,0):
		return ((version[0],version[1],version[2]//2),version[2]&1)
	elif version>=(1,7,0):
		return (version,1)
	elif version>(0,0,0):
		return (version,0)
	else:
		return (version,-1)

def version_str_and_sort(version):
	version,pro = version_convert(version)
	strver = "%u.%u.%u" % version
	sortver = "%05u_%03u_%03u" % version
	if pro==1:
		strver += " PRO"
		sortver += "_2"
	elif pro==0:
		sortver += "_1"
	else:
		sortver += "_0"
	return (strver,sortver)

class MFSConn:
	def __init__(self,host,port):
		self.host = host
		self.port = port
		self.socket = None
		self.connect()
	def __del__(self):
		try:
			if self.socket:
				self.socket.close()
#				print "connection closed with: %s:%u" % (self.host,self.port)
			self.socket = None
		except AttributeError:
			pass
	def connect(self):
		cnt = 0
		while self.socket == None and cnt<3:
			self.socket = socket.socket()
			self.socket.settimeout(1)
			try:
				self.socket.connect((self.host,self.port))
			except Exception:
				self.socket.close()
				self.socket = None
				cnt += 1
		if self.socket==None:
			self.socket = socket.socket()
			self.socket.settimeout(1)
			self.socket.connect((self.host,self.port))
#		else:
#			print "connected to: %s:%u" % (self.host,self.port)
	def close(self):
		if self.socket:
			self.socket.close()
			self.socket = None
	def mysend(self,msg):
		if self.socket == None:
			self.connect()
		totalsent = 0
		while totalsent < len(msg):
			sent = self.socket.send(msg[totalsent:])
			if sent == 0:
				raise RuntimeError("socket connection broken")
			totalsent = totalsent + sent
	def myrecv(self,leng):
		if sys.version_info[0]<3:
			msg = ''
		else:
			msg = bytes(0)
		while len(msg) < leng:
			chunk = self.socket.recv(leng-len(msg))
			if len(chunk) == 0:
				raise RuntimeError("socket connection broken")
			msg = msg + chunk
		return msg
	def command(self,cmdout,cmdin,dataout=None):
		if dataout:
			l = len(dataout)
			msg = struct.pack(">LL",cmdout,l) + dataout
		else:
			msg = struct.pack(">LL",cmdout,0)
		cmdok = 0
		errcnt = 0
		while cmdok==0:
			try:
				self.mysend(msg)
				header = self.myrecv(8)
				cmd,length = struct.unpack(">LL",header)
				if cmd==cmdin:
					datain = self.myrecv(length)
					cmdok = 1
				else:
					raise RuntimeError("MFS communication error - bad answer")
			except Exception:
				if errcnt<3:
					self.close()
					self.connect()
					errcnt+=1
				else:
					raise RuntimeError("MFS communication error")
		return datain,length

class Master(MFSConn):
	def __init__(self,host,port):
		MFSConn.__init__(self,host,port)
		self.version = (0,0,0)
		self.pro = -1
		self.featuremask = 0
	def set_version(self,version):
		self.version,self.pro = version_convert(version)
		if self.version>=(3,0,72):
			self.featuremask |= (1<<FEATURE_EXPORT_UMASK)
		if self.version>=(3,0,112):
			self.featuremask |= (1<<FEATURE_EXPORT_DISABLES)
	def version_at_least(self,v1,v2,v3):
		return (self.version>=(v1,v2,v3))
	def version_less_than(self,v1,v2,v3):
		return (self.version<(v1,v2,v3))
	def version_is(self,v1,v2,v3):
		return (self.version==(v1,v2,v3))
	def version_unknown(self):
		return (self.version==(0,0,0))
	def is_pro(self):
		return self.pro
	def has_feature(self,featureid):
		return True if (self.featuremask & (1<<featureid)) else False
	def sort_ver(self):
		sortver = "%05u_%03u_%03u" % self.version
		if self.pro==1:
			sortver += "_2"
		elif self.pro==0:
			sortver += "_1"
		else:
			sortver += "_0"
		return sortver

class ExportsEntry:
	def __init__(self,fip1,fip2,fip3,fip4,tip1,tip2,tip3,tip4,path,meta,v1,v2,v3,exportflags,sesflags,umaskval,rootuid,rootgid,mapalluid,mapallgid,mingoal,maxgoal,mintrashtime,maxtrashtime,disables):
		self.ipfrom = (fip1,fip2,fip3,fip4)
		self.ipto = (tip1,tip2,tip3,tip4)
		self.version = (v1,v2,v3)
		self.stripfrom = "%u.%u.%u.%u" % (fip1,fip2,fip3,fip4)
		self.sortipfrom = "%03u_%03u_%03u_%03u" % (fip1,fip2,fip3,fip4)
		self.stripto = "%u.%u.%u.%u" % (tip1,tip2,tip3,tip4)
		self.sortipto = "%03u_%03u_%03u_%03u" % (tip1,tip2,tip3,tip4)
		self.strver,self.sortver = version_str_and_sort((v1,v2,v3))
		self.meta = meta
		self.path = path
		self.exportflags = exportflags
		self.sesflags = sesflags
		self.umaskval = umaskval
		self.rootuid = rootuid
		self.rootgid = rootgid
		self.mapalluid = mapalluid
		self.mapallgid = mapallgid
		self.mingoal = mingoal
		self.maxgoal = maxgoal
		self.mintrashtime = mintrashtime
		self.maxtrashtime = maxtrashtime
		self.disables = disables


class Session:
	def __init__(self,sessionid,ip1,ip2,ip3,ip4,info,openfiles,nsocks,expire,v1,v2,v3,meta,path,sesflags,umaskval,rootuid,rootgid,mapalluid,mapallgid,mingoal,maxgoal,mintrashtime,maxtrashtime,disables,stats_c,stats_l):
		self.ip = (ip1,ip2,ip3,ip4)
		self.version = (v1,v2,v3)
		self.strip = "%u.%u.%u.%u" % (ip1,ip2,ip3,ip4)
		self.sortip = "%03u_%03u_%03u_%03u" % (ip1,ip2,ip3,ip4)
		self.strver,self.sortver = version_str_and_sort((v1,v2,v3))
		self.host = resolve(self.strip)
		self.sessionid = sessionid
		self.info = info
		self.openfiles = openfiles
		self.nsocks = nsocks
		self.expire = expire
		self.meta = meta
		self.path = path
		self.sesflags = sesflags
		self.umaskval = umaskval
		self.rootuid = rootuid
		self.rootgid = rootgid
		self.mapalluid = mapalluid
		self.mapallgid = mapallgid
		self.mingoal = mingoal
		self.maxgoal = maxgoal
		self.mintrashtime = mintrashtime
		self.maxtrashtime = maxtrashtime
		self.disables = disables
		self.stats_c = stats_c
		self.stats_l = stats_l


class ChunkServer:
	def __init__(self,ip1,ip2,ip3,ip4,port,csid,v1,v2,v3,flags,used,total,chunks,tdused,tdtotal,tdchunks,errcnt,load,gracetime,labels,mfrstatus):
		self.ip = (ip1,ip2,ip3,ip4)
		self.version = (v1,v2,v3)
		self.strip = "%u.%u.%u.%u" % (ip1,ip2,ip3,ip4)
		self.sortip = "%03u_%03u_%03u_%03u" % (ip1,ip2,ip3,ip4)
		self.strver,self.sortver = version_str_and_sort((v1,v2,v3))
		self.host = resolve(self.strip)
		self.port = port
		self.csid = csid
		self.flags = flags
		self.used = used
		self.total = total
		self.chunks = chunks
		self.tdused = tdused
		self.tdtotal = tdtotal
		self.tdchunks = tdchunks
		self.errcnt = errcnt
		self.load = load
		self.gracetime = gracetime
		self.labels = labels
		self.mfrstatus = mfrstatus


class DataProvider:
	def __init__(self,masterconn):
		self.masterconn = masterconn
		self.sessions = None
		self.chunkservers = None
		self.exports = None
	def get_exports(self):
		if self.exports==None:
			self.exports=[]
			if self.masterconn.has_feature(FEATURE_EXPORT_DISABLES):
				data,length = masterconn.command(CLTOMA_EXPORTS_INFO,MATOCL_EXPORTS_INFO,struct.pack(">B",3))
			elif self.masterconn.has_feature(FEATURE_EXPORT_UMASK):
				data,length = masterconn.command(CLTOMA_EXPORTS_INFO,MATOCL_EXPORTS_INFO,struct.pack(">B",2))
			elif self.masterconn.version_at_least(1,6,26):
				data,length = masterconn.command(CLTOMA_EXPORTS_INFO,MATOCL_EXPORTS_INFO,struct.pack(">B",1))
			else:
				data,length = masterconn.command(CLTOMA_EXPORTS_INFO,MATOCL_EXPORTS_INFO)
			pos = 0
			while pos<length:
				fip1,fip2,fip3,fip4,tip1,tip2,tip3,tip4,pleng = struct.unpack(">BBBBBBBBL",data[pos:pos+12])
				pos+=12
				path = data[pos:pos+pleng]
				path = path.decode('utf-8','replace')
				pos+=pleng
				if self.masterconn.has_feature(FEATURE_EXPORT_DISABLES):
					v1,v2,v3,exportflags,sesflags,umaskval,rootuid,rootgid,mapalluid,mapallgid,mingoal,maxgoal,mintrashtime,maxtrashtime,disables = struct.unpack(">HBBBBHLLLLBBLLL",data[pos:pos+38])
					pos+=38
					if mingoal<=1 and maxgoal>=9:
						mingoal = None
						maxgoal = None
					if mintrashtime==0 and maxtrashtime==0xFFFFFFFF:
						mintrashtime = None
						maxtrashtime = None
				elif self.masterconn.has_feature(FEATURE_EXPORT_UMASK):
					v1,v2,v3,exportflags,sesflags,umaskval,rootuid,rootgid,mapalluid,mapallgid,mingoal,maxgoal,mintrashtime,maxtrashtime = struct.unpack(">HBBBBHLLLLBBLL",data[pos:pos+34])
					pos+=34
					disables = 0
					if mingoal<=1 and maxgoal>=9:
						mingoal = None
						maxgoal = None
					if mintrashtime==0 and maxtrashtime==0xFFFFFFFF:
						mintrashtime = None
						maxtrashtime = None
				elif self.masterconn.version_at_least(1,6,26):
					v1,v2,v3,exportflags,sesflags,rootuid,rootgid,mapalluid,mapallgid,mingoal,maxgoal,mintrashtime,maxtrashtime = struct.unpack(">HBBBBLLLLBBLL",data[pos:pos+32])
					pos+=32
					disables = 0
					if mingoal<=1 and maxgoal>=9:
						mingoal = None
						maxgoal = None
					if mintrashtime==0 and maxtrashtime==0xFFFFFFFF:
						mintrashtime = None
						maxtrashtime = None
					umaskval = None
				else:
					v1,v2,v3,exportflags,sesflags,rootuid,rootgid,mapalluid,mapallgid = struct.unpack(">HBBBBLLLL",data[pos:pos+22])
					pos+=22
					disables = 0
					mingoal = None
					maxgoal = None
					mintrashtime = None
					maxtrashtime = None
					umaskval = None
				if path=='.':
					meta = 1
					umaskval = None
					disables = 0
				else:
					meta = 0
				expent = ExportsEntry(fip1,fip2,fip3,fip4,tip1,tip2,tip3,tip4,path,meta,v1,v2,v3,exportflags,sesflags,umaskval,rootuid,rootgid,mapalluid,mapallgid,mingoal,maxgoal,mintrashtime,maxtrashtime,disables)
				self.exports.append(expent)
		return self.exports
	def get_sessions(self):
		if self.sessions==None:
			self.sessions=[]
			if self.masterconn.has_feature(FEATURE_EXPORT_DISABLES):
				data,length = self.masterconn.command(CLTOMA_SESSION_LIST,MATOCL_SESSION_LIST,struct.pack(">B",4))
			elif self.masterconn.has_feature(FEATURE_EXPORT_UMASK):
				data,length = self.masterconn.command(CLTOMA_SESSION_LIST,MATOCL_SESSION_LIST,struct.pack(">B",3))
			elif self.masterconn.version_at_least(1,7,8):
				data,length = self.masterconn.command(CLTOMA_SESSION_LIST,MATOCL_SESSION_LIST,struct.pack(">B",2))
			elif self.masterconn.version_at_least(1,6,26):
				data,length = self.masterconn.command(CLTOMA_SESSION_LIST,MATOCL_SESSION_LIST,struct.pack(">B",1))
			else:
				data,length = self.masterconn.command(CLTOMA_SESSION_LIST,MATOCL_SESSION_LIST)
			if self.masterconn.version_less_than(1,6,21):
				statscnt = 16
				pos = 0
			elif self.masterconn.version_is(1,6,21):
				statscnt = 21
				pos = 0
			else:
				statscnt = struct.unpack(">H",data[0:2])[0]
				pos = 2
			while pos<length:
				if self.masterconn.version_at_least(1,7,8):
					sessionid,ip1,ip2,ip3,ip4,v1,v2,v3,openfiles,nsocks,expire,ileng = struct.unpack(">LBBBBHBBLBLL",data[pos:pos+25])
					pos+=25
				else:
					sessionid,ip1,ip2,ip3,ip4,v1,v2,v3,ileng = struct.unpack(">LBBBBHBBL",data[pos:pos+16])
					pos+=16
					openfiles = 0
					nsocks = 1
					expire = 0
				info = data[pos:pos+ileng]
				pos+=ileng
				pleng = struct.unpack(">L",data[pos:pos+4])[0]
				pos+=4
				path = data[pos:pos+pleng]
				pos+=pleng
				info = info.decode('utf-8','replace')
				path = path.decode('utf-8','replace')
				if self.masterconn.has_feature(FEATURE_EXPORT_DISABLES):
					sesflags,umaskval,rootuid,rootgid,mapalluid,mapallgid,mingoal,maxgoal,mintrashtime,maxtrashtime,disables = struct.unpack(">BHLLLLBBLLL",data[pos:pos+33])
					pos+=33
					if mingoal<=1 and maxgoal>=9:
						mingoal = None
						maxgoal = None
					if mintrashtime==0 and maxtrashtime==0xFFFFFFFF:
						mintrashtime = None
						maxtrashtime = None
				elif self.masterconn.has_feature(FEATURE_EXPORT_UMASK):
					sesflags,umaskval,rootuid,rootgid,mapalluid,mapallgid,mingoal,maxgoal,mintrashtime,maxtrashtime = struct.unpack(">BHLLLLBBLL",data[pos:pos+29])
					pos+=29
					disables = 0
					if mingoal<=1 and maxgoal>=9:
						mingoal = None
						maxgoal = None
					if mintrashtime==0 and maxtrashtime==0xFFFFFFFF:
						mintrashtime = None
						maxtrashtime = None
				elif self.masterconn.version_at_least(1,6,26):
					sesflags,rootuid,rootgid,mapalluid,mapallgid,mingoal,maxgoal,mintrashtime,maxtrashtime = struct.unpack(">BLLLLBBLL",data[pos:pos+27])
					pos+=27
					disables = 0
					if mingoal<=1 and maxgoal>=9:
						mingoal = None
						maxgoal = None
					if mintrashtime==0 and maxtrashtime==0xFFFFFFFF:
						mintrashtime = None
						maxtrashtime = None
					umaskval = None
				else:
					sesflags,rootuid,rootgid,mapalluid,mapallgid = struct.unpack(">BLLLL",data[pos:pos+17])
					pos+=17
					disables = 0
					mingoal = None
					maxgoal = None
					mintrashtime = None
					maxtrashtime = None
					umaskval = None
				if statscnt<16:
					stats_c = struct.unpack(">"+"L"*statscnt,data[pos:pos+4*statscnt])+(0,)*(16-statscnt)
					pos+=statscnt*4
					stats_l = struct.unpack(">"+"L"*statscnt,data[pos:pos+4*statscnt])+(0,)*(16-statscnt)
					pos+=statscnt*4
				else:
					stats_c = struct.unpack(">LLLLLLLLLLLLLLLL",data[pos:pos+64])
					pos+=statscnt*4
					stats_l = struct.unpack(">LLLLLLLLLLLLLLLL",data[pos:pos+64])
					pos+=statscnt*4
				if path=='.':
					meta=1
				else:
					meta=0
				ses = Session(sessionid,ip1,ip2,ip3,ip4,info,openfiles,nsocks,expire,v1,v2,v3,meta,path,sesflags,umaskval,rootuid,rootgid,mapalluid,mapallgid,mingoal,maxgoal,mintrashtime,maxtrashtime,disables,stats_c,stats_l)
				self.sessions.append(ses)
		return self.sessions
	def get_chunkservers(self):
		if self.chunkservers==None:
			self.chunkservers=[]
			data,length = masterconn.command(CLTOMA_CSERV_LIST,MATOCL_CSERV_LIST)
			if masterconn.version_at_least(3,0,38) and (length%69)==0:
				n = length//69
				for i in range(n):
					d = data[i*69:(i+1)*69]
					flags,v1,v2,v3,ip1,ip2,ip3,ip4,port,csid,used,total,chunks,tdused,tdtotal,tdchunks,errcnt,load,gracetime,labels,mfrstatus = struct.unpack(">BBBBBBBBHHQQLQQLLLLLB",d)
					cs = ChunkServer(ip1,ip2,ip3,ip4,port,csid,v1,v2,v3,flags,used,total,chunks,tdused,tdtotal,tdchunks,errcnt,load,gracetime,labels,mfrstatus)
					self.chunkservers.append(cs)
			elif masterconn.version_at_least(2,1,0) and (length%68)==0:
				n = length//68
				for i in range(n):
					d = data[i*68:(i+1)*68]
					flags,v1,v2,v3,ip1,ip2,ip3,ip4,port,csid,used,total,chunks,tdused,tdtotal,tdchunks,errcnt,load,gracetime,labels = struct.unpack(">BBBBBBBBHHQQLQQLLLLL",d)
					cs = ChunkServer(ip1,ip2,ip3,ip4,port,csid,v1,v2,v3,flags,used,total,chunks,tdused,tdtotal,tdchunks,errcnt,load,gracetime,labels,None)
					self.chunkservers.append(cs)
			elif masterconn.version_at_least(1,7,25) and masterconn.version_less_than(2,1,0) and (length%64)==0:
				n = length//64
				for i in range(n):
					d = data[i*64:(i+1)*64]
					flags,v1,v2,v3,ip1,ip2,ip3,ip4,port,csid,used,total,chunks,tdused,tdtotal,tdchunks,errcnt,load,gracetime = struct.unpack(">BBBBBBBBHHQQLQQLLLL",d)
					cs = ChunkServer(ip1,ip2,ip3,ip4,port,csid,v1,v2,v3,flags,used,total,chunks,tdused,tdtotal,tdchunks,errcnt,load,gracetime,None,None)
					self.chunkservers.append(cs)
			elif masterconn.version_at_least(1,6,28) and masterconn.version_less_than(1,7,25) and (length%62)==0:
				n = length//62
				for i in range(n):
					d = data[i*62:(i+1)*62]
					disconnected,v1,v2,v3,ip1,ip2,ip3,ip4,port,used,total,chunks,tdused,tdtotal,tdchunks,errcnt,load,gracetime = struct.unpack(">BBBBBBBBHQQLQQLLLL",d)
					cs = ChunkServer(ip1,ip2,ip3,ip4,port,csid,v1,v2,v3,1 if disconnected else 0,used,total,chunks,tdused,tdtotal,tdchunks,errcnt,load,gracetime,None,None)
					self.chunkservers.append(cs)
			elif masterconn.version_less_than(1,6,28) and (length%54)==0:
				n = length//54
				for i in range(n):
					d = data[i*54:(i+1)*54]
					disconnected,v1,v2,v3,ip1,ip2,ip3,ip4,port,used,total,chunks,tdused,tdtotal,tdchunks,errcnt = struct.unpack(">BBBBBBBBHQQLQQLL",d)
					cs = ChunkServer(ip1,ip2,ip3,ip4,port,None,v1,v2,v3,1 if disconnected else 0,used,total,chunks,tdused,tdtotal,tdchunks,errcnt,None,None,None,None)
					self.chunkservers.append(cs)
		return self.chunkservers


def resolve_inodes_paths(masterconn,inodes):
	inodepaths = {}
	if len(inodes)>0:
		data,length = masterconn.command(CLTOMA_MASS_RESOLVE_PATHS,MATOCL_MASS_RESOLVE_PATHS,struct.pack(">"+len(inodes)*"L",*inodes))
		pos = 0
		while pos+8<=length:
			inode,psize = struct.unpack(">LL",data[pos:pos+8])
			pos+=8
			if psize == 0:
				if inode not in inodepaths:
					inodepaths[inode] = []
				inodepaths[inode].append("./META")
			elif pos + psize <= length:
				while psize>=4:
					pleng = struct.unpack(">L",data[pos:pos+4])[0]
					pos+=4
					psize-=4
					path = data[pos:pos+pleng]
					pos+=pleng
					psize-=pleng
					path = path.decode('utf-8','replace')
					if inode not in inodepaths:
						inodepaths[inode] = []
					inodepaths[inode].append(path)
				if psize!=0:
					raise RuntimeError("MFS packet malformed")
		if pos!=length:
			raise RuntimeError("MFS packet malformed")
	return inodepaths


# find leader
leaderispro = 0
leaderfound = 0
leader_exports_checksum = None
leader_usectime = None
followerfound = 0
electfound = 0
leaderconn = None
electconn = None
electinfo = None
elect_exports_checksum = None
dataprovider = None
leaderinfo = None
masterlist = getmasteraddresses()
masterlistver = []
masterlistinfo = []

for mhost,mport in masterlist:
	conn = None
	version = (0,0,0)
	statestr = "???"
	statecolor = 1
	memusage = 0
	syscpu = 0
	usercpu = 0
	lastsuccessfulstore = 0
	lastsaveseconds = 0
	lastsavestatus = 0
	metaversion = 0
	exports_checksum = None
	usectime = None
	chlogtime = 0
	try:
		conn = Master(mhost,mport)
		try:
			data,length = conn.command(CLTOMA_INFO,MATOCL_INFO)
			if length==52:
				version = (1,4,0)
				conn.set_version(version)
				if leaderfound==0:
					leaderconn = conn
					leaderinfo = data
					leaderfound = 1
				statestr = "OLD MASTER (LEADER ONLY)"
				statecolor = 0
			elif length==60:
				version = (1,5,0)
				conn.set_version(version)
				if leaderfound==0:
					leaderconn = conn
					leaderinfo = data
					leaderfound = 1
				statestr = "OLD MASTER (LEADER ONLY)"
				statecolor = 0
			elif length==68 or length==76 or length==101:
				version = struct.unpack(">HBB",data[:4])
				conn.set_version(version)
				if leaderfound==0 and version<(1,7,0):
					leaderconn = conn
					leaderinfo = data
					leaderfound = 1
				if length==76:
					memusage = struct.unpack(">Q",data[4:12])[0]
				if length==101:
					memusage,syscpu,usercpu = struct.unpack(">QQQ",data[4:28])
					syscpu/=10000000.0
					usercpu/=10000000.0
					lastsuccessfulstore,lastsaveseconds,lastsavestatus = struct.unpack(">LLB",data[92:101])
				if version<(1,7,0):
					statestr = "OLD MASTER (LEADER ONLY)"
					statecolor = 0
				else:
					statestr = "UPGRADE THIS UNIT !!!"
					statecolor = 2
			elif length==121 or length==129 or length==137 or length==149:
				offset = 8 if (length==137 or length==149) else 0
				version = struct.unpack(">HBB",data[:4])
				conn.set_version(version)
				memusage,syscpu,usercpu = struct.unpack(">QQQ",data[4:28])
				syscpu/=10000000.0
				usercpu/=10000000.0
				lastsuccessfulstore,lastsaveseconds,lastsavestatus = struct.unpack(">LLB",data[offset+92:offset+101])
				if conn.version_at_least(2,0,14):
					lastsaveseconds = lastsaveseconds / 1000.0
				workingstate,nextstate,stablestate,sync,leaderip,changetime,metaversion = struct.unpack(">BBBBLLQ",data[offset+101:offset+121])
				if length>=129:
					exports_checksum = struct.unpack(">Q",data[offset+121:offset+129])[0]
				if length==149:
					usectime,chlogtime = struct.unpack(">QL",data[length-12:length])
				if workingstate==0xFF and nextstate==0xFF and stablestate==0xFF and sync==0xFF:
					if leaderfound==0:
						leaderconn = conn
						leaderinfo = data
						leaderfound = 1
						leader_exports_checksum = exports_checksum
						leader_usectime = usectime
					statestr = "-"
					statecolor = 0
				elif stablestate==0 or workingstate!=nextstate:
					statestr = "transition %s -> %s" % (state_name(workingstate),state_name(nextstate))
					statecolor = 8
				else:
					statestr = state_name(workingstate)
					statecolor = state_color(workingstate,sync)
					if workingstate==STATE_FOLLOWER or workingstate==STATE_USURPER:
						if sync==0:
							statestr += " (DESYNC)"
						followerfound = 1
						followerconn = conn
						followerinfo = data
						follower_exports_checksum = exports_checksum
					if workingstate==STATE_ELECT and electfound==0:
						electfound = 1
						electconn = conn
						electinfo = data
						elect_exports_checksum = exports_checksum
					if workingstate==STATE_LEADER and leaderfound==0:
						leaderispro = 1
						leaderconn = conn
						leaderinfo = data
						leaderfound = 1
						leader_exports_checksum = exports_checksum
						leader_usectime = usectime
		except Exception:
			statestr = "BUSY"
			statecolor = 7
	except Exception:
		statestr = "DEAD"
	try:
		iptab = tuple(map(int,mhost.split('.')))
		strip = "%u.%u.%u.%u" % iptab
		sortip = "%03u_%03u_%03u_%03u" % iptab
	except Exception:
		strip = mhost
		sortip = mhost
	strver,sortver = version_str_and_sort(version)
	if conn and conn!=leaderconn and conn!=electconn:
		del conn
	masterlistver.append((mhost,mport,version))
	masterlistinfo.append((sortip,strip,sortver,strver,statestr,statecolor,metaversion,memusage,syscpu,usercpu,lastsuccessfulstore,lastsaveseconds,lastsavestatus,exports_checksum,usectime,chlogtime))

if leaderfound:
	masterconn = leaderconn
	masterinfo = leaderinfo
	masterispro = leaderispro
	master_exports_checksum = leader_exports_checksum
elif electfound:
	masterconn = electconn
	masterinfo = electinfo
	masterispro = 1
	master_exports_checksum = elect_exports_checksum
elif followerfound:
	masterconn = followerconn
	masterinfo = followerinfo
	masterispro = 1
	master_exports_checksum = follower_exports_checksum
else:
	masterconn = None
	master_exports_checksum = 0
	for sortip,strip,sortver,strver,statestr,statecolor,metaversion,memusage,syscpu,usercpu,lastsuccessfulstore,lastsaveseconds,lastsavestatus,exports_checksum,usectime,chlogtime in masterlistinfo:
		if exports_checksum!=None:
			master_exports_checksum |= exports_checksum

master_minusectime = None
master_maxusectime = None
if leader_usectime==None or leader_usectime==0:
	for sortip,strip,sortver,strver,statestr,statecolor,metaversion,memusage,syscpu,usercpu,lastsuccessfulstore,lastsaveseconds,lastsavestatus,exportschecksum,usectime,chlogtime in masterlistinfo:
		if usectime!=None and usectime>0:
			if master_minusectime==None or usectime<master_minusectime:
				master_minusectime = usectime
			if master_maxusectime==None or usectime>master_maxusectime:
				master_maxusectime = usectime

if leaderfound and masterconn.version_less_than(1,6,10):
	if cgimode:
		print("Content-Type: text/html; charset=UTF-8")
		print("")
		print("""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">""")
		print("""<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">""")
		print("""<head>""")
		print("""<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />""")
		print("""<title>MFS Info (%s)</title>""" % (htmlentities(mastername)))
		print("""<link rel="stylesheet" href="mfs.css" type="text/css" />""")
		print("""</head>""")
		print("""<body>""")
		if masterconn.version_unknown():
			print("""<h1 align="center">Can't detect MFS master version</h1>""")
		else:
			print("""<h1 align="center">MFS master version not supported (pre 1.6.10)</h1>""")
		print("""</body>""")
		print("""</html>""")
	else:
		if masterconn.version_unknown():
			print("""Can't detect MFS master version""")
		else:
			print("""MFS master version not supported (pre 1.6.10)""")
	sys.exit(1)


dataprovider = DataProvider(masterconn)

# commands
if cgimode:
	# commands in CGI mode
	cmd_success = -1
	if "CSremove" in fields:
		cmd_success = 0
		tracedata = ""
		if leaderfound:
			try:
				serverdata = fields.getvalue("CSremove").split(":")
				if len(serverdata)==2:
					csip = list(map(int,serverdata[0].split(".")))
					csport = int(serverdata[1])
					if len(csip)==4:
						if masterconn.version_less_than(1,6,28):
							data,length = masterconn.command(CLTOMA_CSSERV_COMMAND,MATOCL_CSSERV_COMMAND,struct.pack(">BBBBH",csip[0],csip[1],csip[2],csip[3],csport))
							if length==0:
								cmd_success = 1
								status = 0
						else:
							data,length = masterconn.command(CLTOMA_CSSERV_COMMAND,MATOCL_CSSERV_COMMAND,struct.pack(">BBBBBH",MFS_CSSERV_COMMAND_REMOVE,csip[0],csip[1],csip[2],csip[3],csport))
							if length==1:
								status = (struct.unpack(">B",data))[0]
								cmd_success = 1
			except Exception:
				tracedata = traceback.format_exc()
		url = createjslink({"CSremove":""})
	elif "CSbacktowork" in fields:
		cmd_success = 0
		tracedata = ""
		if leaderfound and masterconn.version_at_least(1,6,28):
			try:
				serverdata = fields.getvalue("CSbacktowork").split(":")
				if len(serverdata)==2:
					csip = list(map(int,serverdata[0].split(".")))
					csport = int(serverdata[1])
					if len(csip)==4:
						data,length = masterconn.command(CLTOMA_CSSERV_COMMAND,MATOCL_CSSERV_COMMAND,struct.pack(">BBBBBH",MFS_CSSERV_COMMAND_BACKTOWORK,csip[0],csip[1],csip[2],csip[3],csport))
						if length==1:
							status = (struct.unpack(">B",data))[0]
							cmd_success = 1
			except Exception:
				tracedata = traceback.format_exc()
		url = createjslink({"CSbacktowork":""})
	elif "CSmaintenanceon" in fields:
		cmd_success = 0
		tracedata = ""
		if leaderfound and masterconn.version_at_least(2,0,11):
			try:
				serverdata = fields.getvalue("CSmaintenanceon").split(":")
				if len(serverdata)==2:
					csip = list(map(int,serverdata[0].split(".")))
					csport = int(serverdata[1])
					if len(csip)==4:
						data,length = masterconn.command(CLTOMA_CSSERV_COMMAND,MATOCL_CSSERV_COMMAND,struct.pack(">BBBBBH",MFS_CSSERV_COMMAND_MAINTENANCEON,csip[0],csip[1],csip[2],csip[3],csport))
						if length==1:
							status = (struct.unpack(">B",data))[0]
							cmd_success = 1
			except Exception:
				tracedata = traceback.format_exc()
		url = createjslink({"CSmaintenanceon":""})
	elif "CSmaintenanceoff" in fields:
		cmd_success = 0
		tracedata = ""
		if leaderfound and masterconn.version_at_least(2,0,11):
			try:
				serverdata = fields.getvalue("CSmaintenanceoff").split(":")
				if len(serverdata)==2:
					csip = list(map(int,serverdata[0].split(".")))
					csport = int(serverdata[1])
					if len(csip)==4:
						data,length = masterconn.command(CLTOMA_CSSERV_COMMAND,MATOCL_CSSERV_COMMAND,struct.pack(">BBBBBH",MFS_CSSERV_COMMAND_MAINTENANCEOFF,csip[0],csip[1],csip[2],csip[3],csport))
						if length==1:
							status = (struct.unpack(">B",data))[0]
							cmd_success = 1
			except Exception:
				tracedata = traceback.format_exc()
		url = createjslink({"CSmaintenanceoff":""})
	elif "MSremove" in fields:
		cmd_success = 0
		tracedata = ""
		if leaderfound:
			try:
				sessionid = int(fields.getvalue("MSremove"))
				data,length = masterconn.command(CLTOMA_SESSION_COMMAND,MATOCL_SESSION_COMMAND,struct.pack(">BL",MFS_SESSION_COMMAND_REMOVE,sessionid))
				if length==1:
					status = (struct.unpack(">B",data))[0]
					cmd_success = 1
			except Exception:
				tracedata = traceback.format_exc()
		url = createjslink({"MSremove":""})
	if cmd_success==1:
		print("Status: 302 Found")
		print("Location: %s" % url)
		print("Content-Type: text/html; charset=UTF-8")
		print("")
		print("""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">""")
		print("""<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">""")
		print("""<head>""")
		print("""<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />""")
		print("""<meta http-equiv="Refresh" content="0; url=%s" />""" % url.replace('&','&amp;'))
		print("""<title>MFS Info (%s)</title>""" % (htmlentities(mastername)))
		print("""<link rel="stylesheet" href="mfs.css" type="text/css" />""")
		print("""</head>""")
		print("""<body>""")
		print("""<h1 align="center"><a href="%s">If you see this then it means that redirection didn't work, so click here</a></h1>""" % url)
		print("""</body>""")
		print("""</html>""")
		sys.exit(0)
	elif cmd_success==0:
		print("Content-Type: text/html; charset=UTF-8")
		print("")
		print("""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">""")
		print("""<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">""")
		print("""<head>""")
		print("""<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />""")
		print("""<meta http-equiv="Refresh" content="5; url=%s" />""" % url.replace('&','&amp;'))
		print("""<title>MFS Info (%s)</title>""" % (htmlentities(mastername)))
		print("""<link rel="stylesheet" href="mfs.css" type="text/css" />""")
		print("""</head>""")
		print("""<body>""")
		print("""<h3 align="center">Can't perform command - wait 5 seconds for refresh</h3>""")
		if tracedata:
			print("""<hr />""")
			print("""<pre>%s</pre>""" % tracedata)
		print("""</body>""")
		print("""</html>""")
		sys.exit(0)
else:
	if leaderfound:
		for cmd in clicommands:
			cmddata = cmd.split('/')
			if cmddata[0]=='RC':
				cmd_success = 0
				try:
					csip = list(map(int,cmddata[1].split(".")))
					csport = int(cmddata[2])
					if len(csip)==4:
						if masterconn.version_less_than(1,6,28):
							data,length = masterconn.command(CLTOMA_CSSERV_COMMAND,MATOCL_CSSERV_COMMAND,struct.pack(">BBBBH",csip[0],csip[1],csip[2],csip[3],csport))
							if length==0:
								cmd_success = 1
								status = 0
						else:
							data,length = masterconn.command(CLTOMA_CSSERV_COMMAND,MATOCL_CSSERV_COMMAND,struct.pack(">BBBBBH",MFS_CSSERV_COMMAND_REMOVE,csip[0],csip[1],csip[2],csip[3],csport))
							if length==1:
								status = (struct.unpack(">B",data))[0]
								cmd_success = 1
					if cmd_success:
						if status==STATUS_OK:
							print("Chunkserver %s/%s has been removed" % (cmddata[1],cmddata[2]))
						elif status==ERROR_NOTFOUND:
							print("Chunkserver %s/%s hasn't been found" % (cmddata[1],cmddata[2]))
						elif status==ERROR_ACTIVE:
							print("Chunkserver %s/%s can't be removed because is still active" % (cmddata[1],cmddata[2]))
						else:
							print("Can't remove chunkserver %s/%s (status:%u)" % (cmddata[1],cmddata[2],status))
					else:
						print("Can't remove chunkserver %s/%s" % (cmddata[1],cmddata[2]))
				except Exception:
					print_exception()
			if cmddata[0]=='BW':
				cmd_success = 0
				try:
					csip = list(map(int,cmddata[1].split(".")))
					csport = int(cmddata[2])
					if len(csip)==4:
						if masterconn.version_at_least(1,6,28):
							data,length = masterconn.command(CLTOMA_CSSERV_COMMAND,MATOCL_CSSERV_COMMAND,struct.pack(">BBBBBH",MFS_CSSERV_COMMAND_BACKTOWORK,csip[0],csip[1],csip[2],csip[3],csport))
							if length==1:
								status = (struct.unpack(">B",data))[0]
								cmd_success = 1
					if cmd_success:
						if status==STATUS_OK:
							print("Chunkserver %s/%s has back to work" % (cmddata[1],cmddata[2]))
						elif status==ERROR_NOTFOUND:
							print("Chunkserver %s/%s hasn't been found" % (cmddata[1],cmddata[2]))
						else:
							print("Can't turn chunkserver %s/%s back to work (status:%u)" % (cmddata[1],cmddata[2],status))
					else:
						print("Can't turn chunkserver %s/%s back to work" % (cmddata[1],cmddata[2]))
				except Exception:
					print_exception()
			if cmddata[0]=='M1':
				cmd_success = 0
				try:
					csip = list(map(int,cmddata[1].split(".")))
					csport = int(cmddata[2])
					if len(csip)==4:
						if masterconn.version_at_least(2,0,11):
							data,length = masterconn.command(CLTOMA_CSSERV_COMMAND,MATOCL_CSSERV_COMMAND,struct.pack(">BBBBBH",MFS_CSSERV_COMMAND_MAINTENANCEON,csip[0],csip[1],csip[2],csip[3],csport))
							if length==1:
								status = (struct.unpack(">B",data))[0]
								cmd_success = 1
					if cmd_success:
						if status==STATUS_OK:
							print("Chunkserver %s/%s has been switched to maintenance mode" % (cmddata[1],cmddata[2]))
						elif status==ERROR_NOTFOUND:
							print("Chunkserver %s/%s hasn't been found" % (cmddata[1],cmddata[2]))
						else:
							print("Can't switch chunkserver %s/%s to maintenance mode (status:%u)" % (cmddata[1],cmddata[2],status))
					else:
						print("Can't switch chunkserver %s/%s to maintenance mode" % (cmddata[1],cmddata[2]))
				except Exception:
					print_exception()
			if cmddata[0]=='M0':
				cmd_success = 0
				try:
					csip = list(map(int,cmddata[1].split(".")))
					csport = int(cmddata[2])
					if len(csip)==4:
						if masterconn.version_at_least(2,0,11):
							data,length = masterconn.command(CLTOMA_CSSERV_COMMAND,MATOCL_CSSERV_COMMAND,struct.pack(">BBBBBH",MFS_CSSERV_COMMAND_MAINTENANCEOFF,csip[0],csip[1],csip[2],csip[3],csport))
							if length==1:
								status = (struct.unpack(">B",data))[0]
								cmd_success = 1
					if cmd_success:
						if status==STATUS_OK:
							print("Chunkserver %s/%s has been switched to standard mode" % (cmddata[1],cmddata[2]))
						elif status==ERROR_NOTFOUND:
							print("Chunkserver %s/%s hasn't been found" % (cmddata[1],cmddata[2]))
						else:
							print("Can't switch chunkserver %s/%s to standard mode (status:%u)" % (cmddata[1],cmddata[2],status))
					else:
						print("Can't switch chunkserver %s/%s to standard mode" % (cmddata[1],cmddata[2]))
				except Exception:
					print_exception()
			if cmddata[0]=='RS':
				cmd_success = 0
				try:
					sessionid = int(cmddata[1])
					data,length = masterconn.command(CLTOMA_SESSION_COMMAND,MATOCL_SESSION_COMMAND,struct.pack(">BL",MFS_SESSION_COMMAND_REMOVE,sessionid))
					if length==1:
						status = (struct.unpack(">B",data))[0]
						cmd_success = 1
					if cmd_success:
						if status==STATUS_OK:
							print("Session %u has been removed" % (sessionid))
						elif status==ERROR_NOTFOUND:
							print("Session %u hasn't been found" % (sessionid))
						elif status==ERROR_ACTIVE:
							print("Session %u can't be removed because is still active" % (sessionid))
						else:
							print("Can't remove session %u (status:%u)" % (sessionid,status))
					else:
						print("Can't remove session %u" % (sessionid))
				except Exception:
					print_exception()
	elif len(clicommands)>0:
		print("Can't perform any operation because there is no leading master")

if cgimode:
	if "sections" in fields:
		sectionstr = fields.getvalue("sections")
		sectionset = set(sectionstr.split("|"))
	else:
		sectionset = set(("IN",))
	if "subsections" in fields:
		subsectionstr = fields.getvalue("subsections")
		sectionsubset = set(subsectionstr.split("|"))
	else:
		sectionsubset = ["IM","LI","IG","MU","IC","IL","MF","CS","MB","SC","OF","AL"] # used only in climode - in cgimode turn on all subsections

	if leaderfound:
		if masterconn.version_less_than(1,7,0):
			sectiondef={
				"IN":"Info",
				"CS":"Servers",
				"HD":"Disks",
				"EX":"Exports",
				"MS":"Mounts",
				"MO":"Operations",
				"MC":"Master Charts",
				"CC":"Server Charts"
			}
			sectionorder=["IN","CS","HD","EX","MS","MO","MC","CC"]
		elif masterconn.version_less_than(2,1,0):
			sectiondef={
				"IN":"Info",
				"CS":"Servers",
				"HD":"Disks",
				"EX":"Exports",
				"MS":"Mounts",
				"MO":"Operations",
				"QU":"Quotas",
				"MC":"Master Charts",
				"CC":"Server Charts"
			}
			sectionorder=["IN","CS","HD","EX","MS","MO","QU","MC","CC"]
		else:
			sectiondef={
				"IN":"Info",
				"CS":"Servers",
				"HD":"Disks",
				"EX":"Exports",
				"MS":"Mounts",
				"MO":"Operations",
				"RS":"Resources",
				"QU":"Quotas",
				"MC":"Master Charts",
				"CC":"Server Charts"
			}
			sectionorder=["IN","CS","HD","EX","MS","MO","RS","QU","MC","CC"]
	elif electfound:
		sectiondef = {
			"IN":"Info",
			"CS":"Servers",
			"HD":"Disks",
			"EX":"Exports",
			"QU":"Quotas",
			"MC":"Master Charts",
			"CC":"Server Charts"
		}
		sectionorder=["IN","CS","HD","EX","QU","MC","CC"]
	elif followerfound:
		sectiondef = {
			"IN":"Info",
			"MC":"Master Charts"
		}
		sectionorder=["IN","MC"]
	else:
		sectiondef = {
			"IN":"Info"
		}
		sectionorder=["IN"]

	print("Content-Type: text/html; charset=UTF-8")
	print("")
	# print """<!-- Put IE into quirks mode -->
	print("""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">""")
	print("""<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">""")
	print("""<head>""")
	print("""<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />""")
	print("""<title>MFS Info (%s)</title>""" % (htmlentities(mastername)))
	print("""<link rel="stylesheet" href="mfs.css" type="text/css" />""")
	print("""<script src="acidtab.js" type="text/javascript"></script>""")
	print("""</head>""")
	print("""<body>""")

	#MENUBAR
	print("""<div id="header">""")
	print("""<table class="HDR" cellpadding="0" cellspacing="0" border="0">""")
	print("""<tr>""")
	print("""<td class="LOGO"><a href="http://moosefs.com"><img src="logomini.png" alt="logo" style="border:0;width:100px;height:47px" /></a></td>""")
	print("""<td class="MENU"><table class="MENU" cellspacing="0">""")
	print("""<tr>""")
	last="U"
	for k in sectionorder:
		if k==sectionorder[-1]:
			last = "L%s" % last
		if k in sectionset:
			if len(sectionset)<=1:
				print("""<td class="%sS">%s &#8722;</td>""" % (last,sectiondef[k]))
			else:
				print("""<td class="%sS"><a href="%s">%s</a> <a href="%s">&#8722;</a></td>""" % (last,createlink({"sections":k}),sectiondef[k],createlink({"sections":"|".join(sectionset-set([k]))})))
			last="S"
		else:
			print("""<td class="%sU"><a href="%s">%s</a> <a href="%s">+</a></td>""" % (last,createlink({"sections":k}),sectiondef[k],createlink({"sections":"|".join(sectionset|set([k]))})))
			last="U"
	print("""</tr>""")
	print("""</table></td>""")
	print("""<td class="FILLER" style="white-space:nowrap;">""")
	print("""CGI version: %s ; python: %u.%u<br />""" % (VERSION,sys.version_info[0],sys.version_info[1]))
	print("""date: %s""" % time.strftime("%Y-%m-%d %H:%M:%S %Z",time.localtime(time.time())))
	print("""</td>""")
	print("""</tr>""")
	print("""</table>""")
	print("""</div>""")

	#print """<div id="footer">
	#Moose File System by Jakub Kruszona-Zawadzki
	#</div>
	#"""

	print("""<div id="container">""")

if leaderfound==0:
	if cgimode:
		out = []
		out.append("""<table class="FR" cellspacing="0">""")
		if len(masterlist)==0:
			out.append("""	<tr>""")
			out.append("""		<td align="center">""")
			out.append("""			<span class="ERROR">Can't find masters (resolve given name) !!!</span><br />""")
			out.append("""			<form method="GET">""")
			out.append("""				Input your DNS master name: <input type="text" name="masterhost" value="%s" size="100">""" % (masterhost))
			for i in createinputs(["masterhost"]):
				out.append("""				%s""" % (i))
			out.append("""				<input type="submit" value="Try it !!!">""")
			out.append("""			</form>""")
			out.append("""		</td>""")
			out.append("""	</tr>""")
		elif electfound:
			out.append("""	<tr>""")
			out.append("""		<td align="center">""")
			out.append("""			<span class="ERROR">Leader master server not found, but there is an elect, so make sure that all chunkservers are running - elect should become a leader soon</span><br />""")
			out.append("""		</td>""")
			out.append("""	</tr>""")
		else:
			out.append("""	<tr>""")
			out.append("""		<td align="center">""")
			out.append("""			<span class="ERROR">Can't find working masters !!!</span><br />""")
			out.append("""			<form method="GET">""")
			out.append("""				Input your DNS master name: <input type="text" name="masterhost" value="%s" size="100"><br />""" % (masterhost))
			out.append("""				Input your master-client port number: <input type="text" name="masterport" value="%u" size="5"><br />""" % (masterport))
			out.append("""				Input your master-control port number: <input type="text" name="mastercontrolport" value="%u" size="5"><br />""" % (mastercontrolport))
			for i in createinputs(["masterhost","masterport","mastercontrolport"]):
				out.append("""				%s""" % (i))
			out.append("""				<input type="submit" value="Try it !!!">""")
			out.append("""			</form>""")
			out.append("""		</td>""")
			out.append("""	</tr>""")
		out.append("""</table>""")
		print("\n".join(out))
	else:
		if len(masterlist)==0:
			print("""Can't find masters (resolve '%s') !!!""" % (masterhost))
		elif electfound:
			print("Leader master server not found, but there is an elect, so make sure that all chunkservers are running - elect should become a leader soon")
		else:
			print("Working master servers not found !!! - maybe you are using wrong port number or wrong dns name")
	if not cgimode:
		Tabble.Needseparator=1

if not cgimode:
	if leaderfound:
		if masterconn.version_less_than(1,7,0):
			allowedsections = ["IN","CS","HD","EX","MS","MO","MC","CC"]
		elif masterconn.version_less_than(2,1,0):
			allowedsections = ["IN","CS","HD","EX","MS","MO","QU","MC","CC"]
		else:
			allowedsections = ["IN","CS","HD","EX","MS","MO","RS","QU","MC","CC"]
	elif electfound:
		allowedsections = ["IN","CS","HD","EX","QU","MC","CC"]
	elif followerfound:
		allowedsections = ["IN","MC"]
	elif len(masterlist)>0:
		allowedsections = ["IN"]
	else:
		sys.exit(1)

	filtered_sectionset = []
	for section in sectionset:
		if section in allowedsections:
			filtered_sectionset.append(section)
		else:
			print("""section '%s' not allowed""" % section)
	sectionset = filtered_sectionset

# parse cgi parameters
if cgimode:
	try:
		INmatrix = int(fields.getvalue("INmatrix"))
	except Exception:
		INmatrix = 0
	try:
		IMorder = int(fields.getvalue("IMorder"))
	except Exception:
		IMorder = 0
	try:
		IMrev = int(fields.getvalue("IMrev"))
	except Exception:
		IMrev = 0
	try:
		MForder = int(fields.getvalue("MForder"))
	except Exception:
		MForder = 0
	try:
		MFrev = int(fields.getvalue("MFrev"))
	except Exception:
		MFrev = 0
	try:
		MFlimit = int(fields.getvalue("MFlimit"))
	except Exception:
		MFlimit = 100
	try:
		CSorder = int(fields.getvalue("CSorder"))
	except Exception:
		CSorder = 0
	try:
		CSrev = int(fields.getvalue("CSrev"))
	except Exception:
		CSrev = 0
	try:
		MBorder = int(fields.getvalue("MBorder"))
	except Exception:
		MBorder = 0
	try:
		MBrev = int(fields.getvalue("MBrev"))
	except Exception:
		MBrev = 0
	try:
		HDorder = int(fields.getvalue("HDorder"))
	except Exception:
		HDorder = 0
	try:
		HDrev = int(fields.getvalue("HDrev"))
	except Exception:
		HDrev = 0
	try:
		HDperiod = int(fields.getvalue("HDperiod"))
	except Exception:
		HDperiod = 0
	try:
		HDtime = int(fields.getvalue("HDtime"))
	except Exception:
		HDtime = 0
	try:
		HDaddrname = int(fields.getvalue("HDaddrname"))
	except Exception:
		HDaddrname = 0
	try:
		EXorder = int(fields.getvalue("EXorder"))
	except Exception:
		EXorder = 0
	try:
		EXrev = int(fields.getvalue("EXrev"))
	except Exception:
		EXrev = 0
	try:
		MSorder = int(fields.getvalue("MSorder"))
	except Exception:
		MSorder = 0
	try:
		MSrev = int(fields.getvalue("MSrev"))
	except Exception:
		MSrev = 0
	try:
		MOorder = int(fields.getvalue("MOorder"))
	except Exception:
		MOorder = 0
	try:
		MOrev = int(fields.getvalue("MOrev"))
	except Exception:
		MOrev = 0
	try:
		MOdata = int(fields.getvalue("MOdata"))
	except Exception:
		MOdata = 0
	try:
		SCorder = int(fields.getvalue("SCorder"))
	except Exception:
		SCorder = 0
	try:
		SCrev = int(fields.getvalue("SCrev"))
	except Exception:
		SCrev = 0
	try:
		OForder = int(fields.getvalue("OForder"))
	except Exception:
		OForder = 0
	try:
		OFrev = int(fields.getvalue("OFrev"))
	except Exception:
		OFrev = 0
	try:
		OFsessionid = int(fields.getvalue("OFsessionid"))
	except Exception:
		OFsessionid = 0
	try:
		ALorder = int(fields.getvalue("ALorder"))
	except Exception:
		ALorder = 0
	try:
		ALrev = int(fields.getvalue("ALrev"))
	except Exception:
		ALrev = 0
	try:
		ALinode = int(fields.getvalue("ALinode"))
	except Exception:
		ALinode = 0
	try:
		QUorder = int(fields.getvalue("QUorder"))
	except Exception:
		QUorder = 0
	try:
		QUrev = int(fields.getvalue("QUrev"))
	except Exception:
		QUrev = 0
	try:
		if "MCdata" in fields:
			MCdata = fields.getvalue("MCdata")
		else:
			MCdata = ""
	except Exception:
		MCdata = ""
	try:
		if "CCdata" in fields:
			CCdata = fields.getvalue("CCdata")
		else:
			CCdata = ""
	except Exception:
		CCdata = ""
else:
	# fix order id's
	if CSorder>=2:
		CSorder+=1
	if leaderfound and masterconn.version_less_than(1,7,25) and CSorder>=4:
		CSorder+=1
	if leaderfound and masterconn.version_less_than(1,6,28) and CSorder>=5:
		CSorder+=1
	if CSorder>=6 and CSorder<=9:
		CSorder+=4
	elif CSorder>=10 and CSorder<=13:
		CSorder+=10

	if MBorder>=2:
		MBorder+=1

	if HDorder>=13 and HDorder<=15:
		HDorder+=7

	if leaderfound and masterconn.version_less_than(1,7,0) and EXorder>=10:
		EXorder+=1

	if MSorder>=3:
		MSorder+=1
	if leaderfound and masterconn.version_less_than(1,7,0) and MSorder>=10:
		MSorder+=1
	if MSorder==0:
		MSorder=2

	if MOorder==2:
		MOorder = 3
	elif MOorder>=3 and MOorder<=18:
		MOorder += 97
	elif MOorder==19:
		MOorder = 150
	elif MOorder!=1:
		MOorder = 0

	if QUorder>=2 and QUorder<=6:
		QUorder += 8
	elif QUorder>=7 and QUorder<=10:
		QUorder += 14
	elif QUorder>=11 and QUorder<=22:
		QUorder = (lambda x: x[0]+x[1]*10)(divmod(QUorder-11,3))+31
	elif QUorder<1 or QUorder>22:
		QUorder = 0


if "IN" in sectionset:
	if cgimode and MFS_MESSAGE:
		out = []
		out.append("""<table class="FR" cellspacing="0">""")
		out.append("""<tr><th>Notice</th></tr>""")
		out.append("""<tr><td>You are currently using GPL version of MooseFS. If you want to find out what great features are available in MooseFS Pro go to <a href="https://moosefs.com/products/">https://moosefs.com/products/</a></td></tr>""")
		out.append("""</table>""")
		print("\n".join(out))

	if "IM" in sectionsubset and len(masterlistinfo)>0:
		try:
			if cgimode:
				out = []
				out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_mfsmasters" cellspacing="0">""")
				out.append("""	<tr><th colspan="13">Metadata Servers (masters)</th></tr>""")
				out.append("""	<tr>""")
				out.append("""		<th class="acid_tab_enumerate">#</th>""")
				out.append("""		<th>ip</th>""")
				out.append("""		<th>version</th>""")
				out.append("""		<th>state</th>""")
				out.append("""		<th>local time</th>""")
				out.append("""		<th>metadata version</th>""")
				out.append("""		<th>metadata delay</th>""")
				out.append("""		<th>RAM used</th>""")
				out.append("""		<th>CPU used</th>""")
				out.append("""		<th>last successful metadata save</th>""")
				out.append("""		<th>last metadata save duration</th>""")
				out.append("""		<th>last metadata save status</th>""")
				out.append("""		<th>exports checksum</th>""")
				out.append("""	</tr>""")
			elif ttymode:
				tab = Tabble("Metadata Servers",12,"r")
				tab.header("ip","version","state","local time","metadata version","metadata delay","RAM used","CPU used","last meta save","last save duration","last save status","exports checksum")
			else:
				tab = Tabble("metadata servers",12)
			masterstab = []
			for sortip,strip,sortver,strver,statestr,statecolor,metaversion,memusage,syscpu,usercpu,lastsuccessfulstore,lastsaveseconds,lastsavestatus,exports_checksum,usectime,chlogtime in masterlistinfo:
				if IMorder==1:
					sf = sortip
				elif IMorder==2:
					sf = sortver
				elif IMorder==3:
					sf = statecolor
				elif IMorder==4:
					sf = usectime if usectime!=None else 0
				elif IMorder==5:
					sf = metaversion
				elif IMorder==6:
					sf = chlogtime if chlogtime!=None else 0
				elif IMorder==7:
					sf = memusage
				elif IMorder==8:
					sf = syscpu+usercpu
				elif IMorder==9:
					sf = lastsuccessfulstore
				elif IMorder==10:
					sf = lastsaveseconds
				elif IMorder==11:
					sf = lastsavestatus
				elif IMorder==12:
					sf = exports_checksum
				else:
					sf = 0
				masterstab.append((sf,sortip,strip,sortver,strver,statestr,statecolor,metaversion,memusage,syscpu,usercpu,lastsuccessfulstore,lastsaveseconds,lastsavestatus,exports_checksum,usectime,chlogtime))

			masterstab.sort()
			if IMrev:
				masterstab.reverse()

			for sf,sortip,strip,sortver,strver,statestr,statecolor,metaversion,memusage,syscpu,usercpu,lastsuccessfulstore,lastsaveseconds,lastsavestatus,exports_checksum,usectime,chlogtime in masterstab:
				if usectime==None or usectime==0:
					secdelta = None
				else:
					secdelta = 0.0
					if leader_usectime==None or leader_usectime==0:
						if master_maxusectime!=None and master_minusectime!=None:
							secdelta = (master_maxusectime - master_minusectime) / 1000000.0
					else:
						if leader_usectime > usectime:
							secdelta = (leader_usectime - usectime) / 1000000.0
						else:
							secdelta = (usectime - leader_usectime) / 1000000.0
				if chlogtime==None or chlogtime==0 or leader_usectime==None or leader_usectime==0:
					metadelay = None
				else:
					metadelay = leader_usectime/1000000.0 - chlogtime
					if metadelay>1.0:
						metadelay-=1.0
					else:
						metadelay=0.0
				if cgimode:
					if masterconn!=None and masterconn.is_pro() and not strver.endswith(" PRO"):
						verclass = "BADVERSION"
					elif masterconn!=None and masterconn.sort_ver() > sortver:
						verclass = "LOWERVERSION"
					elif masterconn!=None and masterconn.sort_ver() < sortver:
						verclass = "HIGHERVERSION"
					else:
						verclass = "OKVERSION"
					out.append("""	<tr>""")
					out.append("""		<td align="right"></td><td align="center"><span class="sortkey">%s </span>%s</td><td align="center"><span class="sortkey">%s </span><span class="%s">%s</span></td>""" % (sortip,strip,sortver,verclass,strver))
					out.append("""		<td align="center"><span class="STATECOLOR%u">%s</span></td>""" % (statecolor,statestr))
					if secdelta==None:
						out.append("""		<td align="center">-</td>""")
					else:
						out.append("""		<td align="center"><span class="%s">%s</span></td>""" % (("ERROR" if secdelta>2.0 else "WARNING" if secdelta>1.0 else "SUCCESS" if secdelta>0.0 else "DEFINED"),time.asctime(time.localtime(usectime//1000000))))
					out.append("""		<td align="right">%s</td>""" % (decimal_number(metaversion)))
					if metadelay==None:
						out.append("""		<td align="right">-</td>""")
					else:
						out.append("""		<td align="right"><span class="%s">%.0f s</span></td>""" % (("SUCCESS" if metadelay<1.0 else "WARNING" if metadelay<6.0 else "ERROR"),metadelay))
					if memusage>0:
						out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(memusage),humanize_number(memusage,"&nbsp;")))
					else:
						out.append("""		<td align="center"><a style="cursor:default" title="obtaining memory usage is not supported by your OS or can't be obtained from server">not available</td>""")
					if syscpu>0 or usercpu>0:
						out.append("""		<td align="center"><a style="cursor:default" title="all:%.7f%% sys:%.7f%% user:%.7f%%">all:%.2f%%&nbsp;sys:%.2f%%&nbsp;user:%.2f%%</a></td>""" % (syscpu+usercpu,syscpu,usercpu,syscpu+usercpu,syscpu,usercpu))
					else:
						out.append("""		<td align="center"><a style="cursor:default" title="obtaining cpu usage is not supported by your OS or can't be obtained from server">not available</td>""")
					if lastsuccessfulstore>0:
						out.append("""		<td align="center">%s</td>""" % time.asctime(time.localtime(lastsuccessfulstore)))
						out.append("""		<td align="center"><a style="cursor:default" title="%s">%s</a></td>""" % (timeduration_to_fullstr(lastsaveseconds),timeduration_to_shortstr(lastsaveseconds)))
					else:
						out.append("""		<td align="center">-</td><td align="center">-</td>""")
					if lastsuccessfulstore>0 or lastsavestatus>0:
						out.append("""		<td align="center"><span class="%s">%s</span></td>""" % ("SUCCESS" if lastsavestatus==0 or lastsavestatus==1 else "WARNING" if lastsavestatus==2 else "ERROR","Saved in background" if lastsavestatus==0 else "Downloaded from other master" if lastsavestatus==1 else "Saved in foreground" if lastsavestatus==2 else "Unknown status: %u" % lastsavestatus))
					else:
						out.append("""		<td align="center">-</td>""")
					if exports_checksum!=None:
						out.append("""		<td align="center"><span class="%s">%016X</span></td>""" % (("ERROR" if exports_checksum != master_exports_checksum else "SUCCESS"),exports_checksum))
					else:
						out.append("""		<td align="center">-</td>""")
					out.append("""	</tr>""")
				else:
					clist = [strip,strver,(statestr,"c%u" % statecolor)]
					if secdelta==None:
						clist.append("not available")
					else:
						if ttymode:
							clist.append((time.asctime(time.localtime(usectime//1000000)),("1" if secdelta>2.0 else "3" if secdelta>1.0 else "4" if secdelta>0.0 else "0")))
						else:
							clist.append("%.6lf" % (usectime/1000000.0))
					clist.append(decimal_number(metaversion))
					if metadelay==None:
						clist.append("not available")
					else:
						if ttymode:
							clist.append((("%.0f s" % metadelay),("4" if metadelay<1.0 else "3" if metadelay<6.0 else "1")))
						else:
							clist.append(int(metadelay))
					if memusage>0:
						if ttymode:
							clist.append(humanize_number(memusage," "))
						else:
							clist.append(memusage)
					else:
						clist.append("not available")
					if syscpu>0 or usercpu>0:
						if ttymode:
							clist.append("all:%.2f%% sys:%.2f%% user:%.2f%%" % (syscpu+usercpu,syscpu,usercpu))
						else:
							clist.append("all:%.7f%% sys:%.7f%% user:%.7f%%" % (syscpu+usercpu,syscpu,usercpu))
					else:
						clist.append("not available")
					if lastsuccessfulstore>0:
						if ttymode:
							clist.append(time.asctime(time.localtime(lastsuccessfulstore)))
							clist.append(timeduration_to_shortstr(lastsaveseconds))
						else:
							clist.append(lastsuccessfulstore)
							clist.append("%.3f" % lastsaveseconds)
					else:
						clist.append("-")
						clist.append("-")
					if lastsuccessfulstore>0 or lastsavestatus>0:
						clist.append(("Saved in background","4") if lastsavestatus==0 else ("Downloaded from other master","4") if lastsavestatus==1 else ("Saved in foreground","2") if lastsavestatus==2 else ("Unknown status: %u" % lastsavestatus,"1"))
					else:
						clist.append("-")
					if exports_checksum!=None:
						clist.append((("%016X" % exports_checksum),("1" if exports_checksum != master_exports_checksum else "4")))
					else:
						clist.append("-")
					tab.append(*clist)

			if len(masterstab)==0:
				if cgimode:
					out.append("""	<tr><td colspan="10">Servers not found !!! - check your DNS</td></tr>""")
				else:
					tab.append(("""Servers not found !!! - check your DNS""","c",9))

			if cgimode:
				out.append("""</table>""")
				print("\n".join(out))
			else:
				print(myunicode(tab))
		except Exception:
			print_exception()


	if "IG" in sectionsubset and masterconn!=None:
		try:
			length = len(masterinfo)
			if length==68:
				v1,v2,v3,total,avail,trspace,trfiles,respace,refiles,nodes,dirs,files,chunks,allcopies,tdcopies = struct.unpack(">HBBQQQLQLLLLLLL",masterinfo)
				strver,sortver = version_str_and_sort((v1,v2,v3))
				if cgimode:
					out = []
					out.append("""<table class="FR" cellspacing="0">""")
					out.append("""	<tr><th colspan="13">Info</th></tr>""")
					out.append("""	<tr>""")
					out.append("""		<th>version</th>""")
					out.append("""		<th>total space</th>""")
					out.append("""		<th>avail space</th>""")
					out.append("""		<th>trash space</th>""")
					out.append("""		<th>trash files</th>""")
					out.append("""		<th>sustained space</th>""")
					out.append("""		<th>sustained files</th>""")
					out.append("""		<th>all fs objects</th>""")
					out.append("""		<th>directories</th>""")
					out.append("""		<th>files</th>""")
					out.append("""		<th>chunks</th>""")
					out.append("""		<th><a style="cursor:default" title="chunks from 'regular' hdd space and 'marked for removal' hdd space">all chunk copies</a></th>""")
					out.append("""		<th><a style="cursor:default" title="only chunks from 'regular' hdd space">regular chunk copies</a></th>""")
					out.append("""	</tr>""")
					out.append("""	<tr>""")
					out.append("""		<td align="center">%s</td>""" % strver)
					out.append("""		<td align="right"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(total),humanize_number(total,"&nbsp;")))
					out.append("""		<td align="right"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(avail),humanize_number(avail,"&nbsp;")))
					out.append("""		<td align="right"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(trspace),humanize_number(trspace,"&nbsp;")))
					out.append("""		<td align="right">%u</td>""" % trfiles)
					out.append("""		<td align="right"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(respace),humanize_number(respace,"&nbsp;")))
					out.append("""		<td align="right">%u</td>""" % refiles)
					out.append("""		<td align="right">%u</td>""" % nodes)
					out.append("""		<td align="right">%u</td>""" % dirs)
					out.append("""		<td align="right">%u</td>""" % files)
					out.append("""		<td align="right">%u</td>""" % chunks)
					out.append("""		<td align="right">%u</td>""" % allcopies)
					out.append("""		<td align="right">%u</td>""" % tdcopies)
					out.append("""	</tr>""")
					out.append("""</table>""")
					print("\n".join(out))
				else:
					if ttymode:
						tab = Tabble("Master Info",2)
					else:
						tab = Tabble("master info",2)
					tab.defattr("l","r")
					tab.append("master version",strver)
					if ttymode:
						tab.append("total space",humanize_number(total," "))
						tab.append("avail space",humanize_number(avail," "))
						tab.append("trash space",humanize_number(trspace," "))
					else:
						tab.append("total space",total)
						tab.append("avail space",avail)
						tab.append("trash space",trspace)
					tab.append("trash files",trfiles)
					if ttymode:
						tab.append("sustained space",humanize_number(respace," "))
					else:
						tab.append("sustained space",respace)
					tab.append("sustained files",refiles)
					tab.append("all fs objects",nodes)
					tab.append("directories",dirs)
					tab.append("files",files)
					tab.append("chunks",chunks)
					tab.append("all chunk copies",allcopies)
					tab.append("regular chunk copies",tdcopies)
					print(myunicode(tab))
			elif length==76:
				v1,v2,v3,memusage,total,avail,trspace,trfiles,respace,refiles,nodes,dirs,files,chunks,allcopies,tdcopies = struct.unpack(">HBBQQQQLQLLLLLLL",masterinfo)
				strver,sortver = version_str_and_sort((v1,v2,v3))
				if cgimode:
					out = []
					out.append("""<table class="FR" cellspacing="0">""")
					out.append("""	<tr><th colspan="14">Info</th></tr>""")
					out.append("""	<tr>""")
					out.append("""		<th>version</th>""")
					out.append("""		<th>RAM used</th>""")
					out.append("""		<th>total space</th>""")
					out.append("""		<th>avail space</th>""")
					out.append("""		<th>trash space</th>""")
					out.append("""		<th>trash files</th>""")
					out.append("""		<th>sustained space</th>""")
					out.append("""		<th>sustained files</th>""")
					out.append("""		<th>all fs objects</th>""")
					out.append("""		<th>directories</th>""")
					out.append("""		<th>files</th>""")
					out.append("""		<th>chunks</th>""")
					out.append("""		<th><a style="cursor:default" title="chunks from 'regular' hdd space and 'marked for removal' hdd space">all chunk copies</a></th>""")
					out.append("""		<th><a style="cursor:default" title="only chunks from 'regular' hdd space">regular chunk copies</a></th>""")
					out.append("""	</tr>""")
					out.append("""	<tr>""")
					out.append("""		<td align="center">%s</td>""" % strver)
					if memusage>0:
						out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(memusage),humanize_number(memusage,"&nbsp;")))
					else:
						out.append("""		<td align="center"><a style="cursor:default" title="obtaining memory usage is not supported by your OS">not available</td>""")
					out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(total),humanize_number(total,"&nbsp;")))
					out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(avail),humanize_number(avail,"&nbsp;")))
					out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(trspace),humanize_number(trspace,"&nbsp;")))
					out.append("""		<td align="center">%u</td>""" % trfiles)
					out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(respace),humanize_number(respace,"&nbsp;")))
					out.append("""		<td align="center">%u</td>""" % refiles)
					out.append("""		<td align="center">%u</td>""" % nodes)
					out.append("""		<td align="center">%u</td>""" % dirs)
					out.append("""		<td align="center">%u</td>""" % files)
					out.append("""		<td align="center">%u</td>""" % chunks)
					out.append("""		<td align="center">%u</td>""" % allcopies)
					out.append("""		<td align="center">%u</td>""" % tdcopies)
					out.append("""	</tr>""")
					out.append("""</table>""")
					print("\n".join(out))
				else:
					if ttymode:
						tab = Tabble("Master Info",2)
					else:
						tab = Tabble("master info",2)
					tab.defattr("l","r")
					tab.append("master version",strver)
					if memusage>0:
						if ttymode:
							tab.append("RAM used",humanize_number(memusage," "))
						else:
							tab.append("RAM used",memusage)
					else:
						tab.append("RAM used","not available")
					if ttymode:
						tab.append("total space",humanize_number(total," "))
						tab.append("avail space",humanize_number(avail," "))
						tab.append("trash space",humanize_number(trspace," "))
					else:
						tab.append("total space",total)
						tab.append("avail space",avail)
						tab.append("trash space",trspace)
					tab.append("trash files",trfiles)
					if ttymode:
						tab.append("sustained space",humanize_number(respace," "))
					else:
						tab.append("sustained space",respace)
					tab.append("sustained files",refiles)
					tab.append("all fs objects",nodes)
					tab.append("directories",dirs)
					tab.append("files",files)
					tab.append("chunks",chunks)
					tab.append("all chunk copies",allcopies)
					tab.append("regular chunk copies",tdcopies)
					print(myunicode(tab))
			elif length==101 or length==121 or length==129 or length==137 or length==149:
				if length>=137:
					v1,v2,v3,memusage,syscpu,usercpu,totalspace,availspace,freespace,trspace,trfiles,respace,refiles,nodes,dirs,files,chunks,allcopies,tdcopies,lastsuccessfulstore,lastsaveseconds,lastsavestatus = struct.unpack(">HBBQQQQQQQLQLLLLLLLLLB",masterinfo[:109])
				else:
					v1,v2,v3,memusage,syscpu,usercpu,totalspace,availspace,trspace,trfiles,respace,refiles,nodes,dirs,files,chunks,allcopies,tdcopies,lastsuccessfulstore,lastsaveseconds,lastsavestatus = struct.unpack(">HBBQQQQQQLQLLLLLLLLLB",masterinfo[:101])
					freespace = None
				strver,sortver = version_str_and_sort((v1,v2,v3))
				syscpu/=10000000.0
				usercpu/=10000000.0
				if masterconn.version_at_least(2,0,14):
					lastsaveseconds = lastsaveseconds / 1000.0
				if cgimode:
					out = []
					if length==101:
						out.append("""<table class="FR" cellspacing="0">""")
						out.append("""	<tr><th colspan="6">General Info</th></tr>""")
						out.append("""	<tr>""")
						out.append("""		<th>version</th>""")
						out.append("""		<th>RAM used</th>""")
						out.append("""		<th>CPU used</th>""")
						out.append("""		<th>last successful metadata save</th>""")
						out.append("""		<th>last metadata save duration</th>""")
						out.append("""		<th>last metadata save status</th>""")
						out.append("""	</tr>""")
						out.append("""	<tr>""")
						out.append("""		<td align="center">%s</td>""" % strver)
						if memusage>0:
							out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(memusage),humanize_number(memusage,"&nbsp;")))
						else:
							out.append("""		<td align="center"><a style="cursor:default" title="obtaining memory usage is not supported by your OS">not available</td>""")
						if syscpu>0 or usercpu>0:
							out.append("""		<td align="center"><a style="cursor:default" title="all:%.7f%% sys:%.7f%% user:%.7f">all:%.2f%%&nbsp;sys:%.2f%%&nbsp;user:%.2f%%</a></td>""" % (syscpu+usercpu,syscpu,usercpu,syscpu+usercpu,syscpu,usercpu))
						else:
							out.append("""		<td align="center"><a style="cursor:default" title="obtaining cpu usage is not supported by your OS">not available</td>""")
						if lastsuccessfulstore>0:
							out.append("""		<td align="center">%s</td>""" % time.asctime(time.localtime(lastsuccessfulstore)))
							out.append("""		<td align="center"><a style="cursor:default" title="%s">%s</a></td>""" % (timeduration_to_fullstr(lastsaveseconds),timeduration_to_shortstr(lastsaveseconds)))
						else:
							out.append("""		<td align="center">-</td><td align="center">-</td>""")
						if lastsuccessfulstore>0 or lastsavestatus>0:
							out.append("""		<td align="center"><span class="%s">%s</span></td>""" % ("SUCCESS" if lastsavestatus==0 else "ERROR","OK" if lastsavestatus==0 else "ERROR (%u)" % lastsavestatus))
						else:
							out.append("""		<td align="center">-</td>""")
						out.append("""	</tr>""")
						out.append("""</table>""")
					out.append("""<table class="FR" cellspacing="0">""")
					out.append("""	<tr><th colspan="%u">Metadata Info</th></tr>""" % (12 if freespace==None else 13))
					out.append("""	<tr>""")
					out.append("""		<th>total space</th>""")
					out.append("""		<th>avail space</th>""")
					if freespace!=None:
						out.append("""		<th>free space</th>""")
					out.append("""		<th>trash space</th>""")
					out.append("""		<th>trash files</th>""")
					out.append("""		<th>sustained space</th>""")
					out.append("""		<th>sustained files</th>""")
					out.append("""		<th>all fs objects</th>""")
					out.append("""		<th>directories</th>""")
					out.append("""		<th>files</th>""")
					out.append("""		<th>chunks</th>""")
					out.append("""		<th><a style="cursor:default" title="chunks from 'regular' hdd space and 'marked for removal' hdd space">all chunk copies</a></th>""")
					out.append("""		<th><a style="cursor:default" title="only chunks from 'regular' hdd space">regular chunk copies</a></th>""")
					out.append("""	</tr>""")
					out.append("""	<tr>""")
					out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(totalspace),humanize_number(totalspace,"&nbsp;")))
					out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(availspace),humanize_number(availspace,"&nbsp;")))
					if freespace!=None:
						out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(freespace),humanize_number(freespace,"&nbsp;")))
					out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(trspace),humanize_number(trspace,"&nbsp;")))
					out.append("""		<td align="center">%u</td>""" % trfiles)
					out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(respace),humanize_number(respace,"&nbsp;")))
					out.append("""		<td align="center">%u</td>""" % refiles)
					out.append("""		<td align="center">%u</td>""" % nodes)
					out.append("""		<td align="center">%u</td>""" % dirs)
					out.append("""		<td align="center">%u</td>""" % files)
					out.append("""		<td align="center">%u</td>""" % chunks)
					out.append("""		<td align="center">%u</td>""" % allcopies)
					out.append("""		<td align="center">%u</td>""" % tdcopies)
					out.append("""	</tr>""")
					out.append("""</table>""")
					print("\n".join(out))
				else:
					if ttymode:
						tab = Tabble("Master Info",2)
					else:
						tab = Tabble("master info",2)
					tab.defattr("l","r")
					tab.append("master version",strver)
					if memusage>0:
						if ttymode:
							tab.append("RAM used",humanize_number(memusage," "))
						else:
							tab.append("RAM used",memusage)
					else:
						tab.append("RAM used","not available")
					if syscpu>0 or usercpu>0:
						if ttymode:
							tab.append("CPU used","%.2f%%" % (syscpu+usercpu))
							tab.append("CPU used (system)","%.2f%%" % (syscpu))
							tab.append("CPU used (user)","%.2f%%" % (usercpu))
						else:
							tab.append("CPU used (system)","%.9f" % (syscpu/100.0))
							tab.append("CPU used (user)","%.9f" % (usercpu/100.0))
					else:
						tab.append("CPU used","not available")
					if ttymode:
						tab.append("total space",humanize_number(totalspace," "))
						tab.append("avail space",humanize_number(availspace," "))
						if freespace!=None:
							tab.append("free space",humanize_number(freespace," "))
						tab.append("trash space",humanize_number(trspace," "))
					else:
						tab.append("total space",totalspace)
						tab.append("avail space",availspace)
						if freespace!=None:
							tab.append("free space",freespace)
						tab.append("trash space",trspace)
					tab.append("trash files",trfiles)
					if ttymode:
						tab.append("sustained space",humanize_number(respace," "))
					else:
						tab.append("sustained space",respace)
					tab.append("sustained files",refiles)
					tab.append("all fs objects",nodes)
					tab.append("directories",dirs)
					tab.append("files",files)
					tab.append("chunks",chunks)
					tab.append("all chunk copies",allcopies)
					tab.append("regular chunk copies",tdcopies)
					if lastsuccessfulstore>0:
						if ttymode:
							tab.append("last successful store",time.asctime(time.localtime(lastsuccessfulstore)))
							tab.append("last save duration",timeduration_to_shortstr(lastsaveseconds))
						else:
							tab.append("last successful store",lastsuccessfulstore)
							tab.append("last save duration","%.3f" % lastsaveseconds)
					else:
						tab.append("last successful store","-")
						tab.append("last save duration","-")
					if lastsuccessfulstore>0 or lastsavestatus>0:
						tab.append("last save status",("Saved in background","4") if lastsavestatus==0 else ("Downloaded from another master","4") if lastsavestatus==1 else ("Saved in foreground","2") if lastsavestatus==2 else ("Unknown status: %u" % lastsavestatus,"1"))
					else:
						tab.append("last save status","-")
					print(myunicode(tab))
			else:
				if cgimode:
					out = []
					out.append("""<table class="FR" cellspacing="0">""")
					out.append("""	<tr><td align="left">unrecognized answer from MFSmaster</td></tr>""")
					out.append("""</table>""")
					print("\n".join(out))
				else:
					print("unrecognized answer from MFSmaster")
		except Exception:
			print_exception()

	if "MU" in sectionsubset and masterconn!=None and masterconn.version_at_least(1,7,16):
		try:
			data,length = masterconn.command(CLTOMA_MEMORY_INFO,MATOCL_MEMORY_INFO)
			if length>=176 and length%16==0:
				memusage = struct.unpack(">QQQQQQQQQQQQQQQQQQQQQQ",data[:176])
				memlabels = ["chunk hash","chunks","cs lists","edge hash","edges","node hash","nodes","deleted nodes","chunk tabs","symlinks","quota"]
				abrlabels = ["c.h.","c.","c.l.","e.h.","e.","n.h.","n.","d.n.","c.t.","s.","q."]
				totalused = 0
				totalallocated = 0
				for i in xrange(11):
					totalused += memusage[1+i*2]
					totalallocated += memusage[i*2]
				if cgimode:
					out = []
					out.append("""<table class="FR" cellspacing="0">""")
					out.append("""	<tr><th colspan="%d">Memory usage detailed info</th></tr>""" % (len(memlabels)+2))
					out.append("""	<tr><th></th>""")
					for i in xrange(11):
						out.append("""		<th>%s</th>""" % memlabels[i])
					out.append("""	<th>total</th></tr>""")
					out.append("""	<tr><th align="center">used</th>""")
					for i in xrange(11):
						out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(memusage[1+i*2]),humanize_number(memusage[1+i*2],"&nbsp;")))
					out.append("""	<td align="center"><a style="cursor:default" title="%s B">%s</a></td></tr>""" % (decimal_number(totalused),humanize_number(totalused,"&nbsp;")))
					out.append("""	<tr><th align="center">allocated</th>""")
					for i in xrange(11):
						out.append("""		<td align="center"><a style="cursor:default" title="%s B">%s</a></td>""" % (decimal_number(memusage[i*2]),humanize_number(memusage[i*2],"&nbsp;")))
					out.append("""	<td align="center"><a style="cursor:default" title="%s B">%s</a></td></tr>""" % (decimal_number(totalallocated),humanize_number(totalallocated,"&nbsp;")))
					out.append("""	<tr><th align="center">utilization</th>""")
					for i in xrange(11):
						if memusage[i*2]:
							percent = "%.2f %%" % (100.0 * memusage[1+i*2] / memusage[i*2])
						else:
							percent = "-"
						out.append("""		<td align="center">%s</td>""" % percent)
					if totalallocated:
						percent = "%.2f %%" % (100.0 * totalused / totalallocated)
					else:
						percent = "-"
					out.append("""	<td align="center">%s</td></tr>""" % percent)
					if totalallocated>0:
						out.append("""	<tr><th align="center">distribution</th>""")
						for i in xrange(11):
							tpercent = "%.2f %%" % (100.0 * memusage[i*2] / totalallocated)
							out.append("""		<td align="center">%s</td>""" % tpercent)
						out.append("""	<td>-</td></tr>""")
						out.append("""  <tr><th align="center">distribution bar</th>""")
						out.append("""		<td colspan="%d" class="NOPADDING">""" % (len(memlabels)+1))
						out.append("""			<table width="100%" cellspacing="0" style="border:0px;" id="bar"><tr>""")
						memdistribution = []
						other = 0.0
						for i,(label,abr) in enumerate(zip(memlabels,abrlabels)):
							tpercent = (100.0 * memusage[i*2] / totalallocated)
							if tpercent>1.0:
								memdistribution.append((tpercent,label,abr))
							else:
								other+=tpercent
						memdistribution.sort()
						memdistribution.reverse()
						if other>0:
							memdistribution.append((other,None,None))
						cl = "FIRST"
						labels = []
						tooltips = []
						for i,(percent,label,abr) in enumerate(memdistribution):
							if label:
								if percent>10.0:
									out.append("""				<td style="width:%.2f%%;" class="MEMDIST%d MEMDIST%s" align="center"><a style="cursor:default;" title="%s (%.2f %%)">%s</a></td>""" % (percent,i,cl,label,percent,label))
								elif percent>3.0:
									out.append("""				<td style="width:%.2f%%;" class="MEMDIST%d MEMDIST%s" align="center"><a style="cursor:default;" title="%s (%.2f %%)">%s</a></td>""" % (percent,i,cl,label,percent,abr))
								else:
									out.append("""				<td style="width:%.2f%%;" class="MEMDIST%d MEMDIST%s" align="center"><a style="cursor:default;" title="%s (%.2f %%)">%s</a></td>""" % (percent,i,cl,label,percent,"#"))
								labels.append(label)
								tooltips.append("%s (%.2f %%)" % (label,percent))
							else:
								out.append("""				<td style="width:%.2f%%;" class="MEMDISTOTHER MEMDIST%s"></td>""" % (percent,cl))
								labels.append("others")
								tooltips.append("other memory segments (%.2f %%)" % (percent))
							cl = "MID"
						out.append("""			</tr></table>""")
						out.append("""<script type="text/javascript">""")
						out.append("""<!--//--><![CDATA[//><!--""")
						out.append("""	var bar_labels = [%s];""" % ",".join(map(repr,labels)))
						out.append("""	var bar_tooltips = [%s];""" % ",".join(map(repr,tooltips)))
						out.append("""//--><!]]>""")
						out.append("""</script>""")
						out.append("""<script type="text/javascript">
<!--//--><![CDATA[//><!--
	function bar_refresh() {
		var b = document.getElementById("bar");
		var i,j,x;
		if (b) {
			var x = b.getElementsByTagName("td");
			for (i=0 ; i<x.length ; i++) {
				x[i].innerHTML = "";
			}
			for (i=0 ; i<x.length ; i++) {
				var width = x[i].clientWidth;
				var label = bar_labels[i];
				var tooltip = bar_tooltips[i];
				x[i].innerHTML = "<a title='" + tooltip + "'>" + label + "</a>";
				if (width<x[i].clientWidth) {
					x[i].innerHTML = "<a title='" + tooltip + "'>&#8230;</a>";
					if (width<x[i].clientWidth) {
						x[i].innerHTML = "<a title='" + tooltip + "'>&#8226;</a>";
						if (width<x[i].clientWidth) {
							x[i].innerHTML = "<a title='" + tooltip + "'>.</a>";
							if (width<x[i].clientWidth) {
								x[i].innerHTML = "";
							}
						}
					} else {
						for (j=1 ; j<bar_labels[i].length-1 ; j++) {
							x[i].innerHTML = "<a title='" + tooltip + "'>"+label.substring(0,j) + "&#8230;</a>";
							if (width<x[i].clientWidth) {
								break;
							}
						}
						x[i].innerHTML = "<a title='" + tooltip + "'>" + label.substring(0,j-1) + "&#8230;</a>";
					}
				}
			}
		}
	}

	function bar_add_event(obj,type,fn) {
		if (obj.addEventListener) {
			obj.addEventListener(type, fn, false);
		} else if (obj.attachEvent) {
			obj.attachEvent('on'+type, fn);
		}
	}

	bar_add_event(window,"load",bar_refresh);
	bar_add_event(window,"resize",bar_refresh);
//--><!]]>
</script>""")
						out.append("""		</td>""")
						out.append("""	</tr>""")
					out.append("""</table>""")
					print("\n".join(out))
				else:
					if ttymode:
						tab = Tabble("Memory Usage Detailed Info",5)
						tab.defattr("l","r","r","r","r")
						tab.header("object name","memory used","memory allocated","utilization percent","percent of total allocated memory")
					else:
						tab = Tabble("memory usage detailed info",3)
						tab.defattr("l","r","r")
						tab.header("object name","memory used","memory allocated")
					for i in xrange(11):
						if ttymode:
							if memusage[i*2]>0:
								upercent = "%.2f %%" % (100.0 * memusage[1+i*2] / memusage[i*2])
							else:
								upercent = "-"
							if totalallocated:
								tpercent = "%.2f %%" % (100.0 * memusage[i*2] / totalallocated)
							else:
								tpercent = "-"
							tab.append(memlabels[i],humanize_number(memusage[1+i*2]," "),humanize_number(memusage[i*2]," "),upercent,tpercent)
						else:
							tab.append(memlabels[i],memusage[1+i*2],memusage[i*2])
					if ttymode:
						tab.append(("---","",5))
						percent = 100.0 * totalused / totalallocated
						tab.append("total",humanize_number(totalused," "),humanize_number(totalallocated," "),"%.2f %%" % percent,"-")
					print(myunicode(tab))
		except Exception:
			print_exception()

	if "IC" in sectionsubset and leaderfound:
		try:
			if masterconn.version_less_than(1,7,0):
				data,length = masterconn.command(CLTOMA_CHUNKS_MATRIX,MATOCL_CHUNKS_MATRIX,struct.pack(">B",0))
				if length==484:
					matrix = []
					matrix.append([])
					for i in range(11):
						matrix[0].append(list(struct.unpack(">LLLLLLLLLLL",data[i*44:i*44+44])))
					data,length = masterconn.command(CLTOMA_CHUNKS_MATRIX,MATOCL_CHUNKS_MATRIX,struct.pack(">B",1))
					if length==484:
						matrix.append([])
						for i in range(11):
							matrix[1].append(list(struct.unpack(">LLLLLLLLLLL",data[i*44:i*44+44])))
				progressstatus = 0
			else:
				data,length = masterconn.command(CLTOMA_CHUNKS_MATRIX,MATOCL_CHUNKS_MATRIX)
				if length==969:
					progressstatus = struct.unpack(">B",data[0:1])[0]
					matrix = ([],[])
					for x in range(2):
						for i in range(11):
							matrix[x].append(list(struct.unpack(">LLLLLLLLLLL",data[1+x*484+i*44:45+x*484+i*44])))
			progressstr = "disconnections" if (progressstatus==1) else "connections" if (progressstatus==2) else "connections and disconnections"
			if len(matrix)==2:
				if cgimode:
					out = []
					out.append("""<table class="acid_tab acid_tab_storageid_mfsmatrix" cellspacing="0" id="mfsmatrix">""")
					out.append("""	<tr><th colspan="13">""")
					out.append("""		<span class="matrix_vis0">All chunks state matrix (counts 'regular' hdd space and 'marked for removal' hdd space : <a href="javascript:acid_tab.switchdisplay('mfsmatrix','matrix_vis',1)" class="VISIBLELINK">switch to 'regular'</a>)</span>""")
					out.append("""		<span class="matrix_vis1">Regular chunks state matrix (counts only 'regular' hdd space : <a href="javascript:acid_tab.switchdisplay('mfsmatrix','matrix_vis',0)" class="VISIBLELINK">switch to 'all'</a>)</span>""")
					out.append("""	</th></tr>""")
					if progressstatus>0:
						out.append("""<tr><th colspan="13"><span class="ERROR">Warning: counters may not be valid - %s in progress</span></th></tr>""" % progressstr)
					out.append("""	<tr>""")
					out.append("""		<th rowspan="2" class="PERC4 acid_tab_skip">goal</th>""")
					out.append("""		<th colspan="12" class="PERC96 acid_tab_skip">valid copies</th>""")
					out.append("""	</tr>""")
					out.append("""	<tr>""")
					out.append("""		<th class="PERC8 acid_tab_skip">0</th>""")
					out.append("""		<th class="PERC8 acid_tab_skip">1</th>""")
					out.append("""		<th class="PERC8 acid_tab_skip">2</th>""")
					out.append("""		<th class="PERC8 acid_tab_skip">3</th>""")
					out.append("""		<th class="PERC8 acid_tab_skip">4</th>""")
					out.append("""		<th class="PERC8 acid_tab_skip">5</th>""")
					out.append("""		<th class="PERC8 acid_tab_skip">6</th>""")
					out.append("""		<th class="PERC8 acid_tab_skip">7</th>""")
					out.append("""		<th class="PERC8 acid_tab_skip">8</th>""")
					out.append("""		<th class="PERC8 acid_tab_skip">9</th>""")
					out.append("""		<th class="PERC8 acid_tab_skip">10+</th>""")
					out.append("""		<th class="PERC8 acid_tab_skip">all</th>""")
					out.append("""	</tr>""")
				elif ttymode:
					if INmatrix==0:
						tab = Tabble("All chunks state matrix",13,"r")
					else:
						tab = Tabble("Regular chunks state matrix",13,"r")
					if progressstatus>0:
						tab.header(("Warning: counters may not be valid - %s in progress" % progressstr,"1c",13))
						tab.header(("---","",13))
					tab.header("",("valid copies","",12))
					tab.header("goal",("---","",12))
					tab.header("","    0    ","    1    ","    2    ","    3    ","    4    ","    5    ","    6    ","    7    ","    8    ","    9    ","   10+   ","   all   ")
				else:
					out = []
					if INmatrix==0:
						mtypeprefix=("all chunks matrix:%s" % plaintextseparator)
					else:
						mtypeprefix=("regular chunks matrix:%s" % plaintextseparator)
				classsum = []
				classsum.append(7*[0])
				classsum.append(7*[0])
				sumlist = []
				sumlist.append(11*[0])
				sumlist.append(11*[0])
				for goal in range(11):
					if cgimode:
						out.append("""	<tr>""")
						if goal==10:
							out.append("""		<th align="center" class="acid_tab_skip">10+</th>""")
						else:
							out.append("""		<th align="center" class="acid_tab_skip">%u</th>""" % goal)
					else:
						if goal==10:
							clist = ["10+"]
						else:
							clist = [goal]
					for vc in range(11):
						if goal==0:
							if vc==0:
								cl = "DELETEREADY"
								clidx = 6
							else:
								cl = "DELETEPENDING"
								clidx = 5
						elif vc==0:
							cl = "MISSING"
							clidx = 0
						elif vc>goal:
							cl = "OVERGOAL"
							clidx = 4
						elif vc<goal:
							if vc==1:
								cl = "ENDANGERED"
								clidx = 1
							else:
								cl = "UNDERGOAL"
								clidx = 2
						else:
							cl = "NORMAL"
							clidx = 3
						classsum[0][clidx]+=matrix[0][goal][vc]
						classsum[1][clidx]+=matrix[1][goal][vc]
						if cgimode:
							out.append("""		<td align="right" class="acid_tab_skip">""")
							if matrix[0][goal][vc]>0:
								out.append("""			<span class="%s matrix_vis0">%u</span>""" % (cl,matrix[0][goal][vc]))
							if matrix[1][goal][vc]>0:
								out.append("""			<span class="%s matrix_vis1">%u</span>""" % (cl,matrix[1][goal][vc]))
							out.append("""		</td>""")
						elif ttymode:
							if matrix[INmatrix][goal][vc]>0:
								clist.append((matrix[INmatrix][goal][vc],"1234678"[clidx]))
							else:
								clist.append("-")
						else:
							if matrix[INmatrix][goal][vc]>0:
								out.append("""%sgoal/copies/chunks:%s%u%s%u%s%u""" % (mtypeprefix,plaintextseparator,goal,plaintextseparator,vc,plaintextseparator,matrix[INmatrix][goal][vc]))
					if cgimode:
						if goal==0:
							out.append("""		<td align="right" class="acid_tab_skip">""")
							out.append("""			<span class="IGNORE matrix_vis0">%u</span>""" % sum(matrix[0][goal]))
							out.append("""			<span class="IGNORE matrix_vis1">%u</span>""" % sum(matrix[1][goal]))
							out.append("""		</td>""")
						else:
							out.append("""		<td align="right" class="acid_tab_skip">""")
							out.append("""			<span class="matrix_vis0">%u</span>""" % sum(matrix[0][goal]))
							out.append("""			<span class="matrix_vis1">%u</span>""" % sum(matrix[1][goal]))
							out.append("""		</td>""")
						out.append("""	</tr>""")
					elif ttymode:
						clist.append(sum(matrix[INmatrix][goal]))
						tab.append(*clist)
					if goal>0:
						sumlist[0] = [ a + b for (a,b) in zip(sumlist[0],matrix[0][goal])]
						sumlist[1] = [ a + b for (a,b) in zip(sumlist[1],matrix[1][goal])]
				if cgimode:
					out.append("""	<tr>""")
					out.append("""		<th align="center" class="acid_tab_skip">all 1+</th>""")
					for vc in range(11):
						out.append("""		<td align="right" class="acid_tab_skip"><span class="matrix_vis0">%u</span><span class="matrix_vis1">%u</span></td>""" % (sumlist[0][vc],sumlist[1][vc]))
					out.append("""		<td align="right" class="acid_tab_skip"><span class="matrix_vis0">%u</span><span class="matrix_vis1">%u</span></td>""" % (sum(sumlist[0]),sum(sumlist[1])))
					out.append("""	</tr>""")
					out.append("""	<tr><th align="center" class="acid_tab_skip">colors</th><td colspan="12" class="acid_tab_skip">""")
					out.append("""		<span class="matrix_vis0">"""+(" / ".join(["""<span class="%sBOX"></span>&nbsp;-&nbsp;%s (<span class="%s">%u</span>)""" % (cl,desc,cl,classsum[0][clidx]) for clidx,cl,desc in [(0,"MISSING","missing"),(1,"ENDANGERED","endangered"),(2,"UNDERGOAL","undergoal"),(3,"NORMAL","stable"),(4,"OVERGOAL","overgoal"),(5,"DELETEPENDING","pending&nbsp;deletion"),(6,"DELETEREADY","ready&nbsp;to&nbsp;be&nbsp;removed")]]))+"</span>")
					out.append("""		<span class="matrix_vis1">"""+(" / ".join(["""<span class="%sBOX"></span>&nbsp;-&nbsp;%s (<span class="%s">%u</span>)""" % (cl,desc,cl,classsum[1][clidx]) for clidx,cl,desc in [(0,"MISSING","missing"),(1,"ENDANGERED","endangered"),(2,"UNDERGOAL","undergoal"),(3,"NORMAL","stable"),(4,"OVERGOAL","overgoal"),(5,"DELETEPENDING","pending&nbsp;deletion"),(6,"DELETEREADY","ready&nbsp;to&nbsp;be&nbsp;removed")]]))+"</span>")
					out.append("""	</td></tr>""")
					out.append("""</table>""")
					print("\n".join(out))
				elif ttymode:
					clist = ["all 1+"]
					for vc in range(11):
						clist.append(sumlist[INmatrix][vc])
					clist.append(sum(sumlist[INmatrix]))
					tab.append(*clist)
					tab.append(("---","",13))
					#tab.append(("missing: %s%u%s / endangered: %s%u%s / undergoal: %s%u%s / stable: %s%u%s / overgoal: %s%u%s / pending deletion: %s%u%s / to be removed: %s%u%s" % (colorcode[0],classsum[0],ttyreset,colorcode[1],classsum[1],ttyreset,colorcode[2],classsum[2],ttyreset,colorcode[3],classsum[3],ttyreset,colorcode[5],classsum[4],ttyreset,colorcode[6],classsum[5],ttyreset,colorcode[7],classsum[6],ttyreset),"c",13))
					tab.append(("missing: %u / endangered: %u / undergoal: %u / stable: %u / overgoal: %u / pending deletion: %u / to be removed: %u" % (classsum[INmatrix][0],classsum[INmatrix][1],classsum[INmatrix][2],classsum[INmatrix][3],classsum[INmatrix][4],classsum[INmatrix][5],classsum[INmatrix][6]),"c",13))
#							out.append("chunkclass missing: %s%u%s" % (colorcode[0],classsum[0],ttyreset))
#							out.append("chunkclass endangered: %s%u%s" % (colorcode[1],classsum[1],ttyreset))
#							out.append("chunkclass undergoal: %s%u%s" % (colorcode[2],classsum[2],ttyreset))
#							out.append("chunkclass stable: %s%u%s" % (colorcode[3],classsum[3],ttyreset))
#							out.append("chunkclass overgoal: %s%u%s" % (colorcode[4],classsum[4],ttyreset))
#							out.append("chunkclass pending deletion: %s%u%s" % (colorcode[5],classsum[5],ttyreset))
#							out.append("chunkclass to be removed: %s%u%s" % (colorcode[6],classsum[6],ttyreset))
					print(myunicode(tab))
				else:
					out.append("%schunkclass missing:%s%u" % (mtypeprefix,plaintextseparator,classsum[INmatrix][0]))
					out.append("%schunkclass endangered:%s%u" % (mtypeprefix,plaintextseparator,classsum[INmatrix][1]))
					out.append("%schunkclass undergoal:%s%u" % (mtypeprefix,plaintextseparator,classsum[INmatrix][2]))
					out.append("%schunkclass stable:%s%u" % (mtypeprefix,plaintextseparator,classsum[INmatrix][3]))
					out.append("%schunkclass overgoal:%s%u" % (mtypeprefix,plaintextseparator,classsum[INmatrix][4]))
					out.append("%schunkclass pending deletion:%s%u" % (mtypeprefix,plaintextseparator,classsum[INmatrix][5]))
					out.append("%schunkclass to be removed:%s%u" % (mtypeprefix,plaintextseparator,classsum[INmatrix][6]))
					print("\n".join(out))
		except Exception:
			print_exception()

	if "IL" in sectionsubset and leaderfound:
		try:
			data,length = masterconn.command(CLTOMA_CHUNKSTEST_INFO,MATOCL_CHUNKSTEST_INFO)
			if length==52:
				loopstart,loopend,del_invalid,ndel_invalid,del_unused,ndel_unused,del_dclean,ndel_dclean,del_ogoal,ndel_ogoal,rep_ugoal,nrep_ugoal,rebalnce = struct.unpack(">LLLLLLLLLLLLL",data)
				if cgimode:
					out = []
					out.append("""<table class="FR" cellspacing="0">""")
					out.append("""	<tr><th colspan="8">Chunk operations info</th></tr>""")
					out.append("""	<tr>""")
					out.append("""		<th colspan="2">loop time</th>""")
					out.append("""		<th colspan="4">deletions</th>""")
					out.append("""		<th colspan="2">replications</th>""")
					out.append("""	</tr>""")
					out.append("""	<tr>""")
					out.append("""		<th>start</th>""")
					out.append("""		<th>end</th>""")
					out.append("""		<th>invalid</th>""")
					out.append("""		<th>unused</th>""")
					out.append("""		<th>disk clean</th>""")
					out.append("""		<th>over goal</th>""")
					out.append("""		<th>under goal</th>""")
					out.append("""		<th>rebalance</th>""")
					out.append("""	</tr>""")
					if loopstart>0:
						out.append("""	<tr>""")
						out.append("""		<td align="center">%s</td>""" % (time.asctime(time.localtime(loopstart)),))
						out.append("""		<td align="center">%s</td>""" % (time.asctime(time.localtime(loopend)),))
						out.append("""		<td align="right">%u/%u</td>""" % (del_invalid,del_invalid+ndel_invalid))
						out.append("""		<td align="right">%u/%u</td>""" % (del_unused,del_unused+ndel_unused))
						out.append("""		<td align="right">%u/%u</td>""" % (del_dclean,del_dclean+ndel_dclean))
						out.append("""		<td align="right">%u/%u</td>""" % (del_ogoal,del_ogoal+ndel_ogoal))
						out.append("""		<td align="right">%u/%u</td>""" % (rep_ugoal,rep_ugoal+nrep_ugoal))
						out.append("""		<td align="right">%u</td>""" % rebalnce)
						out.append("""	</tr>""")
					else:
						out.append("""	<tr>""")
						out.append("""		<td colspan="8" align="center">no data</td>""")
						out.append("""	</tr>""")
					out.append("""</table>""")
					print("\n".join(out))
				elif ttymode:
					tab = Tabble("Chunk operations info",8,"r")
					tab.header(("loop time","",2),("deletions","",4),("replications","",2))
					tab.header(("---","",8))
					tab.header("start","end","invalid","unused","disk clean","over goal","under goal","rebalance")
					if loopstart>0:
						tab.append((time.asctime(time.localtime(loopstart)),"c"),(time.asctime(time.localtime(loopend)),"c"),"%u/%u" % (del_invalid,del_invalid+ndel_invalid),"%u/%u" % (del_unused,del_unused+ndel_unused),"%u/%u" % (del_dclean,del_dclean+ndel_dclean),"%u/%u" % (del_ogoal,del_ogoal+ndel_ogoal),"%u/%u" % (rep_ugoal,rep_ugoal+nrep_ugoal),rebalnce)
					else:
						tab.append(("no data","c",8))
					print(myunicode(tab))
				else:
					out = []
					if loopstart>0:
						out.append("""chunk loop%sstart:%s%u""" % (plaintextseparator,plaintextseparator,loopstart))
						out.append("""chunk loop%send:%s%u""" % (plaintextseparator,plaintextseparator,loopend))
						out.append("""chunk loop%sdeletions%sinvalid:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,del_invalid,del_invalid+ndel_invalid))
						out.append("""chunk loop%sdeletions%sunused:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,del_unused,del_unused+ndel_unused))
						out.append("""chunk loop%sdeletions%sdisk clean:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,del_dclean,del_dclean+ndel_dclean))
						out.append("""chunk loop%sdeletions%sover goal:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,del_ogoal,del_ogoal+ndel_ogoal))
						out.append("""chunk loop%sreplications%sunder goal:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,rep_ugoal,rep_ugoal+nrep_ugoal))
						out.append("""chunk loop%sreplications%srebalance:%s%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,rebalnce))
					else:
						out.append("""chunk loop%sno data""" % plaintextseparator)
					print("\n".join(out))
			elif length==60:
				loopstart,loopend,del_invalid,ndel_invalid,del_unused,ndel_unused,del_dclean,ndel_dclean,del_ogoal,ndel_ogoal,rep_ugoal,nrep_ugoal,rebalnce,locked_unused,locked_used = struct.unpack(">LLLLLLLLLLLLLLL",data)
				if cgimode:
					out = []
					out.append("""<table class="FR" cellspacing="0">""")
					out.append("""	<tr><th colspan="10">Chunk operations info</th></tr>""")
					out.append("""	<tr>""")
					out.append("""		<th colspan="2">loop time</th>""")
					out.append("""		<th colspan="4">deletions</th>""")
					out.append("""		<th colspan="2">replications</th>""")
					out.append("""		<th colspan="2">locked</th>""")
					out.append("""	</tr>""")
					out.append("""	<tr>""")
					out.append("""		<th>start</th>""")
					out.append("""		<th>end</th>""")
					out.append("""		<th>invalid</th>""")
					out.append("""		<th>unused</th>""")
					out.append("""		<th>disk clean</th>""")
					out.append("""		<th>over goal</th>""")
					out.append("""		<th>under goal</th>""")
					out.append("""		<th>rebalance</th>""")
					out.append("""		<th>unused</th>""")
					out.append("""		<th>used</th>""")
					out.append("""	</tr>""")
					if loopstart>0:
						out.append("""	<tr>""")
						out.append("""		<td align="center">%s</td>""" % (time.asctime(time.localtime(loopstart)),))
						out.append("""		<td align="center">%s</td>""" % (time.asctime(time.localtime(loopend)),))
						out.append("""		<td align="right">%u/%u</td>""" % (del_invalid,del_invalid+ndel_invalid))
						out.append("""		<td align="right">%u/%u</td>""" % (del_unused,del_unused+ndel_unused))
						out.append("""		<td align="right">%u/%u</td>""" % (del_dclean,del_dclean+ndel_dclean))
						out.append("""		<td align="right">%u/%u</td>""" % (del_ogoal,del_ogoal+ndel_ogoal))
						out.append("""		<td align="right">%u/%u</td>""" % (rep_ugoal,rep_ugoal+nrep_ugoal))
						out.append("""		<td align="right">%u</td>""" % rebalnce)
						out.append("""		<td align="right">%u</td>""" % locked_unused)
						out.append("""		<td align="right">%u</td>""" % locked_used)
						out.append("""	</tr>""")
					else:
						out.append("""	<tr>""")
						out.append("""		<td colspan="10" align="center">no data</td>""")
						out.append("""	</tr>""")
					out.append("""</table>""")
					print("\n".join(out))
				elif ttymode:
					tab = Tabble("Chunk operations info",10,"r")
					tab.header(("loop time","",2),("deletions","",4),("replications","",2),("locked","",2))
					tab.header(("---","",10))
					tab.header("start","end","invalid","unused","disk clean","over goal","under goal","rebalance","unused","used")
					if loopstart>0:
						tab.append((time.asctime(time.localtime(loopstart)),"c"),(time.asctime(time.localtime(loopend)),"c"),"%u/%u" % (del_invalid,del_invalid+ndel_invalid),"%u/%u" % (del_unused,del_unused+ndel_unused),"%u/%u" % (del_dclean,del_dclean+ndel_dclean),"%u/%u" % (del_ogoal,del_ogoal+ndel_ogoal),"%u/%u" % (rep_ugoal,rep_ugoal+nrep_ugoal),rebalnce,locked_unused,locked_used)
					else:
						tab.append(("no data","c",10))
					print(myunicode(tab))
				else:
					out = []
					if loopstart>0:
						out.append("""chunk loop%sstart:%s%u""" % (plaintextseparator,plaintextseparator,loopstart))
						out.append("""chunk loop%send:%s%u""" % (plaintextseparator,plaintextseparator,loopend))
						out.append("""chunk loop%sdeletions%sinvalid:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,del_invalid,del_invalid+ndel_invalid))
						out.append("""chunk loop%sdeletions%sunused:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,del_unused,del_unused+ndel_unused))
						out.append("""chunk loop%sdeletions%sdisk clean:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,del_dclean,del_dclean+ndel_dclean))
						out.append("""chunk loop%sdeletions%sover goal:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,del_ogoal,del_ogoal+ndel_ogoal))
						out.append("""chunk loop%sreplications%sunder goal:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,rep_ugoal,rep_ugoal+nrep_ugoal))
						out.append("""chunk loop%sreplications%srebalance:%s%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,rebalnce))
						out.append("""chunk loop%slocked%sunused:%s%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,locked_unused))
						out.append("""chunk loop%slocked%sused:%s%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,locked_used))
					else:
						out.append("""chunk loop%sno data""" % plaintextseparator)
					print("\n".join(out))
			elif length==72:
				loopstart,loopend,del_invalid,ndel_invalid,del_unused,ndel_unused,del_dclean,ndel_dclean,del_ogoal,ndel_ogoal,rep_ugoal,nrep_ugoal,rep_wlab,nrep_wlab,rebalnce,labels_dont_match,locked_unused,locked_used = struct.unpack(">LLLLLLLLLLLLLLLLLL",data)
				if cgimode:
					out = []
					out.append("""<table class="FR" cellspacing="0">""")
					out.append("""	<tr><th colspan="11">Chunk operations info</th></tr>""")
					out.append("""	<tr>""")
					out.append("""		<th colspan="2">loop time</th>""")
					out.append("""		<th colspan="4">deletions</th>""")
					out.append("""		<th colspan="3">replications</th>""")
					out.append("""		<th colspan="2">locked</th>""")
					out.append("""	</tr>""")
					out.append("""	<tr>""")
					out.append("""		<th>start</th>""")
					out.append("""		<th>end</th>""")
					out.append("""		<th>invalid</th>""")
					out.append("""		<th>unused</th>""")
					out.append("""		<th>disk clean</th>""")
					out.append("""		<th>over goal</th>""")
					out.append("""		<th>under goal</th>""")
					out.append("""		<th>wrong labels</th>""")
					out.append("""		<th>rebalance</th>""")
					out.append("""		<th>unused</th>""")
					out.append("""		<th>used</th>""")
					out.append("""	</tr>""")
					if loopstart>0:
						out.append("""	<tr>""")
						out.append("""		<td align="center">%s</td>""" % (time.asctime(time.localtime(loopstart)),))
						out.append("""		<td align="center">%s</td>""" % (time.asctime(time.localtime(loopend)),))
						out.append("""		<td align="right">%u/%u</td>""" % (del_invalid,del_invalid+ndel_invalid))
						out.append("""		<td align="right">%u/%u</td>""" % (del_unused,del_unused+ndel_unused))
						out.append("""		<td align="right">%u/%u</td>""" % (del_dclean,del_dclean+ndel_dclean))
						out.append("""		<td align="right">%u/%u</td>""" % (del_ogoal,del_ogoal+ndel_ogoal))
						out.append("""		<td align="right">%u/%u</td>""" % (rep_ugoal,rep_ugoal+nrep_ugoal))
						out.append("""		<td align="right">%u/%u/%u</td>""" % (rep_wlab,labels_dont_match,rep_wlab+nrep_wlab+labels_dont_match))
						out.append("""		<td align="right">%u</td>""" % rebalnce)
						out.append("""		<td align="right">%u</td>""" % locked_unused)
						out.append("""		<td align="right">%u</td>""" % locked_used)
						out.append("""	</tr>""")
					else:
						out.append("""	<tr>""")
						out.append("""		<td colspan="11" align="center">no data</td>""")
						out.append("""	</tr>""")
					out.append("""</table>""")
					print("\n".join(out))
				elif ttymode:
					tab = Tabble("Chunk operations info",11,"r")
					tab.header(("loop time","",2),("deletions","",4),("replications","",3),("locked","",2))
					tab.header(("---","",11))
					tab.header("start","end","invalid","unused","disk clean","over goal","under goal","wrong labels","rebalance","unused","used")
					if loopstart>0:
						tab.append((time.asctime(time.localtime(loopstart)),"c"),(time.asctime(time.localtime(loopend)),"c"),"%u/%u" % (del_invalid,del_invalid+ndel_invalid),"%u/%u" % (del_unused,del_unused+ndel_unused),"%u/%u" % (del_dclean,del_dclean+ndel_dclean),"%u/%u" % (del_ogoal,del_ogoal+ndel_ogoal),"%u/%u" % (rep_ugoal,rep_ugoal+nrep_ugoal),"%u/%u/%u" % (rep_wlab,labels_dont_match,rep_wlab+nrep_wlab+labels_dont_match),rebalnce,locked_unused,locked_used)
					else:
						tab.append(("no data","c",11))
					print(myunicode(tab))
				else:
					out = []
					if loopstart>0:
						out.append("""chunk loop%sstart:%s%u""" % (plaintextseparator,plaintextseparator,loopstart))
						out.append("""chunk loop%send:%s%u""" % (plaintextseparator,plaintextseparator,loopend))
						out.append("""chunk loop%sdeletions%sinvalid:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,del_invalid,del_invalid+ndel_invalid))
						out.append("""chunk loop%sdeletions%sunused:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,del_unused,del_unused+ndel_unused))
						out.append("""chunk loop%sdeletions%sdisk clean:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,del_dclean,del_dclean+ndel_dclean))
						out.append("""chunk loop%sdeletions%sover goal:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,del_ogoal,del_ogoal+ndel_ogoal))
						out.append("""chunk loop%sreplications%sunder goal:%s%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,rep_ugoal,rep_ugoal+nrep_ugoal))
						out.append("""chunk loop%sreplications%swrong labels:%s%u/%u/%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,rep_wlab,labels_dont_match,rep_wlab+nrep_wlab+labels_dont_match))
						out.append("""chunk loop%sreplications%srebalance:%s%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,rebalnce))
						out.append("""chunk loop%slocked%sunused:%s%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,locked_unused))
						out.append("""chunk loop%slocked%sused:%s%u""" % (plaintextseparator,plaintextseparator,plaintextseparator,locked_used))
					else:
						out.append("""chunk loop%sno data""" % plaintextseparator)
					print("\n".join(out))
		except Exception:
			print_exception()

		try:
			if (masterconn.version_at_least(2,0,66) and masterconn.version_less_than(3,0,0)) or masterconn.version_at_least(3,0,19):
				data,length = masterconn.command(CLTOMA_FSTEST_INFO,MATOCL_FSTEST_INFO,struct.pack(">B",0))
				pver = 1
			else:
				data,length = masterconn.command(CLTOMA_FSTEST_INFO,MATOCL_FSTEST_INFO)
				pver = 0
			if length>=(36 + pver*8):
				if pver==1:
					loopstart,loopend,files,ugfiles,mfiles,mtfiles,msfiles,chunks,ugchunks,mchunks,msgbuffleng = struct.unpack(">LLLLLLLLLLL",data[:44])
					datastr = data[44:].decode('utf-8','replace')
				else:
					loopstart,loopend,files,ugfiles,mfiles,chunks,ugchunks,mchunks,msgbuffleng = struct.unpack(">LLLLLLLLL",data[:36])
					datastr = data[36:].decode('utf-8','replace')
				if cgimode:
					out = []
					out.append("""<table class="FR" cellspacing="0">""")
					out.append("""	<tr><th colspan="%u">Filesystem check info</th></tr>""" % (8 if pver==0 else 10))
					out.append("""	<tr>""")
					out.append("""		<th>check loop start time</th>""")
					out.append("""		<th>check loop end time</th>""")
					out.append("""		<th>files</th>""")
					out.append("""		<th>under-goal files</th>""")
					out.append("""		<th>missing files</th>""")
					if pver==1:
						out.append("""		<th>missing trash files</th>""")
						out.append("""		<th>missing sustained files</th>""")
					out.append("""		<th>chunks</th>""")
					out.append("""		<th>under-goal chunks</th>""")
					out.append("""		<th>missing chunks</th>""")
					out.append("""	</tr>""")
					if loopstart>0:
						out.append("""	<tr>""")
						out.append("""		<td align="center">%s</td>""" % (time.asctime(time.localtime(loopstart)),))
						out.append("""		<td align="center">%s</td>""" % (time.asctime(time.localtime(loopend)),))
						out.append("""		<td align="right">%u</td>""" % files)
						out.append("""		<td align="right">%u</td>""" % ugfiles)
						out.append("""		<td align="right">%u</td>""" % mfiles)
						if pver==1:
							out.append("""		<td align="right">%u</td>""" % mtfiles)
							out.append("""		<td align="right">%u</td>""" % msfiles)
						out.append("""		<td align="right">%u</td>""" % chunks)
						out.append("""		<td align="right">%u</td>""" % ugchunks)
						out.append("""		<td align="right">%u</td>""" % mchunks)
						out.append("""	</tr>""")
						if msgbuffleng>0:
							if msgbuffleng==100000:
								out.append("""	<tr><th colspan="8">Important messages (first 100k):</th></tr>""")
							else:
								out.append("""	<tr><th colspan="8">Important messages:</th></tr>""")
							out.append("""	<tr>""")
							out.append("""		<td colspan="8" align="left"><pre>%s</pre></td>""" % (datastr.replace("&","&amp;").replace(">","&gt;").replace("<","&lt;")))
							out.append("""	</tr>""")
					else:
						out.append("""	<tr>""")
						out.append("""		<td colspan="%u" align="center">no data</td>""" % (8 if pver==0 else 10))
						out.append("""	</tr>""")
					out.append("""</table>""")
					print("\n".join(out))
				elif ttymode:
					if pver==1:
						tab = Tabble("Filesystem check info",10,"r")
						tabwidth = 10
						tab.header("check loop start time","check loop end time","files","under-goal files","missing files","missing trash files","missing sustained files","chunks","under-goal chunks","missing chunks")
					else:
						tab = Tabble("Filesystem check info",8,"r")
						tabwidth = 8
						tab.header("check loop start time","check loop end time","files","under-goal files","missing files","chunks","under-goal chunks","missing chunks")
					if loopstart>0:
						if pver==1:
							tab.append((time.asctime(time.localtime(loopstart)),"c"),(time.asctime(time.localtime(loopend)),"c"),files,ugfiles,mfiles,mtfiles,msfiles,chunks,ugchunks,mchunks)
						else:
							tab.append((time.asctime(time.localtime(loopstart)),"c"),(time.asctime(time.localtime(loopend)),"c"),files,ugfiles,mfiles,chunks,ugchunks,mchunks)
						if msgbuffleng>0:
							tab.append(("---","",tabwidth))
							if msgbuffleng==100000:
								tab.append(("Important messages (first 100k):","c",tabwidth))
							else:
								tab.append(("Important messages:","c",tabwidth))
							tab.append(("---","",tabwidth))
							for line in datastr.strip().split("\n"):
								tab.append((line.strip(),"l",tabwidth))
					else:
						tab.append(("no data","c",tabwidth))
					print(myunicode(tab))
				else:
					out = []
					if loopstart>0:
						out.append("""check loop%sstart:%s%u""" % (plaintextseparator,plaintextseparator,loopstart))
						out.append("""check loop%send:%s%u""" % (plaintextseparator,plaintextseparator,loopend))
						out.append("""check loop%sfiles:%s%u""" % (plaintextseparator,plaintextseparator,files))
						out.append("""check loop%sunder-goal files:%s%u""" % (plaintextseparator,plaintextseparator,ugfiles))
						out.append("""check loop%smissing files:%s%u""" % (plaintextseparator,plaintextseparator,mfiles))
						if pver==1:
							out.append("""check loop%smissing trash files:%s%u""" % (plaintextseparator,plaintextseparator,mtfiles))
							out.append("""check loop%smissing sustained files:%s%u""" % (plaintextseparator,plaintextseparator,msfiles))
						out.append("""check loop%schunks:%s%u""" % (plaintextseparator,plaintextseparator,chunks))
						out.append("""check loop%sunder-goal chunks:%s%u""" % (plaintextseparator,plaintextseparator,ugchunks))
						out.append("""check loop%smissing chunks:%s%u""" % (plaintextseparator,plaintextseparator,mchunks))
						if msgbuffleng>0:
							for line in datastr.strip().split("\n"):
								out.append("check loop%simportant messages:%s%s" % (plaintextseparator,plaintextseparator,line.strip()))
					else:
						out.append("""check loop: no data""")
					print("\n".join(out))
		except Exception:
			print_exception()

	if "MF" in sectionsubset and leaderfound and ((masterconn.version_at_least(2,0,66) and masterconn.version_less_than(3,0,0)) or masterconn.version_at_least(3,0,19)):
		try:
			inodes = set()
			missingchunks = []
			if ((masterconn.version_at_least(2,0,71) and masterconn.version_less_than(3,0,0)) or masterconn.version_at_least(3,0,25)):
				data,length = masterconn.command(CLTOMA_MISSING_CHUNKS,MATOCL_MISSING_CHUNKS,struct.pack(">B",1))
				if length%17==0:
					n = length//17
					for x in xrange(n):
						chunkid,inode,indx,mtype = struct.unpack(">QLLB",data[x*17:x*17+17])
						inodes.add(inode)
						missingchunks.append((chunkid,inode,indx,mtype))
				mode = 1
			else:
				data,length = masterconn.command(CLTOMA_MISSING_CHUNKS,MATOCL_MISSING_CHUNKS)
				if length%16==0:
					n = length//16
					for x in xrange(n):
						chunkid,inode,indx = struct.unpack(">QLL",data[x*16:x*16+16])
						inodes.add(inode)
						missingchunks.append((chunkid,inode,indx,None))
				mode = 0
			inodepaths = resolve_inodes_paths(masterconn,inodes)
			mcdata = []
			mccnt = 0
			for chunkid,inode,indx,mtype in missingchunks:
				if inode in inodepaths:
					paths = inodepaths[inode]
					mccnt += len(paths)
				else:
					paths = []
					mccnt += 1
				sf = paths
				if MForder==1:
					sf = paths
				elif MForder==2:
					sf = inode
				elif MForder==3:
					sf = indx
				elif MForder==4:
					sf = chunkid
				elif MForder==5:
					sf = mtype
				mcdata.append((sf,paths,inode,indx,chunkid,mtype))
			mcdata.sort()
			if MFrev:
				mcdata.reverse()
			if cgimode:
				out = []
				if mccnt>0:
					out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_missingfiles" cellspacing="0">""")
					if MFlimit>0 and mccnt>MFlimit:
						out.append("""	<tr><th colspan="%u">Missing files (gathered by previous file-loop) - %u/%u entries - <a href="%s" class="VISIBLELINK">show more</a> - <a href="%s" class="VISIBLELINK">show all</a></th></tr>""" % ((6 if mode==1 else 5),MFlimit,mccnt,createlink({"MFlimit":"%u" % (MFlimit + 100)}),createlink({"MFlimit":"0"})))
					else:
						out.append("""	<tr><th colspan="%u">Missing files (gathered by previous file-loop)</th></tr>""" % (6 if mode==1 else 5))
					out.append("""	<tr>""")
					out.append("""		<th rowspan="2" class="acid_tab_enumerate">#</th>""")
					out.append("""		<th rowspan="2">paths</th>""")
					out.append("""		<th rowspan="2">inode</th>""")
					out.append("""		<th rowspan="2">index</th>""")
					out.append("""		<th rowspan="2">chunk&nbsp;id</th>""")
					if mode==1:
						out.append("""		<th rowspan="2">type&nbsp;of&nbsp;missing&nbsp;chunk</th>""")
					out.append("""	</tr>""")
			elif ttymode:
				if mode==1:
					tab = Tabble("Missing Files/Chunks (gathered by previous file-loop)",5)
					tab.header("path","inode","index","chunk id","type of missing chunk")
					tab.defattr("l","r","r","r","r")
				else:
					tab = Tabble("Missing Files/Chunks (gathered by previous file-loop)",4)
					tab.header("path","inode","index","chunk id")
					tab.defattr("l","r","r","r")
			else:
				tab = Tabble("missing files",(5 if mode==1 else 4))
			missingcount = 0
			for sf,paths,inode,indx,chunkid,mtype in mcdata:
				if mtype==0:
					mtypestr = "NO COPY"
				elif mtype==1:
					mtypestr = "INVALID COPIES"
				elif mtype==2:
					mtypestr = "WRONG VERSIONS"
				else:
					mtypestr = "OTHER"
				if cgimode:
					if mccnt>0:
						if len(paths)==0:
							if missingcount<MFlimit or MFlimit==0:
								out.append("""	<tr>""")
								out.append("""		<td align="right"></td>""")
								out.append("""		<td align="left"> * unknown path * (deleted file)</td>""")
								out.append("""		<td align="right">%u</td>""" % inode)
								out.append("""		<td align="right">%u</td>""" % indx)
								out.append("""		<td align="right">%016X</td>""" % chunkid)
								if mode==1:
									out.append("""		<td align="right">%s</td>""" % mtypestr)
								out.append("""	</tr>""")
							missingcount += 1
						else:
							for path in paths:
								if missingcount<MFlimit or MFlimit==0:
									out.append("""	<tr>""")
									out.append("""		<td align="right"></td>""")
									out.append("""		<td align="left">%s</td>""" % path)
									out.append("""		<td align="right">%u</td>""" % inode)
									out.append("""		<td align="right">%u</td>""" % indx)
									out.append("""		<td align="right">%016X</td>""" % chunkid)
									if mode==1:
										out.append("""		<td align="right">%s</td>""" % mtypestr)
									out.append("""	</tr>""")
								missingcount += 1
				else:
					if len(paths)==0:
						dline = [" * unknown path * (deleted file)",inode,indx,"%016X" % chunkid]
						if mode==1:
							dline.append(mtypestr)
						tab.append(*dline)
					else:
						for path in paths:
							dline = [path,inode,indx,"%016X" % chunkid]
							if mode==1:
								dline.append(mtypestr)
							tab.append(*dline)
			if cgimode:
				if mccnt>0:
					out.append("""</table>""")
				print("\n".join(out))
			else:
				print(myunicode(tab))
		except Exception:
			print_exception()

if "CS" in sectionset:
	if "CS" in sectionsubset:
		try:
			if cgimode:
				out = []
				out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_mfscs" cellspacing="0">""")
				if masterconn.version_at_least(3,0,38):
					out.append("""	<tr><th colspan="19">Chunk Servers</th></tr>""")
				elif masterconn.version_at_least(2,1,0):
					out.append("""	<tr><th colspan="18">Chunk Servers</th></tr>""")
				elif masterconn.version_at_least(2,0,11):
					out.append("""	<tr><th colspan="17">Chunk Servers</th></tr>""")
				elif masterconn.version_at_least(1,7,25):
					out.append("""	<tr><th colspan="16">Chunk Servers</th></tr>""")
				elif masterconn.version_at_least(1,6,28):
					out.append("""	<tr><th colspan="15">Chunk Servers</th></tr>""")
				else:
					out.append("""	<tr><th colspan="14">Chunk Servers</th></tr>""")
				out.append("""	<tr>""")
				out.append("""		<th rowspan="2" class="acid_tab_enumerate">#</th>""")
				out.append("""		<th rowspan="2">host</th>""")
				out.append("""		<th rowspan="2">ip</th>""")
				out.append("""		<th rowspan="2">port</th>""")
				if masterconn.version_at_least(1,7,25):
					out.append("""		<th rowspan="2">id</th>""")
				if masterconn.version_at_least(2,1,0):
					out.append("""		<th rowspan="2">labels</th>""")
				out.append("""		<th rowspan="2">version</th>""")
				if masterconn.version_at_least(1,6,28):
					out.append("""		<th rowspan="2">load</th>""")
				if masterconn.version_at_least(2,0,11):
					out.append("""		<th rowspan="2">maintenance</th>""")
				out.append("""		<th colspan="4">'regular' hdd space</th>""")
				if masterconn.version_at_least(3,0,38):
					out.append("""		<th colspan="5">'marked for removal' hdd space</th>""")
				else:
					out.append("""		<th colspan="4">'marked for removal' hdd space</th>""")
				out.append("""	</tr>""")
				out.append("""	<tr>""")
				out.append("""		<th>chunks</th>""")
				out.append("""		<th>used</th>""")
				out.append("""		<th>total</th>""")
				out.append("""		<th class="PROGBAR">% used</th>""")
				if masterconn.version_at_least(3,0,38):
					out.append("""		<th>status</th>""")
				out.append("""		<th>chunks</th>""")
				out.append("""		<th>used</th>""")
				out.append("""		<th>total</th>""")
				out.append("""		<th class="PROGBAR">% used</th>""")
				out.append("""	</tr>""")
			elif ttymode:
				if masterconn.version_at_least(3,0,38):
					tab = Tabble("Chunk Servers",16,"r")
					tab.header("","","","","","","",("'regular' hdd space","",4),("'marked for removal' hdd space","",5))
					tab.header("ip/host","port","id","labels","version","load","maintenance",("---","",9))
					tab.header("","","","","","","","chunks","used","total","% used","status","chunks","used","total","% used")
				elif masterconn.version_at_least(2,1,0):
					tab = Tabble("Chunk Servers",15,"r")
					tab.header("","","","","","","",("'regular' hdd space","",4),("'marked for removal' hdd space","",4))
					tab.header("ip/host","port","id","labels","version","load","maintenance",("---","",8))
					tab.header("","","","","","","","chunks","used","total","% used","chunks","used","total","% used")
				elif masterconn.version_at_least(2,0,11):
					tab = Tabble("Chunk Servers",14,"r")
					tab.header("","","","","","",("'regular' hdd space","",4),("'marked for removal' hdd space","",4))
					tab.header("ip/host","port","id","version","load","maintenance",("---","",8))
					tab.header("","","","","","","chunks","used","total","% used","chunks","used","total","% used")
				elif masterconn.version_at_least(1,7,25):
					tab = Tabble("Chunk Servers",13,"r")
					tab.header("","","","","",("'regular' hdd space","",4),("'marked for removal' hdd space","",4))
					tab.header("ip/host","port","id","version","load",("---","",8))
					tab.header("","","","","","chunks","used","total","% used","chunks","used","total","% used")
				elif masterconn.version_at_least(1,6,28):
					tab = Tabble("Chunk Servers",12,"r")
					tab.header("","","","",("'regular' hdd space","",4),("'marked for removal' hdd space","",4))
					tab.header("ip/host","port","version","load",("---","",8))
					tab.header("","","","","chunks","used","total","% used","chunks","used","total","% used")
				else:
					tab = Tabble("Chunk Servers",11,"r")
					tab.header("","","",("'regular' hdd space","",4),("'marked for removal' hdd space","",4))
					tab.header("ip/host","port","version",("---","",8))
					tab.header("","","","chunks","used","total","% used","chunks","used","total","% used")
			else:
				if masterconn.version_at_least(3,0,38):
					tab = Tabble("chunk servers",14)
				elif masterconn.version_at_least(2,1,0):
					tab = Tabble("chunk servers",13)
				elif masterconn.version_at_least(2,0,11):
					tab = Tabble("chunk servers",12)
				elif masterconn.version_at_least(1,7,25):
					tab = Tabble("chunk servers",11)
				elif masterconn.version_at_least(1,6,28):
					tab = Tabble("chunk servers",10)
				else:
					tab = Tabble("chunk servers",9)
			servers = []
			dservers = []
			usedsum = 0
			totalsum = 0
			for cs in dataprovider.get_chunkservers():
				if cs.total>0:
					usedsum+=cs.used
					totalsum+=cs.total
				if CSorder==1:
					sf = cs.host
				elif CSorder==2 or CSorder==0:
					sf = cs.sortip
				elif CSorder==3:
					sf = cs.port
				elif CSorder==4:
					sf = cs.csid
				elif CSorder==5:
					sf = cs.sortver
				elif CSorder==6:
					sf = (cs.gracetime,cs.load)
				elif CSorder==10:
					sf = cs.chunks
				elif CSorder==11:
					sf = cs.used
				elif CSorder==12:
					sf = cs.total
				elif CSorder==13:
					if cs.total>0:
						sf = (1.0*cs.used)/cs.total
					else:
						sf = 0
				elif CSorder==20:
					sf = cs.tdchunks
				elif CSorder==21:
					sf = cs.tdused
				elif CSorder==22:
					sf = cs.tdtotal
				elif CSorder==23:
					if cs.tdtotal>0:
						sf = (1.0*cs.tdused)/cs.tdtotal
					else:
						sf = 0
				else:
					sf = 0
				if (cs.flags&1)==0:
					servers.append((sf,cs.host,cs.sortip,cs.strip,cs.port,cs.csid,cs.sortver,cs.strver,cs.flags,cs.used,cs.total,cs.chunks,cs.tdused,cs.tdtotal,cs.tdchunks,cs.errcnt,cs.load,cs.gracetime,cs.labels,cs.mfrstatus))
				else:
					dservers.append((sf,cs.host,cs.sortip,cs.strip,cs.port,cs.csid,cs.flags))
			servers.sort()
			dservers.sort()
			if CSrev:
				servers.reverse()
				dservers.reverse()
			if totalsum>0:
				avgpercent = (usedsum*100.0)/totalsum
			else:
				avgpercent = 0
			for sf,host,sortip,strip,port,csid,sortver,strver,flags,used,total,chunks,tdused,tdtotal,tdchunks,errcnt,load,gracetime,labels,mfrstatus in servers:
				if cgimode:
					if masterconn.is_pro() and not strver.endswith(" PRO"):
						verclass = "BADVERSION"
					elif masterconn.sort_ver() > sortver:
						verclass = "LOWERVERSION"
					elif masterconn.sort_ver() < sortver:
						verclass = "HIGHERVERSION"
					else:
						verclass = "OKVERSION"
					if masterconn.version_at_least(2,0,11) and leaderfound:
						if (flags&2)==0:
							mmstr = "OFF"
							mm = "switch on"
							mmurl = createlink({"CSmaintenanceon":("%s:%u" % (strip,port))})
							cl = None
						elif (flags&4)==0:
							mmstr = "ON"
							mm = "switch off"
							mmurl = createlink({"CSmaintenanceoff":("%s:%u" % (strip,port))})
							cl = "MAINTAINREADY"
						else:
							mmstr = "ON (TEMP)"
							mm = "switch off"
							mmurl = createlink({"CSmaintenanceoff":("%s:%u" % (strip,port))})
							cl = "MAINTAINREADY"
					else:
						cl = None
					out.append("""	<tr>""")
					out.append("""		<td align="right"></td>""")
					if cl:
						out.append("""		<td align="left"><span class="%s">%s</span></td>""" % (cl,host))
						out.append("""		<td align="center"><span class="sortkey">%s </span><span class="%s">%s</span></td>""" % (sortip,cl,strip))
						out.append("""		<td align="center"><span class="%s">%u</span></td>""" % (cl,port))
						if masterconn.version_at_least(1,7,25):
							out.append("""		<td align="center"><span class="%s">%u</span></td>""" % (cl,csid))
					else:
						out.append("""		<td align="left">%s</td>""" % (host))
						out.append("""		<td align="center"><span class="sortkey">%s </span>%s</td>""" % (sortip,strip))
						out.append("""		<td align="center">%u</td>""" % (port))
						if masterconn.version_at_least(1,7,25):
							out.append("""		<td align="center">%u</td>""" % (csid))
					if masterconn.version_at_least(2,1,0):
						if labels==0:
							labelstr = "-"
						else:
							labelstab = []
							for bit,char in enumerate(map(chr,range(ord('A'),ord('Z')+1))):
								if labels & (1<<bit):
									labelstab.append(char)
							labelstr = ",".join(labelstab)
						out.append("""		<td align="left">%s</td>""" % labelstr)
					out.append("""		<td align="center"><span class="sortkey">%s </span><span class="%s">%s</span></td>""" % (sortver,verclass,strver))
					if masterconn.version_at_least(1,6,28):
						if gracetime>=0x80000000:
							if gracetime>=0xC0000000:
								out.append("""		<td align="right"><a style="cursor:default" title="server in heavy load state"><span class="GRACETIME">&lt;%u&gt;</span></a></td>""" % (load))
							else:
								out.append("""		<td align="right"><a style="cursor:default" title="internal rebalance in progress"><span class="GRACETIME">(%u)</span></a></td>""" % (load))
						elif gracetime>0:
							out.append("""		<td align="right"><a style="cursor:default" title="back after %u seconds" href="%s"><span class="GRACETIME">[%u]</span></a></td>""" % (gracetime,createlink({"CSbacktowork":("%s:%u" % (strip,port))}),load))
						else:
							out.append("""		<td align="right">%u</td>""" % (load))
					if masterconn.version_at_least(2,0,11):
						if leaderfound:
							out.append("""		<td align="center">%s : <a href="%s">%s</a></td>""" % (mmstr,mmurl,mm))
						else:
							out.append("""		<td align="center">not available</td>""")
					out.append("""		<td align="right">%u</td><td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B">%s</a></td><td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B">%s</a></td>""" % (chunks,used,decimal_number(used),humanize_number(used,"&nbsp;"),total,decimal_number(total),humanize_number(total,"&nbsp;")))
					if (total>0):
						usedpercent = (used*100.0)/total
						if usedpercent<avgpercent:
							diffstr = "&#8722;%.4f" % (avgpercent-usedpercent)
						else:
							diffstr = "+%.4f" % (usedpercent-avgpercent)
						out.append("""		<td align="center"><span class="sortkey">%.10f </span><div class="PROGBOX" style="width:200px;"><div class="PROGCOVER" style="width:%.2f%%;"></div><div class="PROGAVG" style="width:%.2f%%"></div><div class="PROGVALUE"><a style="cursor:default" title="%.4f%% = (avg%s%%)">%.2f</a></div></div></td>""" % (usedpercent,100.0-usedpercent,avgpercent,usedpercent,diffstr,usedpercent))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span><div class="PROGBOX" style="width:200px;"><div class="PROGCOVER" style="width:100%;"></div><div class="PROGVALUE">-</div></div></td>""")
					if masterconn.version_at_least(3,0,38):
						if tdchunks==0 or leaderfound==0:
							out.append("""		<td align="center">-</td>""")
						elif mfrstatus==1:
							out.append("""		<td align="center"><a style="cursor:default" title="disks can not be safely removed - please wait"><span class="NOTICE">NOT&nbsp;READY</span></a></td>""")
						elif mfrstatus==2:
							out.append("""		<td align="center"><a style="cursor:default" title="all disks marked for removal can be safely removed"><span class="OK">READY</span></a></td>""")
						else:
							out.append("""		<td align="center"><a style="cursor:default" title="wait for chunk loop finish to stabilize state">PENDING</a></td>""")
					out.append("""		<td align="right">%u</td><td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B">%s</a></td><td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B">%s</a></td>""" % (tdchunks,tdused,decimal_number(tdused),humanize_number(tdused,"&nbsp;"),tdtotal,decimal_number(tdtotal),humanize_number(tdtotal,"&nbsp;")))
					if (tdtotal>0):
						usedpercent = (tdused*100.0)/tdtotal
						out.append("""		<td align="center"><span class="sortkey">%.10f </span><div class="PROGBOX" style="width:200px;"><div class="PROGCOVER" style="width:%.2f%%;"></div><div class="PROGVALUE">%.2f</div></div></td>""" % (usedpercent,100.0-usedpercent,usedpercent))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span><div class="PROGBOX" style="width:200px;"><div class="PROGCOVER" style="width:100%;"></div><div class="PROGVALUE">-</div></div></td>""")
					out.append("""	</tr>""")
				elif ttymode:
					if total>0:
						regperc = "%.2f%%" % ((used*100.0)/total)
					else:
						regperc = "-"
					if tdtotal>0:
						tdperc = "%.2f%%" % ((tdused*100.0)/tdtotal)
					else:
						tdperc = "-"
					data = [host,port]
					if masterconn.version_at_least(1,7,25):
						data.append(csid)
					if masterconn.version_at_least(2,1,0):
						if labels==0xFFFFFFFF or labels==0:
							labelstr = "-"
						else:
							labelstab = []
							for bit,char in enumerate(map(chr,range(ord('A'),ord('Z')+1))):
								if labels & (1<<bit):
									labelstab.append(char)
							labelstr = ",".join(labelstab)
						data.append(labelstr)
					data.append(strver)
					if masterconn.version_at_least(1,6,28):
						if gracetime>=0x80000000:
							if gracetime>=0xC0000000:
								data.append("<%u>" % load)
							else:
								data.append("(%u)" % load)
						elif gracetime>0:
							data.append("[%u]" % load)
						else:
							data.append(load)
					if masterconn.version_at_least(2,0,11):
						if leaderfound==0:
							data.append("not available")
						elif (flags&2)==0:
							data.append("off")
						elif (flags&4)==0:
							data.append("on")
						else:
							data.append("on (temp)")
					data.extend([chunks,humanize_number(used," "),humanize_number(total," "),regperc])
					if masterconn.version_at_least(3,0,38):
						if tdchunks==0 or leaderfound==0:
							data.append("-")
						elif mfrstatus==1:
							data.append(("NOT READY",'3'))
						elif mfrstatus==2:
							data.append(("READY",'4'))
						else:
							data.append("PENDING")
					data.extend([tdchunks,humanize_number(tdused," "),humanize_number(tdtotal," "),tdperc])
					tab.append(*data)
				else:
					data = [host,port]
					if masterconn.version_at_least(1,7,25):
						data.append(csid)
					if masterconn.version_at_least(2,1,0):
						if labels==0xFFFFFFFF or labels==0:
							labelstr = "-"
						else:
							labelstab = []
							for bit,char in enumerate(map(chr,range(ord('A'),ord('Z')+1))):
								if labels & (1<<bit):
									labelstab.append(char)
							labelstr = ",".join(labelstab)
						data.append(labelstr)
					data.append(strver)
					if masterconn.version_at_least(1,6,28):
						if gracetime>=0x80000000:
							if gracetime>=0xC0000000:
								data.append("<%u>" % load)
							else:
								data.append("(%u)" % load)
						elif gracetime>0:
							data.append("[%u]" % load)
						else:
							data.append(load)
					if masterconn.version_at_least(2,0,11):
						if leaderfound==0:
							data.append("-")
						elif (flags&2)==0:
							data.append("maintenance_off")
						elif (flags&4)==0:
							data.append("maintenance_on")
						else:
							data.append("maintenance_tmp_on")
					data.extend([chunks,used,total])
					if masterconn.version_at_least(3,0,38):
						if tdchunks==0 or leaderfound==0:
							data.append("-")
						elif mfrstatus==1:
							data.append("NOT READY")
						elif mfrstatus==2:
							data.append("READY")
						else:
							data.append("PENDING")
					data.extend([tdchunks,tdused,tdtotal])
					tab.append(*data)
			if len(dservers)>0:
				if cgimode:
					out.append("""</table>""")
					out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_mfsdiscs" cellspacing="0">""")
					if masterconn.version_at_least(2,0,11):
						out.append("""	<tr><th colspan="7">Disconnected Chunk Servers</th></tr>""")
					elif masterconn.version_at_least(1,7,25):
						out.append("""	<tr><th colspan="6">Disconnected Chunk Servers</th></tr>""")
					else:
						out.append("""	<tr><th colspan="5">Disconnected Chunk Servers</th></tr>""")
					out.append("""	<tr>""")
					out.append("""		<th class="acid_tab_enumerate">#</th>""")
					out.append("""		<th>host</th>""")
					out.append("""		<th>ip</th>""")
					out.append("""		<th>port</th>""")
					if masterconn.version_at_least(1,7,25):
						out.append("""		<th>id</th>""")
					if masterconn.version_at_least(2,0,11):
						out.append("""		<th>maintenance</th>""")
					if leaderfound:
						out.append("""		<th class="acid_tab_skip">remove</th>""")
					else:
						out.append("""		<th class="acid_tab_skip">temporarily remove</th>""")
					out.append("""	</tr>""")
				elif ttymode:
					if masterconn.version_at_least(3,0,38):
						tab.append(("---","",16))
						tab.append(("disconnected servers","1c",16))
						tab.append(("---","",16))
						tab.append(("ip/host","c"),("port","c"),("id","r"),("maintenance","c"),("change maintenance command","c",6),("remove command","c",6))
						tab.append(("---","",16))
					elif masterconn.version_at_least(2,1,0):
						tab.append(("---","",15))
						tab.append(("disconnected servers","1c",15))
						tab.append(("---","",15))
						tab.append(("ip/host","c"),("port","c"),("id","r"),("maintenance","c"),("change maintenance command","c",5),("remove command","c",6))
						tab.append(("---","",15))
					elif masterconn.version_at_least(2,0,11):
						tab.append(("---","",14))
						tab.append(("disconnected servers","1c",14))
						tab.append(("---","",14))
						tab.append(("ip/host","c"),("port","c"),("id","r"),("maintenance","c"),("change maintenance command","c",5),("remove command","c",5))
						tab.append(("---","",14))
					elif masterconn.version_at_least(1,7,25):
						tab.append(("---","",13))
						tab.append(("disconnected servers","1c",13))
						tab.append(("---","",13))
						tab.append(("ip/host","c"),("port","c"),("id","r"),("remove command","c",10))
						tab.append(("---","",13))
					elif masterconn.version_at_least(1,6,28):
						tab.append(("---","",12))
						tab.append(("disconnected servers","1c",12))
						tab.append(("---","",12))
						tab.append(("ip/host","c"),("port","c"),("remove command","c",10))
						tab.append(("---","",12))
					else:
						tab.append(("---","",11))
						tab.append(("disconnected servers","1c",11))
						tab.append(("---","",11))
						tab.append(("ip/host","c"),("port","c"),("remove command","c",9))
						tab.append(("---","",11))
				else:
					print(myunicode(tab))
					print("")
					if masterconn.version_at_least(2,0,11):
						tab = Tabble("Disconnected chunk servers",4)
					elif masterconn.version_at_least(1,7,25):
						tab = Tabble("Disconnected chunk servers",3)
					else:
						tab = Tabble("Disconnected chunk servers",2)
			for sf,host,sortip,strip,port,csid,flags in dservers:
				if cgimode:
					out.append("""	<tr>""")
					if masterconn.version_at_least(2,0,11):
						if leaderfound==0:
							cl = "DISCONNECTED"
						elif (flags&2)==0:
							mmstr = "OFF"
							mm = "switch on"
							mmurl = createlink({"CSmaintenanceon":("%s:%u" % (strip,port))})
							cl = "DISCONNECTED"
						elif (flags&4)==0:
							mmstr = "ON"
							mm = "switch off"
							mmurl = createlink({"CSmaintenanceoff":("%s:%u" % (strip,port))})
							cl = "MAINTAINED"
						else:
							mmstr = "ON (temp)"
							mm = "switch off"
							mmurl = createlink({"CSmaintenanceoff":("%s:%u" % (strip,port))})
							cl = "TMPMAINTAINED"
						out.append("""		<td align="right"></td><td align="left"><span class="%s">%s</span></td>""" % (cl,host))
						out.append("""		<td align="center"><span class="sortkey">%s </span><span class="%s">%s</span></td>""" % (sortip,cl,strip))
						out.append("""		<td align="center"><span class="%s">%u</span></td>""" % (cl,port))
						if masterconn.version_at_least(1,7,25):
							out.append("""		<td align="right"><span class="%s">%u</span></td>""" % (cl,csid))
						if leaderfound:
							out.append("""		<td align="center"><span class="%s">%s : <a href="%s">%s</a></span></td>""" % (cl,mmstr,mmurl,mm))
						else:
							out.append("""		<td align="center"><span class="%s">not available</td>""" % cl)
						if leaderfound:
							out.append("""		<td align="center"><a href="%s">click to remove</a></td>""" % (createlink({"CSremove":("%s:%u" % (strip,port))})))
						elif masterconn.version_at_least(3,0,67):
							out.append("""		<td align="center"><a href="%s">click to temporarily remove</a></td>""" % (createlink({"CStmpremove":("%s:%u" % (strip,port))})))
						else:
							out.append("""		<td align="center">not available</td>""")
					else:
						out.append("""		<td align="right"></td><td align="left"><span class="DISCONNECTED">%s</span></td>""" % (host))
						out.append("""		<td align="center"><span class="sortkey">%s </span><span class="DISCONNECTED">%s</span></td>""" % (sortip,strip))
						out.append("""		<td align="center"><span class="DISCONNECTED">%u</span></td>""" % (port))
						if masterconn.version_at_least(1,7,25):
							out.append("""		<td align="right"><span class="DISCONNECTED">%u</span></td>""" % (csid))
						if leaderfound:
							out.append("""		<td align="center"><a href="%s">click to remove</a></td>""" % (createlink({"CSremove":("%s:%u" % (strip,port))})))
						else:
							out.append("""		<td align="center">not available</td>""")
					out.append("""	</tr>""")
				elif ttymode:
					data = [host,port]
					if masterconn.version_at_least(1,7,25):
						data.append(csid)
					if masterconn.version_at_least(2,0,11):
						if leaderfound==0:
							mm = "-"
							mmcmd = "not available"
						elif (flags&2)==0:
							mm = "off"
							mmcmd = "%s -H %s -P %u -CM1/%s/%s" % (sys.argv[0],masterhost,masterport,strip,port)
						elif (flags&4)==0:
							mm = "on"
							mmcmd = "%s -H %s -P %u -CM0/%s/%s" % (sys.argv[0],masterhost,masterport,strip,port)
						else:
							mm = "on (temp)"
							mmcmd = "%s -H %s -P %u -CM0/%s/%s" % (sys.argv[0],masterhost,masterport,strip,port)
						data.append(mm)
						if masterconn.version_at_least(3,0,38):
							data.append((mmcmd,"l",6))
						else:
							data.append((mmcmd,"l",5))
						if leaderfound:
							rmcmd = "%s -H %s -P %u -CRC/%s/%s" % (sys.argv[0],masterhost,masterport,strip,port)
						elif masterconn.version_at_least(3,0,67):
							rmcmd = "%s -H %s -P %u -CTR/%s/%s" % (sys.argv[0],masterhost,masterport,strip,port)
						else:
							rmcmd = "not available"
						if masterconn.version_at_least(2,1,0):
							data.append((rmcmd,"l",6))
						else:
							data.append((rmcmd,"l",5))
					else:
						if leaderfound:
							rmcmd = "%s -H %s -P %u -CRC/%s/%s" % (sys.argv[0],masterhost,masterport,strip,port)
						else:
							rmcmd = "not available"
						if masterconn.version_at_least(1,6,28):
							data.append((rmcmd,"l",10))
						else:
							data.append((rmcmd,"l",9))
					tab.append(*data)
				else:
					if masterconn.version_at_least(2,0,11):
						if leaderfound==0:
							mm = "-"
						elif (flags&2)==0:
							mm = "maintenance_off"
						elif (flags&4)==0:
							mm = "maintenance_on"
						else:
							mm = "maintenance_temp_on"
						tab.append(host,port,csid,mm)
					elif masterconn.version_at_least(1,7,25):
						tab.append(host,port,csid)
					else:
						tab.append(host,port)
			if cgimode:
				out.append("""</table>""")
				print("\n".join(out))
			else:
				print(myunicode(tab))
		except Exception:
			print_exception()

	if "MB" in sectionsubset and leaderfound:
		try:
			if cgimode:
				out = []
				out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_mfsmbl" cellspacing="0">""")
				out.append("""	<tr><th colspan="4">Metadata Backup Loggers</th></tr>""")
				out.append("""	<tr>""")
				out.append("""		<th class="acid_tab_enumerate">#</th>""")
				out.append("""		<th>host</th>""")
				out.append("""		<th>ip</th>""")
				out.append("""		<th>version</th>""")
				out.append("""	</tr>""")
			elif ttymode:
				tab = Tabble("Metadata Backup Loggers",2,"r")
				tab.header("ip/host","version")
			else:
				tab = Tabble("metadata backup loggers",2)
			data,length = masterconn.command(CLTOMA_MLOG_LIST,MATOCL_MLOG_LIST)
			if (length%8)==0:
				n = length//8
				servers = []
				for i in range(n):
					d = data[i*8:(i+1)*8]
					v1,v2,v3,ip1,ip2,ip3,ip4 = struct.unpack(">HBBBBBB",d)
					strip = "%u.%u.%u.%u" % (ip1,ip2,ip3,ip4)
					host = resolve(strip)
					sortip = "%03u_%03u_%03u_%03u" % (ip1,ip2,ip3,ip4)
					strver,sortver = version_str_and_sort((v1,v2,v3))
					sf = (ip1,ip2,ip3,ip4)
					if MBorder==1:
						sf = host
					elif MBorder==2:
						sf = sortip
					elif MBorder==3:
						sf = sortver
					servers.append((sf,host,sortip,strip,sortver,strver))
				servers.sort()
				if MBrev:
					servers.reverse()
				for sf,host,sortip,strip,sortver,strver in servers:
					if cgimode:
						if masterconn.is_pro() and not strver.endswith(" PRO"):
							verclass = "BADVERSION"
						elif masterconn.sort_ver() > sortver:
							verclass = "LOWERVERSION"
						elif masterconn.sort_ver() < sortver:
							verclass = "HIGHERVERSION"
						else:
							verclass = "OKVERSION"
						out.append("""	<tr>""")
						out.append("""		<td align="right"></td><td align="left">%s</td><td align="center"><span class="sortkey">%s </span>%s</td><td align="center"><span class="sortkey">%s </span><span class="%s">%s</span></td>""" % (host,sortip,strip,sortver,verclass,strver))
						out.append("""	</tr>""")
					else:
						tab.append(host,strver)
			if cgimode:
				out.append("""</table>""")
				print("\n".join(out))
			else:
				print(myunicode(tab))
		except Exception:
			print_exception()

if "HD" in sectionset:
	try:
		# get cs list
		hostlist = []
		for cs in dataprovider.get_chunkservers():
			if (cs.flags&1)==0:
				hostlist.append((cs.ip,cs.port,cs.version,cs.mfrstatus))

		# get hdd lists one by one
		hdd = []
		shdd = []
		for (ip1,ip2,ip3,ip4),port,version,mfrstatus in hostlist:
#		for v1,v2,v3,ip1,ip2,ip3,ip4,port in hostlist:
			hostip = "%u.%u.%u.%u" % (ip1,ip2,ip3,ip4)
			hostkey = "%s:%u" % (hostip,port)
			hoststr = resolve(hostip)
			if port>0:
				if version<=(1,6,8):
					hdd.append((None,hostkey,"0","version too old","version too old",0,0,0,0,0,0,[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]))
				else:
					conn = MFSConn(hostip,port)
					data,length = conn.command(CLTOCS_HDD_LIST,CSTOCL_HDD_LIST)
					while length>0:
						entrysize = struct.unpack(">H",data[:2])[0]
						entry = data[2:2+entrysize]
						data = data[2+entrysize:]
						length -= 2+entrysize
						if sys.version_info[0]<3:
							plen = ord(entry[0])
						else:
							plen = entry[0]
						hddpath = entry[1:plen+1]
						hddpath = hddpath.decode('utf-8','replace')
						hostpath = "%s:%u:%s" % (hoststr,port,hddpath)
						ippath = "%s:%u:%s" % (hostip,port,hddpath)
						sortippath = "%03u.%03u.%03u.%03u:%05u:%s" % (ip1,ip2,ip3,ip4,port,hddpath)
						flags,errchunkid,errtime,used,total,chunkscnt = struct.unpack(">BQLQQL",entry[plen+1:plen+34])
						rbytes = [0,0,0]
						wbytes = [0,0,0]
						usecreadsum = [0,0,0]
						usecwritesum = [0,0,0]
						usecfsyncsum = [0,0,0]
						rops = [0,0,0]
						wops = [0,0,0]
						fsyncops = [0,0,0]
						usecreadmax = [0,0,0]
						usecwritemax = [0,0,0]
						usecfsyncmax = [0,0,0]
						if entrysize==plen+34+144:
							rbytes[0],wbytes[0],usecreadsum[0],usecwritesum[0],rops[0],wops[0],usecreadmax[0],usecwritemax[0] = struct.unpack(">QQQQLLLL",entry[plen+34:plen+34+48])
							rbytes[1],wbytes[1],usecreadsum[1],usecwritesum[1],rops[1],wops[1],usecreadmax[1],usecwritemax[1] = struct.unpack(">QQQQLLLL",entry[plen+34+48:plen+34+96])
							rbytes[2],wbytes[2],usecreadsum[2],usecwritesum[2],rops[2],wops[2],usecreadmax[2],usecwritemax[2] = struct.unpack(">QQQQLLLL",entry[plen+34+96:plen+34+144])
#								if HDperiod==0:
#									rbytes,wbytes,usecreadsum,usecwritesum,rops,wops,usecreadmax,usecwritemax = struct.unpack(">QQQQLLLL",entry[plen+34:plen+34+48])
#								elif HDperiod==1:
#									rbytes,wbytes,usecreadsum,usecwritesum,rops,wops,usecreadmax,usecwritemax = struct.unpack(">QQQQLLLL",entry[plen+34+48:plen+34+96])
#								elif HDperiod==2:
#									rbytes,wbytes,usecreadsum,usecwritesum,rops,wops,usecreadmax,usecwritemax = struct.unpack(">QQQQLLLL",entry[plen+34+96:plen+34+144])
						elif entrysize==plen+34+192:
							rbytes[0],wbytes[0],usecreadsum[0],usecwritesum[0],usecfsyncsum[0],rops[0],wops[0],fsyncops[0],usecreadmax[0],usecwritemax[0],usecfsyncmax[0] = struct.unpack(">QQQQQLLLLLL",entry[plen+34:plen+34+64])
							rbytes[1],wbytes[1],usecreadsum[1],usecwritesum[1],usecfsyncsum[1],rops[1],wops[1],fsyncops[1],usecreadmax[1],usecwritemax[1],usecfsyncmax[1] = struct.unpack(">QQQQQLLLLLL",entry[plen+34+64:plen+34+128])
							rbytes[2],wbytes[2],usecreadsum[2],usecwritesum[2],usecfsyncsum[2],rops[2],wops[2],fsyncops[2],usecreadmax[2],usecwritemax[2],usecfsyncmax[2] = struct.unpack(">QQQQQLLLLLL",entry[plen+34+128:plen+34+192])
#								if HDperiod==0:
#									rbytes,wbytes,usecreadsum,usecwritesum,usecfsyncsum,rops,wops,fsyncops,usecreadmax,usecwritemax,usecfsyncmax = struct.unpack(">QQQQQLLLLLL",entry[plen+34:plen+34+64])
#								elif HDperiod==1:
#									rbytes,wbytes,usecreadsum,usecwritesum,usecfsyncsum,rops,wops,fsyncops,usecreadmax,usecwritemax,usecfsyncmax = struct.unpack(">QQQQQLLLLLL",entry[plen+34+64:plen+34+128])
#								elif HDperiod==2:
#									rbytes,wbytes,usecreadsum,usecwritesum,usecfsyncsum,rops,wops,fsyncops,usecreadmax,usecwritemax,usecfsyncmax = struct.unpack(">QQQQQLLLLLL",entry[plen+34+128:plen+34+192])
						rbw = [0,0,0]
						wbw = [0,0,0]
						usecreadavg = [0,0,0]
						usecwriteavg = [0,0,0]
						usecfsyncavg = [0,0,0]
						for i in range(3):
							if usecreadsum[i]>0:
								rbw[i] = rbytes[i]*1000000//usecreadsum[i]
							if usecwritesum[i]+usecfsyncsum[i]>0:
								wbw[i] = wbytes[i]*1000000//(usecwritesum[i]+usecfsyncsum[i])
							if rops[i]>0:
								usecreadavg[i] = usecreadsum[i]//rops[i]
							if wops[i]>0:
								usecwriteavg[i] = usecwritesum[i]//wops[i]
							if fsyncops[i]>0:
								usecfsyncavg[i] = usecfsyncsum[i]//fsyncops[i]
						sf = sortippath
						if HDorder==1:
							sf = sortippath
						elif HDorder==2:
							sf = chunkscnt
						elif HDorder==3:
							sf = errtime
						elif HDorder==4:
							sf = -flags
						elif HDorder==5:
							sf = rbw[HDperiod]
						elif HDorder==6:
							sf = wbw[HDperiod]
						elif HDorder==7:
							if HDtime==1:
								sf = usecreadavg[HDperiod]
							else:
								sf = usecreadmax[HDperiod]
						elif HDorder==8:
							if HDtime==1:
								sf = usecwriteavg[HDperiod]
							else:
								sf = usecwritemax[HDperiod]
						elif HDorder==9:
							if HDtime==1:
								sf = usecfsyncavg[HDperiod]
							else:
								sf = usecfsyncmax[HDperiod]
						elif HDorder==10:
							sf = rops[HDperiod]
						elif HDorder==11:
							sf = wops[HDperiod]
						elif HDorder==12:
							sf = fsyncops[HDperiod]
						elif HDorder==20:
							if flags&4==0:
								sf = used
							else:
								sf = 0
						elif HDorder==21:
							if flags&4==0:
								sf = total
							else:
								sf = 0
						elif HDorder==22:
							if flags&4==0 and total>0:
								sf = (1.0*used)/total
							else:
								sf = 0
						if flags&4 and not cgimode and ttymode:
							shdd.append((sf,hostkey,sortippath,ippath,hostpath,flags,errchunkid,errtime,used,total,chunkscnt,rbw,wbw,usecreadavg,usecwriteavg,usecfsyncavg,usecreadmax,usecwritemax,usecfsyncmax,rops,wops,fsyncops,rbytes,wbytes,mfrstatus))
						else:
							hdd.append((sf,hostkey,sortippath,ippath,hostpath,flags,errchunkid,errtime,used,total,chunkscnt,rbw,wbw,usecreadavg,usecwriteavg,usecfsyncavg,usecreadmax,usecwritemax,usecfsyncmax,rops,wops,fsyncops,rbytes,wbytes,mfrstatus))

		if len(hdd)>0 or len(shdd)>0:
			if cgimode:
				out = []
				out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_mfshdd" cellspacing="0" id="mfshdd">""")
				out.append("""	<tr><th colspan="16">Disks</th></tr>""")
				out.append("""	<tr>""")
				out.append("""		<th rowspan="3" class="acid_tab_enumerate">#</th>""")
				out.append("""		<th colspan="4" rowspan="2">""")
				out.append("""			<span class="hddaddrname_vis0">info (<a href="javascript:acid_tab.switchdisplay('mfshdd','hddaddrname_vis',1)" class="VISIBLELINK">switch IP to name</a>)</span>""")
				out.append("""			<span class="hddaddrname_vis1">info (<a href="javascript:acid_tab.switchdisplay('mfshdd','hddaddrname_vis',0)" class="VISIBLELINK">switch name to IP</a>)</span>""")
				out.append("""		</th>""")
				out.append("""		<th colspan="8">""")
				out.append("""			<span class="hddperiod_vis0">I/O stats last min (switch to <a href="javascript:acid_tab.switchdisplay('mfshdd','hddperiod_vis',1)" class="VISIBLELINK">hour</a>,<a href="javascript:acid_tab.switchdisplay('mfshdd','hddperiod_vis',2)" class="VISIBLELINK">day</a>)</span>""")
				out.append("""			<span class="hddperiod_vis1">I/O stats last hour (switch to <a href="javascript:acid_tab.switchdisplay('mfshdd','hddperiod_vis',0)" class="VISIBLELINK">min</a>,<a href="javascript:acid_tab.switchdisplay('mfshdd','hddperiod_vis',2)" class="VISIBLELINK">day</a>)</span>""")
				out.append("""			<span class="hddperiod_vis2">I/O stats last day (switch to <a href="javascript:acid_tab.switchdisplay('mfshdd','hddperiod_vis',0)" class="VISIBLELINK">min</a>,<a href="javascript:acid_tab.switchdisplay('mfshdd','hddperiod_vis',1)" class="VISIBLELINK">hour</a>)</span>""")
				out.append("""		</th>""")
#				if HDperiod==2:
#					out.append("""		<th colspan="8">I/O stats last day (switch to <a href="%s" class="VISIBLELINK">min</a>,<a href="%s" class="VISIBLELINK">hour</a>)</th>""" % (createlink({"HDperiod":"0"}),createlink({"HDperiod":"1"})))
#				elif HDperiod==1:
#					out.append("""		<th colspan="8">I/O stats last hour (switch to <a href="%s" class="VISIBLELINK">min</a>,<a href="%s" class="VISIBLELINK">day</a>)</th>""" % (createlink({"HDperiod":"0"}),createlink({"HDperiod":"2"})))
#				else:
#					out.append("""		<th colspan="8">I/O stats last min (switch to <a href="%s" class="VISIBLELINK">hour</a>,<a href="%s" class="VISIBLELINK">day</a>)</th>""" % (createlink({"HDperiod":"1"}),createlink({"HDperiod":"2"})))
				out.append("""		<th colspan="3" rowspan="2">space</th>""")
				out.append("""	</tr>""")
				out.append("""	<tr>""")
				out.append("""		<th colspan="2"><a style="cursor:default" title="average data transfer speed">transfer</a></th>""")
				out.append("""		<th colspan="3">""")
				out.append("""			<span class="hddtime_vis0"><a style="cursor:default" title="max time of read or write one chunk block (up to 64kB)">max time</a> (<a href="javascript:acid_tab.switchdisplay('mfshdd','hddtime_vis',1)" class="VISIBLELINK">switch to avg</a>)</span>""")
				out.append("""			<span class="hddtime_vis1"><a style="cursor:default" title="average time of read or write chunk block (up to 64kB)">avg time</a> (<a href="javascript:acid_tab.switchdisplay('mfshdd','hddtime_vis',0)" class="VISIBLELINK">switch to max</a>)</span>""")
				out.append("""		</th>""")
#				if HDtime==1:
#					out.append("""		<th colspan="3"><a style="cursor:default" title="average time of read or write chunk block (up to 64kB)">avg time</a> (<a href="%s" class="VISIBLELINK">switch to max</a>)</th>""" % (createlink({"HDtime":"0"})))
#				else:
#					out.append("""		<th colspan="3"><a style="cursor:default" title="max time of read or write one chunk block (up to 64kB)">max time</a> (<a href="%s" class="VISIBLELINK">switch to avg</a>)</th>""" % (createlink({"HDtime":"1"})))
				out.append("""		<th colspan="3"><a style="cursor:default" title="number of chunk block operations / chunk fsyncs"># of ops</a></th>""")
				out.append("""	</tr>""")
				out.append("""	<tr>""")
				out.append("""		<th class="acid_tab_level_1"><span class="hddaddrname_vis0">IP</span><span class="hddaddrname_vis1">name</span> path</th>""")
				out.append("""		<th>chunks</th>""")
				out.append("""		<th>last error</th>""")
				out.append("""		<th>status</th>""")
				out.append("""		<th class="acid_tab_level_1">read</th>""")
				out.append("""		<th class="acid_tab_level_1">write</th>""")
				out.append("""		<th class="acid_tab_level_2">read</th>""")
				out.append("""		<th class="acid_tab_level_2">write</th>""")
				out.append("""		<th class="acid_tab_level_2">fsync</th>""")
				out.append("""		<th class="acid_tab_level_1">read</th>""")
				out.append("""		<th class="acid_tab_level_1">write</th>""")
				out.append("""		<th class="acid_tab_level_1">fsync</th>""")
				out.append("""		<th>used</th>""")
				out.append("""		<th>total</th>""")
				out.append("""		<th class="SMPROGBAR">% used</th>""")
				#out.append("""		<th><a href="%s">chunks</a></th>""" % (createorderlink("HD",2)))
				#out.append("""		<th><a href="%s">last error</a></th>""" % (createorderlink("HD",3)))
				#out.append("""		<th><a href="%s">status</a></th>""" % (createorderlink("HD",4)))
				#out.append("""		<th><a href="%s">read</a></th>""" % (createorderlink("HD",5)))
				#out.append("""		<th><a href="%s">write</a></th>""" % (createorderlink("HD",6)))
				#out.append("""		<th><a href="%s">read</a></th>""" % (createorderlink("HD",7)))
				#out.append("""		<th><a href="%s">write</a></th>""" % (createorderlink("HD",8)))
				#out.append("""		<th><a href="%s">fsync</a></th>""" % (createorderlink("HD",9)))
				#out.append("""		<th><a href="%s">read</a></th>""" % (createorderlink("HD",10)))
				#out.append("""		<th><a href="%s">write</a></th>""" % (createorderlink("HD",11)))
				#out.append("""		<th><a href="%s">fsync</a></th>""" % (createorderlink("HD",12)))
				#out.append("""		<th><a href="%s">used</a></th>""" % (createorderlink("HD",20)))
				#out.append("""		<th><a href="%s">total</a></th>""" % (createorderlink("HD",21)))
				#out.append("""		<th class="SMPROGBAR"><a href="%s">used (%%)</a></th>""" % (createorderlink("HD",22)))
				out.append("""	</tr>""")
			elif ttymode:
				tab = Tabble("Disks",15,"r")
				tab.header(("","",4),("I/O stats last %s" % ("day" if HDperiod==2 else "hour" if HDperiod==1 else "min"),"",8),("","",3))
				tab.header(("info","",4),("---","",8),("space","",3))
				tab.header(("","",4),("transfer","",2),("%s time" % ("avg" if HDtime==1 else "max"),"",3),("# of ops","",3),("","",3))
				tab.header(("---","",15))
				if len(hdd)>0 or len(shdd)==0:
					tab.header("IP path","chunks","last error","status","read","write","read","write","fsync","read","write","fsync","used","total","used %")
					lscanning = 0
				else:
					tab.header("IP path","chunks","last error","status","read","write","read","write","fsync","read","write","fsync",("progress","c",3))
					lscanning = 1
			else:
				tab = Tabble("disks",14)
			hdd.sort()
			shdd.sort()
			if HDrev:
				hdd.reverse()
				shdd.reverse()
			usedsum = {}
			totalsum = {}
			hostavg = {}
			for sf,hostkey,sortippath,ippath,hostpath,flags,errchunkid,errtime,used,total,chunkscnt,rbw,wbw,usecreadavg,usecwriteavg,usecfsyncavg,usecreadmax,usecwritemax,usecfsyncmax,rops,wops,fsyncops,rbytes,wbytes,mfrstatus in hdd+shdd:
				if hostkey not in usedsum:
					usedsum[hostkey]=0
					totalsum[hostkey]=0
					hostavg[hostkey]=0
				if flags&4==0 and total>0:
					usedsum[hostkey]+=used
					totalsum[hostkey]+=total
					if totalsum[hostkey]>0:
						hostavg[hostkey] = (usedsum[hostkey] * 100.0) / totalsum[hostkey]
			for sf,hostkey,sortippath,ippath,hostpath,flags,errchunkid,errtime,used,total,chunkscnt,rbw,wbw,usecreadavg,usecwriteavg,usecfsyncavg,usecreadmax,usecwritemax,usecfsyncmax,rops,wops,fsyncops,rbytes,wbytes,mfrstatus in hdd+shdd:
				statuslist = []
				if (flags&8):
					statuslist.append('invalid')
				if (flags&2) and (flags&4)==0 and (flags&8)==0:
					statuslist.append('damaged')
				if flags&1:
					if mfrstatus==1:
						statuslist.append('marked for removal (not ready)')
					elif mfrstatus==2:
						statuslist.append('marked for removal (ready)')
					else:
						statuslist.append('marked for removal')
				if flags&4:
					statuslist.append('scanning')
				if flags==0:
					statuslist.append('ok')
				status = ", ".join(statuslist)
				if errtime==0 and errchunkid==0:
					lerror = 'no errors'
				else:
					if cgimode:
						errtimetuple = time.localtime(errtime)
						lerror = '<a style="cursor:default" title="%s on chunk: %016X">%s</a>' % (time.strftime("%Y-%m-%d %H:%M:%S",errtimetuple),errchunkid,time.strftime("%Y-%m-%d %H:%M",errtimetuple))
					elif ttymode:
						errtimetuple = time.localtime(errtime)
						lerror = time.strftime("%Y-%m-%d %H:%M",errtimetuple)
					else:
						lerror = errtime
				if cgimode:
					out.append("""	<tr>""")
					out.append("""		<td align="right"></td>""")
					out.append("""		<td align="left"><span class="hddaddrname_vis0"><span class="sortkey">%s </span>%s</span><span class="hddaddrname_vis1">%s</span></td>""" % (htmlentities(sortippath),htmlentities(ippath),htmlentities(hostpath)))
					out.append("""		<td align="right">%u</td><td align="right"><span class="sortkey">%u </span>%s</td><td align="right">%s</td>""" % (chunkscnt,errtime,lerror,status))
					validdata = [1,1,1]
					for i in range(3):
						if rbw[i]==0 and wbw[i]==0 and usecreadmax[i]==0 and usecwritemax[i]==0 and usecfsyncmax[i]==0 and rops[i]==0 and wops[i]==0:
							validdata[i] = 0
					# rbw
					out.append("""		<td align="right">""")
					for i in range(3):
						out.append("""			<span class="hddperiod_vis%u">""" % i)
						if validdata[i]:
							out.append("""				<span class="sortkey">%u </span><a style="cursor:default" title="%s B/s">%s/s</a>""" % (rbw[i],decimal_number(rbw[i]),humanize_number(rbw[i],"&nbsp;")))
						else:
							out.append("""				<span class="sortkey">-1 </span>-""")
						out.append("""			</span>""")
					out.append("""		</td>""")
					# wbw
					out.append("""		<td align="right">""")
					for i in range(3):
						out.append("""			<span class="hddperiod_vis%u">""" % i)
						if validdata[i]:
							out.append("""				<span class="sortkey">%u </span><a style="cursor:default" title="%s B/s">%s/s</a>""" % (wbw[i],decimal_number(wbw[i]),humanize_number(wbw[i],"&nbsp;")))
						else:
							out.append("""				<span class="sortkey">-1 </span>-""")
						out.append("""			</span>""")
					out.append("""		</td>""")
					# readtime
					out.append("""		<td align="right">""")
					for i in range(3):
						out.append("""			<span class="hddperiod_vis%u">""" % i)
						if validdata[i]:
							out.append("""				<span class="hddtime_vis0">%u us</span>""" % usecreadmax[i])
							out.append("""				<span class="hddtime_vis1">%u us</span>""" % usecreadavg[i])
						else:
							out.append("""				<span><span class="sortkey">-1 </span>-</span>""")
						out.append("""			</span>""")
					out.append("""		</td>""")
					# writetime
					out.append("""		<td align="right">""")
					for i in range(3):
						out.append("""			<span class="hddperiod_vis%u">""" % i)
						if validdata[i]:
							out.append("""				<span class="hddtime_vis0">%u us</span>""" % usecwritemax[i])
							out.append("""				<span class="hddtime_vis1">%u us</span>""" % usecwriteavg[i])
						else:
							out.append("""				<span><span class="sortkey">-1 </span>-</span>""")
						out.append("""			</span>""")
					out.append("""		</td>""")
					# fsynctime
					out.append("""		<td align="right">""")
					for i in range(3):
						out.append("""			<span class="hddperiod_vis%u">""" % i)
						if validdata[i]:
							out.append("""				<span class="hddtime_vis0">%u us</span>""" % usecfsyncmax[i])
							out.append("""				<span class="hddtime_vis1">%u us</span>""" % usecfsyncavg[i])
						else:
							out.append("""				<span><span class="sortkey">-1 </span>-</span>""")
						out.append("""			</span>""")
					out.append("""		</td>""")
					# rops
					out.append("""		<td align="right">""")
					for i in range(3):
						out.append("""			<span class="hddperiod_vis%u">""" % i)
						if validdata[i]:
							if rops[i]>0:
								bsize = rbytes[i]/rops[i]
							else:
								bsize = 0
							out.append("""				<a style="cursor:default" title="average block size: %u B">%u</a>""" % (bsize,rops[i]))
						else:
							out.append("""				<span class="sortkey">-1 </span>-""")
						out.append("""			</span>""")
					out.append("""		</td>""")
					# wops
					out.append("""		<td align="right">""")
					for i in range(3):
						out.append("""			<span class="hddperiod_vis%u">""" % i)
						if validdata[i]:
							if wops[i]>0:
								bsize = wbytes[i]/wops[i]
							else:
								bsize = 0
							out.append("""				<a style="cursor:default" title="average block size: %u B">%u</a>""" % (bsize,wops[i]))
						else:
							out.append("""				<span class="sortkey">-1 </span>-""")
						out.append("""			</span>""")
					out.append("""		</td>""")
					# fsyncops
					out.append("""		<td align="right">""")
					for i in range(3):
						out.append("""			<span class="hddperiod_vis%u">""" % i)
						if validdata[i]:
							out.append("""				%u""" % (fsyncops[i]))
						else:
							out.append("""				<span class="sortkey">-1 </span>-""")
						out.append("""			</span>""")
					out.append("""		</td>""")
#					if rbw==0 and wbw==0 and rtime==0 and wtime==0 and rops==0 and wops==0:
#						out.append("""		<td><span class="sortkey">-1 </span>-</td><td><span class="sortkey">-1 </span>-</td><td><span class="sortkey">-1 </span>-</td><td><span class="sortkey">-1 </span>-</td><td><span class="sortkey">-1 </span>-</td><td><span class="sortkey">-1 </span>-</td><td><span class="sortkey">-1 </span>-</td><td><span class="sortkey">-1 </span>-</td>""")
#					else:
#						if rops>0:
#							rbsize = rbytes/rops
#						else:
#							rbsize = 0
#						if wops>0:
#							wbsize = wbytes/wops
#						else:
#							wbsize = 0
#						out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B/s">%s/s</a></td><td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B">%s/s</a></td>""" % (rbw,decimal_number(rbw),humanize_number(rbw,"&nbsp;"),wbw,decimal_number(wbw),humanize_number(wbw,"&nbsp;")))
#						out.append("""		<td align="right">%u us</td><td align="right">%u us</td><td align="right">%u us</td><td align="right"><a style="cursor:default" title="average block size: %u B">%u</a></td><td align="right"><a style="cursor:default" title="average block size: %u B">%u</a></td><td align="right">%u</td>""" % (rtime,wtime,fsynctime,rbsize,rops,wbsize,wops,fsyncops))
					if flags&4:
						out.append("""		<td colspan="3" align="right"><span class="sortkey">0 </span><div class="PROGBOX" style="width:200px;"><div class="PROGCOVER" style="width:%.0f%%;"></div><div class="PROGVALUE">%.0f%% scanned</div></div></td>""" % (100.0-used,used))
					else:
						out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B">%s</a></td><td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B">%s</a></td>""" % (used,decimal_number(used),humanize_number(used,"&nbsp;"),total,decimal_number(total),humanize_number(total,"&nbsp;")))
						if total>0:
							usedpercent = (used*100.0)/total
							avgpercent = hostavg[hostkey]
							if usedpercent<avgpercent:
								diffstr = "&#8722;%.4f" % (avgpercent-usedpercent)
							else:
								diffstr = "+%.4f" % (usedpercent-avgpercent)
							out.append("""		<td align="center"><span class="sortkey">%.10f </span><div class="PROGBOX" style="width:100px;"><div class="PROGCOVER" style="width:%.2f%%;"></div><div class="PROGAVG" style="width:%.2f%%"></div><div class="PROGVALUE"><a style="cursor:default" title="%.4f%% = (avg%s%%)">%.2f</a></div></div></td>""" % (usedpercent,100.0-usedpercent,avgpercent,usedpercent,diffstr,usedpercent))
						else:
							out.append("""		<td align="center"><span class="sortkey">-1 </span><div class="PROGBOX" style="width:100px;"><div class="PROGCOVER" style="width:100%;"></div><div class="PROGVALUE">-</div></div></td>""")
					out.append("""	</tr>""")
				elif ttymode:
					rtime = usecreadmax[HDperiod] if HDtime==0 else usecreadavg[HDperiod]
					wtime = usecwritemax[HDperiod] if HDtime==0 else usecwriteavg[HDperiod]
					fsynctime = usecfsyncmax[HDperiod] if HDtime==0 else usecfsyncavg[HDperiod]
					ldata = [ippath,chunkscnt,lerror,status]
					if rbw[HDperiod]==0 and wbw[HDperiod]==0 and usecreadmax[HDperiod]==0 and usecwritemax[HDperiod]==0 and usecfsyncmax[HDperiod]==0 and rops[HDperiod]==0 and wops[HDperiod]==0:
						ldata.extend(("-","-","-","-","-","-","-","-"))
					else:
						ldata.extend(("%s/s" % humanize_number(rbw[HDperiod]," "),"%s/s" % humanize_number(wbw[HDperiod]," "),"%u us" % rtime,"%u us" % wtime,"%u us" % fsynctime,rops[HDperiod],wops[HDperiod],fsyncops[HDperiod]))
					if flags&4:
						if lscanning==0:
							lscanning=1
							tab.append(("---","",15))
							tab.append("IP path","chunks","last error","status","read","write","read","write","fsync","read","write","fsync",("progress","c",3))
							tab.append(("---","",15))
						ldata.append(("%.0f%%" % used,"r",3))
					else:
						if total>0:
							perc = "%.2f%%" % ((used*100.0)/total)
						else:
							perc = "-"
						ldata.extend((humanize_number(used," "),humanize_number(total," "),perc))
					tab.append(*ldata)
				else:
					rtime = usecreadmax[HDperiod] if HDtime==0 else usecreadavg[HDperiod]
					wtime = usecwritemax[HDperiod] if HDtime==0 else usecwriteavg[HDperiod]
					fsynctime = usecfsyncmax[HDperiod] if HDtime==0 else usecfsyncavg[HDperiod]
					ldata = [ippath,chunkscnt,lerror,status]
					if rbw[HDperiod]==0 and wbw[HDperiod]==0 and usecreadmax[HDperiod]==0 and usecwritemax[HDperiod]==0 and usecfsyncmax[HDperiod]==0 and rops[HDperiod]==0 and wops[HDperiod]==0:
						ldata.extend(("-","-","-","-","-","-","-","-"))
					else:
						ldata.extend((rbw[HDperiod],wbw[HDperiod],rtime,wtime,fsynctime,rops[HDperiod],wops[HDperiod],fsyncops[HDperiod]))
					if flags&4:
						ldata.extend(("progress:",used))
					else:
						ldata.extend((used,total))
					tab.append(*ldata)
			if cgimode:
				out.append("""</table>""")
				print("\n".join(out))
			else:
				print(myunicode(tab))
	except Exception:
		print_exception()

if "EX" in sectionset:
	try:
		if cgimode:
			out = []
			out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_mfsexports" cellspacing="0">""")
			out.append("""	<tr><th colspan="%u">Exports</th></tr>""" % (21 if masterconn.has_feature(FEATURE_EXPORT_DISABLES) else 20 if masterconn.has_feature(FEATURE_EXPORT_UMASK) else 19 if masterconn.version_at_least(1,7,0) else 18 if masterconn.version_at_least(1,6,26) else 14))
			out.append("""	<tr>""")
			out.append("""		<th rowspan="2" class="acid_tab_enumerate">#</th>""")
			out.append("""		<th colspan="2">ip&nbsp;range</th>""")
#			out.append("""		<th rowspan="2"><a href="%s">path</a></th>""" % (createorderlink("EX",3)))
#			out.append("""		<th rowspan="2"><a href="%s">minversion</a></th>""" % (createorderlink("EX",4)))
#			out.append("""		<th rowspan="2"><a href="%s">alldirs</a></th>""" % (createorderlink("EX",5)))
#			out.append("""		<th rowspan="2"><a href="%s">password</a></th>""" % (createorderlink("EX",6)))
#			out.append("""		<th rowspan="2"><a href="%s">ro/rw</a></th>""" % (createorderlink("EX",7)))
#			out.append("""		<th rowspan="2"><a href="%s">restricted&nbsp;ip</a></th>""" % (createorderlink("EX",8)))
#			out.append("""		<th rowspan="2"><a href="%s">ignore&nbsp;gid</a></th>""" % (createorderlink("EX",9)))
			out.append("""		<th rowspan="2">path</th>""")
			out.append("""		<th rowspan="2">minversion</th>""")
			out.append("""		<th rowspan="2">alldirs</th>""")
			out.append("""		<th rowspan="2">password</th>""")
			out.append("""		<th rowspan="2">ro/rw</th>""")
			out.append("""		<th rowspan="2">restricted&nbsp;ip</th>""")
			out.append("""		<th rowspan="2">ignore&nbsp;gid</th>""")
			if masterconn.version_at_least(1,7,0):
#				out.append("""		<th rowspan="2"><a href="%s">can&nbsp;change&nbsp;quota</a></th>""" % (createorderlink("EX",10)))
				out.append("""		<th rowspan="2">admin</th>""")
			out.append("""		<th colspan="2">map&nbsp;root</th>""")
			out.append("""		<th colspan="2">map&nbsp;users</th>""")
			if masterconn.version_at_least(1,6,26):
				out.append("""		<th colspan="2">goal&nbsp;limit</th>""")
				out.append("""		<th colspan="2">trashtime&nbsp;limit</th>""")
			if masterconn.has_feature(FEATURE_EXPORT_UMASK):
				out.append("""		<th rowspan="2">global&nbsp;umask</th>""")
			if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
				out.append("""		<th rowspan="2">disables&nbsp;mask</th>""")
			out.append("""	</tr>""")
			out.append("""	<tr>""")
#			out.append("""		<th><a href="%s">from</a></th>""" % (createorderlink("EX",1)))
#			out.append("""		<th><a href="%s">to</a></th>""" % (createorderlink("EX",2)))
#			out.append("""		<th><a href="%s">uid</a></th>""" % (createorderlink("EX",11)))
#			out.append("""		<th><a href="%s">gid</a></th>""" % (createorderlink("EX",12)))
#			out.append("""		<th><a href="%s">uid</a></th>""" % (createorderlink("EX",13)))
#			out.append("""		<th><a href="%s">gid</a></th>""" % (createorderlink("EX",14)))
			out.append("""		<th>from</th>""")
			out.append("""		<th>to</th>""")
			out.append("""		<th>uid</th>""")
			out.append("""		<th>gid</th>""")
			out.append("""		<th>uid</th>""")
			out.append("""		<th>gid</th>""")
			if masterconn.version_at_least(1,6,26):
#				out.append("""		<th><a href="%s">min</a></th>""" % (createorderlink("EX",15)))
#				out.append("""		<th><a href="%s">max</a></th>""" % (createorderlink("EX",16)))
#				out.append("""		<th><a href="%s">min</a></th>""" % (createorderlink("EX",17)))
#				out.append("""		<th><a href="%s">max</a></th>""" % (createorderlink("EX",18)))
				out.append("""		<th>min</th>""")
				out.append("""		<th>max</th>""")
				out.append("""		<th>min</th>""")
				out.append("""		<th>max</th>""")
			out.append("""	</tr>""")
		elif ttymode:
			tab = Tabble("Exports",(20 if masterconn.has_feature(FEATURE_EXPORT_DISABLES) else 19 if masterconn.has_feature(FEATURE_EXPORT_UMASK) else 18 if masterconn.version_at_least(1,7,0) else 17 if masterconn.version_at_least(1,6,26) else 13))

			dline = ["r","r","l","c","c","c","c","c","c"]
			if masterconn.version_at_least(1,7,0):
				dline.append("c")
			dline.extend(("r","r","r","r"))
			if masterconn.version_at_least(1,6,26):
				dline.extend(("r","r","r","r"))
			if masterconn.has_feature(FEATURE_EXPORT_UMASK):
				dline.append("c")
			if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
				dline.append("c")
			tab.defattr(*dline)

			dline = [("ip range","",2),"","","","","","",""]
			if masterconn.version_at_least(1,7,0):
				dline.append("")
			dline.extend((("map root","",2),("map users","",2)))
			if masterconn.version_at_least(1,6,26):
				dline.extend((("goal limit","",2),("trashtime limit","",2)))
			if masterconn.has_feature(FEATURE_EXPORT_UMASK):
				dline.append("")
			if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
				dline.append("")
			tab.header(*dline)

			dline = [("---","",2),"path","minversion","alldirs","password","ro/rw","restrict ip","ignore gid"]
			if masterconn.version_at_least(1,7,0):
				dline.append("admin")
			if masterconn.version_at_least(1,6,26):
				dline.append(("---","",8))
			else:
				dline.append(("---","",4))
			if masterconn.has_feature(FEATURE_EXPORT_UMASK):
				dline.append("global umask")
			if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
				dline.append("disables mask")
			tab.header(*dline)

			dline = ["from","to","","","","","","",""]
			if masterconn.version_at_least(1,7,0):
				dline.append("")
			dline.extend(("uid","gid","uid","gid"))
			if masterconn.version_at_least(1,6,26):
				dline.extend(("min","max","min","max"))
			if masterconn.has_feature(FEATURE_EXPORT_UMASK):
				dline.append("")
			if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
				dline.append("")
			tab.header(*dline)

		else:
			tab = Tabble("exports",(20 if masterconn.has_feature(FEATURE_EXPORT_DISABLES) else 19 if masterconn.has_feature(FEATURE_EXPORT_UMASK) else 18 if masterconn.version_at_least(1,7,0) else 17 if masterconn.version_at_least(1,6,26) else 13))
		servers = []
		for expe in dataprovider.get_exports():
			sf = expe.ipfrom + expe.ipto
			if EXorder==1:
				sf = expe.sortipfrom
			elif EXorder==2:
				sf = expe.sortipto
			elif EXorder==3:
				sf = expe.path
			elif EXorder==4:
				sf = expe.sortver
			elif EXorder==5:
				if expe.meta:
					sf = None
				else:
					sf = expe.exportflags&1
			elif EXorder==6:
				sf = expe.exportflags&2
			elif EXorder==7:
				sf = expe.sesflags&1
			elif EXorder==8:
				sf = 2-(expe.sesflags&2)
			elif EXorder==9:
				if expe.meta:
					sf = None
				else:
					sf = expe.sesflags&4
			elif EXorder==10:
				if expe.meta:
					sf = None
				else:
					sf = expe.sesflags&8
			elif EXorder==11:
				if expe.meta:
					sf = None
				else:
					sf = expe.rootuid
			elif EXorder==12:
				if expe.meta:
					sf = None
				else:
					sf = expe.rootgid
			elif EXorder==13:
				if expe.meta or (expe.sesflags&16)==0:
					sf = None
				else:
					sf = expe.mapalluid
			elif EXorder==14:
				if expe.meta or (expe.sesflags&16)==0:
					sf = None
				else:
					sf = expe.mapalguid
			elif EXorder==15:
				sf = expe.mingoal
			elif EXorder==16:
				sf = expe.maxgoal
			elif EXorder==17:
				sf = expe.mintrashtime
			elif EXorder==18:
				sf = expe.maxtrashtime
			elif EXorder==19:
				sf = expe.umaskval
			elif EXorder==20:
				sf = expe.disables
			servers.append((sf,expe.sortipfrom,expe.stripfrom,expe.sortipto,expe.stripto,expe.path,expe.meta,expe.sortver,expe.strver,expe.exportflags,expe.sesflags,expe.umaskval,expe.rootuid,expe.rootgid,expe.mapalluid,expe.mapallgid,expe.mingoal,expe.maxgoal,expe.mintrashtime,expe.maxtrashtime,expe.disables))
		servers.sort()
		if EXrev:
			servers.reverse()
		for sf,sortipfrom,ipfrom,sortipto,ipto,path,meta,sortver,strver,exportflags,sesflags,umaskval,rootuid,rootgid,mapalluid,mapallgid,mingoal,maxgoal,mintrashtime,maxtrashtime,disables in servers:
			if cgimode:
				out.append("""	<tr>""")
				out.append("""		<td align="right"></td>""")
				out.append("""		<td align="center"><span class="sortkey">%s </span>%s</td>""" % (sortipfrom,ipfrom))
				out.append("""		<td align="center"><span class="sortkey">%s </span>%s</td>""" % (sortipto,ipto))
				out.append("""		<td align="left">%s</td>""" % (".&nbsp;(META)" if meta else htmlentities(path)))
				out.append("""		<td align="center"><span class="sortkey">%s </span>%s</td>""" % (sortver,strver))
				out.append("""		<td align="center">%s</td>""" % ("-" if meta else "yes" if exportflags&1 else "no"))
				out.append("""		<td align="center">%s</td>""" % ("yes" if exportflags&2 else "no"))
				out.append("""		<td align="center">%s</td>""" % ("ro" if sesflags&1 else "rw"))
				out.append("""		<td align="center">%s</td>""" % ("no" if sesflags&2 else "yes"))
				out.append("""		<td align="center">%s</td>""" % ("-" if meta else "yes" if sesflags&4 else "no"))
				if masterconn.version_at_least(1,7,0):
					out.append("""		<td align="center">%s</td>""" % ("-" if meta else "yes" if sesflags&8 else "no"))
				if meta:
					out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
				else:
					out.append("""		<td align="right">%u</td>""" % rootuid)
					out.append("""		<td align="right">%u</td>""" % rootgid)
				if meta or (sesflags&16)==0:
					out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
				else:
					out.append("""		<td align="right">%u</td>""" % mapalluid)
					out.append("""		<td align="right">%u</td>""" % mapallgid)
				if masterconn.version_at_least(1,6,26):
					if mingoal!=None and maxgoal!=None:
						out.append("""		<td align="right">%u</td>""" % mingoal)
						out.append("""		<td align="right">%u</td>""" % maxgoal)
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if mintrashtime!=None and maxtrashtime!=None:
						out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s">%s</a></td>""" % (mintrashtime,timeduration_to_fullstr(mintrashtime),timeduration_to_shortstr(mintrashtime)))
						out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s">%s</a></td>""" % (maxtrashtime,timeduration_to_fullstr(maxtrashtime),timeduration_to_shortstr(maxtrashtime)))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
				if masterconn.has_feature(FEATURE_EXPORT_UMASK):
					if umaskval==None:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					else:
						out.append("""		<td align="center">%03o</td>""" % umaskval)
				if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
					out.append("""		<td align="center"><span class="sortkey">%u </span><a style="cursor:default" title="%s">%08X</a></td>""" % (disables,disablesmask_to_string(disables),disables))
				out.append("""	</tr>""")
			elif ttymode:
				dline = [ipfrom,ipto,". (META)" if meta else path,strver,"-" if meta else "yes" if exportflags&1 else "no","yes" if exportflags&2 else "no","ro" if sesflags&1 else "rw","no" if sesflags&2 else "yes","-" if meta else "yes" if sesflags&4 else "no"]
				if masterconn.version_at_least(1,7,0):
					dline.append("-" if meta else "yes" if sesflags&8 else "no")
				if meta:
					dline.extend(("-","-"))
				else:
					dline.extend((rootuid,rootgid))
				if meta or (sesflags&16)==0:
					dline.extend(("-","-"))
				else:
					dline.extend((mapalluid,mapallgid))
				if masterconn.version_at_least(1,6,26):
					if mingoal!=None and maxgoal!=None:
						dline.extend((mingoal,maxgoal))
					else:
						dline.extend(("-","-"))
					if mintrashtime!=None and maxtrashtime!=None:
						dline.extend((timeduration_to_shortstr(mintrashtime),timeduration_to_shortstr(maxtrashtime)))
					else:
						dline.extend(("-","-"))
				if masterconn.has_feature(FEATURE_EXPORT_UMASK):
					if umaskval==None:
						dline.append("-")
					else:
						dline.append("%03o" % umaskval)
				if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
					dline.append("%08X (%s)" % (disables,disablesmask_to_string(disables)))
				tab.append(*dline)
			else:
				dline = [ipfrom,ipto,". (META)" if meta else path,strver,"-" if meta else "yes" if exportflags&1 else "no","yes" if exportflags&2 else "no","ro" if sesflags&1 else "rw","no" if sesflags&2 else "yes","-" if meta else "yes" if sesflags&4 else "no"]
				if masterconn.version_at_least(1,7,0):
					dline.append("-" if meta else "yes" if sesflags&8 else "no")
				if meta:
					dline.extend(("-","-"))
				else:
					dline.extend((rootuid,rootgid))
				if meta or (sesflags&16)==0:
					dline.extend(("-","-"))
				else:
					dline.extend((mapalluid,mapallgid))
				if masterconn.version_at_least(1,6,26):
					if mingoal!=None and maxgoal!=None:
						dline.extend((mingoal,maxgoal))
					else:
						dline.extend(("-","-"))
					if mintrashtime!=None and maxtrashtime!=None:
						dline.extend((mintrashtime,maxtrashtime))
					else:
						dline.extend(("-","-"))
				if masterconn.has_feature(FEATURE_EXPORT_UMASK):
					if umaskval==None:
						dline.append("-")
					else:
						dline.append("%03o" % umaskval)
				if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
					dline.append("%08X" % disables)
				tab.append(*dline)
		if cgimode:
			out.append("""</table>""")
			print("\n".join(out))
		else:
			print(myunicode(tab))
	except Exception:
		print_exception()

if "MS" in sectionset and leaderfound:
	try:
		if cgimode:
			out = []
			out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_mfsmounts" cellspacing="0">""")
			out.append("""	<tr><th colspan="%u">Active mounts (parameters)</th></tr>""" % (23 if masterconn.has_feature(FEATURE_EXPORT_DISABLES) else 22 if masterconn.has_feature(FEATURE_EXPORT_UMASK) else 21 if masterconn.version_at_least(1,7,8) else 19 if masterconn.version_at_least(1,7,0) else 18 if masterconn.version_at_least(1,6,26) else 14))
			out.append("""	<tr>""")
			out.append("""		<th rowspan="2" class="acid_tab_enumerate">#</th>""")
#			out.append("""		<th rowspan="2"><a href="%s">session&nbsp;id</a></th>""" % (createorderlink("MS",1)))
#			out.append("""		<th rowspan="2"><a href="%s">host</a></th>""" % (createorderlink("MS",2)))
#			out.append("""		<th rowspan="2"><a href="%s">ip</a></th>""" % (createorderlink("MS",3)))
#			out.append("""		<th rowspan="2"><a href="%s">mount&nbsp;point</a></th>""" % (createorderlink("MS",4)))
#			out.append("""		<th rowspan="2"><a href="%s">version</a></th>""" % (createorderlink("MS",5)))
#			out.append("""		<th rowspan="2"><a href="%s">root&nbsp;dir</a></th>""" % (createorderlink("MS",6)))
#			out.append("""		<th rowspan="2"><a href="%s">ro/rw</a></th>""" % (createorderlink("MS",7)))
#			out.append("""		<th rowspan="2"><a href="%s">restricted&nbsp;ip</a></th>""" % (createorderlink("MS",8)))
#			out.append("""		<th rowspan="2"><a href="%s">ignore&nbsp;gid</a></th>""" % (createorderlink("MS",9)))
			out.append("""		<th rowspan="2">session&nbsp;id</th>""")
			out.append("""		<th rowspan="2">host</th>""")
			out.append("""		<th rowspan="2">ip</th>""")
			out.append("""		<th rowspan="2">mount&nbsp;point</th>""")
			if masterconn.version_at_least(1,7,8):
				out.append("""		<th rowspan="2">open files</th>""")
				out.append("""		<th rowspan="2"># of connections</th>""")
			out.append("""		<th rowspan="2">version</th>""")
			out.append("""		<th rowspan="2">root&nbsp;dir</th>""")
			out.append("""		<th rowspan="2">ro/rw</th>""")
			out.append("""		<th rowspan="2">restricted&nbsp;ip</th>""")
			out.append("""		<th rowspan="2">ignore&nbsp;gid</th>""")
			if masterconn.version_at_least(1,7,0):
#				out.append("""		<th rowspan="2"><a href="%s">can&nbsp;change&nbsp;quota</a></th>""" % (createorderlink("MS",10)))
				out.append("""		<th rowspan="2">admin</th>""")
			out.append("""		<th colspan="2">map&nbsp;root</th>""")
			out.append("""		<th colspan="2">map&nbsp;users</th>""")
			if masterconn.version_at_least(1,6,26):
				out.append("""		<th colspan="2">goal&nbsp;limits</th>""")
				out.append("""		<th colspan="2">trashtime&nbsp;limits</th>""")
			if masterconn.has_feature(FEATURE_EXPORT_UMASK):
				out.append("""		<th rowspan="2">global umask</th>""")
			if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
				out.append("""		<th rowspan="2">disables mask</th>""")
			out.append("""	</tr>""")
			out.append("""	<tr>""")
#			out.append("""		<th><a href="%s">uid</a></th>""" % (createorderlink("MS",11)))
#			out.append("""		<th><a href="%s">gid</a></th>""" % (createorderlink("MS",12)))
#			out.append("""		<th><a href="%s">uid</a></th>""" % (createorderlink("MS",13)))
#			out.append("""		<th><a href="%s">gid</a></th>""" % (createorderlink("MS",14)))
			out.append("""		<th>uid</th>""")
			out.append("""		<th>gid</th>""")
			out.append("""		<th>uid</th>""")
			out.append("""		<th>gid</th>""")
			if masterconn.version_at_least(1,6,26):
#				out.append("""		<th><a href="%s">min</a></th>""" % (createorderlink("MS",15)))
#				out.append("""		<th><a href="%s">max</a></th>""" % (createorderlink("MS",16)))
#				out.append("""		<th><a href="%s">min</a></th>""" % (createorderlink("MS",17)))
#				out.append("""		<th><a href="%s">max</a></th>""" % (createorderlink("MS",18)))
				out.append("""		<th>min</th>""")
				out.append("""		<th>max</th>""")
				out.append("""		<th>min</th>""")
				out.append("""		<th>max</th>""")
			out.append("""	</tr>""")
		elif ttymode:
			tab = Tabble("Active mounts (parameters)",(21 if masterconn.has_feature(FEATURE_EXPORT_DISABLES) else 20 if masterconn.has_feature(FEATURE_EXPORT_UMASK) else 19 if masterconn.version_at_least(1,7,8) else 17 if masterconn.version_at_least(1,7,0) else 16 if masterconn.version_at_least(1,6,26) else 12))

			dline = ["r","r","l"]
			if masterconn.version_at_least(1,7,8):
				dline.extend(("r","r"))
			dline.extend(("r","l","c","c","c"))
			if masterconn.version_at_least(1,7,0):
				dline.append("c")
			dline.extend(("r","r","r","r"))
			if masterconn.version_at_least(1,6,26):
				dline.extend(("r","r","r","r"))
			if masterconn.has_feature(FEATURE_EXPORT_UMASK):
				dline.append("c")
			if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
				dline.append("c")
			tab.defattr(*dline)

			dline = ["","","","","","","",""]
			if masterconn.version_at_least(1,7,0):
				if masterconn.version_at_least(1,7,8):
					dline.extend(("",""))
				dline.append("")
			dline.extend((("map root","",2),("map users","",2)))
			if masterconn.version_at_least(1,6,26):
				dline.extend((("goal limit","",2),("trashtime limit","",2)))
			if masterconn.has_feature(FEATURE_EXPORT_UMASK):
				dline.append("")
			if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
				dline.append("")
			tab.header(*dline)

			dline = ["session id","ip/host","mount point"]
			if masterconn.version_at_least(1,7,8):
				dline.extend(("open files","# of connections"))
			dline.extend(("version","root dir","ro/rw","restrict ip","ignore gid"))
			if masterconn.version_at_least(1,7,0):
				dline.append("admin")
			if masterconn.version_at_least(1,6,26):
				dline.append(("---","",8))
			else:
				dline.append(("---","",4))
			if masterconn.has_feature(FEATURE_EXPORT_UMASK):
				dline.append("global umask")
			if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
				dline.append("disables mask")
			tab.header(*dline)

			dline = ["","","","","","","",""]
			if masterconn.version_at_least(1,7,0):
				if masterconn.version_at_least(1,7,8):
					dline.extend(("",""))
				dline.append("")
			dline.extend(("uid","gid","uid","gid"))
			if masterconn.version_at_least(1,6,26):
				dline.extend(("min","max","min","max"))
			if masterconn.has_feature(FEATURE_EXPORT_UMASK):
				dline.append("")
			if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
				dline.append("")
			tab.header(*dline)
		else:
			tab = Tabble("active mounts, parameters",(21 if masterconn.has_feature(FEATURE_EXPORT_DISABLES) else 20 if masterconn.has_feature(FEATURE_EXPORT_UMASK) else 19 if masterconn.version_at_least(1,7,8) else 17 if masterconn.version_at_least(1,7,0) else 16 if masterconn.version_at_least(1,6,26) else 12))

		servers = []
		dservers = []
		for ses in dataprovider.get_sessions():
			sf = ses.sortip
			if MSorder==1:
				sf = ses.sessionid
			elif MSorder==2:
				sf = ses.host
			elif MSorder==3:
				sf = ses.sortip
			elif MSorder==4:
				sf = ses.info
			elif MSorder==5:
				sf = ses.openfiles
			elif MSorder==6:
				if ses.nsocks>0:
					sf = ses.nsocks
				else:
					sf = ses.expire
			elif MSorder==7:
				sf = ses.sortver
			elif MSorder==8:
				sf = ses.path
			elif MSorder==9:
				sf = ses.sesflags&1
			elif MSorder==10:
				sf = 2-(ses.sesflags&2)
			elif MSorder==11:
				if ses.meta:
					sf = None
				else:
					sf = ses.sesflags&4
			elif MSorder==12:
				if ses.meta:
					sf = None
				else:
					sf = ses.sesflags&8
			elif MSorder==13:
				if ses.meta:
					sf = None
				else:
					sf = ses.rootuid
			elif MSorder==14:
				if ses.meta:
					sf = None
				else:
					sf = ses.rootgid
			elif MSorder==15:
				if ses.meta or (ses.sesflags&16)==0:
					sf = None
				else:
					sf = ses.mapalluid
			elif MSorder==16:
				if ses.meta or (ses.sesflags&16)==0:
					sf = None
				else:
					sf = ses.mapallgid
			elif MSorder==17:
				sf = ses.mingoal
			elif MSorder==18:
				sf = ses.maxgoal
			elif MSorder==19:
				sf = ses.mintrashtime
			elif MSorder==20:
				sf = ses.maxtrashtime
			elif MSorder==21:
				sf = ses.umaskval
			elif MSorder==22:
				sf = ses.disables
			if ses.nsocks>0:
				servers.append((sf,ses.sessionid,ses.host,ses.sortip,ses.strip,ses.info,ses.openfiles,ses.nsocks,ses.sortver,ses.strver,ses.meta,ses.path,ses.sesflags,ses.umaskval,ses.rootuid,ses.rootgid,ses.mapalluid,ses.mapallgid,ses.mingoal,ses.maxgoal,ses.mintrashtime,ses.maxtrashtime,ses.disables))
			else:
				dservers.append((sf,ses.sessionid,ses.host,ses.sortip,ses.strip,ses.info,ses.openfiles,ses.expire))
		servers.sort()
		dservers.sort()
		if MSrev:
			servers.reverse()
			dservers.reverse()
		for sf,sessionid,host,sortipnum,ipnum,info,openfiles,nsocks,sortver,strver,meta,path,sesflags,umaskval,rootuid,rootgid,mapalluid,mapallgid,mingoal,maxgoal,mintrashtime,maxtrashtime,disables in servers:
			if cgimode:
				if masterconn.is_pro() and not strver.endswith(" PRO"):
					verclass = "BADVERSION"
				elif masterconn.sort_ver() > sortver:
					verclass = "LOWERVERSION"
				elif masterconn.sort_ver() < sortver:
					verclass = "HIGHERVERSION"
				else:
					verclass = "OKVERSION"
				out.append("""	<tr>""")
				out.append("""		<td align="right"></td>""")
				out.append("""		<td align="center">%u</td>""" % sessionid)
				out.append("""		<td align="left">%s</td>""" % host)
				out.append("""		<td align="center"><span class="sortkey">%s </span>%s</td>""" % (sortipnum,ipnum))
				out.append("""		<td align="left">%s</td>""" % htmlentities(info))
				if masterconn.version_at_least(1,7,8):
					out.append("""		<td align="center">%u</td>""" % openfiles)
					out.append("""		<td align="center">%u</td>""" % nsocks)
				out.append("""		<td align="center"><span class="sortkey">%s </span><span class="%s">%s</span></td>""" % (sortver,verclass,strver))
				out.append("""		<td align="left">%s</td>""" % (".&nbsp;(META)" if meta else htmlentities(path)))
				out.append("""		<td align="center">%s</td>""" % ("ro" if sesflags&1 else "rw"))
				out.append("""		<td align="center">%s</td>""" % ("no" if sesflags&2 else "yes"))
				out.append("""		<td align="center">%s</td>""" % ("-" if meta else "yes" if sesflags&4 else "no"))
				if masterconn.version_at_least(1,7,0):
					out.append("""		<td align="center">%s</td>""" % ("-" if meta else "yes" if sesflags&8 else "no"))
				if meta:
					out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
				else:
					out.append("""		<td align="right">%u</td>""" % rootuid)
					out.append("""		<td align="right">%u</td>""" % rootgid)
				if meta or (sesflags&16)==0:
					out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
				else:
					out.append("""		<td align="right">%u</td>""" % mapalluid)
					out.append("""		<td align="right">%u</td>""" % mapallgid)
				if masterconn.version_at_least(1,6,26):
					if mingoal!=None and maxgoal!=None:
						out.append("""		<td align="right">%u</td>""" % mingoal)
						out.append("""		<td align="right">%u</td>""" % maxgoal)
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if mintrashtime!=None and maxtrashtime!=None:
						out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s">%s</a></td>""" % (mintrashtime,timeduration_to_fullstr(mintrashtime),timeduration_to_shortstr(mintrashtime)))
						out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s">%s</a></td>""" % (maxtrashtime,timeduration_to_fullstr(maxtrashtime),timeduration_to_shortstr(maxtrashtime)))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
				if masterconn.has_feature(FEATURE_EXPORT_UMASK):
					if umaskval==None:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					else:
						out.append("""		<td align="center">%03o</td>""" % umaskval)
				if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
					out.append("""		<td align="center"><span class="sortkey">%u </span><a style="cursor:default" title="%s">%08X</a></td>""" % (disables,disablesmask_to_string(disables),disables))
				out.append("""	</tr>""")
			elif ttymode:
				dline = [sessionid,host,info]
				if masterconn.version_at_least(1,7,8):
					dline.extend((openfiles,nsocks))
				dline.extend((strver,".&nbsp;(META)" if meta else path,"ro" if sesflags&1 else "rw","no" if sesflags&2 else "yes","-" if meta else "yes" if sesflags&4 else "no"))
				if masterconn.version_at_least(1,7,0):
					dline.append("-" if meta else "yes" if sesflags&8 else "no")
				if meta:
					dline.extend(("-","-"))
				else:
					dline.extend((rootuid,rootgid))
				if meta or (sesflags&16)==0:
					dline.extend(("-","-"))
				else:
					dline.extend((mapalluid,mapallgid))
				if masterconn.version_at_least(1,6,26):
					if mingoal!=None and maxgoal!=None:
						dline.extend((mingoal,maxgoal))
					else:
						dline.extend(("-","-"))
					if mintrashtime!=None and maxtrashtime!=None:
						dline.extend((timeduration_to_shortstr(mintrashtime),timeduration_to_shortstr(maxtrashtime)))
					else:
						dline.extend(("-","-"))
				if masterconn.has_feature(FEATURE_EXPORT_UMASK):
					if umaskval==None:
						dline.append("-")
					else:
						dline.append("%03o" % umaskval)
				if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
					dline.append("%08X (%s)" % (disables,disablesmask_to_string(disables)))
				tab.append(*dline)
			else:
				dline = [sessionid,host,info]
				if masterconn.version_at_least(1,7,8):
					dline.extend((openfiles,nsocks))
				dline.extend((strver,".&nbsp;(META)" if meta else path,"ro" if sesflags&1 else "rw","no" if sesflags&2 else "yes","-" if meta else "yes" if sesflags&4 else "no"))
				if masterconn.version_at_least(1,7,0):
					dline.append("-" if meta else "yes" if sesflags&8 else "no")
				if meta:
					dline.extend(("-","-"))
				else:
					dline.extend((rootuid,rootgid))
				if meta or (sesflags&16)==0:
					dline.extend(("-","-"))
				else:
					dline.extend((mapalluid,mapallgid))
				if masterconn.version_at_least(1,6,26):
					if mingoal!=None and maxgoal!=None:
						dline.extend((mingoal,maxgoal))
					else:
						dline.extend(("-","-"))
					if mintrashtime!=None and maxtrashtime!=None:
						dline.extend((mintrashtime,maxtrashtime))
					else:
						dline.extend(("-","-"))
				if masterconn.has_feature(FEATURE_EXPORT_UMASK):
					if umaskval==None:
						dline.append("-")
					else:
						dline.append("%03o" % umaskval)
				if masterconn.has_feature(FEATURE_EXPORT_DISABLES):
					dline.append("%08X" % disables)
				tab.append(*dline)
		if len(dservers)>0 and masterconn.version_at_least(1,7,8):
			if cgimode:
				out.append("""</table>""")
				out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_mfsmounts" cellspacing="0">""")
				out.append("""	<tr><th colspan="8">Inactive mounts (parameters)</th></tr>""")
				out.append("""	<tr>""")
				out.append("""		<th class="acid_tab_enumerate">#</th>""")
				out.append("""		<th>session&nbsp;id</th>""")
				out.append("""		<th>host</th>""")
				out.append("""		<th>ip</th>""")
				out.append("""		<th>mount&nbsp;point</th>""")
				out.append("""		<th>open files</th>""")
				out.append("""		<th>expires</th>""")
				out.append("""		<th>cmd</th>""")
				out.append("""	</tr>""")
			elif ttymode:
				tabcols = (21 if masterconn.has_feature(FEATURE_EXPORT_DISABLES) else 20 if masterconn.has_feature(FEATURE_EXPORT_UMASK) else 19 if masterconn.version_at_least(1,7,8) else 17 if masterconn.version_at_least(1,7,0) else 16 if masterconn.version_at_least(1,6,26) else 12)
				tab.append(("---","",tabcols))
				tab.append(("Inactive mounts (parameters)","1c",tabcols))
				tab.append(("---","",tabcols))
				dline = [("session id","c"),("ip/host","c"),("mount point","c"),("open files","c"),("expires","c"),("command to remove","c",tabcols-5)]
				tab.append(*dline)
				tab.append(("---","",tabcols))
			else:
				print(myunicode(tab))
				print("")
				tab = Tabble("inactive mounts, parameters",5)
		for sf,sessionid,host,sortipnum,ipnum,info,openfiles,expire in dservers:
			if cgimode:
				out.append("""	<tr>""")
				out.append("""		<td align="right"></td>""")
				out.append("""		<td align="center">%u</td>""" % sessionid)
				out.append("""		<td align="left">%s</td>""" % host)
				out.append("""		<td align="center"><span class="sortkey">%s </span>%s</td>""" % (sortipnum,ipnum))
				out.append("""		<td align="left">%s</td>""" % info)
				out.append("""		<td align="center">%u</td>""" % openfiles)
				out.append("""		<td align="center">%u</td>""" % expire)
				out.append("""		<td align="center"><a href="%s">click to remove</a></td>""" % createlink({"MSremove":("%u" % (sessionid))}))
				out.append("""	</tr>""")
			elif ttymode:
				tabcols = (21 if masterconn.has_feature(FEATURE_EXPORT_DISABLES) else 20 if masterconn.has_feature(FEATURE_EXPORT_UMASK) else 19 if masterconn.version_at_least(1,7,8) else 17 if masterconn.version_at_least(1,7,0) else 16 if masterconn.version_at_least(1,6,26) else 12)
				dline = [sessionid,host,info,openfiles,expire,("%s -H %s -P %u -CRS/%u" % (sys.argv[0],masterhost,masterport,sessionid),"l",tabcols-5)]
				tab.append(*dline)
			else:
				dline = [sessionid,host,info,openfiles,expire]
				tab.append(*dline)
		if cgimode:
			out.append("""</table>""")
			print("\n".join(out))
		else:
			print(myunicode(tab))
	except Exception:
		print_exception()

if "MO" in sectionset and leaderfound:
	try:
		if cgimode:
			out = []
			out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_mfsops" cellspacing="0" id="mfsops">""")
#			out.append("""<table class="FR" cellspacing="0">""")
			out.append("""	<tr><th colspan="21">Active mounts (operations)</th></tr>""")
			out.append("""	<tr>""")
			out.append("""		<th rowspan="2" class="acid_tab_enumerate">#</th>""")
#			out.append("""		<th rowspan="2"><a href="%s">host</a></th>""" % (createorderlink("MO",1)))
#			out.append("""		<th rowspan="2"><a href="%s">ip</a></th>""" % (createorderlink("MO",2)))
#			out.append("""		<th rowspan="2"><a href="%s">mount&nbsp;point</a></th>""" % (createorderlink("MO",3)))
			out.append("""		<th rowspan="2">host</th>""")
			out.append("""		<th rowspan="2">ip</th>""")
			out.append("""		<th rowspan="2">mount&nbsp;point</th>""")
			out.append("""		<th colspan="17">""")
			out.append("""			<span class="opshour_vis0">operations last hour (<a href="javascript:acid_tab.switchdisplay('mfsops','opshour_vis',1)" class="VISIBLELINK">switch to current</a>)</span>""")
			out.append("""			<span class="opshour_vis1">operations current hour (<a href="javascript:acid_tab.switchdisplay('mfsops','opshour_vis',0)" class="VISIBLELINK">switch to last</a>)</span>""")
			out.append("""		</th>""")
			out.append("""	</tr>""")
			out.append("""	<tr>""")
#			out.append("""		<th><a href="%s">statfs</a></th>""" % (createorderlink("MO",100)))
#			out.append("""		<th><a href="%s">getattr</a></th>""" % (createorderlink("MO",101)))
#			out.append("""		<th><a href="%s">setattr</a></th>""" % (createorderlink("MO",102)))
#			out.append("""		<th><a href="%s">lookup</a></th>""" % (createorderlink("MO",103)))
#			out.append("""		<th><a href="%s">mkdir</a></th>""" % (createorderlink("MO",104)))
#			out.append("""		<th><a href="%s">rmdir</a></th>""" % (createorderlink("MO",105)))
#			out.append("""		<th><a href="%s">symlink</a></th>""" % (createorderlink("MO",106)))
#			out.append("""		<th><a href="%s">readlink</a></th>""" % (createorderlink("MO",107)))
#			out.append("""		<th><a href="%s">mknod</a></th>""" % (createorderlink("MO",108)))
#			out.append("""		<th><a href="%s">unlink</a></th>""" % (createorderlink("MO",109)))
#			out.append("""		<th><a href="%s">rename</a></th>""" % (createorderlink("MO",110)))
#			out.append("""		<th><a href="%s">link</a></th>""" % (createorderlink("MO",111)))
#			out.append("""		<th><a href="%s">readdir</a></th>""" % (createorderlink("MO",112)))
#			out.append("""		<th><a href="%s">open</a></th>""" % (createorderlink("MO",113)))
#			out.append("""		<th><a href="%s">read</a></th>""" % (createorderlink("MO",114)))
#			out.append("""		<th><a href="%s">write</a></th>""" % (createorderlink("MO",115)))
#			out.append("""		<th><a href="%s">total</a></th>""" % (createorderlink("MO",150)))
			out.append("""		<th class="acid_tab_level_1">statfs</th>""")
			out.append("""		<th class="acid_tab_level_1">getattr</th>""")
			out.append("""		<th class="acid_tab_level_1">setattr</th>""")
			out.append("""		<th class="acid_tab_level_1">lookup</th>""")
			out.append("""		<th class="acid_tab_level_1">mkdir</th>""")
			out.append("""		<th class="acid_tab_level_1">rmdir</th>""")
			out.append("""		<th class="acid_tab_level_1">symlink</th>""")
			out.append("""		<th class="acid_tab_level_1">readlink</th>""")
			out.append("""		<th class="acid_tab_level_1">mknod</th>""")
			out.append("""		<th class="acid_tab_level_1">unlink</th>""")
			out.append("""		<th class="acid_tab_level_1">rename</th>""")
			out.append("""		<th class="acid_tab_level_1">link</th>""")
			out.append("""		<th class="acid_tab_level_1">readdir</th>""")
			out.append("""		<th class="acid_tab_level_1">open</th>""")
			out.append("""		<th class="acid_tab_level_1">read</th>""")
			out.append("""		<th class="acid_tab_level_1">write</th>""")
			out.append("""		<th class="acid_tab_level_1">total</th>""")
			out.append("""	</tr>""")
		elif ttymode:
			tab = Tabble("Active mounts (operations)",19)
			tab.header("","",("operations %s hour" % ("last" if MOdata==0 else "current"),"",17))
			tab.header("host/ip","mount point",("---","",17))
			tab.header("","","statfs","getattr","setattr","lookup","mkdir","rmdir","symlink","readlink","mknod","unlink","rename","link","readdir","open","read","write","total")
			tab.defattr("r","l","r","r","r","r","r","r","r","r","r","r","r","r","r","r","r","r","r")
		else:
			tab = Tabble("active mounts, operations",19)
		servers = []
		for ses in dataprovider.get_sessions():
			sf = ses.sortip
			if MOorder==1:
				sf = ses.host
			elif MOorder==2:
				sf = ses.sortip
			elif MOorder==3:
				sf = ses.info
			elif MOorder>=100 and MOorder<=115:
				sfmul = -1 if cgimode else 1
				if MOdata==0:
					sf = sfmul * ses.stats_l[MOorder-100]
				else:
					sf = sfmul * ses.stats_c[MOorder-100]
			elif MOorder==150:
				sfmul = -1 if cgimode else 1
				if MOdata==0:
					sf = sfmul * sum(ses.stats_l)
				else:
					sf = sfmul * sum(ses.stats_c)
			if ses.path!='.':
				servers.append((sf,ses.host,ses.sortip,ses.strip,ses.info,ses.stats_c,ses.stats_l))
		servers.sort()
		if MOrev:
			servers.reverse()
		for sf,host,sortipnum,ipnum,info,stats_c,stats_l in servers:
			if cgimode:
				out.append("""	<tr>""")
				out.append("""		<td align="right"></td>""")
				out.append("""		<td align="left">%s</td>""" % host)
				out.append("""		<td align="center"><span class="sortkey">%s</span>%s</td>""" % (sortipnum,ipnum))
				out.append("""		<td align="left">%s</td>""" % htmlentities(info))
				for st in range(16):
					out.append("""		<td align="right">""")
					out.append("""			<span class="opshour_vis0"><a style="cursor:default" title="current:%u last:%u">%u</a></span>""" % (stats_c[st],stats_l[st],stats_l[st]))
					out.append("""			<span class="opshour_vis1"><a style="cursor:default" title="current:%u last:%u">%u</a></span>""" % (stats_c[st],stats_l[st],stats_c[st]))
					out.append("""		</td>""")
				out.append("""		<td align="right">""")
				out.append("""			<span class="opshour_vis0"><a style="cursor:default" title="current:%u last:%u">%u</a></span>""" % (sum(stats_c),sum(stats_l),sum(stats_l)))
				out.append("""			<span class="opshour_vis1"><a style="cursor:default" title="current:%u last:%u">%u</a></span>""" % (sum(stats_c),sum(stats_l),sum(stats_c)))
				out.append("""		</td>""")
#					if MOdata==0:
#						for st in xrange(16):
#							out.append("""		<td align="right"><a style="cursor:default" title="current:%u last:%u">%u</a></td>""" % (stats_c[st],stats_l[st],stats_l[st]))
#						out.append("""		<td align="right"><a style="cursor:default" title="current:%u last:%u">%u</a></td>""" % (sum(stats_c),sum(stats_l),sum(stats_l)))
#					else:
#						for st in xrange(16):
#							out.append("""		<td align="right"><a style="cursor:default" title="current:%u last:%u">%u</a></td>""" % (stats_c[st],stats_l[st],stats_c[st]))
#						out.append("""		<td align="right"><a style="cursor:default" title="current:%u last:%u">%u</a></td>""" % (sum(stats_c),sum(stats_l),sum(stats_c)))
				out.append("""	</tr>""")
			else:
				ldata = [host,info]
				if MOdata==0:
					ldata.extend(stats_l)
					ldata.append(sum(stats_l))
				else:
					ldata.extend(stats_c)
					ldata.append(sum(stats_c))
				tab.append(*ldata)
		if cgimode:
			out.append("""</table>""")
			print("\n".join(out))
		else:
			print(myunicode(tab))
	except Exception:
		print_exception()

if "RS" in sectionset and leaderfound:

	if "SC" in sectionsubset:
		try:
			if cgimode:
				out = []
				out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_mfsls" cellspacing="0">""")
				out.append("""	<tr><th colspan="22">Storage Classes</th></tr>""")
				out.append("""	<tr>""")
				out.append("""		<th rowspan="2">id</th>""")
				out.append("""		<th rowspan="2">name</th>""")
				out.append("""		<th rowspan="2">admin only</th>""")
				out.append("""		<th rowspan="2">mode</th>""")
				out.append("""		<th colspan="2"># of inodes</th>""")
				out.append("""		<th colspan="3"># of standard chunks</th>""")
				out.append("""		<th colspan="3"># of archived chunks</th>""")
				out.append("""		<th colspan="3">create</th>""")
				out.append("""		<th colspan="3">keep</th>""")
				out.append("""		<th colspan="4">archive</th>""")
				out.append("""	</tr>""")
				out.append("""	<tr>""")
				out.append("""		<th>files</th>""")
				out.append("""		<th>dirs</th>""")
				out.append("""		<th>under</th>""")
				out.append("""		<th>exact</th>""")
				out.append("""		<th>over</th>""")
				out.append("""		<th>under</th>""")
				out.append("""		<th>exact</th>""")
				out.append("""		<th>over</th>""")
				out.append("""		<th>can be fulfilled</th>""")
				out.append("""		<th>goal</th>""")
				out.append("""		<th>labels</th>""")
				out.append("""		<th>can be fulfilled</th>""")
				out.append("""		<th>goal</th>""")
				out.append("""		<th>labels</th>""")
				out.append("""		<th>can be fulfilled</th>""")
				out.append("""		<th>goal</th>""")
				out.append("""		<th>labels</th>""")
				out.append("""		<th>delay</th>""")
				out.append("""	</tr>""")
			elif ttymode:
				tab = Tabble("Storage Classes",22,"r")
				tab.header("","","","",("# of inodes","",2),("# of standard chunks","",3),("# of archived chunks","",3),("create","",3),("keep","",3),("archive","",4))
				tab.header("id","name","admin only","mode",("---","",18))
				tab.header("","","","","files","dirs","under","exact","over","under","exact","over","can be fulfilled","goal","labels","can be fulfilled","goal","labels","can be fulfilled","goal","labels","delay")
				tab.defattr("r","l","c","c","r","r","r","r","r","r","r","r","c","r","l","c","r","l","c","r","l","r")
			else:
				tab = Tabble("storage classes",22)
			sclasses = []
			data,length = masterconn.command(CLTOMA_SCLASS_INFO,MATOCL_SCLASS_INFO)
			scount = struct.unpack(">H",data[:2])[0]
			pos = 2
			while pos < length:
				if masterconn.version_at_least(3,0,75):
					sclassid,sclassnleng = struct.unpack_from(">BB",data,pos)
					pos += 2
					sclassname = data[pos:pos+sclassnleng]
					sclassname = sclassname.decode('utf-8','replace')
					pos += sclassnleng
					files,dirs,stdchunks_under,archchunks_under,stdchunks_exact,archchunks_exact,stdchunks_over,archchunks_over,admin_only,mode,arch_delay,create_canbefulfilled,create_labelscnt,keep_canbefulfilled,keep_labelscnt,arch_canbefulfilled,arch_labelscnt = struct.unpack_from(">LLQQQQQQBBHBBBBBB",data,pos)
					pos += 18 + 3 * 16
					if arch_delay==0:
						stdchunks_under += archchunks_under
						stdchunks_exact += archchunks_exact
						stdchunks_over += archchunks_over
						archchunks_under = None
						archchunks_exact = None
						archchunks_over = None
				elif masterconn.version_at_least(3,0,9):
					sclassid,files,dirs,stdchunks_under,archchunks_under,stdchunks_exact,archchunks_exact,stdchunks_over,archchunks_over,mode,arch_delay,create_canbefulfilled,create_labelscnt,keep_canbefulfilled,keep_labelscnt,arch_canbefulfilled,arch_labelscnt = struct.unpack_from(">BLLQQQQQQBHBBBBBB",data,pos)
					pos += 18 + 3 * 16
					admin_only = 0
					if sclassid<10:
						sclassname = str(sclassid)
					else:
						sclassname = "sclass_%u" % (sclassid-9)
					if arch_delay==0:
						stdchunks_under += archchunks_under
						stdchunks_exact += archchunks_exact
						stdchunks_over += archchunks_over
						archchunks_under = None
						archchunks_exact = None
						archchunks_over = None
				else:
					sclassid,files,create_canbefulfilled,create_labelscnt = struct.unpack_from(">BLBB",data,pos)
					admin_only = 0
					if sclassid<10:
						sclassname = str(sclassid)
					else:
						sclassname = "sclass_%u" % (sclassid-9)
					dirs = 0
					if create_canbefulfilled:
						create_canbefulfilled = 3
					keep_canbefulfilled = create_canbefulfilled
					arch_canbefulfilled = create_canbefulfilled
					keep_labelscnt = create_labelscnt
					arch_labelscnt = create_labelscnt
					mode = 1
					arch_delay = 0
					stdchunks_under = None
					archchunks_under = None
					stdchunks_exact = None
					archchunks_exact = None
					stdchunks_over = None
					archchunks_over = None
					pos+=7
				create_labellist = []
				for i in xrange(create_labelscnt):
					labelmasks = struct.unpack_from(">"+"L"*MASKORGROUP,data,pos)
					pos+=4*MASKORGROUP
					matchingservers = struct.unpack_from(">H",data,pos)[0]
					pos+=2
					create_labellist.append((labelmasks_to_str(labelmasks),matchingservers))
				if masterconn.version_at_least(3,0,9):
					keep_labellist = []
					for i in xrange(keep_labelscnt):
						labelmasks = struct.unpack_from(">"+"L"*MASKORGROUP,data,pos)
						pos+=4*MASKORGROUP
						matchingservers = struct.unpack_from(">H",data,pos)[0]
						pos+=2
						keep_labellist.append((labelmasks_to_str(labelmasks),matchingservers))
					arch_labellist = []
					for i in xrange(arch_labelscnt):
						labelmasks = struct.unpack_from(">"+"L"*MASKORGROUP,data,pos)
						pos+=4*MASKORGROUP
						matchingservers = struct.unpack_from(">H",data,pos)[0]
						pos+=2
						arch_labellist.append((labelmasks_to_str(labelmasks),matchingservers))
				else:
					keep_labellist = create_labellist
					arch_labellist = create_labellist
				sf = sclassid
				if SCorder==2:
					sf = sclassname
				elif SCorder==3:
					sf = admin_only
				elif SCorder==4:
					sf = files
				elif SCorder==5:
					sf = dirs
				elif SCorder==6:
					sf = stdchunks_under
				elif SCorder==7:
					sf = stdchunks_exact
				elif SCorder==8:
					sf = stdchunks_over
				elif SCorder==9:
					sf = archchunks_under
				elif SCorder==10:
					sf = archchunks_exact
				elif SCorder==11:
					sf = archchunks_over
				elif SCorder==12:
					sf = mode
				elif SCorder==13:
					sf = create_canbefulfilled
				elif SCorder==14:
					sf = create_labelscnt
				elif SCorder==15:
					sf = create_labellist
				elif SCorder==16:
					sf = keep_canbefulfilled
				elif SCorder==17:
					sf = keep_labelscnt
				elif SCorder==18:
					sf = keep_labellist
				elif SCorder==19:
					sf = arch_canbefulfilled
				elif SCorder==20:
					sf = arch_labelscnt
				elif SCorder==21:
					sf = arch_labellist
				elif SCorder==22:
					sf = arch_delay
				sclasses.append((sf,sclassid,sclassname,admin_only,mode,files,dirs,stdchunks_under,stdchunks_exact,stdchunks_over,archchunks_under,archchunks_exact,archchunks_over,create_canbefulfilled,create_labellist,keep_canbefulfilled,keep_labellist,arch_canbefulfilled,arch_labellist,arch_delay))
			sclasses.sort()
			if SCrev:
				sclasses.reverse()
			for sf,sclassid,sclassname,admin_only,mode,files,dirs,stdchunks_under,stdchunks_exact,stdchunks_over,archchunks_under,archchunks_exact,archchunks_over,create_canbefulfilled,create_labellist,keep_canbefulfilled,keep_labellist,arch_canbefulfilled,arch_labellist,arch_delay in sclasses:
				if cgimode:
					allcolor = (0,160,224)
					zerocolor = (0,0,128)
					out.append("""	<tr>""")
					out.append("""		<td align="right">%u</td>""" % sclassid)
					out.append("""		<td align="right">%s</td>""" % htmlentities(sclassname))
					out.append("""		<td align="right">%s</td>""" % ("YES" if admin_only else "NO"))
					out.append("""		<td align="center">%s</td>""" % ("LOOSE" if mode==0 else "STD" if mode==1 else "STRICT"))
					out.append("""		<td align="right">%u</td>""" % files)
					out.append("""		<td align="right">%u</td>""" % dirs)
					if stdchunks_under!=None and stdchunks_exact!=None and stdchunks_over!=None:
						out.append("""		<td align="right"><span class="UNDERGOAL">%s</span></td>""" % (("%u" % stdchunks_under) if stdchunks_under>0 else "&nbsp;"))
						out.append("""		<td align="right"><span class="NORMAL">%u</span></td>""" % stdchunks_exact)
						out.append("""		<td align="right"><span class="OVERGOAL">%s</span></td>""" % (("%u" % stdchunks_over) if stdchunks_over>0 else "&nbsp;"))
					else:
						out.append("""		<td align="center">-</td>""")
						out.append("""		<td align="center">-</td>""")
						out.append("""		<td align="center">-</td>""")
					if archchunks_under!=None and archchunks_exact!=None and archchunks_over!=None:
						out.append("""		<td align="right"><span class="UNDERGOAL">%s</span></td>""" % (("%u" % archchunks_under) if archchunks_under>0 else "&nbsp;"))
						out.append("""		<td align="right"><span class="NORMAL">%u</span></td>""" % archchunks_exact)
						out.append("""		<td align="right"><span class="OVERGOAL">%s</span></td>""" % (("%u" % archchunks_over) if archchunks_over>0 else "&nbsp;"))
					else:
						out.append("""		<td align="center">-</td>""")
						out.append("""		<td align="center">-</td>""")
						out.append("""		<td align="center">-</td>""")
					if create_canbefulfilled==3:
						out.append("""		<td align="center">YES</td>""")
					elif create_canbefulfilled==2:
						out.append("""		<td align="center"><span class="WARNING">OVERLOADED</span></td>""")
					elif create_canbefulfilled==1:
						out.append("""		<td align="center"><span class="WARNING">NO SPACE</span></td>""")
					else:
						out.append("""		<td align="center"><span class="ERROR">NO</span></td>""")
					labelsarr = []
					for labelstr,mscount in create_labellist:
						if scount==0:
							msperc = 0;
						else:
							msperc = (1.0 * mscount) / scount
						perccolor = (int(zerocolor[0]+(allcolor[0]-zerocolor[0])*msperc),int(zerocolor[1]+(allcolor[1]-zerocolor[1])*msperc),int(zerocolor[2]+(allcolor[2]-zerocolor[2])*msperc))
						color = "#%02X%02X%02X" % perccolor
						labelsarr.append("""<span style="color:%s"><a style="cursor:default" title="%u/%u servers">%s</a></span>""" % (color,mscount,scount,labelstr))
					out.append("""		<td align="center">%u</td>""" % (len(labelsarr)))
					out.append("""		<td align="center">%s</td>""" % ("&nbsp;,&nbsp;".join(labelsarr)))
					if keep_canbefulfilled==3:
						out.append("""		<td align="center">YES</td>""")
					elif keep_canbefulfilled==2:
						out.append("""		<td align="center"><span class="WARNING">OVERLOADED</span></td>""")
					elif keep_canbefulfilled==1:
						out.append("""		<td align="center"><span class="WARNING">NO SPACE</span></td>""")
					else:
						out.append("""		<td align="center"><span class="ERROR">NO</span></td>""")
					labelsarr = []
					for labelstr,mscount in keep_labellist:
						if scount==0:
							msperc = 0;
						else:
							msperc = (1.0 * mscount) / scount
						perccolor = (int(zerocolor[0]+(allcolor[0]-zerocolor[0])*msperc),int(zerocolor[1]+(allcolor[1]-zerocolor[1])*msperc),int(zerocolor[2]+(allcolor[2]-zerocolor[2])*msperc))
						color = "#%02X%02X%02X" % perccolor
						labelsarr.append("""<span style="color:%s"><a style="cursor:default" title="%u/%u servers">%s</a></span>""" % (color,mscount,scount,labelstr))
					out.append("""		<td align="center">%u</td>""" % (len(labelsarr)))
					out.append("""		<td align="center">%s</td>""" % ("&nbsp;,&nbsp;".join(labelsarr)))
					if arch_canbefulfilled==3:
						out.append("""		<td align="center">YES</td>""")
					elif arch_canbefulfilled==2:
						out.append("""		<td align="center"><span class="WARNING">OVERLOADED</span></td>""")
					elif arch_canbefulfilled==1:
						out.append("""		<td align="center"><span class="WARNING">NO SPACE</span></td>""")
					else:
						out.append("""		<td align="center"><span class="ERROR">NO</span></td>""")
					labelsarr = []
					for labelstr,mscount in arch_labellist:
						msperc = (1.0 * mscount) / scount
						perccolor = (int(zerocolor[0]+(allcolor[0]-zerocolor[0])*msperc),int(zerocolor[1]+(allcolor[1]-zerocolor[1])*msperc),int(zerocolor[2]+(allcolor[2]-zerocolor[2])*msperc))
						color = "#%02X%02X%02X" % perccolor
						labelsarr.append("""<span style="color:%s"><a style="cursor:default" title="%u/%u servers">%s</a></span>""" % (color,mscount,scount,labelstr))
					out.append("""		<td align="center">%u</td>""" % (len(labelsarr)))
					out.append("""		<td align="center">%s</td>""" % ("&nbsp;,&nbsp;".join(labelsarr)))
					if arch_delay>0:
						out.append("""		<td align="center">%ud</td>""" % arch_delay)
					else:
						out.append("""		<td align="center">-</td>""")
					out.append("""	</tr>""")
				else:
					data = [sclassid,sclassname,("YES" if admin_only else "NO"),"LOOSE" if mode==0 else "STD" if mode==1 else "STRICT",files,dirs]
					if stdchunks_under!=None and stdchunks_exact!=None and stdchunks_over!=None:
						data.append((stdchunks_under,'3') if stdchunks_under>0 else "-")
						data.append((stdchunks_exact,'4'))
						data.append((stdchunks_over,'5') if stdchunks_over>0 else "-")
					else:
						data.extend(["-","-","-"])
					if archchunks_under!=None and archchunks_exact!=None and archchunks_over!=None:
						data.append((archchunks_under,'3') if archchunks_under>0 else "-")
						data.append((archchunks_exact,'4'))
						data.append((archchunks_over,'5') if archchunks_over>0 else "-")
					else:
						data.extend(["-","-","-"])
					if create_canbefulfilled==3:
						data.append(("YES",'4'))
					elif create_canbefulfilled==2:
						data.append(("OVERLOADED",'3'))
					elif create_canbefulfilled==1:
						data.append(("NO SPACE",'2'))
					else:
						data.append(("NO",'1'))
					data.append("%u" % len(create_labellist))
					data.append("%s" % (" , ".join([x for x,y in create_labellist])))
					if keep_canbefulfilled==3:
						data.append(("YES",'4'))
					elif keep_canbefulfilled==2:
						data.append(("OVERLOADED",'3'))
					elif keep_canbefulfilled==1:
						data.append(("NO SPACE",'2'))
					else:
						data.append(("NO",'1'))
					data.append("%u" % len(keep_labellist))
					data.append("%s" % (" , ".join([x for x,y in keep_labellist])))
					if arch_canbefulfilled==3:
						data.append(("YES",'4'))
					elif arch_canbefulfilled==2:
						data.append(("OVERLOADED",'3'))
					elif arch_canbefulfilled==1:
						data.append(("NO SPACE",'2'))
					else:
						data.append(("NO",'1'))
					data.append("%u" % len(arch_labellist))
					data.append("%s" % (" , ".join([x for x,y in arch_labellist])))
					if arch_delay>0:
						data.append("%ud" % arch_delay)
					else:
						data.append("-")
					tab.append(*data)
			if cgimode:
				out.append("""</table>""")
				print("\n".join(out))
			else:
				print(myunicode(tab))
		except Exception:
			print_exception()

	inodes = set()
	if "OF" in sectionsubset:
		try:
			sessionsdata = {}
			for ses in dataprovider.get_sessions():
				sessionsdata[ses.sessionid]=(ses.host,ses.sortip,ses.strip,ses.info,ses.openfiles)
			if cgimode:
				out = []
				out.append("""<form action="#"><table class="FR" cellspacing="0"><tr><th>Show open files for: <select name="server" size="1" onchange="document.location.href='%s&OFsessionid='+this.options[this.selectedIndex].value">""" % createjslink({"OFsessionid":""}))
				if OFsessionid==0:
					out.append("""<option value="0" selected="selected"> select session</option>""")
				sessions = list(sessionsdata.keys())
				sessions.sort()
				for sessionid in sessions:
					host,sortipnum,ipnum,info,openfiles = sessionsdata[sessionid]
					if OFsessionid==sessionid:
						out.append("""<option value="%s" selected="selected">%s: %s:%s (open files: ~%u)</option>""" % (sessionid,sessionid,host,info,openfiles))
					else:
						out.append("""<option value="%s">%s: %s:%s (open files: ~%u)</option>""" % (sessionid,sessionid,host,info,openfiles))
				out.append("""</select></th></tr></table></form>""")
				if OFsessionid!=0:
					out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_mfsopenfiles" cellspacing="0">""")
					out.append("""	<tr><th colspan="7">Open files by client with session id: %u</th></tr>""" % OFsessionid)
					out.append("""	<tr>""")
					out.append("""		<th rowspan="2" class="acid_tab_enumerate">#</th>""")
					out.append("""		<th rowspan="2">session&nbsp;id</th>""")
					out.append("""		<th rowspan="2">host</th>""")
					out.append("""		<th rowspan="2">ip</th>""")
					out.append("""		<th rowspan="2">mount&nbsp;point</th>""")
					out.append("""		<th rowspan="2">inode</th>""")
					out.append("""		<th rowspan="2">paths</th>""")
					out.append("""	</tr>""")
			elif ttymode:
				tab = Tabble("Open Files",5)
				tab.header("session id","ip/host","mount point","inode","path")
				tab.defattr("r","r","l","r","l")
			else:
				tab = Tabble("open file",5)
			if cgimode and OFsessionid==0:
				ofdata = []
			else:
				data,length = masterconn.command(CLTOMA_LIST_OPEN_FILES,MATOCL_LIST_OPEN_FILES,struct.pack(">L",OFsessionid))
				openfiles = []
				if OFsessionid==0:
					n = length//8
					for x in xrange(n):
						sessionid,inode = struct.unpack(">LL",data[x*8:x*8+8])
						openfiles.append((sessionid,inode))
						inodes.add(inode)
				else:
					n = length//4
					for x in xrange(n):
						inode = struct.unpack(">L",data[x*4:x*4+4])[0]
						openfiles.append((OFsessionid,inode))
						inodes.add(inode)
				inodepaths = resolve_inodes_paths(masterconn,inodes)
				ofdata = []
				for sessionid,inode in openfiles:
					if sessionid in sessionsdata:
						host,sortipnum,ipnum,info,openfiles = sessionsdata[sessionid]
					else:
						host = 'unknown'
						sortipnum = ''
						ipnum = ''
						info = 'unknown'
					if inode in inodepaths:
						paths = inodepaths[inode]
					else:
						paths = []
					sf = sortipnum
					if OForder==1:
						sf = sessionid
					elif OForder==2:
						sf = hostip
					elif OForder==3:
						sf = sortipnum
					elif OForder==4:
						sf = info
					elif OForder==5:
						sf = inode
					elif OForder==6:
						sf = paths
					ofdata.append((sf,sessionid,host,sortipnum,ipnum,info,inode,paths))
				ofdata.sort()
				if OFrev:
					ofdata.reverse()
			for sf,sessionid,host,sortipnum,ipnum,info,inode,paths in ofdata:
				if cgimode:
					for path in paths:
						out.append("""	<tr>""")
						out.append("""		<td align="right"></td>""")
						out.append("""		<td align="center">%u</td>""" % sessionid)
						out.append("""		<td align="left">%s</td>""" % host)
						out.append("""		<td align="center"><span class="sortkey">%s </span>%s</td>""" % (sortipnum,ipnum))
						out.append("""		<td align="left">%s</td>""" % htmlentities(info))
						out.append("""		<td align="center">%u</td>""" % inode)
						out.append("""		<td align="left">%s</td>""" % htmlentities(path))
						out.append("""	</tr>""")
				else:
					if len(paths)==0:
						dline = [sessionid,host,info,inode,"unknown"]
						tab.append(*dline)
					else:
						for path in paths:
							dline = [sessionid,host,info,inode,path]
							tab.append(*dline)
			if cgimode:
				if OFsessionid!=0:
					out.append("""</table>""")
				print("\n".join(out))
			else:
				#print(openfiles)
				print(myunicode(tab))
		except Exception:
			print_exception()

	if "AL" in sectionsubset:
		try:
			sessionsdata = {}
			for ses in dataprovider.get_sessions():
				sessionsdata[ses.sessionid]=(ses.host,ses.sortip,ses.strip,ses.info,ses.openfiles)
			if cgimode:
				if ALinode not in inodes:
					ALinode = 0
				out = []
				if len(inodes)>0:
					out.append("""<form action="#"><table class="FR" cellspacing="0"><tr><th>Show acquired locks for: <select name="server" size="1" onchange="document.location.href='%s&ALinode='+this.options[this.selectedIndex].value">""" % createjslink({"ALinode":""}))
					if ALinode==0:
						out.append("""<option value="0" selected="selected"> select inode</option>""")
					inodeslist = list(inodes)
					inodeslist.sort()
					for inode in inodeslist:
						if ALinode==inode:
							out.append("""<option value="%u" selected="selected">%u</option>""" % (inode,inode))
						else:
							out.append("""<option value="%u">%u</option>""" % (inode,inode))
					out.append("""</select></th></tr></table></form>""")
					if ALinode!=0:
						out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_acquiredlocks" cellspacing="0">""")
						out.append("""	<tr><th colspan="11">Acquired locks for inode: %u</th></tr>""" % ALinode)
						out.append("""	<tr>""")
						out.append("""		<th rowspan="2" class="acid_tab_enumerate">#</th>""")
						out.append("""		<th rowspan="2">session&nbsp;id</th>""")
						out.append("""		<th rowspan="2">host</th>""")
						out.append("""		<th rowspan="2">ip</th>""")
						out.append("""		<th rowspan="2">mount&nbsp;point</th>""")
						out.append("""		<th rowspan="2">lock type</th>""")
						out.append("""		<th rowspan="2">owner id</th>""")
						out.append("""		<th rowspan="2">pid</th>""")
						out.append("""		<th rowspan="2">start</th>""")
						out.append("""		<th rowspan="2">end</th>""")
						out.append("""		<th rowspan="2">r/w</th>""")
						out.append("""	</tr>""")
			elif ttymode:
				tab = Tabble("Acquired Locks",10,"r")
				tab.header("inode","session id","ip/host","mount point","lock type","owner","pid","start","end","r/w")
			else:
				tab = Tabble("acquired locks",10)
			if cgimode and ALinode==0:
				aldata = []
			else:
				data,length = masterconn.command(CLTOMA_LIST_ACQUIRED_LOCKS,MATOCL_LIST_ACQUIRED_LOCKS,struct.pack(">L",ALinode))
				locks = []
				if ALinode==0:
					n = length//37
					for x in xrange(n):
						inode,sessionid,owner,pid,start,end,ctype = struct.unpack(">LLQLQQB",data[x*37:x*37+37])
						locks.append((inode,sessionid,owner,pid,start,end,ctype))
				else:
					n = length//33
					for x in xrange(n):
						sessionid,owner,pid,start,end,ctype = struct.unpack(">LQLQQB",data[x*33:x*33+33])
						locks.append((ALinode,sessionid,owner,pid,start,end,ctype))
				aldata = []
				for inode,sessionid,owner,pid,start,end,ctype in locks:
					if sessionid in sessionsdata:
						host,sortipnum,ipnum,info,openfiles = sessionsdata[sessionid]
					else:
						host = 'unknown'
						sortipnum = ''
						ipnum = ''
						info = 'unknown'
					if pid==0 and start==0 and end==0:
						locktype = "FLOCK"
					else:
						locktype = "POSIX"
					sf = inode
					if ALorder==1:
						sf = inode
					elif ALorder==2:
						sf = sessionid
					elif ALorder==3:
						sf = hostip
					elif ALorder==4:
						sf = sortipnum
					elif ALorder==5:
						sf = info
					elif ALorder==6:
						sf = locktype
					elif ALorder==7:
						sf = owner
					elif ALorder==8:
						sf = pid
					elif ALorder==9:
						sf = start
					elif ALorder==10:
						sf = end
					elif ALorder==11:
						sf = ctype
					aldata.append((sf,inode,sessionid,host,sortipnum,ipnum,info,locktype,owner,pid,start,end,ctype))
				aldata.sort()
				if ALrev:
					aldata.reverse()
			for sf,inode,sessionid,host,sortipnum,ipnum,info,locktype,owner,pid,start,end,ctype in aldata:
				if cgimode:
					out.append("""	<tr>""")
					out.append("""		<td align="right"></td>""")
					out.append("""		<td align="center">%u</td>""" % sessionid)
					out.append("""		<td align="left">%s</td>""" % host)
					out.append("""		<td align="center"><span class="sortkey">%s </span>%s</td>""" % (sortipnum,ipnum))
					out.append("""		<td align="left">%s</td>""" % htmlentities(info))
					out.append("""		<td align="center">%s</td>""" % locktype)
					out.append("""		<td align="right">%u</td>""" % owner)
					if pid==0 and start==0 and end==0:
						out.append("""		<td align="right">-1</td>""")
						out.append("""		<td align="right">0</td>""")
						out.append("""		<td align="right">EOF</td>""")
					else:
						out.append("""		<td align="right">%u</td>""" % pid)
						out.append("""		<td align="right">%u</td>""" % start)
						if end > 0x7FFFFFFFFFFFFFFF:
							out.append("""		<td align="right">EOF</td>""")
						else:
							out.append("""		<td align="right">%u</td>""" % end)
					out.append("""		<td align="right">%s</td>""" % ("READ(SHARED)" if ctype==1 else "WRITE(EXCLUSIVE)" if ctype==2 else "???"))
					out.append("""	</tr>""")
				else:
					if pid==0 and start==0 and end==0:
						pid = "-1"
						start = "0"
						end = "EOF"
					elif end > 0x7FFFFFFFFFFFFFFF:
						end = "EOF"
					if ctype==1:
						ctypestr = "READ(SHARED)"
					elif ctype==2:
						ctypestr = "WRITE(EXCLUSIVE)"
					else:
						ctypestr = "???"
					dline = [inode,sessionid,host,info,locktype,owner,pid,start,end,ctypestr]
					tab.append(*dline)
			if cgimode:
				if ALinode!=0:
					out.append("""</table>""")
				print("\n".join(out))
			else:
#				print(locks)
				print(myunicode(tab))
		except Exception:
			print_exception()

if "QU" in sectionset:
	try:
		if cgimode:
			out = []
			out.append("""<table class="acid_tab acid_tab_zebra_C1_C2 acid_tab_storageid_mfsquota" cellspacing="0">""")
			out.append("""	<tr><th colspan="24">Active quotas</th></tr>""")
			out.append("""	<tr>""")
			out.append("""		<th rowspan="3" class="acid_tab_enumerate">#</th>""")
#			out.append("""		<th rowspan="2"><a href="%s">path</a></th>""" % (createorderlink("QU",11)))
#			out.append("""		<th rowspan="2"><a href="%s">exceeded</a></th>""" % (createorderlink("QU",2)))
			out.append("""		<th rowspan="3">path</th>""")
			out.append("""	<th colspan="6">soft&nbsp;quota</th>""")
			out.append("""	<th colspan="4">hard&nbsp;quota</th>""")
			out.append("""	<th colspan="12">current&nbsp;values</th>""")
			out.append("""	</tr>""")
			out.append("""	<tr>""")
#			out.append("""		<th><a href="%s">time&nbsp;to&nbsp;expire</a></th>""" % (createorderlink("QU",10)))
#			out.append("""		<th><a href="%s">inodes</a></th>""" % (createorderlink("QU",11)))
#			out.append("""		<th><a href="%s">length</a></th>""" % (createorderlink("QU",12)))
#			out.append("""		<th><a href="%s">size</a></th>""" % (createorderlink("QU",13)))
#			out.append("""		<th><a href="%s">real&nbsp;size</a></th>""" % (createorderlink("QU",14)))
#			out.append("""		<th><a href="%s">inodes</a></th>""" % (createorderlink("QU",21)))
#			out.append("""		<th><a href="%s">length</a></th>""" % (createorderlink("QU",22)))
#			out.append("""		<th><a href="%s">size</a></th>""" % (createorderlink("QU",23)))
#			out.append("""		<th><a href="%s">real&nbsp;size</a></th>""" % (createorderlink("QU",24)))
#			out.append("""		<th><a href="%s">inodes</a></th>""" % (createorderlink("QU",31)))
#			out.append("""		<th><a href="%s">length</a></th>""" % (createorderlink("QU",32)))
#			out.append("""		<th><a href="%s">size</a></th>""" % (createorderlink("QU",33)))
#			out.append("""		<th><a href="%s">real&nbsp;size</a></th>""" % (createorderlink("QU",34)))
#			out.append("""		<th>exceeded</th>""")
			out.append("""		<th rowspan="2">grace&nbsp;period</th>""")
			out.append("""		<th rowspan="2">time&nbsp;to&nbsp;expire</th>""")
			out.append("""		<th rowspan="2">inodes</th>""")
			out.append("""		<th rowspan="2">length</th>""")
			out.append("""		<th rowspan="2">size</th>""")
			out.append("""		<th rowspan="2">real&nbsp;size</th>""")
			out.append("""		<th rowspan="2">inodes</th>""")
			out.append("""		<th rowspan="2">length</th>""")
			out.append("""		<th rowspan="2">size</th>""")
			out.append("""		<th rowspan="2">real&nbsp;size</th>""")
			out.append("""		<th colspan="3">inodes</th>""")
			out.append("""		<th colspan="3">length</th>""")
			out.append("""		<th colspan="3">size</th>""")
			out.append("""		<th colspan="3">real&nbsp;size</th>""")
			out.append("""	</tr>""")
			out.append("""	<tr>""")
			out.append("""		<th>value</th>""")
			out.append("""		<th>% soft</th>""")
			out.append("""		<th>% hard</th>""")
			out.append("""		<th>value</th>""")
			out.append("""		<th>% soft</th>""")
			out.append("""		<th>% hard</th>""")
			out.append("""		<th>value</th>""")
			out.append("""		<th>% soft</th>""")
			out.append("""		<th>% hard</th>""")
			out.append("""		<th>value</th>""")
			out.append("""		<th>% soft</th>""")
			out.append("""		<th>% hard</th>""")
			out.append("""	</tr>""")
		elif ttymode:
#			tab = Tabble("Active quotas",14)
#			tab.header("",("soft quota","",5),("hard quota","",4),("current values","",4))
#			tab.header("path",("---","",13))
#			tab.header("","time to expire","inodes","length","size","real size","inodes","length","size","real size","inodes","length","size","real size")
#			tab.defattr("l","r","r","r","r","r","r","r","r","r","r","r","r","r")
			tab = Tabble("Active quotas",23)
			tab.header("",("soft quota","",6),("hard quota","",4),("current values","",12))
			tab.header("",("---","",22))
			tab.header("path","","","","","","","","","","",("inodes","",3),("length","",3),("size","",3),("real size","",3))
			tab.header("","grace period","time to expire","inodes","length","size","real size","inodes","length","size","real size",("---","",12))
			tab.header("","","","","","","","","","","","value","% soft","% hard","value","% soft","% hard","value","% soft","% hard","value","% soft","% hard")
			tab.defattr("l","r","r","r","r","r","r","r","r","r","r","r","r","r","r","r","r","r","r","r","r","r","r")
		else:
			tab = Tabble("active quotas",16)
		data,length = masterconn.command(CLTOMA_QUOTA_INFO,MATOCL_QUOTA_INFO)
		if length>=4 and masterconn.version_at_least(1,7,0):
			quotas = []
			maxperc = 0.0
			pos = 0
			while pos<length:
				inode,pleng = struct.unpack(">LL",data[pos:pos+8])
				pos+=8
				path = data[pos:pos+pleng]
				path = path.decode('utf-8','replace')
				pos+=pleng
				if masterconn.version_at_least(3,0,9):
					graceperiod,exceeded,qflags,timetoblock = struct.unpack(">LBBL",data[pos:pos+10])
					pos+=10
				else:
					exceeded,qflags,timetoblock = struct.unpack(">BBL",data[pos:pos+6])
					pos+=6
					graceperiod = 0
				sinodes,slength,ssize,srealsize = struct.unpack(">LQQQ",data[pos:pos+28])
				pos+=28
				hinodes,hlength,hsize,hrealsize = struct.unpack(">LQQQ",data[pos:pos+28])
				pos+=28
				cinodes,clength,csize,crealsize = struct.unpack(">LQQQ",data[pos:pos+28])
				pos+=28
				if (qflags&1) and sinodes>0:
					perc = 100.0*cinodes/sinodes
					if perc>maxperc:
						maxperc = perc
				if (qflags&2) and slength>0:
					perc = 100.0*clength/slength
					if perc>maxperc:
						maxperc = perc
				if (qflags&4) and ssize>0:
					perc = 100.0*csize/ssize
					if perc>maxperc:
						maxperc = perc
				if (qflags&8) and srealsize>0:
					perc = 100.0*crealsize/srealsize
					if perc>maxperc:
						maxperc = perc
				if (qflags&16) and hinodes>0:
					perc = 100.0*cinodes/hinodes
					if perc>maxperc:
						maxperc = perc
				if (qflags&32) and hlength>0:
					perc = 100.0*clength/hlength
					if perc>maxperc:
						maxperc = perc
				if (qflags&64) and hsize>0:
					perc = 100.0*csize/hsize
					if perc>maxperc:
						maxperc = perc
				if (qflags&128) and hrealsize>0:
					perc = 100.0*crealsize/hrealsize
					if perc>maxperc:
						maxperc = perc
				sf = path
				if QUorder==1:
					sf = path
				elif QUorder==2:
					sf = exceeded
				elif QUorder==9:
					sf = graceperiod
				elif QUorder==10:
					sf = timetoblock
				elif QUorder==11:
					sf = sinodes
				elif QUorder==12:
					sf = slength
				elif QUorder==13:
					sf = ssize
				elif QUorder==14:
					sf = srealsize
				elif QUorder==21:
					sf = hinodes
				elif QUorder==22:
					sf = hlength
				elif QUorder==23:
					sf = hsize
				elif QUorder==24:
					sf = hrealsize
				elif QUorder==31:
					sf = cinodes
				elif QUorder==32:
					sf = clength
				elif QUorder==33:
					sf = csize
				elif QUorder==34:
					sf = crealsize
				elif QUorder==41:
					sf = (-1,0) if (qflags&1)==0 else (1,0) if sinodes==0 else (0,1.0*cinodes/sinodes)
				elif QUorder==42:
					sf = (-1,0) if (qflags&2)==0 else (1,0) if slength==0 else (0,1.0*clength/slength)
				elif QUorder==43:
					sf = (-1,0) if (qflags&4)==0 else (1,0) if ssize==0 else (0,1.0*csize/ssize)
				elif QUorder==44:
					sf = (-1,0) if (qflags&8)==0 else (1,0) if srealsize==0 else (0,1.0*crealsize/srealsize)
				elif QUorder==51:
					sf = (-1,0) if (qflags&16)==0 else (1,0) if hinodes==0 else (0,1.0*cinodes/hinodes)
				elif QUorder==52:
					sf = (-1,0) if (qflags&32)==0 else (1,0) if hlength==0 else (0,1.0*clength/hlength)
				elif QUorder==53:
					sf = (-1,0) if (qflags&64)==0 else (1,0) if hsize==0 else (0,1.0*csize/hsize)
				elif QUorder==54:
					sf = (-1,0) if (qflags&128)==0 else (1,0) if hrealsize==0 else (0,1.0*crealsize/hrealsize)
				quotas.append((sf,path,exceeded,qflags,graceperiod,timetoblock,sinodes,slength,ssize,srealsize,hinodes,hlength,hsize,hrealsize,cinodes,clength,csize,crealsize))
			quotas.sort()
			if QUrev:
				quotas.reverse()
			maxperc += 0.01
			for sf,path,exceeded,qflags,graceperiod,timetoblock,sinodes,slength,ssize,srealsize,hinodes,hlength,hsize,hrealsize,cinodes,clength,csize,crealsize in quotas:
				if cgimode:
					out.append("""	<tr>""")
					out.append("""		<td align="right"></td>""")
					out.append("""		<td align="left">%s</td>""" % htmlentities(path))
	#				out.append("""		<td align="center">%s</td>""" % ("yes" if exceeded else "no"))
					if graceperiod>0:
						out.append("""		<td align="center"><span class="sortkey">%u </span><a style="cursor:default" title="%s">%s</a></td>""" % (graceperiod,timeduration_to_fullstr(graceperiod),timeduration_to_shortstr(graceperiod)))
					else:
						out.append("""		<td align="center"><span class="sortkey">0 </span>default</td>""")
					if timetoblock<0xFFFFFFFF:
						if timetoblock>0:
	#						days,rest = divmod(timetoblock,86400)
	#						hours,rest = divmod(rest,3600)
	#						min,sec = divmod(rest,60)
	#						if days>0:
	#							tbstr = "%ud,&nbsp;%uh&nbsp;%um&nbsp;%us" % (days,hours,min,sec)
	#						elif hours>0:
	#							tbstr = "%uh&nbsp;%um&nbsp;%us" % (hours,min,sec)
	#						elif min>0:
	#							tbstr = "%um&nbsp;%us" % (min,sec)
	#						else:
	#							tbstr = "%us" % sec
							out.append("""		<td align="center"><span class="SEXCEEDED"><span class="sortkey">%u </span><a style="cursor:default" title="%s">%s</a></span></td>""" % (timetoblock,timeduration_to_fullstr(timetoblock),timeduration_to_shortstr(timetoblock)))
						else:
							out.append("""		<td align="center"><span class="EXCEEDED"><span class="sortkey">0 </span>expired</span></td>""")
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if qflags&1:
						out.append("""		<td align="right"><span>%u</span></td>""" % (sinodes))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if qflags&2:
						out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B"><span>%s</span></a></td>""" % (slength,decimal_number(slength),humanize_number(slength,"&nbsp;")))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if qflags&4:
						out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B"><span>%s</span></a></td>""" % (ssize,decimal_number(ssize),humanize_number(ssize,"&nbsp;")))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if qflags&8:
						out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B"><span>%s</span></a></td>""" % (srealsize,decimal_number(srealsize),humanize_number(srealsize,"&nbsp;")))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if qflags&16:
						out.append("""		<td align="right"><span>%u</span></td>""" % (hinodes))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if qflags&32:
						out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B"><span>%s</span></a></td>""" % (hlength,decimal_number(hlength),humanize_number(hlength,"&nbsp;")))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if qflags&64:
						out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B"><span>%s</span></a></td>""" % (hsize,decimal_number(hsize),humanize_number(hsize,"&nbsp;")))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if qflags&128:
						out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B"><span>%s</span></a></td>""" % (hrealsize,decimal_number(hrealsize),humanize_number(hrealsize,"&nbsp;")))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					out.append("""		<td align="right">%u</td>""" % cinodes)
					if qflags&1:
						if sinodes>0:
							if sinodes>=cinodes:
								cl="NOTEXCEEDED"
							elif timetoblock>0:
								cl="SEXCEEDED"
							else:
								cl="EXCEEDED"
							out.append("""		<td align="right"><span class="%s">%.2f</span></td>""" % (cl,(100.0*cinodes)/sinodes))
						else:
							out.append("""		<td align="right"><span class="sortkey">%.2f </span><span class="EXCEEDED">inf</span></td>""" % (maxperc))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if qflags&16:
						if hinodes>0:
							if hinodes>cinodes:
								cl="NOTEXCEEDED"
							else:
								cl="EXCEEDED"
							out.append("""		<td align="right"><span class="%s">%.2f</span></td>""" % (cl,(100.0*cinodes)/hinodes))
						else:
							out.append("""		<td align="right"><span class="sortkey">%.2f </span><span class="EXCEEDED">inf</span></td>""" % (maxperc))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B">%s</a></td>""" % (clength,decimal_number(clength),humanize_number(clength,"&nbsp;")))
					if qflags&2:
						if slength>0:
							if slength>=clength:
								cl="NOTEXCEEDED"
							elif timetoblock>0:
								cl="SEXCEEDED"
							else:
								cl="EXCEEDED"
							out.append("""		<td align="right"><span class="%s">%.2f</span></td>""" % (cl,(100.0*clength)/slength))
						else:
							out.append("""		<td align="right"><span class="sortkey">%.2f </span><span class="EXCEEDED">inf</span></td>""" % (maxperc))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if qflags&32:
						if hlength>0:
							if hlength>clength:
								cl="NOTEXCEEDED"
							else:
								cl="EXCEEDED"
							out.append("""		<td align="right"><span class="%s">%.2f</span></td>""" % (cl,(100.0*clength)/hlength))
						else:
							out.append("""		<td align="right"><span class="sortkey">%.2f </span><span class="EXCEEDED">inf</span></td>""" % (maxperc))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B">%s</a></td>""" % (csize,decimal_number(csize),humanize_number(csize,"&nbsp;")))
					if qflags&4:
						if ssize>0:
							if ssize>=csize:
								cl="NOTEXCEEDED"
							elif timetoblock>0:
								cl="SEXCEEDED"
							else:
								cl="EXCEEDED"
							out.append("""		<td align="right"><span class="%s">%.2f</span></td>""" % (cl,(100.0*csize)/ssize))
						else:
							out.append("""		<td align="right"><span class="sortkey">%.2f </span><span class="EXCEEDED">inf</span></td>""" % (maxperc))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if qflags&64:
						if hsize>0:
							if hsize>csize:
								cl="NOTEXCEEDED"
							else:
								cl="EXCEEDED"
							out.append("""		<td align="right"><span class="%s">%.2f</span></td>""" % (cl,(100.0*csize)/hsize))
						else:
							out.append("""		<td align="right"><span class="sortkey">%.2f </span><span class="EXCEEDED">inf</span></td>""" % (maxperc))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					out.append("""		<td align="right"><span class="sortkey">%u </span><a style="cursor:default" title="%s B">%s</a></td>""" % (crealsize,decimal_number(crealsize),humanize_number(crealsize,"&nbsp;")))
					if qflags&8:
						if srealsize>0:
							if srealsize>=crealsize:
								cl="NOTEXCEEDED"
							elif timetoblock>0:
								cl="SEXCEEDED"
							else:
								cl="EXCEEDED"
							out.append("""		<td align="right"><span class="%s">%.2f</span></td>""" % (cl,(100.0*crealsize)/srealsize))
						else:
							out.append("""		<td align="right"><span class="sortkey">%.2f </span><span class="EXCEEDED">inf</span></td>""" % (maxperc))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					if qflags&128:
						if hrealsize>0:
							if hrealsize>crealsize:
								cl="NOTEXCEEDED"
							else:
								cl="EXCEEDED"
							out.append("""		<td align="right"><span class="%s">%.2f</span></td>""" % (cl,(100.0*crealsize)/hrealsize))
						else:
							out.append("""		<td align="right"><span class="sortkey">%.2f </span><span class="EXCEEDED">inf</span></td>""" % (maxperc))
					else:
						out.append("""		<td align="center"><span class="sortkey">-1 </span>-</td>""")
					out.append("""	</tr>""")
				elif ttymode:
					dline = [path] #,"yes" if exceeded else "no"]
					if graceperiod>0:
						dline.append(timeduration_to_shortstr(graceperiod))
					else:
						dline.append("default")
					if timetoblock<0xFFFFFFFF:
						if timetoblock>0:
							dline.append((timeduration_to_shortstr(timetoblock),"2"))
						else:
							dline.append(("expired","1"))
					else:
						dline.append("-")
					if qflags&1:
						dline.append(sinodes)
					else:
						dline.append("-")
					if qflags&2:
						dline.append(humanize_number(slength," "))
					else:
						dline.append("-")
					if qflags&4:
						dline.append(humanize_number(ssize," "))
					else:
						dline.append("-")
					if qflags&8:
						dline.append(humanize_number(srealsize," "))
					else:
						dline.append("-")
					if qflags&16:
						dline.append(hinodes)
					else:
						dline.append("-")
					if qflags&32:
						dline.append(humanize_number(hlength," "))
					else:
						dline.append("-")
					if qflags&64:
						dline.append(humanize_number(hsize," "))
					else:
						dline.append("-")
					if qflags&128:
						dline.append(humanize_number(hrealsize," "))
					else:
						dline.append("-")
					dline.append(cinodes)
					if qflags&1:
						if sinodes>0:
							dline.append(("%.2f" % ((100.0*cinodes)/sinodes),"4" if sinodes>=cinodes else "2" if timetoblock>0 else "1"))
						else:
							dline.append(("inf","1"))
					else:
						dline.append("-")
					if qflags&16:
						if hinodes>0:
							dline.append(("%.2f" % ((100.0*cinodes)/hinodes),"4" if hinodes>cinodes else "1"))
						else:
							dline.append(("inf","1"))
					else:
						dline.append("-")
					dline.append(humanize_number(clength," "))
					if qflags&2:
						if slength>0:
							dline.append(("%.2f" % ((100.0*clength)/slength),"4" if slength>=clength else "2" if timetoblock>0 else "1"))
						else:
							dline.append(("inf","1"))
					else:
						dline.append("-")
					if qflags&32:
						if hlength>0:
							dline.append(("%.2f" % ((100.0*clength)/hlength),"4" if hlength>clength else "1"))
						else:
							dline.append(("inf","1"))
					else:
						dline.append("-")
					dline.append(humanize_number(csize," "))
					if qflags&4:
						if ssize>0:
							dline.append(("%.2f" % ((100.0*csize)/ssize),"4" if ssize>=csize else "2" if timetoblock>0 else "1"))
						else:
							dline.append(("inf","1"))
					else:
						dline.append("-")
					if qflags&64:
						if hsize>0:
							dline.append(("%.2f" % ((100.0*csize)/hsize),"4" if hsize>csize else "1"))
						else:
							dline.append(("inf","1"))
					else:
						dline.append("-")
					dline.append(humanize_number(crealsize," "))
					if qflags&8:
						if srealsize>0:
							dline.append(("%.2f" % ((100.0*crealsize)/srealsize),"4" if srealsize>=crealsize else "2" if timetoblock>0 else "1"))
						else:
							dline.append(("inf","1"))
					else:
						dline.append("-")
					if qflags&128:
						if hrealsize>0:
							dline.append(("%.2f" % ((100.0*crealsize)/hrealsize),"4" if hrealsize>crealsize else "1"))
						else:
							dline.append(("inf","1"))
					else:
						dline.append("-")
					tab.append(*dline)
				else:
					dline = [path,"yes" if exceeded else "no"]
					if graceperiod>0:
						dline.append(graceperiod)
					else:
						dline.append("default")
					if timetoblock<0xFFFFFFFF:
						if timetoblock>0:
							dline.append(timetoblock)
						else:
							dline.append("expired")
					else:
						dline.append("-")
					dline.append(sinodes if qflags&1 else "-")
					dline.append(slength if qflags&2 else "-")
					dline.append(ssize if qflags&4 else "-")
					dline.append(srealsize if qflags&8 else "-")
					dline.append(hinodes if qflags&16 else "-")
					dline.append(hlength if qflags&32 else "-")
					dline.append(hsize if qflags&64 else "-")
					dline.append(hrealsize if qflags&128 else "-")
					dline.extend((cinodes,clength,csize,crealsize))
					tab.append(*dline)
		if cgimode:
			out.append("""</table>""")
			print("\n".join(out))
		else:
			print(myunicode(tab))
	except Exception:
		print_exception()

if "MC" in sectionset:
	out = []
	try:
		if cgimode:
			charts = (
				(100,'cpu','cpu usage (percent)'),
				(101,'memory','memory usage (if available - rss + virt)'),
				(102,'space','raw disk space usage (total / used)'),
				(103,'dels','chunk deletions per minute (successful/unsuccessful)'),
				(104,'repl','chunk replications per minute (successful/unsuccessful)'),
				(105,'creat','chunk creations per minute (successful/unsuccessful)'),
				(106,'change','chunk internal operations per minute (successful/unsuccessful)'),
				(4,'statfs','statfs operations (per minute)'),
				(5,'getattr','getattr operations (per minute)'),
				(6,'setattr','setattr operations (per minute)'),
				(7,'lookup','lookup operations (per minute)'),
				(8,'mkdir','mkdir operations (per minute)'),
				(9,'rmdir','rmdir operations (per minute)'),
				(10,'symlink','symlink operations (per minute)'),
				(11,'readlink','readlink operations (per minute)'),
				(12,'mknod','mknod operations (per minute)'),
				(13,'unlink','unlink operations (per minute)'),
				(14,'rename','rename operations (per minute)'),
				(15,'link','link operations (per minute)'),
				(16,'readdir','readdir operations (per minute)'),
				(17,'open','open operations (per minute)'),
				(18,'read','read operations (per minute)'),
				(19,'write','write operations (per minute)'),
				(21,'prcvd','packets received (per second)'),
				(22,'psent','packets sent (per second)'),
				(23,'brcvd','bits received (per second)'),
				(24,'bsent','bits sent (per second)')
			)

			if MCdata=="" and leaderfound:
				MCdata="%s:%u:%u" % (masterconn.host,masterconn.port,1 if masterconn.version_at_least(2,0,0) else 0)
			servers = []
			mixedservers = 0
			if len(masterlistver)>0:
				masterlistver.sort()
				out.append("""<form action="#"><table class="FR" cellspacing="0"><tr><th>Select: <select name="server" size="1" onchange="document.location.href='%s&MCdata='+this.options[this.selectedIndex].value">""" % createjslink({"MCdata":""}))
				entrystr = []
				entrydesc = {}
				for id,oname,desc in charts:
					name = oname.replace(":","")
					entrystr.append(name)
					entrydesc[name] = desc
				for strip,port,version in masterlistver:
					nc = 1 if version>=(2,0,0) else 0
					if mixedservers==0:
						mixedservers = nc+1
					if mixedservers!=nc+1:
						mixedservers = 3
					name = "%s:%u" % (strip,port)
					namearg = "%s:%u" % (name,nc)
					hostx = resolve(strip)
					if hostx==UNRESOLVED:
						host = ""
					else:
						host = " / "+hostx
					entrystr.append(namearg)
					entrydesc[namearg] = "Server: %s%s%s" % (name,host," *" if (leaderfound and strip==masterconn.host) else "")
					servers.append((strip,port,"ma_"+name.replace(".","_").replace(":","_"),entrydesc[namearg],nc))
				if MCdata not in entrystr:
					out.append("""<option value="" selected="selected"> data type or server</option>""")
				for estr in entrystr:
					if estr==MCdata:
						out.append("""<option value="%s" selected="selected">%s</option>""" % (estr,entrydesc[estr]))
					else:
						out.append("""<option value="%s">%s</option>""" % (estr,entrydesc[estr]))
				out.append("""</select></th></tr></table></form>""")

			mchtmp = MCdata.split(":")
			if len(mchtmp)==2:
				mchtmp = (mchtmp[0],mchtmp[1],0)
			if len(mchtmp)==3:
				mahost = mchtmp[0]
				maport = mchtmp[1]
				manc = int(mchtmp[2])

				out.append("""<script type="text/javascript">""")
				out.append("""<!--//--><![CDATA[//><!--""")
				out.append("""	var ma_vids = [%s];""" % ",".join(map(repr,[ x[0] for x in charts ])))
				out.append("""	var ma_inames = [%s];""" % ",".join(map(repr,[ x[1] for x in charts ])))
				out.append("""	var ma_idesc = [%s];""" % ",".join(map(repr,[ x[2] for x in charts ])))
				out.append("""	var ma_host = "%s";""" % mahost)
				out.append("""	var ma_port = "%s";""" % maport)
				out.append("""	var ma_nc = %u;""" % manc)
				out.append("""//--><!]]>""")
				out.append("""</script>""")
				out.append("""<script type="text/javascript">
<!--//--><![CDATA[//><!--
	var i,j;
	var ma_chartid = [0,0];
	var ma_range_up=0;
	var ma_range_down=0;
	var ma_zoomed = [];
	var ma_resizeto;
	function ma_refresh() {
		var i;
		var minutes = Math.floor((new Date()).getTime()/60000);
		for (i=0 ; i<ma_inames.length ; i++) {
			var name = ma_inames[i];
			var vid = ma_vids[i];
			var id = vid*10+ma_range_up;
			var element = document.getElementById(name);
			if (element) {
				var url;
				if (ma_nc) {
					var width = element.scrollWidth;
					var height = element.scrollHeight;
					url = "chart.cgi?host="+ma_host+"&port="+ma_port+"&id="+id+"&width="+width+"&height="+height+"&antycache="+minutes;
				} else {
					url = "chart.cgi?host="+ma_host+"&port="+ma_port+"&id="+id+"&antycache="+minutes;
				}
				if (typeof(element.ma_url)=="undefined" || element.ma_url!=url) {
					element.ma_url = url;
					element.style.backgroundImage = "url('"+url+"')";
				}
			}
		}
		for (i=0 ; i<2 ; i++) {
			var vid = ma_vids[ma_chartid[i]];
			var id = vid*10+ma_range_down;
			var iname = "ma_chart"+i;
			var element = document.getElementById(iname);
			if (element) {
				var url;
				if (ma_nc) {
					var width = element.scrollWidth;
					var height = element.scrollHeight;
					url = "chart.cgi?host="+ma_host+"&port="+ma_port+"&id="+id+"&width="+width+"&height="+height+"&antycache="+minutes;
				} else {
					url = "chart.cgi?host="+ma_host+"&port="+ma_port+"&id="+id+"&antycache="+minutes;
				}
				if (typeof(element.ma_url)=="undefined" || element.ma_url!=url) {
					element.ma_url = url;
					element.style.backgroundImage = "url('"+url+"')";
				}
			}
		}
	}
	function ma_change_up(num) {
		ma_range_up = num;
		ma_refresh();
	}
	function ma_change_down(num) {
		ma_range_down = num;
		ma_refresh();
	}
	function ma_zoom(element) {
		var name = element.id;
		if (typeof(ma_zoomed[name])=="undefined") {
			ma_zoomed[name]=0;
		}
		if (ma_zoomed[name]==0) {
			ma_zoomed[name]=1;
			element.style.height = '220px';
		} else if (ma_zoomed[name]==1) {
			ma_zoomed[name]=2;
			element.style.height = '420px';
		} else if (ma_zoomed[name]==2) {
			ma_zoomed[name]=3;
			element.style.height = '820px';
		} else {
			ma_zoomed[name]=0;
			element.style.height = '120px';
		}
		ma_refresh();
	}
	function ma_resized() {
		clearTimeout(ma_resizeto);
		ma_resizeto = setTimeout(ma_refresh,250);
	}
	function ma_change_type(id,no) {
		var o;
		ma_chartid[id]=no;
		o = document.getElementById("ma_desc"+id);
		o.innerHTML = ma_idesc[no];
		ma_refresh();
	}
	function ma_add_event(obj,type,fn) {
		if (obj.addEventListener) {
			obj.addEventListener(type, fn, false);
		} else if (obj.attachEvent) {
			obj.attachEvent('on'+type, fn);
		}
	}
	ma_add_event(window,"load",ma_refresh);
	ma_add_event(window,"resize",ma_resized);
//--><!]]>
</script>""")
				out.append("""<table class="FR" cellspacing="0" cellpadding="0">""")
				out.append("""	<tr>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:ma_change_up(0);">short range</a></th>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:ma_change_up(1);">medium range</a></th>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:ma_change_up(2);">long range</a></th>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:ma_change_up(3);">very long range</a></th>""")
				out.append("""	</tr>""")
				for id,name,desc in charts:
					divclass = "CHARTDYNAMIC" if manc else "CHARTSTATIC"
					divclick = 'onclick="ma_zoom(this)"' if manc else ""
					out.append("""	<tr class="C2">""")
					out.append("""		<td colspan="4" style="height:124px;" valign="middle">""")
					out.append("""			<div class="%s" id="%s" %s>""" % (divclass,name,divclick))
					out.append("""				<span class="CAPTION">%s</span>""" % desc)
					out.append("""			</div>""")
					out.append("""		</td>""")
					out.append("""	</tr>""")
				out.append("""</table>""")

				out.append("""<form action="#"><table class="FR" cellspacing="0" cellpadding="0">""")
				out.append("""	<tr>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:ma_change_down(0);">short range</a></th>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:ma_change_down(1);">medium range</a></th>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:ma_change_down(2);">long range</a></th>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:ma_change_down(3);">very long range</a></th>""")
				out.append("""	</tr>""")
				for i in range(2):
					divclass = "CHARTDYNAMIC" if manc else "CHARTSTATIC"
					divclick = 'onclick="ma_zoom(this)"' if manc else ""
					out.append("""	<tr class="C2">""")
					out.append("""		<td colspan="4" style="height:124px;" valign="middle">""")
					out.append("""			<div class="%s" id="ma_chart%u" %s>""" % (divclass,i,divclick))
					out.append("""				<span class="CAPTION" id="ma_desc%u">%s</span>""" % (i,charts[0][2]))
					out.append("""			</div>""")
					out.append("""		</td>""")
					out.append("""	</tr>""")
					out.append("""	<tr>""")
					out.append("""		<th colspan="4">""")
					out.append("""			<select name="machart%u" size="1" onchange="ma_change_type(%u,this.options[this.selectedIndex].value)">""" % (i,i))
					no = 0
					for id,name,desc in charts:
						out.append("""				<option value="%u">%s</option>""" % (no,desc))
						no += 1
					out.append("""		</th>""")
					out.append("""	</tr>""")
				out.append("""</table></form>""")
			elif len(mchtmp)==1 and len(MCdata)>0:
				chid = 0
				for id,name,desc in charts:
					if name==MCdata:
						chid = id
				if chid==0:
					try:
						chid = int(MCdata)
					except Exception:
						pass
				if chid>0 and chid<1000:
					out.append("""<script type="text/javascript">""")
					out.append("""<!--//--><![CDATA[//><!--""")
					out.append("""	var ma_vhosts = [%s];""" % ",".join(map(repr,[ x[0] for x in servers ])))
					out.append("""	var ma_vports = [%s];""" % ",".join(map(repr,[ x[1] for x in servers ])))
					out.append("""	var ma_inames = [%s];""" % ",".join(map(repr,[ x[2] for x in servers ])))
					out.append("""	var ma_nc = [%s];""" % ",".join(map(repr,[ x[4] for x in servers ])))
					out.append("""	var ma_chid = %u;""" % chid)
					out.append("""//--><!]]>""")
					out.append("""</script>""")
					out.append("""<script type="text/javascript">
<!--//--><![CDATA[//><!--
	var i,j;
	var ma_range=0;
	var ma_zoomed = [];
	var ma_resizeto;
	function ma_refresh() {
		var i;
		var minutes = Math.floor((new Date()).getTime()/60000);
		for (i=0 ; i<ma_inames.length ; i++) {
			var name = ma_inames[i];
			var vhost = ma_vhosts[i];
			var vport = ma_vports[i];
			var manc = ma_nc[i];
			var id = ma_chid*10+ma_range;
			var element = document.getElementById(name);
			if (element) {
				var url;
				if (manc) {
					var width = element.scrollWidth;
					var height = element.scrollHeight;
					url = "chart.cgi?host="+vhost+"&port="+vport+"&id="+id+"&width="+width+"&height="+height+"&antycache="+minutes;
				} else {
					url = "chart.cgi?host="+vhost+"&port="+vport+"&id="+id+"&antycache="+minutes;
				}
				if (typeof(element.ma_url)=="undefined" || element.ma_url!=url) {
					element.ma_url = url;
					element.style.backgroundImage = "url('"+url+"')";
				}
			}
		}
	}
	function ma_change(num) {
		ma_range = num;
		ma_refresh();
	}
	function ma_zoom(element) {
		var name = element.id;
		if (typeof(ma_zoomed[name])=="undefined") {
			ma_zoomed[name]=0;
		}
		if (ma_zoomed[name]==0) {
			ma_zoomed[name]=1;
			element.style.height = '220px';
		} else if (ma_zoomed[name]==1) {
			ma_zoomed[name]=2;
			element.style.height = '420px';
		} else if (ma_zoomed[name]==2) {
			ma_zoomed[name]=3;
			element.style.height = '820px';
		} else {
			ma_zoomed[name]=0;
			element.style.height = '120px';
		}
		ma_refresh();
	}
	function ma_resized() {
		clearTimeout(ma_resizeto);
		ma_resizeto = setTimeout(ma_refresh,250);
	}
	function ma_add_event(obj,type,fn) {
		if (obj.addEventListener) {
			obj.addEventListener(type, fn, false);
		} else if (obj.attachEvent) {
			obj.attachEvent('on'+type, fn);
		}
	}
	ma_add_event(window,"load",ma_refresh);
	ma_add_event(window,"resize",ma_resized);
//--><!]]>
</script>""")
					out.append("""<table class="FR" cellspacing="0" cellpadding="0">""")
					out.append("""	<tr>""")
					out.append("""		<th class="RANGEBAR"><a href="javascript:ma_change(0);">short range</a></th>""")
					out.append("""		<th class="RANGEBAR"><a href="javascript:ma_change(1);">medium range</a></th>""")
					out.append("""		<th class="RANGEBAR"><a href="javascript:ma_change(2);">long range</a></th>""")
					out.append("""		<th class="RANGEBAR"><a href="javascript:ma_change(3);">very long range</a></th>""")
					out.append("""	</tr>""")
					for mahost,maport,name,desc,manc in servers:
						divclass = "CHARTDYNAMIC" if manc else "CHARTSTATICMIXED" if mixedservers==3 else "CHARTSTATIC"
						divclick = 'onclick="ma_zoom(this)"' if manc else ""
						out.append("""	<tr class="C2">""")
						out.append("""		<td colspan="4" style="height:124px;" valign="middle">""")
						out.append("""			<div class="%s" id="%s" %s>""" % (divclass,name,divclick))
						out.append("""				<span class="CAPTION">%s</span>""" % desc)
						out.append("""			</div>""")
						out.append("""		</td>""")
						out.append("""	</tr>""")
					out.append("""</table>""")
		else:
			if masterconn.version_at_least(2,0,15):
				if ttymode:
					tab = Tabble("Master chart data",len(MCchdata)+1,"r")
					hdrstr = ["host/port ->"]
					for host,port,no,mode,desc,raw in MCchdata:
						if (host==None or port==None):
							hdrstr.append("leader")
						else:
							hdrstr.append("%s:%s" % (host,port))
					tab.header(*hdrstr)
					tab.header(("---","",len(MCchdata)+1))
					hdrstr = ["Time"]
					for host,port,no,mode,desc,raw in MCchdata:
						if raw:
							if (no==0 or no==1 or no==100):
								hdrstr.append("%s (+)" % desc)
							else:
								hdrstr.append("%s (raw)" % desc)
						else:
							hdrstr.append(desc)
					tab.header(*hdrstr)
				else:
					tab = Tabble("Master chart data",len(MCchdata)+1)
				chrange = MCrange
				if chrange<0 or chrange>3:
					chrange = 0
				if MCcount<0 or MCcount>4095:
					MCcount = 4095
				chrangestep = [60,360,1800,86400][chrange]
				series = set()
				for host,port,no,mode,desc,raw in MCchdata:
					if no==100:
						series.add((host,port,0))
						series.add((host,port,1))
					else:
						series.add((host,port,no))
				for gpass in (1,2):
					MCresult = {}
					timestamp = 0
					entries = 0
					repeat = 0
					for host,port,x in series:
						if host==None or port==None:
							data,length = masterconn.command(CLTOAN_CHART_DATA,ANTOCL_CHART_DATA,struct.pack(">LL",x*10+chrange,MCcount))
						else:
							conn = MFSConn(host,port)
							data,length = conn.command(CLTOAN_CHART_DATA,ANTOCL_CHART_DATA,struct.pack(">LL",x*10+chrange,MCcount))
						if length>=8:
							ts,e = struct.unpack(">LL",data[:8])
							if e*8+8==length and (entries==0 or entries==e):
								entries = e
								if timestamp==0 or timestamp==ts or gpass==2:
									timestamp=ts
									MCresult[(host,port,x)] = list(struct.unpack(">"+e*"Q",data[8:]))
								else:
									repeat = 1
									break
							else:
								MCresult[(host,port,x)]=None
						else:
							MCresult[(host,port,x)]=None
					if repeat:
						continue
					else:
						break
				for e in xrange(entries):
					ts = timestamp-chrangestep*e
					timestring = time.strftime("%Y-%m-%d %H:%M",time.gmtime(ts))
					dline = [timestring]
					for host,port,no,mode,desc,raw in MCchdata:
						if no==100:
							datalist1 = MCresult[(host,port,0)]
							datalist2 = MCresult[(host,port,1)]
							if (datalist1!=None and datalist2!=None and datalist1[e]<((2**64)-1) and datalist2[e]<((2**64)-1)):
								data = datalist1[e]+datalist2[e]
							else:
								data = None
						else:
							datalist = MCresult[(host,port,no)]
							if datalist!=None and datalist[e]<((2**64)-1):
								data = datalist[e]
							else:
								data = None
						if data==None:
							dline.append("-")
						elif mode==0:
							cpu = (data/(10000.0*chrangestep))
							if raw:
								dline.append("%.8f%%" % (cpu))
							else:
								dline.append("%.2f%%" % (cpu))
						elif mode==1:
							if raw:
								dline.append("%u" % data)
							else:
								data = float(data)/float(chrangestep)
								dline.append("%.3f/s" % data)
						elif mode==2:
							if raw:
								dline.append("%u" % data)
							else:
								dline.append("%s" % humanize_number(data," "))
					tab.append(*dline)
			else:
				tab = Tabble("Master chart data are not supported in your version of MFS - please upgrade",1,"r")
		if cgimode:
			print("\n".join(out))
		else:
			print(myunicode(tab))
	except Exception:
		print_exception()

if "CC" in sectionset:
	out = []
	try:
		if cgimode:
			# get cs list
			hostlist = []
			for cs in dataprovider.get_chunkservers():
				if (cs.flags&1)==0:
					hostlist.append((cs.ip,cs.port,cs.version))
#			data,length = masterconn.command(CLTOMA_CSERV_LIST,MATOCL_CSERV_LIST)
#			if masterconn.version_at_least(1,7,25) and (length%64)==0:
#				n = length//64
#				servers = []
#				for i in range(n):
#					d = data[i*64:(i+1)*64]
#					flags,v1,v2,v3,ip1,ip2,ip3,ip4,port = struct.unpack(">BBBBBBBBH",d[:10])
#					if (flags&1)==0:
#						hostlist.append(((ip1,ip2,ip3,ip4),port,(v1,v2,v3)))
#			elif masterconn.version_at_least(1,6,28) and masterconn.version_less_than(1,7,25) and (length%62)==0:
#				n = length//62
#				servers = []
#				for i in range(n):
#					d = data[i*62:(i+1)*62]
#					disconnected,v1,v2,v3,ip1,ip2,ip3,ip4,port = struct.unpack(">BBBBBBBBH",d[:10])
#					if disconnected==0:
#						hostlist.append(((ip1,ip2,ip3,ip4),port,(v1,v2,v3)))
#			elif masterconn.version_less_than(1,6,28) and (length%54)==0:
#				n = length//54
#				servers = []
#				for i in range(n):
#					d = data[i*54:(i+1)*54]
#					disconnected,v1,v2,v3,ip1,ip2,ip3,ip4,port = struct.unpack(">BBBBBBBBH",d[:10])
#					if disconnected==0:
#						hostlist.append(((ip1,ip2,ip3,ip4),port,(v1,v2,v3)))
			charts = (
				(100,'cpu','cpu usage (percent)'),
				(107,'memory','memory usage (if available - rss + virt)'),
				(101,'datain','traffic from clients and other chunkservers (bits/s - main server + replicator)'),
				(102,'dataout','traffic to clients and other chunkservers (bits/s - main server + replicator)'),
				(103,'bytesr','bytes read - data/other (bytes/s)'),
				(104,'bytesw','bytes written - data/other (bytes/s)'),
				(2,'masterin','traffic from master (bits/s)'),
				(3,'masterout','traffic to master (bits/s)'),
				(105,'hddopr','number of low-level read operations per minute'),
				(106,'hddopw','number of low-level write operations per minute'),
				(16,'hlopr','number of high-level read operations per minute'),
				(17,'hlopw','number of high-level write operations per minute'),
				(18,'rtime','time of data read operations'),
				(19,'wtime','time of data write operations'),
				(20,'repl','number of chunk replications per minute'),
				(21,'create','number of chunk creations per minute'),
				(22,'delete','number of chunk deletions per minute'),
				(33,'change','number of chunk internal operations (duplicate,truncate,etc.) per minute'),
				(108,'move','number of chunk internal rebalances per minute (low speed + high speed)'),
				(28,'load','load - max operations in queue'),
			)

			servers = []
			mixedservers = 0
			if len(hostlist)>0:
				hostlist.sort()
				out.append("""<form action="#"><table class="FR" cellspacing="0"><tr><th>Select: <select name="server" size="1" onchange="document.location.href='%s&CCdata='+this.options[this.selectedIndex].value">""" % createjslink({"CCdata":""}))
				entrystr = []
				entrydesc = {}
				for id,oname,desc in charts:
					name = oname.replace(":","")
					entrystr.append(name)
					entrydesc[name] = desc
				for ip,port,version in hostlist:
					nc = 1 if version>=(2,0,0) else 0
					if mixedservers==0:
						mixedservers = nc+1
					if mixedservers!=nc+1:
						mixedservers = 3
					strip = "%u.%u.%u.%u" % ip
					name = "%s:%u" % (strip,port)
					namearg = "%s:%u" % (name,nc)
					hostx = resolve(strip)
					if hostx==UNRESOLVED:
						host = ""
					else:
						host = " / "+hostx
					entrystr.append(namearg)
					entrydesc[namearg] = "Server: %s%s" % (name,host)
					servers.append((strip,port,"cs_"+name.replace(".","_").replace(":","_"),entrydesc[namearg],nc))
				if CCdata not in entrystr:
					out.append("""<option value="" selected="selected"> data type or server</option>""")
				for estr in entrystr:
					if estr==CCdata:
						out.append("""<option value="%s" selected="selected">%s</option>""" % (estr,entrydesc[estr]))
					else:
						out.append("""<option value="%s">%s</option>""" % (estr,entrydesc[estr]))
				out.append("""</select></th></tr></table></form>""")

			cchtmp = CCdata.split(":")
			if len(cchtmp)==2:
				cchtmp = (cchtmp[0],cchtmp[1],0)
			if len(cchtmp)==3:
				cshost = cchtmp[0]
				csport = cchtmp[1]
				csnc = int(cchtmp[2])

				out.append("""<script type="text/javascript">""")
				out.append("""<!--//--><![CDATA[//><!--""")
				out.append("""	var cs_vids = [%s];""" % ",".join(map(repr,[ x[0] for x in charts ])))
				out.append("""	var cs_inames = [%s];""" % ",".join(map(repr,[ x[1] for x in charts ])))
				out.append("""	var cs_idesc = [%s];""" % ",".join(map(repr,[ x[2] for x in charts ])))
				out.append("""	var cs_host = "%s";""" % cshost)
				out.append("""	var cs_port = "%s";""" % csport)
				out.append("""	var cs_nc = %u;""" % csnc)
				out.append("""//--><!]]>""")
				out.append("""</script>""")
				out.append("""<script type="text/javascript">
<!--//--><![CDATA[//><!--
	var i,j;
	var cs_chartid = [0,0];
	var cs_range_up=0;
	var cs_range_down=0;
	var cs_zoomed = [];
	var cs_resizeto;
	function cs_refresh() {
		var i;
		var minutes = Math.floor((new Date()).getTime()/60000);
		for (i=0 ; i<cs_inames.length ; i++) {
			var name = cs_inames[i];
			var vid = cs_vids[i];
			var id = vid*10+cs_range_up;
			var element = document.getElementById(name);
			if (element) {
				var url;
				if (cs_nc) {
					var width = element.scrollWidth;
					var height = element.scrollHeight;
					url = "chart.cgi?host="+cs_host+"&port="+cs_port+"&id="+id+"&width="+width+"&height="+height+"&antycache="+minutes;
				} else {
					url = "chart.cgi?host="+cs_host+"&port="+cs_port+"&id="+id+"&antycache="+minutes;
				}
				if (typeof(element.cs_url)=="undefined" || element.cs_url!=url) {
					element.cs_url = url;
					element.style.backgroundImage = "url('"+url+"')";
				}
			}
		}
		for (i=0 ; i<2 ; i++) {
			var vid = cs_vids[cs_chartid[i]];
			var id = vid*10+cs_range_down;
			var iname = "cs_chart"+i;
			var element = document.getElementById(iname);
			if (element) {
				var url;
				if (cs_nc) {
					var width = element.scrollWidth;
					var height = element.scrollHeight;
					url = "chart.cgi?host="+cs_host+"&port="+cs_port+"&id="+id+"&width="+width+"&height="+height+"&antycache="+minutes;
				} else {
					url = "chart.cgi?host="+cs_host+"&port="+cs_port+"&id="+id+"&antycache="+minutes;
				}
				if (typeof(element.cs_url)=="undefined" || element.cs_url!=url) {
					element.cs_url = url;
					element.style.backgroundImage = "url('"+url+"')";
				}
			}
		}
	}
	function cs_change_up(num) {
		cs_range_up = num;
		cs_refresh();
	}
	function cs_change_down(num) {
		cs_range_down = num;
		cs_refresh();
	}
	function cs_zoom(element) {
		var name = element.id;
		if (typeof(cs_zoomed[name])=="undefined") {
			cs_zoomed[name]=0;
		}
		if (cs_zoomed[name]==0) {
			cs_zoomed[name]=1;
			element.style.height = '220px';
		} else if (cs_zoomed[name]==1) {
			cs_zoomed[name]=2;
			element.style.height = '420px';
		} else if (cs_zoomed[name]==2) {
			cs_zoomed[name]=3;
			element.style.height = '820px';
		} else {
			cs_zoomed[name]=0;
			element.style.height = '120px';
		}
		cs_refresh()
	}
	function cs_resized() {
		clearTimeout(cs_resizeto);
		cs_resizeto = setTimeout(cs_refresh,250);
	}
	function cs_change_type(id,no) {
		var o;
		cs_chartid[id]=no;
		o = document.getElementById("cs_desc"+id);
		o.innerHTML = cs_idesc[no];
		cs_refresh();
	}
	function cs_add_event(obj,type,fn) {
		if (obj.addEventListener) {
			obj.addEventListener(type, fn, false);
		} else if (obj.attachEvent) {
			obj.attachEvent('on'+type, fn);
		}
	}
	cs_add_event(window,"load",cs_refresh);
	cs_add_event(window,"resize",cs_resized);
//--><!]]>
</script>""")
				out.append("""<table class="FR" cellspacing="0" cellpadding="0">""")
				out.append("""	<tr>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:cs_change_up(0);">short range</a></th>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:cs_change_up(1);">medium range</a></th>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:cs_change_up(2);">long range</a></th>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:cs_change_up(3);">very long range</a></th>""")
				out.append("""	</tr>""")
				for id,name,desc in charts:
					divclass = "CHARTDYNAMIC" if csnc else "CHARTSTATIC"
					divclick = 'onclick="cs_zoom(this)"' if csnc else ""
					out.append("""	<tr class="C2">""")
					out.append("""		<td colspan="4" style="height:124px;" valign="middle">""")
					out.append("""			<div class="%s" id="%s" %s>""" % (divclass,name,divclick))
					out.append("""				<span class="CAPTION">%s</span>""" % desc)
					out.append("""			</div>""")
					out.append("""		</td>""")
					out.append("""	</tr>""")
				out.append("""</table>""")

				out.append("""<form action="#"><table class="FR" cellspacing="0" cellpadding="0">""")
				out.append("""	<tr>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:cs_change_down(0);">short range</a></th>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:cs_change_down(1);">medium range</a></th>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:cs_change_down(2);">long range</a></th>""")
				out.append("""		<th class="RANGEBAR"><a href="javascript:cs_change_down(3);">very long range</a></th>""")
				out.append("""	</tr>""")
				for i in range(2):
					divclass = "CHARTDYNAMIC" if csnc else "CHARTSTATIC"
					divclick = 'onclick="cs_zoom(this)"' if csnc else ""
					out.append("""	<tr class="C2">""")
					out.append("""		<td colspan="4" style="height:124px;" valign="middle">""")
					out.append("""			<div class="%s" id="cs_chart%u" %s>""" % (divclass,i,divclick))
					out.append("""				<span class="CAPTION" id="cs_desc%u">%s</span>""" % (i,charts[0][2]))
					out.append("""			</div>""")
					out.append("""		</td>""")
					out.append("""	</tr>""")
					out.append("""	<tr>""")
					out.append("""		<th colspan="4">""")
					out.append("""			<select name="cschart%u" size="1" onchange="cs_change_type(%u,this.options[this.selectedIndex].value)">""" % (i,i))
					no=0
					for id,name,desc in charts:
						out.append("""				<option value="%u">%s</option>""" % (no,desc))
						no+=1
					out.append("""		</th>""")
					out.append("""	</tr>""")
				out.append("""</table></form>""")
			elif len(cchtmp)==1 and len(CCdata)>0:
				chid = 0
				for id,name,desc in charts:
					if name==CCdata:
						chid = id
				if chid==0:
					try:
						chid = int(CCdata)
					except Exception:
						pass
				if chid>0 and chid<1000:
					out.append("""<script type="text/javascript">""")
					out.append("""<!--//--><![CDATA[//><!--""")
					out.append("""	var i,j;""")
					out.append("""	var cs_range=0;""")
					out.append("""	var cs_vhosts = [%s];""" % ",".join(map(repr,[ x[0] for x in servers ])))
					out.append("""	var cs_vports = [%s];""" % ",".join(map(repr,[ x[1] for x in servers ])))
					out.append("""	var cs_inames = [%s];""" % ",".join(map(repr,[ x[2] for x in servers ])))
					out.append("""	var cs_nc = [%s];""" % ",".join(map(repr,[ x[4] for x in servers ])))
					out.append("""	var cs_chid = %u;""" % chid)
					out.append("""//--><!]]>""")
					out.append("""</script>""")
					out.append("""<script type="text/javascript">
<!--//--><![CDATA[//><!--
	var i,j;
	var cs_range=0;
	var cs_zoomed = [];
	var cs_resizeto;
	function cs_refresh() {
		var i;
		var minutes = Math.floor((new Date()).getTime()/60000);
		for (i=0 ; i<cs_inames.length ; i++) {
			var name = cs_inames[i];
			var vhost = cs_vhosts[i];
			var vport = cs_vports[i];
			var csnc = cs_nc[i];
			var id = cs_chid*10+cs_range;
			var element = document.getElementById(name);
			if (element) {
				var url;
				if (csnc) {
					var width = element.scrollWidth;
					var height = element.scrollHeight;
					url = "chart.cgi?host="+vhost+"&port="+vport+"&id="+id+"&width="+width+"&height="+height+"&antycache="+minutes;
				} else {
					url = "chart.cgi?host="+vhost+"&port="+vport+"&id="+id+"&antycache="+minutes;
				}
				if (typeof(element.cs_url)=="undefined" || element.cs_url!=url) {
					element.cs_url = url;
					element.style.backgroundImage = "url('"+url+"')";
				}
			}
		}
	}
	function cs_change(num) {
		cs_range = num;
		cs_refresh();
	}
	function cs_zoom(element) {
		var name = element.id;
		if (typeof(cs_zoomed[name])=="undefined") {
			cs_zoomed[name]=0;
		}
		if (cs_zoomed[name]==0) {
			cs_zoomed[name]=1;
			element.style.height = '220px';
		} else if (cs_zoomed[name]==1) {
			cs_zoomed[name]=2;
			element.style.height = '420px';
		} else if (cs_zoomed[name]==2) {
			cs_zoomed[name]=3;
			element.style.height = '820px';
		} else {
			cs_zoomed[name]=0;
			element.style.height = '120px';
		}
		cs_refresh();
	}
	function cs_resized() {
		clearTimeout(cs_resizeto);
		cs_resizeto = setTimeout(cs_refresh,250);
	}
	function cs_add_event(obj,type,fn) {
		if (obj.addEventListener) {
			obj.addEventListener(type, fn, false);
		} else if (obj.attachEvent) {
			obj.attachEvent('on'+type, fn);
		}
	}
	cs_add_event(window,"load",cs_refresh);
	cs_add_event(window,"resize",cs_resized);
//--><!]]>
</script>""")
					out.append("""<table class="FR" cellspacing="0" cellpadding="0">""")
					out.append("""	<tr>""")
					out.append("""		<th class="RANGEBAR"><a href="javascript:cs_change(0);">short range</a></th>""")
					out.append("""		<th class="RANGEBAR"><a href="javascript:cs_change(1);">medium range</a></th>""")
					out.append("""		<th class="RANGEBAR"><a href="javascript:cs_change(2);">long range</a></th>""")
					out.append("""		<th class="RANGEBAR"><a href="javascript:cs_change(3);">very long range</a></th>""")
					out.append("""	</tr>""")
					for cshost,csport,name,desc,csnc in servers:
						divclass = "CHARTDYNAMIC" if csnc else "CHARTSTATICMIXED" if mixedservers==3 else "CHARTSTATIC"
						divclick = 'onclick="cs_zoom(this)"' if csnc else ""
						out.append("""	<tr class="C2">""")
						out.append("""		<td colspan="4" style="height:124px;" valign="middle">""")
						out.append("""			<div class="%s" id="%s" %s>""" % (divclass,name,divclick))
						out.append("""				<span class="CAPTION">%s</span>""" % desc)
						out.append("""			</div>""")
						out.append("""		</td>""")
						out.append("""	</tr>""")
					out.append("""</table>""")
		else:
			if masterconn.version_at_least(2,0,15):
				if ttymode:
					tab = Tabble("Chunkserver chart data",len(CCchdata)+1,"r")
					hdrstr = ["host/port ->"]
					for host,port,no,mode,desc,raw in CCchdata:
						hdrstr.append("%s:%s" % (host,port))
					tab.header(*hdrstr)
					tab.header(("---","",len(CCchdata)+1))
					hdrstr = ["Time"]
					for host,port,no,mode,desc,raw in CCchdata:
						if raw:
							if mode==0:
								hdrstr.append("%s (+)" % desc)
							else:
								hdrstr.append("%s (raw)" % desc)
						else:
							hdrstr.append(desc)
					tab.header(*hdrstr)
				else:
					tab = Tabble("Chunkserver chart data",len(CCchdata)+1)
				chrange = CCrange
				if chrange<0 or chrange>3:
					chrange = 0
				if CCcount<0 or CCcount>4095:
					CCcount = 4095
				chrangestep = [60,360,1800,86400][chrange]
				series = set()
				for host,port,no,mode,desc,raw in CCchdata:
					if no==100:
						series.add((host,port,0))
						series.add((host,port,1))
					else:
						series.add((host,port,no))
				for gpass in (1,2):
					CCresult = {}
					timestamp = 0
					entries = 0
					repeat = 0
					for host,port,x in series:
						conn = MFSConn(host,port)
						data,length = conn.command(CLTOAN_CHART_DATA,ANTOCL_CHART_DATA,struct.pack(">LL",x*10+chrange,CCcount))
						if length>=8:
							ts,e = struct.unpack(">LL",data[:8])
							if e*8+8==length and (entries==0 or entries==e):
								entries = e
								if timestamp==0 or timestamp==ts or gpass==2:
									timestamp=ts
									CCresult[(host,port,x)] = list(struct.unpack(">"+e*"Q",data[8:]))
								else:
									repeat = 1
									break
							else:
								CCresult[(host,port,x)]=None
						else:
							CCresult[(host,port,x)]=None
					if repeat:
						continue
					else:
						break
				for e in xrange(entries):
					ts = timestamp-chrangestep*e
					timestring = time.strftime("%Y-%m-%d %H:%M",time.gmtime(ts))
					dline = [timestring]
					for host,port,no,mode,desc,raw in CCchdata:
						if no==100:
							datalist1 = CCresult[(host,port,0)]
							datalist2 = CCresult[(host,port,1)]
							if (datalist1!=None and datalist2!=None):
								data = datalist1[e]+datalist2[e]
							else:
								data = None
						else:
							datalist = CCresult[(host,port,no)]
							if datalist!=None:
								data = datalist[e]
							else:
								data = None
						if data==None:
							dline.append("-")
						elif mode==0:
							cpu = (data/(10000.0*chrangestep))
							if raw:
								dline.append("%.8f%%" % (cpu))
							else:
								dline.append("%.2f%%" % (cpu))
						elif mode==1:
							if raw:
								dline.append("%u" % data)
							else:
								data = float(data)/float(chrangestep)
								dline.append("%.3f/s" % data)
						elif mode==2:
							if raw:
								dline.append("%u" % data)
							else:
								dline.append("%s" % humanize_number(data," "))
						elif mode==3:
							dline.append("%u threads" % data)
						elif mode==4:
							if raw:
								dline.append("%u" % data)
							else:
								data = float(data)/float(chrangestep)
								data /= 10000000.0
								dline.append("%.2f%%" % (data))
						elif mode==5:
							if raw:
								dline.append("%u" % data)
							else:
								data = float(data)/float(chrangestep)
								dline.append("%.3fMB/s" % (data/(1024.0*1024.0)))
					tab.append(*dline)
			else:
				tab = Tabble("Chunkserver chart data are not supported in your version of MFS - please upgrade",1,"r")
		if cgimode:
			print("\n".join(out))
		else:
			print(myunicode(tab))
	except Exception:
		print_exception()

if cgimode:
	print("""</div> <!-- end of container -->""")

	print("""</body>""")
	print("""</html>""")
