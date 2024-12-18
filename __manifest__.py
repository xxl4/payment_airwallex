# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Airwallex',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'summary': "An Airwallex payment provider for online payments all over the world.",
    'author': "Steve Liu",
    'sequence': 5000,
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['payment'],
    'data': [
        'views/payment_form_templates.xml',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'data/payment_provider_data.xml',
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
