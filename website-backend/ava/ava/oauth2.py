
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect

from urlparse import parse_qsl # Python3: from urllib.parse import parse_qs
import urllib2
import json
import jwt

from rest_framework_jwt.settings import api_settings

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

class OAuth2Backend:
   
    def authenticate(self, request, token=None):

        # If necessary, payload should have been validated 
        unverified_payload = jwt.decode(token, None, False, algorithms=['HS256'])

        # Field Validation
        if not unverified_payload.get('email_verified'):
            return None

        # find user with same email address
        try:
            user = User.objects.get(email=unverified_payload.get('email'))
            return user
        except:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None            

def get_oauth2(request):

    # https://developers.google.com/identity/protocols/OpenIDConnect

    AUTH_ENDPOINT = 'https://www.googleapis.com/oauth2/v4/token'
    AUTH_CLIENT_ID = settings.OAUTH2_CLIENT_ID
    AUTH_CLIENT_SECRET = settings.OAUTH2_CLIENT_SECRET
    AUTH_REDIRECT_URI = settings.OAUTH2_REDIRECT_URI

    if not AUTH_CLIENT_ID or not AUTH_CLIENT_SECRET or not AUTH_REDIRECT_URI:
        return HttpResponse('OAuth2 not configured in settings', status=401)

    get_code = request.GET.get('code')
    get_prompt = request.GET.get('prompt')
    get_state = request.GET.get('state')
    get_session_state = request.GET.get('session_state')
    get_scope = request.GET.get('scope')

    if not get_state:
        return HttpResponse('Missing query string', status=401)

    state = dict(parse_qsl(get_state))

    # 3. Confirm anti-forgery state token
    security_token = state.get('security_token')
    # TODO Confirm anti-forgery state token in state.get('security_token'), if there is a problem, return 401

    # 4. Exchange code for access token and ID token
    body = '&'.join([
        'code='+get_code,
        'client_id='+AUTH_CLIENT_ID,
        'client_secret='+AUTH_CLIENT_SECRET,
        'redirect_uri=' + AUTH_REDIRECT_URI,
        'grant_type=authorization_code'
    ])
    result = urllib2.urlopen(AUTH_ENDPOINT, data=body, timeout=2).read()
    result_dict = json.loads(result)

    # 5. Obtain user information from the ID token
    access_token = result_dict.get('access_token')
    id_token = result_dict.get('id_token') # JWT signed by Google

    # Documentation from Google states that it is not necessary to validate signature of the JWT token as it was recieved directly from Google

    # Find existing user in database
    try:
        user = authenticate(request=request, token=id_token)
        if not user:
            raise Exception('Authentication Failed')
    except:
        # User does not exist, need to create a new user, if valid
        logout(request)
        return HttpResponse('User does not exist', status=401)

    # Login the user in Django
    login(request, user, backend='ava.oauth2.OAuth2Backend')

    # Redirect user
    redirect_url = state.get('url')
    if state.get('anchor'):
        redirect_url = redirect_url + '#' + state.get('anchor')
    
    # Generate new JWT Token for this user
    payload = jwt_payload_handler(user)
    token = jwt_encode_handler(payload)

    redirect_url = redirect_url + '?token='+token+'&userid='+ user.username
    return redirect(redirect_url)
