import os,shutil
from flask import render_template, make_response, request, Flask
from flask_restful import Api
from flask_pymongo import PyMongo
from bson.json_util import dumps

basedir = os.path.abspath(os.path.dirname(__file__))

    shutil.copyfile(srcfile,dstfile)    

#try:
#   from flask_cache import Cache
#except:
srcfile=os.path.join(basedir,"jinja2ext.py")
distfile="/app/.heroku/python/lib/python3.6/site-packages/flask_cache/jinja2ext.py"
#distfile="/home/vasp/.pyenv/versions/mpt_a3/lib/python3.6/site-packages/flask_cache/jinja2ext.py"
print(srcfile)
print(distfile)
shutil.copyfile(srcfile,dstfile)    
from flask_cache import Cache

MONGO_URL = os.environ.get('MONGO_URL')
if not MONGO_URL:
    MONGO_URL = "mongodb://localhost:27017/restfulapi";


UPLOAD_FOLDER='upload'
CACHE_TYPE = 'simple'
DATA_FOLDER = 'data'
print(basedir)
ALLOWED_EXTENSIONS = set(['json','yaml','vasp','cif','lammps'])


app = Flask(__name__)
cache = Cache(app,config={'CACHE_TYPE': CACHE_TYPE})
cache.init_app(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DATA_FOLDER'] = DATA_FOLDER
app.config['MONGO_URI'] = MONGO_URL
mongo = PyMongo(app)
#print(mongo)
#print(dir(mongo))
#print(mongo.db.items.find_one())
#print(dir(mongo.db))

def output_json(obj, code, headers=None):
    resp = make_response(dumps(obj), code)
    resp.headers.extend(headers or {})
    return resp

DEFAULT_REPRESENTATIONS = {'application/json': output_json}
api = Api(app)
#api = restful.Api(app)
api.representations = DEFAULT_REPRESENTATIONS

import flask_rest_service.resources
