#!/usr/bin/python

import XenAPI
import string, time, os, ConfigParser, sys, re
from socket import socket

def bytesToGB(num):
  """
  bytesToGB(num)
  takes in data in bytes as the variable num
  converts the bytes to GB and assigns to outputGB
  outputGB is returned (1073741824 bytes = 1GB)
  """
  outputGB = float (num / 1073741824)
  return outputGB

def sendDataToCarbon(config, name, data):
  """
  sendDataToCarbon(name, data)
  takes in data passed as a name, and associated data
  calculates time as of now
  appends all data to a list and then sends to carbon/graphite
  """
  timeNow = getTime()
  
  cs = str(config.get('GRAPHITE','CARBON_HOST'))
  cp = int(config.get('GRAPHITE','CARBON_PORT'))
  sock = socket() 
  try:
    sock.connect((cs, cp))
  except:
    errorAndExit("Can't connect to CARBON")
    sys.exit(1)

  message = "%s %d %d\n" % (name, data, timeNow)
  sock.sendall(message)
  print "%s %d %d" % (name, data, timeNow)
  
def getTime():
  """
  Just getting the time and returning it as 'timeNow'
  """
  timeNow = int ( time.time() )
  return timeNow

def errorAndExit(message):
  print "ERROR: Something went wrong! -", message
  exit(1)

def grabXenData(session, config):
  """
  takes in the xen api session and config
  retrieves information:
    storage repository stats, # of vm's, memory stats
  sends data along with a name over to sendDataToCarbon
  """
  # get vm information and count # of total vm's
  # exclude powered-off VMs and XenServer hosts
  # todo: figure out a faster way to get count total

  sr_uuid =  config.get('XENAPI', 'SR-UUID')
  count = 1

  try:
    vms = session.xenapi.VM.get_all()
  except:
    errorAndExit("Couldn't retrieve all VM's")
  for vm in vms:
    record = session.xenapi.VM.get_record(vm)
    if (record["power_state"] == "Running") and not (record["is_control_domain"]):
      count += 1
  running_vm_total = count

  # get storage repository information
  # retrieve name, utilisation, and physical size

  try:
    sr = session.xenapi.SR.get_by_uuid(sr_uuid)
  except:
    errorAndExit("Couldn't retrieve storage repository information")
  sr_name_label = string.lower(string.join(session.xenapi.SR.\
      get_name_label(sr).split(),""))
  sr_phys_util = float(session.xenapi.SR.get_physical_utilisation(sr))
  sr_phys_size = float(session.xenapi.SR.get_physical_size(sr))

  hostname = parseHostname((config.get('XENAPI', 'URL')))

  gp = config.get('GRAPHITE', 'CARBON_NAME')

  sendDataToCarbon(config, (gp + hostname + '.sr.' + sr_name_label + '.space.used'), bytesToGB(sr_phys_util))
  sendDataToCarbon(config, (gp + hostname + '.sr.' + sr_name_label + '.space.total'), bytesToGB(sr_phys_size))  
  sendDataToCarbon(config, (gp + hostname + '.vm.total'), running_vm_total)
  
def parseHostname(hostname):
  """
  strip out the http:// https:// and trailing /
  split hostname into .'s and get the first entry which is the hostname
  """
  hostname = re.sub('http:\/\/|https://\/\/|\/', '', hostname)
  hostname = hostname.split(".")
  return str(hostname[0])

if __name__ == '__main__':

  # CONFIG_FILE should be changed if configuration file resides \
  #   in another directory

  CONFIG_FILE = (os.getcwd() + "/.config")
  config = ConfigParser.ConfigParser()
  config.read([CONFIG_FILE])
  
  delay = 60

  url = config.get('XENAPI', 'URL')
  username =  config.get('XENAPI', 'USERNAME')
  password =  config.get('XENAPI', 'PASSWORD')
  while True:
    session = XenAPI.Session(url)

    try:
      session.xenapi.login_with_password(username, password)
    except:
      errorAndExit("Couldn't connect to host, are username/password/url correct?")

    grabXenData(session, config)
    time.sleep(delay)
