#!/usr/bin/env python
from bottle import *
import bottle_mysql
import os
import config

import httplib2
from apiclient.discovery import build
from oauth2client import client

from update_google_fit import get_fit_data

app = Bottle()
# dbhost is optional, default is localhost
plugin = bottle_mysql.Plugin(dbhost=config.dbhost, dbuser=config.dbuser, dbpass=config.dbpass, dbname=config.dbname)
app.install(plugin)

@app.get('/')
def default_get(db):
  name = request.query.get('state', '')
  if not name:  
    return static_file("index.html", ".")
  p = request.urlparts
  redirect_uri = "{}://{}".format(p.scheme, p.netloc)
  flow = client.flow_from_clientsecrets(
    'client_secret.json',
    scope=["profile", "email", 'https://www.googleapis.com/auth/fitness.activity.read'],
    redirect_uri=redirect_uri)
  if 'code' not in request.query:
    auth_uri = flow.step1_get_authorize_url(state=name)
    redirect(auth_uri)
  else:
    creds = flow.step2_exchange(code=request.query.code)
    http_auth = creds.authorize(httplib2.Http())
    user_info_service = build('oauth2', 'v2', http=http_auth)
    u = user_info_service.userinfo().get().execute()
    db.execute("REPLACE INTO google_fit SET username=%s, google_id=%s, full_name=%s, gender=%s, image_url=%s, email=%s, refresh_token=%s", (name, u['id'], u['name'], u['gender'], u['picture'], u['email'], creds.refresh_token))
    print("Inserted", u)
    return get_fit_data(http_auth)

@app.get('/steps_for_user/<name>')
def steps_for_user(name, db):
  print(name)
  db.execute("SELECT day, steps FROM steps WHERE username=%s", (name,))
  result = dict([(r['day'], r['steps']) for r in db.fetchall()])
  print(result)
  return result

port = int(os.environ.get('PORT', 8080))

if __name__ == "__main__":
  try:
    try:
      app.run(host='0.0.0.0', port=port, debug=True, server='gunicorn', workers=8)
    except ImportError:
      app.run(host='0.0.0.0', port=port, debug=True)
  except Exception as e:
    logger.error(e)
    sys.stdin.readline()