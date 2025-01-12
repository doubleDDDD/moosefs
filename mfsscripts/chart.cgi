#!/usr/bin/env python3

import socket
import struct
import cgi
import cgitb; cgitb.enable()
import sys

PROTO_BASE = 0

CUTOAN_CHART = (PROTO_BASE+504)
ANTOCU_CHART = (PROTO_BASE+505)

fields = cgi.FieldStorage()

if "host" in fields:
	host = fields.getvalue("host")
else:
	host = ''
if "port" in fields:
	try:
		port = int(fields.getvalue("port"))
	except ValueError:
		port = 0
else:
	port = 0
if "id" in fields:
	try:
		chartid = int(fields.getvalue("id"))
	except ValueError:
		chartid = -1
else:
	chartid = -1
if "width" in fields and "height" in fields:
	try:
		width = int(fields.getvalue("width"))
		height = int(fields.getvalue("height"))
	except ValueError:
		width = 0
		height = 0
else:
	width = 0
	height = 0

def mysend(socket,msg):
	totalsent = 0
	while totalsent < len(msg):
		sent = socket.send(msg[totalsent:])
		if sent == 0:
			raise RuntimeError("socket connection broken")
		totalsent = totalsent + sent

def myrecv(socket,leng):
	if sys.version<'3':
		msg = ''
	else:
		msg = bytes(0)
	while len(msg) < leng:
		chunk = socket.recv(leng-len(msg))
		if len(chunk) == 0:
			raise RuntimeError("socket connection broken")
		msg = msg + chunk
	return msg

def senderr():
	print("Content-Type: image/gif")
	print("")
	sys.stdout.flush()
	f = open('err.gif','rb')
	if sys.version >= '3':
		sys.stdout.buffer.write(f.read())
	else:
		sys.stdout.write(f.read())
	f.close()

if host=='' or port==0 or chartid<0:
	senderr()
else:
	try:
		s = socket.socket()
		s.connect((host,port))
		if width==0 and height==0:
			mysend(s,struct.pack(">LLL",CUTOAN_CHART,4,chartid))
		else:
			mysend(s,struct.pack(">LLLHH",CUTOAN_CHART,8,chartid,width,height))
		header = myrecv(s,8)
		cmd,length = struct.unpack(">LL",header)
		if cmd==ANTOCU_CHART and length>0:
			data = myrecv(s,length)
			if sys.version < '3':
				if data[:3]=="GIF":
					print("Content-Type: image/gif")
					print("")
					sys.stdout.flush()
					sys.stdout.write(data)
				elif data[:8]=="\x89PNG\x0d\x0a\x1a\x0a":
					print("Content-Type: image/png")
					print("")
					sys.stdout.flush()
					sys.stdout.write(data)
				else:
					senderr()
			else:
				if data[:3]=="GIF".encode("latin-1"):
					print("Content-Type: image/gif")
					print("")
					sys.stdout.flush()
					sys.stdout.buffer.write(data)
				elif data[:8]=="\x89PNG\x0d\x0a\x1a\x0a".encode("latin-1"):
					print("Content-Type: image/png")
					print("")
					sys.stdout.flush()
					sys.stdout.buffer.write(data)
				else:
					senderr()
		else:
			senderr()
		s.close()
	except Exception:
		senderr()
