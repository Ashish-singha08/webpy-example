#!/usr/bin/python

import os
import sys
import json
import time
import base64
import getopt
import oauth2
import urllib
import urllib2
import datetime
import cookielib

BASE_URL = 'http://localhost/webpy-example/'
COOKIE_FILE = '.cookies'

KEY    = 'rGgkUYhqjNEtwZdhnnLZoBkXkdKCPJmI'
SECRET = 'OSdTYJAeQJLLOHlOdmatRvEdBcuxuKGD'

HEADERS = {
  'User-Agent'    : 'Python-urllib/2.6 Tony Edition',
  'Accept'        : 'application/json',
}

LOGIN_URL  = BASE_URL + 'login/rest'
LOGOUT_URL = BASE_URL + 'logout'

def generate_oauth_request( method, url, parameters={} ):

  # Generate our Consumer object
  consumer = oauth2.Consumer( key = KEY, secret = SECRET )

  # Add parameters required by OAuth
  parameters['oauth_version']      = "1.0"
  parameters['oauth_nonce']        = oauth2.generate_nonce()
  parameters['oauth_timestamp']    = int(time.time())
  parameters['oauth_consumer_key'] = consumer.key

  # Generate and sign the request
  req = oauth2.Request( method = method, url = url, parameters = parameters )
  signature_method = oauth2.SignatureMethod_HMAC_SHA1()
  req.sign_request( signature_method, consumer, None )

  return req

def load_cookies():
  cj = cookielib.LWPCookieJar( COOKIE_FILE )
  if os.path.isfile( COOKIE_FILE ):
    cj.load( ignore_discard=True )
  opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( cj ) )
  urllib2.install_opener( opener )
  return cj

def login( account_info ):
  cj = load_cookies()
  parameters = {
    "username" : account_info['username'],
    "password" : account_info['password'],
    "format" : "json"
  }
  oauth = generate_oauth_request( 'POST', LOGIN_URL, parameters )
  req = urllib2.Request( LOGIN_URL, oauth.to_postdata(), headers = HEADERS )
  result = urllib2.urlopen( req ).read()
  cj.save( ignore_discard=True ) 
  json_result = json.loads( result )
  return json_result

def logout():
  cj = load_cookies()
  req = urllib2.Request( LOGOUT_URL, headers = HEADERS )
  result = urllib2.urlopen( req ).read()
  cj.clear() 
  cj.save()

# End
