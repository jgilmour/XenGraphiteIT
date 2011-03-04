#!/usr/bin/python

import XenAPI
import string
import time
import os
import ConfigParser
import sys
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

def sendDataToCarbon(name, data):
  """
  sendDataToCarbon(name, data)
  takes in data passed as a name, and associated data
  calculates time as of now
  appends all data to a list and then sends to carbon/graphite
  """
  timeNow = getTime()
  print "The time is: %d" % timeNow

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

  sendDataToCarbon(sr_name_label,bytesToGB(sr_phys_util))

  print 'total vms: %s \nname: %s \nphysical util: %dGB \nphys size: %dGB' % \
      (running_vm_total, sr_name_label, bytesToGB(sr_phys_util), bytesToGB(sr_phys_size))

if __name__ == '__main__':

  # CONFIG_FILE should be changed if configuration file resides \
  #   in another directory

  CONFIG_FILE = (os.getcwd() + "/.config")
  config = ConfigParser.ConfigParser()
  config.read([CONFIG_FILE])

  url = config.get('XENAPI', 'URL')
  username =  config.get('XENAPI', 'USERNAME')
  password =  config.get('XENAPI', 'PASSWORD')
  session = XenAPI.Session(url)

  try:
    session.xenapi.login_with_password(username, password)
  except:
    errorAndExit("Couldn't connect to host, are username/password/url correct?")

  grabXenData(session, config)
