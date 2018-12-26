import json
from flask import request, abort
#from flask.ext import restful
from flask_restful import Api, Resource
#from flask.ext.restful import reqparse
from flask_restful import reqparse
from flask_rest_service import app, api, mongo
from bson.objectid import ObjectId

class ReadingList(Resource):
    def __init__(self, *args, **kwargs):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('reading', type=str)
        super(ReadingList, self).__init__()

    def get(self):
        return  [x for x in mongo.db.items.find()]

    def post(self):
        args = self.parser.parse_args()
        if not args['reading']:
            abort(400)

        jo = json.loads(args['reading'])
        reading_id =  mongo.db.items.insert(jo)
        return mongo.db.items.find_one({"_id": reading_id})


class Reading(Resource):
    def get(self, reading_id):
        return mongo.db.items.find_one_or_404({"_id": reading_id})

    def delete(self, reading_id):
        mongo.db.items.find_one_or_404({"_id": reading_id})
        mongo.db.items.remove({"_id": reading_id})
        return '', 204


class Root(Resource):
    def get(self):
        return {
            'status': 'OK',
            'mongo': str(mongo.db),
        }

api.add_resource(Root, '/')
api.add_resource(ReadingList, '/items/')
api.add_resource(Reading, '/items/<ObjectId:reading_id>')
