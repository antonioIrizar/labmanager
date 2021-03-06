# -*-*- encoding: utf-8 -*-*-
# 
# gateway4labs is free software: you can redistribute it and/or modify
# it under the terms of the BSD 2-Clause License
# gateway4labs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

import sys
import json
import urllib2

import requests

from flask.ext.wtf import TextField, Required, URL, PasswordField

from labmanager.forms import AddForm, RetrospectiveForm, GenericPermissionForm
from labmanager.rlms import register, Laboratory, BaseRLMS, BaseFormCreator, Versions

def get_module(version):
    return sys.modules[__name__]

class HttpAddForm(AddForm):

    base_url = TextField("Base URL",    validators = [Required(), URL(False) ])
    login    = TextField("Login",    validators = [Required() ])
    password = PasswordField("Password",    validators = [])

    def __init__(self, add_or_edit, *args, **kwargs):
        super(HttpAddForm, self).__init__(*args, **kwargs)

    @staticmethod
    def process_configuration(old_configuration, new_configuration):
        return new_configuration

class HttpPermissionForm(RetrospectiveForm):
    pass

class HttpLmsPermissionForm(HttpPermissionForm, GenericPermissionForm):
    pass

class HttpFormCreator(BaseFormCreator):

    def get_add_form(self):
        return HttpAddForm

    def get_permission_form(self):
        return HttpPermissionForm

    def get_lms_permission_form(self):
        return HttpLmsPermissionForm

FORM_CREATOR = HttpFormCreator()

class RLMS(BaseRLMS):

    def __init__(self, configuration):
        self.configuration = configuration

        config = json.loads(configuration or '{}')
        self.base_url = config.get('base_url')
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]

        self.login    = config.get('login')
        self.password = config.get('password')
        self.context_id = str(config.get('context_id', ''))

        if not self.base_url or not self.login or not self.password:
            raise Exception("Laboratory misconfigured: fields missing" )

    def _request(self, remaining, headers = {}):
        if '?' in remaining:
            context_remaining = remaining + '&context_id=' + self.context_id
        else:
            context_remaining = remaining + '?context_id=' + self.context_id
        r = requests.get('%s%s' % (self.base_url, context_remaining), auth = (self.login, self.password), headers = headers)
        r.raise_for_status()
        return r.json()

    def _request_post(self, remaining, data, headers = None):
        if headers is None:
            headers = {}
        if '?' in remaining:
            context_remaining = remaining + '&context_id=' + self.context_id
        else:
            context_remaining = remaining + '?context_id=' + self.context_id

        headers['Content-Type'] = 'application/json'
        r = requests.post('%s%s' % (self.base_url, context_remaining), data = json.dumps(data), auth = (self.login, self.password), headers = headers)
        return r.json()

    def get_version(self):
        return Versions.VERSION_1

    def get_capabilities(self):
        capabilities = self._request('/capabilities')
        return capabilities['capabilities']

    def setup(self, back_url):
        setup_url = self._request('/setup?back_url=%s' % back_url)
        return setup_url['url']

    def test(self):
        response = self._request('/test_plugin')
        valid = response.get('valid', False)
        if not valid:
            return response.get('error_messages', ['Invalid error message'])

    def get_laboratories(self, **kwargs):
        labs = self._request('/labs')['labs']
        laboratories = []
        for lab in labs:
            laboratory = Laboratory(name = lab['name'], laboratory_id = lab['laboratory_id'], description = lab.get('description'), autoload = lab.get('autoload'))
            laboratories.append(laboratory)
        return laboratories

    def reserve(self, laboratory_id, username, institution, general_configuration_str, particular_configurations, request_payload, user_properties, *args, **kwargs):
        request = {
            'laboratory_id' :  laboratory_id,
            'username'    : username,
            'institution' : institution,
            'general_configuration_str' : general_configuration_str,
            'particular_configurations' : particular_configurations,
            'request_payload' : request_payload,
            'user_properties' : user_properties,
        }
        request.update(kwargs)
        response = self._request_post('/reserve', request)
        return {
            'reservation_id' : response['reservation_id'],
            'load_url' : response['load_url']
        }

    def load_widget(self, reservation_id, widget_name, **kwargs):
        response = self._request('/widget?widget_name=%s' % widget_name, headers = { 'X-G4L-reservation-id' : reservation_id })
        return {
            'url' : response['url']
        }

    def list_widgets(self, laboratory_id, **kwargs):
        widgets_json = self._request('/widgets?laboratory_id=%s' % urllib2.quote(laboratory_id))
        widgets = []
        for widget_json in widgets_json['widgets']:
            widget = {
                'name' : widget_json['name'],
                'description' : widget_json.get('description',''),
            }
            widgets.append(widget)

        return widgets

PLUGIN_NAME = "HTTP plug-in"
PLUGIN_VERSIONS = ['1.0']

register(PLUGIN_NAME, PLUGIN_VERSIONS, __name__)

