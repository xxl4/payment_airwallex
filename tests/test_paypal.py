# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_airwallex.controllers.main import AirwallexController
from odoo.addons.payment_airwallex.tests.common import AirwallexCommon


@tagged('post_install', '-at_install')
class AirwallexTest(AirwallexCommon, PaymentHttpCommon):

    def test_processing_values(self):
        tx = self._create_transaction(flow='direct')
        with patch(
            'odoo.addons.payment_airwallex.models.payment_provider.PaymentProvider'
            '._airwallex_make_request', return_value={'id': self.order_id},
        ):
            processing_values = tx._get_processing_values()
        self.assertEqual(processing_values['order_id'], self.order_id)

    @mute_logger('odoo.addons.payment_airwallex.controllers.main')
    def test_complete_order_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('direct')
        normalized_data = AirwallexController._normalize_airwallex_data(self, self.completed_order)
        self.env['payment.transaction']._handle_notification_data('airwallex', normalized_data)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, normalized_data['id'])

    def test_feedback_processing(self):
        normalized_data = AirwallexController._normalize_airwallex_data(
            self, self.notification_data.get('resource'), from_webhook=True
        )
        # Unknown transaction
        with self.assertRaises(ValidationError):
            self.env['payment.transaction']._handle_notification_data('airwallex', normalized_data)

        # Confirmed transaction
        tx = self._create_transaction('direct')
        self.env['payment.transaction']._handle_notification_data('airwallex', normalized_data)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, normalized_data['id'])

        # Pending transaction
        self.reference = 'Test Transaction 2'
        tx = self._create_transaction('direct')
        payload = {
            **normalized_data,
            'reference_id': self.reference,
            'status': 'PENDING',
            'pending_reason': 'multi_currency',
        }
        self.env['payment.transaction']._handle_notification_data('airwallex', payload)
        self.assertEqual(tx.state, 'pending')
        self.assertEqual(tx.state_message, payload['pending_reason'])

    @mute_logger('odoo.addons.payment_airwallex.controllers.main')
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('direct')
        url = self._build_url(AirwallexController._webhook_url)
        with patch(
            'odoo.addons.payment_airwallex.controllers.main.AirwallexController'
            '._verify_notification_origin'
        ):
            self._make_json_request(url, data=self.notification_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_airwallex.controllers.main')
    def test_webhook_notification_triggers_origin_check(self):
        """ Test that receiving a webhook notification triggers an origin check. """
        self._create_transaction('direct')
        url = self._build_url(AirwallexController._webhook_url)
        with patch(
            'odoo.addons.payment_airwallex.controllers.main.AirwallexController'
            '._verify_notification_origin'
        ) as origin_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_json_request(url, data=self.notification_data)
            self.assertEqual(origin_check_mock.call_count, 1)
