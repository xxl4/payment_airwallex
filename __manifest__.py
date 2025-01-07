# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Airwallex',
    'version': '1.1',
    'category': 'Accounting/Payment Providers',
    'summary': "An Airwallex payment provider for online payments all over the world.",
    'author': "Steve Liu",
    'description': "This module adds Airwallex as a payment method in Odoo.",  # Non-empty string to avoid loading the README file.
    'depends': ['payment','account'],
    'data': [
        'views/payment_method_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_airwallex/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
}
