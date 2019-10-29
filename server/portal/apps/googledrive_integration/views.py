import google_auth_oauthlib.flow
import requests
import os
from django.db import IntegrityError
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import (HttpResponse, HttpResponseRedirect, HttpResponseBadRequest,
                         Http404)
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.shortcuts import render
from portal.apps.googledrive_integration.models import GoogleDriveUserToken
from portal.apps.googledrive_integration.tasks import check_connection

import logging
logger = logging.getLogger(__name__)

def get_client_config():
    if 'google-drive' not in settings.EXTERNAL_RESOURCE_SECRETS:
        raise Exception("Google Drive not configured")
    googledrive_secrets = settings.EXTERNAL_RESOURCE_SECRETS['google-drive']
    CLIENT_CONFIG = {'web': {
        "client_id": googledrive_secrets['client_id'],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://accounts.google.com/o/oauth2/token",
        "client_secret": googledrive_secrets['client_secret']
    }}
    return CLIENT_CONFIG

@login_required
def index(request):
    context = {}
    try:
        GoogleDriveUserToken.objects.get(user=request.user)
        context['googledrive_enabled'] = True
        try:
            googledrive_user = check_connection(request.user.username)
            context['googledrive_connection'] = googledrive_user
        except Exception as e:
            # authentication failed
            logger.exception('google drive failed to authenticate: {}'.format(e))
            logger.warning('Google Drive oauth token for user=%s failed to authenticate' %
                           request.user.username)
            context['googledrive_connection'] = False

    except GoogleDriveUserToken.DoesNotExist:
        logger.debug('GoogleDriveUserToken does not exist for user=%s' % request.user.username)

    return render(request, 'portal/apps/googledrive_integration/index.html', context)


@csrf_exempt
@login_required
def initialize_token(request):
    redirect_uri = reverse('googledrive_integration:oauth2_callback')
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        get_client_config(),
        scopes=['https://www.googleapis.com/auth/drive',])
    flow.redirect_uri = request.build_absolute_uri(redirect_uri)

    auth_url, state = flow.authorization_url(access_type='offline')

    request.session['googledrive'] = {
        'state': state
    }

    return HttpResponseRedirect(auth_url)


@csrf_exempt
@login_required
def oauth2_callback(request):
    state = request.GET.get('state')
    if 'googledrive' in request.session:
        googledrive = request.session['googledrive']
    else:
        return HttpResponseBadRequest('Unexpected request')

    if not (state == googledrive['state']):
        return HttpResponseBadRequest('Request expired')

    try:
        redirect_uri = reverse('googledrive_integration:oauth2_callback')
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            get_client_config(),
            scopes=['https://www.googleapis.com/auth/drive',],
            state=state)
        flow.redirect_uri = request.build_absolute_uri(redirect_uri)

        # Use the authorization server's response to fetch the OAuth 2.0 tokens.
        authorization_response = request.build_absolute_uri()
        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials
        if not credentials.refresh_token:
            # Auth flow completed previously, and no refresh_token granted. Need to disconnect to get
            # another refresh_token.

            logger.debug('GoogleDriveUserToken refresh_token cannot be null, revoking previous access and restart flow.')
            requests.post('https://accounts.google.com/o/oauth2/revoke',
                    params={'token': credentials.token},
                    headers = {'content-type': 'application/x-www-form-urlencoded'})
            HttpResponseRedirect(reverse('googledrive_integration:initialize_token'))

        token = GoogleDriveUserToken(
            user=request.user,
            credentials=credentials
        )
        token.save()

    except Exception as e:
        logger.exception('Unable to complete Google Drive integration setup: %s' % e)
        messages.error(request, 'Oh no! An unexpected error occurred while trying to set '
                                'up the Google Drive application. Please try again.')

    return HttpResponseRedirect(reverse('googledrive_integration:index'))


@login_required
def disconnect(request):
    if request.method == 'POST':
        logger.info('Disconnect Google Drive requested by user...')
        try:
            googledrive_user_token = GoogleDriveUserToken.objects.get(user=request.user)

            revoke = requests.post('https://accounts.google.com/o/oauth2/revoke',
                params={'token': googledrive_user_token.credentials.token},
                headers = {'content-type': 'application/x-www-form-urlencoded'})

            status_code = getattr(revoke, 'status_code')

            googledrive_user_token.delete()

            if status_code == 200:
                messages.success(request, 'Your Google Drive account has been disconnected from {}.'.format(
                    settings.PORTAL_NAMESPACE))
                return HttpResponseRedirect(reverse('googledrive_integration:index'))

            else:
                logger.error('Disconnect Google Drive; google drive account revoke error.',
                         extra={'user': request.user})
                logger.debug('status code:{}'.format(status_code))

                return HttpResponseRedirect(reverse('googledrive_integration:index'))

        except GoogleDriveUserToken.DoesNotExist:
            logger.warn('Disconnect Google Drive; GoogleDriveUserToken does not exist.',
                        extra={'user': request.user})

        except Exception as e:
            logger.error('Disconnect Google Drive; GoogleDriveUserToken delete error.',
                         extra={'user': request.user})
            logger.exception('google drive delete error: {}'.format(e))

        messages.success(request, 'Your Google Drive account has been disconnected from {}.'.format(settings.PORTAL_NAMESPACE))

        return HttpResponseRedirect(reverse('googledrive_integration:index'))

    return render(request, 'portal/apps/googledrive_integration/disconnect.html')


def privacy_policy(request):
    return render(request, 'portal/apps/googledrive_integration/privacy-policy.html')
