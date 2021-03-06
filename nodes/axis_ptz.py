#!/usr/bin/env python
#
# Basic PTZ node, based on documentation here:
#   http://www.axis.com/files/manuals/vapix_ptz_45621_en_1112.pdf
#

import os, sys, string, time, getopt, threading
import httplib, urllib, base64

import roslib; roslib.load_manifest('axis_camera') 
import rospy 

from axis_camera.msg import Axis


class StateThread(threading.Thread):
  def __init__(self, axis):
    threading.Thread.__init__(self)

    self.axis = axis
    self.daemon = True

  def run(self):
    r = rospy.Rate(10)
    msg = Axis()

    while True:
      url = '%s:%s@%s' % (self.axis.username, self.axis.password, self.axis.hostname)
      auth = base64.encodestring("%s:%s" % (self.axis.username, self.axis.password))
      headers = {"Authorization" : "Basic %s" % auth}
      conn = httplib.HTTPConnection(self.axis.hostname)
      params = { 'query':'position' }
      conn.request("GET", "/axis-cgi/com/ptz.cgi?query=position",headers=headers) #, urllib.urlencode(params)
      response = conn.getresponse()
      #print(response.status)
      if response.status == 200:
        body = response.read()
        params = dict([s.split('=',2) for s in body.splitlines()])
        msg.pan = float(params['pan'])
        # Flip pan orient if the camera is mounted backwards and facing down
        if self.axis.flip:
            msg.pan = 180 - msg.pan
            if msg.pan > 180:
                msg.pan -= 360
            if msg.pan < -180:
                msg.pan += 360
        msg.tilt = float(params['tilt'])
        msg.zoom = float(params['zoom'])
        msg.iris = float(params['iris'])
        msg.focus = 0.0
        if 'focus' in params:
          msg.focus = float(params['focus'])
        msg.autofocus = (params['autofocus'] == 'on')
        self.axis.pub.publish(msg)
      r.sleep()
      

class AxisPTZ:
  def __init__(self, hostname, username, password, flip):
    self.hostname = hostname
    self.username = username
    self.password = password
    self.flip = flip

    self.st = None
    self.pub = rospy.Publisher("state", Axis, self)
    self.sub = rospy.Subscriber("cmd", Axis, self.cmd)

  def peer_subscribe(self, topic_name, topic_publish, peer_publish):
    # Lazy-start the state publisher.
    if self.st is None:
      self.st = StateThread(self)
      self.st.start()

  def cmd(self, msg):
    auth = base64.encodestring("%s:%s" % (self.username, self.password))
    headers = {"Authorization" : "Basic %s" % auth}
    
    conn = httplib.HTTPConnection(self.hostname)
    # Flip pan orient if the camera is mounted backwards and facing down
    if self.flip:
    	msg.pan = 180 - msg.pan
        if msg.pan > 180:
	    msg.pan -= 360
        if msg.pan < -180:
	    msg.pan += 360
    params = { 'pan': msg.pan, 'tilt': msg.tilt, 'zoom': msg.zoom, 'brightness': msg.brightness }
    if msg.autofocus:
      params['autofocus'] = 'on'
    else:
      params['autofocus'] = 'off'
      params['focus'] = msg.focus
    if msg.iris > 0.000001:
      rospy.logwarn("Iris value is read-only.")
    conn.request("GET", "/axis-cgi/com/ptz.cgi?%s" % urllib.urlencode(params),headers=headers)


def main():
  rospy.init_node("axis")

  arg_defaults = {
      'hostname': '192.168.0.64',
      'username': 'root',
      'password': 'drrobot',
      'flip': True,
      }
  args = {}
  for name in arg_defaults:
    args[name] = rospy.get_param(rospy.search_param(name), arg_defaults[name])

  AxisPTZ(**args)
  rospy.spin()


if __name__ == "__main__":
  main()
