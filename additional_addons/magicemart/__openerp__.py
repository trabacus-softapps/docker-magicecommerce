{
    'name': "Magicemart 8",
    'version': '1.0',
    'sequence': 1,
        'depends': [
                    'base','sale','sale_margin','website_quote','purchase','purchase_requisition','project','stock','account','account_analytic_default',
                    'delivery','account_accountant','website','hr','fleet','marketing','knowledge', 'hr_timesheet','hr_holidays',
                    'website_sale'
                ],
    'author': 'Softappsit solutions',
    'category': 'E-commerce',
    'description': """
    Description text
    """,
#     'website': 'http://www.softappsit.com',
    'qweb': ['static/src/xml/base.xml'],
    # data files always loaded at installation
    'data': [
            'security/security_groups.xml',
            'security/security_rule.xml',
            'wizard/m8_mail_compose_msg.xml',

            'm8_portal.xml',
            'm8_config.xml',
            'wizard/m8_print_report.xml',

            'm8_user.xml',
            'm8_partner.xml',
            'm8_sale.xml',
            'm8_mail_template.xml',

            'm8_stock_picking.xml',
            'm8_purchase.xml',
            'm8_purchase_workflow.xml',
            'm8_account_invoice.xml',
#             'report/standard/m_report.xml',  
            'security/ir.model.access.csv',

#             'views/m8_saleweb.xml',
            'views/treeview_image.xml',
    ],
    
        'css' :['static/src/css/base.css'],
#         'js':['static/src/js/magicemart.js'],
    
    # data files containing optionally loaded demonstration data
    'demo': [
        
    ],
}