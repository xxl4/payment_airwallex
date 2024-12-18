# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint
import requests

from datetime import timedelta
from werkzeug import urls

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment_airwallex import const
from odoo.addons.payment_airwallex.controllers.main import AirwallexController


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('airwallex', "Airwallex")], ondelete={'airwallex': 'set default'}
    )
    airwallex_email_account = fields.Char(
        string="Email",
        help="The public business email solely used to identify the account with Airwallex",
        required_if_provider='airwallex',
        default=lambda self: self.env.company.email,
    )
    airwallex_client_id = fields.Char(string="Airwallex Client ID", required_if_provider='airwallex')
    airwallex_client_secret = fields.Char(string="Airwallex Client Secret", groups='base.group_system')
    airwallex_access_token = fields.Char(
        string="Airwallex Access Token",
        help="The short-lived token used to access Airwallex APIs",
        groups='base.group_system',
    )
    airwallex_access_token_expiry = fields.Datetime(
        string="Airwallex Access Token Expiry",
        help="The moment at which the access token becomes invalid.",
        default='1970-01-01',
        groups='base.group_system',
    )
    airwallex_webhook_id = fields.Char(string="Airwallex Webhook ID")

    # === ACTION METHODS === #

    def action_airwallex_create_webhook(self):
        """ Create a new webhook.

        Note: This action only works for instances using a public URL.

        :return: None
        :raise UserError: If the base URL is not in HTTPS.
        """
        base_url = self.get_base_url()
        base_url = base_url.replace('http://', 'https://')
        if 'localhost' in base_url:
            raise UserError(
                "Airwallex: " + _("You must have an HTTPS connection to generate a webhook.")
            )
        data = {
            'url': urls.url_join(base_url, AirwallexController._webhook_url),
            'event_types': [{'name': event_type} for event_type in const.HANDLED_WEBHOOK_EVENTS]
        }
        webhook_data = self._airwallex_make_request('/v1/notifications/webhooks', json_payload=data)
        self.airwallex_webhook_id = webhook_data.get('id')

    #=== BUSINESS METHODS ===#

    def _airwallex_make_request(
        self, endpoint, data=None, json_payload=None, auth=None, is_refresh_token_request=False,
        idempotency_key=None,
    ):
        """ Make a request to Airwallex API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict data: The string payload of the request.
        :param dict json_payload: The JSON-formatted payload of the request.
        :param tuple auth: The authentication data.
        :param bool is_refresh_token_request: Whether the request is for refreshing the access
                                              token.
        :param str idempotency_key: The idempotency key to pass in the request.
        :return: The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        url = self._airwallex_get_api_url() + endpoint
        headers = {'Content-Type': 'application/json'}  # Airwallex always wants JSON content-type.
        if idempotency_key:
            headers['Airwallex-Request-Id'] = idempotency_key
        if not is_refresh_token_request:
            headers['Authorization'] = f'Bearer {self._airwallex_fetch_access_token()}'
        try:
            response = requests.post(
                url, headers=headers, data=data, json=json_payload, auth=auth, timeout=10
            )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                payload = data or json_payload
                # Airwallex errors https://developer.airwallex.com/api/rest/reference/orders/v2/errors/
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload)
                )
                msg = response.json().get('message', '')
                raise ValidationError(
                    "Airwallex: " + _("The communication with the API failed. Details: %s", msg)
                )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError("Airwallex: " + _("Could not establish the connection to the API."))
        return response.json()

    def _airwallex_fetch_access_token(self):
        """ Generate a new access token if it's expired, otherwise return the existing access token.

        :return: A valid access token.
        :rtype: str
        :raise ValidationError: If the access token can not be fetched.
        """
        if fields.Datetime.now() > self.airwallex_access_token_expiry - timedelta(minutes=5):
            response_content = self._airwallex_make_request(
                '/v1/oauth2/token',
                data={'grant_type': 'client_credentials'},
                auth=(self.airwallex_client_id, self.airwallex_client_secret),
                is_refresh_token_request=True,
            )
            access_token = response_content['access_token']
            if not access_token:
                raise ValidationError("Airwallex: " + _("Could not generate a new access token."))
            self.write({
                'airwallex_access_token': access_token,
                'airwallex_access_token_expiry': fields.Datetime.now() + timedelta(
                    seconds=response_content['expires_in']
                ),
            })
        return self.airwallex_access_token

    # === BUSINESS METHODS - GETTERS === #

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'airwallex':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _airwallex_get_api_url(self):
        """ Return the API URL according to the provider state.

        Note: self.ensure_one()

        :return: The API URL
        :rtype: str
        """
        self.ensure_one()

        if self.state == 'enabled':
            return 'https://api-m.airwallex.com'
        else:
            return 'https://api-m.sandbox.airwallex.com'

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'airwallex':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _airwallex_get_inline_form_values(self, currency=None):
        """ Return a serialized JSON of the required values to render the inline form.

        Note: `self.ensure_one()`

        :param res.currency currency: The transaction currency.
        :return: The JSON serial of the required values to render the inline form.
        :rtype: str
        """
        inline_form_values = {
            'provider_id': self.id,
            'client_id': self.airwallex_client_id,
            'currency_code': currency and currency.name,
        }
        return json.dumps(inline_form_values)
