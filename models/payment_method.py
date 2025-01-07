from odoo import models, fields, api

class PaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def create_airwallex_payment_method(self):
        payment_method_vals = {
            'name': 'Airwallex',
            'code': 'airwallex',
            'payment_type': 'inbound',  # or 'outbound' based on your requirement
        }
        payment_method = self.create(payment_method_vals)
        return payment_method