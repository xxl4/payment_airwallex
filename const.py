# Part of Odoo. See LICENSE file for full copyright and licensing details.

# ISO 4217 codes of currencies supported by Airwallex.
# See https://www.airwallex.com/docs/issuing__supported-regions-and-currencies
# Last seen on: 22 September 2022.
SUPPORTED_CURRENCIES = (
    'USD',  # United States Dollar
    'AUD',  # Australian Dollar
    'CAD',  # Canadian Dollar
    'SGD',  # Singapore Dollar
    'NZD',  # New Zealand Dollar
    'HKD',  # Hong Kong Dollar
    'JPY',  # Japanese Yen
    'EUR',  # Euro
    'GBP',  # British Pound
    'CHF',  # Swiss Franc
)

# The codes of the payment methods to activate when Airwallex is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'airwallex',
}

# Mapping of transaction states to Airwallex payment statuses.
# See https://www.airwallex.com/docs/payouts__create-a-transfer__transfer-statuses
PAYMENT_STATUS_MAPPING = {
    'pending': (
        'PENDING',
        'CREATED',
        'APPROVED',  # The buyer approved a checkout order.
    ),
    'done': (
        'COMPLETED',
        'CAPTURED',
    ),
    'cancel': (
        'DECLINED',
        'DENIED',
        'VOIDED',
    ),
    'error': ('FAILED',),
}

# Events which are handled by the webhook.
# See https://www.airwallex.com/docs/developer-tools__listen-for-webhook-events__event-types__online-payments
HANDLED_WEBHOOK_EVENTS = [
    'payment_intent.succeeded',
    'payment_intent.payment_failed',
    'payment_intent.canceled',
    'payment_intent.created',
    'payment_intent.requires_capture',
    'refund.succeeded',
    'refund.failed',
    'refund.created',
    'payment_dispute.requires_response',
    'payment_dispute.challenged',
]
