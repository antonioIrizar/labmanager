from flask import Flask, session
from flask.ext.testing import TestCase
from labmanager import app
from labmanager.sample_data import add_sample_users
from labmanager.db import db

class G4lTestCase(TestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True

    def create_app(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['TESTING'] = True
        return app

    def setUp(self):
        add_sample_users(silence = True)

    def tearDown(self):
        db.drop_all()
        db.session.remove()
