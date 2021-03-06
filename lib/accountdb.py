#!/usr/bin/python

import os
import sys
import web
import time

from credentials import Credentials

from passlib.apps import custom_app_context as pwd_context

import wputil

log = wputil.Log('accountdb')

INFO_BLACKLIST = [ 'username', 'password', 'password2', 'submit', 'cancel',
                   'oauth_body_hash', 'oauth_nonce', 'oauth_timestamp',
                   'oauth_consumer_key', 'oauth_signature_method', 'oauth_version',
                   'oauth_signature' ]

class AccountDB(object):
  """
  AccountDB() - abstracts the database access away for accounts
  """

  def __init__( self ):
    """
    The database credentials are stored in the Credentials class which is generated
    by the dbconfig-common package via debconf.
    """
    log.loggit( 'AccountDB()' )
    self.db = web.database(
      dbn  = 'postgres',
      db   = Credentials.dbdefault,
      user = Credentials.dbuser,
      pw   = Credentials.dbpassword
    )


  def _set_account_info( self, account, data ):
    """
    @param account is a result from accounts
    @param data is the data for account_info
    @returns a dict of the account with its associated info
    """
    log.loggit( 'AccountDB._set_account_info()' )
    for key,val in data.iteritems():
      if key not in INFO_BLACKLIST:
        result = self.db.delete( 'account_info',
                                 where='username = $username and key = $key',
                                 vars = { 'username' : account['username'], 'key' : key } )
        account[key] = val
        info = { 'username': account['username'],
                 'key': key,
                 'value': val }
        tmp_id = self.db.insert( 'account_info', **info )
    return account


  def _get_account_info( self, account ):
    """
    @param account is a result from the database
    @returns a dict of the account with its associated info
    """
    log.loggit( 'AccountDB._get_account_info()' )
    res = self.db.select(
      'account_info',
      where = 'username = $username',
      vars = dict( username = account['username'] )
    )
    for info in res:
      account[ info['key'] ] = info['value']
    return account


  def create_account( self, data ):
    """
    @param data is a Storage (or Dict)
    """
    log.loggit( 'AccountDB.create_account()' )
    account = {}
    account['username'] = data['username']
    account['password'] = pwd_context.encrypt( data['password'] )
    account['id'] = self.db.insert( 'accounts', **account )
    return self._set_account_info( account, data )


  def review_accounts( self ):
    """
    @returns a list of Storage elements from the database
    """
    log.loggit( 'AccountDB.review_accounts()' )
    res = self.db.select( 'accounts', order = 'id ASC' )
    accounts = []
    for a in res:
      accounts.append( self._get_account_info( a ) )
    return accounts


  def review_account( self, username ):
    """
    @param username is the username of the account
    @returns a single record from the database as a Storage object
    """
    log.loggit( 'AccountDB.review_account()' )
    res = self.db.select(
      'accounts',
      where = 'username = $username',
      limit = 1,
      vars = dict( username = username )
    )
    if not res:
      return False
    return self._get_account_info( res[0] )


  def review_account_using_info( self, key, value ):
    """
    @param key is the content in an account_info 'key' string
    @param value is the content in an account_info 'value' string
    @returns a single record from the database as a Storage object
    """
    res = self.db.select(
      'accounts',
      where = 'username = ( select username from account_info where key=$key and value=$value )',
      limit = 1,
      vars = dict( key = key, value = value )
    )
    if not res:
      return False
    return self._get_account_info( res[0] )


  def update_account( self, data ):
    """
    @param data is a Storage (or Dict)
    """
    log.loggit( 'AccountDB.set_account()' )
    account = {}
    account['id'] = data['id']
    account['username'] = data['username']
    # Leave password alone if it is not set from the form or is already
    # a valid password hash string
    if data['password'] and not pwd_context.identify( data['password'] ):
      account['password'] = pwd_context.encrypt( data['password'] )
    # If we rename the account, we need to update the account_info table
    old_account = self.db.select( 'accounts', where = 'id = $id', vars = dict( id = data['id'] ) )[0]
    if old_account['username'] != account['username']:
      result = self.db.update( 'account_info',
                               where='username = $username',
                               vars = dict( username = old_account['username'] ),
                               username = account['username'] )
    # Update the accounts database and then update the extra info
    result = self.db.update( 'accounts', where='id = $id', vars = dict( id = account['id'] ), **account )
    return self._set_account_info( account, data )

  
  def delete_account( self, username ):
    """
    @param account_id is the record id of the account to be deleted
    """
    log.loggit( 'AccountDB.delete_account()' )
    result = self.db.delete('account_info', where='username = $username', vars = dict( username = username ) )
    result = self.db.delete('accounts', where='username = $username', vars = dict( username = username ) )
    return True


  def login( self, username, password, session_login=True ):
    """
    @param username is the username of an account
    @param password is the password of an account
    @returns a single record from the database as a Storage object
    """
    log.loggit( 'AccountDB.login()' )
    # Try to login
    account = self.review_account( username )
    if not account:
      return False
    if not pwd_context.verify( password, account['password'] ):
      return False

    account = wputil.clean_account( account )
    if session_login:
      # Update the account information
      data = {}
      data['last_ip'] = web.ctx.ip
      data['last_login'] = str(int(time.time()))
      account = self._set_account_info( account, data )

      # Put account information in session key
      for key,value in account.items():
        value = str(value)
        web.ctx.session[ key ] = ( value[:50] + '...' ) if len(value) > 50 else value

    return account

# End
