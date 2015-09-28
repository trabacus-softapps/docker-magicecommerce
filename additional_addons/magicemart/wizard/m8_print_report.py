from openerp.osv import osv,fields
from openerp.tools.translate import _
import openerp.pooler 
from dateutil import parser
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp import netsvc
import time

class print_reportwiz(osv.osv_memory):
    _name = 'print.reportwiz'
    _columns = {
                'type'    :   fields.selection([('pdf', 'PDF'),('xls','XLS')]," Report Type"),
                'option_sign' : fields.boolean("Company Seal")
                
                }
    _defaults={
               'type'     :  'pdf',
               'option_sign': True,
               
               }
    
#     Sale Quotation
    def but_print(self, cr, uid, ids, context=None):
        sale_obj = self.pool.get("sale.order")
        
        if not context:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            sale = sale_obj.browse(cr, uid, active_id)
            for case in self.browse(cr, uid, ids, context=context):
                report_name = 'Sales Quotation' 
                data = {}
                data['ids'] = [active_id]
                data['model'] = context.get('active_model', 'ir.ui.menu')
         
                data['output_type'] = case.type
                 
        return {
        'type': 'ir.actions.report.xml',
        'report_name': report_name,
        'name' : sale.name and 'Sales Quotation - ' + sale.name  or 'Sales Quotation',
        'datas': data,
            }
#         Purchase Order
    def print_purchase(self, cr, uid, ids, context=None):
        purchase_obj = self.pool.get("purchase.order")
        if not context:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            pur = purchase_obj.browse(cr, uid, active_id)
            for case in self.browse(cr, uid, ids, context=context):
                report_name = 'Purchase Order' 
                data = {}
                data['ids'] = [active_id]
                data['model'] = context.get('active_model', 'ir.ui.menu')
         
                data['output_type'] = case.type
                 
        return {
        'type': 'ir.actions.report.xml',
        'report_name': report_name,
        'name' : pur.name and 'Purchase Order - ' + pur.name  or 'Purchase Order',
        'datas': data,
            }  
        
#         Delivery Challan
    def print_deliverychallan(self, cr, uid, ids, context=None):
        stock_obj = self.pool.get("stock.picking")
        if not context:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            stock = stock_obj.browse(cr, uid, active_id)
            for case in self.browse(cr, uid, ids, context=context):
                report_name = 'Delivery challan' 
                data = {}
                data['ids'] = [active_id]
                data['model'] = context.get('active_model', 'ir.ui.menu')
         
                data['output_type'] = case.type

        return {
        'type': 'ir.actions.report.xml',
        'report_name': report_name,
        'name' : stock.name and 'Delivery challan - ' + stock.name  or 'Delivery challan',
        'datas': data,
            } 
        
#    Invoice Format 1
    def print_invoice(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get("account.invoice")
        if not context:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            invoice = inv_obj.browse(cr, uid, active_id)
            for case in self.browse(cr, uid, ids, context=context):
                report_name = 'sales invoice' 
                data = {}
                data['ids'] = [active_id]
                data['model'] = context.get('active_model', 'ir.ui.menu')
         
                data['output_type'] = case.type
                data['variables'] = {
                                     'option_sign'    : case.option_sign or False,  
                                    }
                 
        return {
        'type': 'ir.actions.report.xml',
        'report_name': report_name,
        'name' : invoice.number and 'Invoice / Refund - ' + invoice.number  or 'Invoice / Refund',
        'datas': data,
            } 
        
        
    #    Invoice Format 2
    def print_invoice1(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get("account.invoice")
        if not context:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            invoice = inv_obj.browse(cr, uid, active_id)
            for case in self.browse(cr, uid, ids, context=context):

                report_name = 'Sales Invoice1' 
                data = {}
                data['ids'] = [active_id]
                data['model'] = context.get('active_model', 'ir.ui.menu')
         
                data['output_type'] = case.type
                data['variables'] = {
                                     'option_sign'    : case.option_sign or False,
                                    }
                 
        return {
        'type': 'ir.actions.report.xml',
        'report_name': report_name,
        'name' : invoice.number and 'Sales Invoice1 - ' + invoice.number  or 'Sales Invoice1',
        'datas': data,
            } 
        
        

        
print_reportwiz()

class sale_reportwiz(osv.osv_memory):
    _name = 'sale.reportwiz'
    
    def get_partner_id(self, cr, uid, context=None):
        user_id = self.pool.get('res.users').browse(cr,uid, [uid])[0]
        if user_id.partner_id.customer == True:
            return user_id.partner_id.id
        if user_id.partner_id.supplier == True:
            return user_id.partner_id.id
        return False

    def get_partner_company_id(self, cr, uid, context=None):
        user_id = self.pool.get('res.users').browse(cr,uid, [uid])[0]
        if user_id:
            partner_company_id = user_id.partner_id.company_id.id
            return partner_company_id
        return False
    
        #to get currenct fiscal year
    def _get_fiscalyear(self, cr, uid, context=None):
        """Return default Fiscalyear value"""
        return self.pool.get('account.fiscalyear').find(cr, uid, context=context)
    
    _columns = {
                'inv_type'    :   fields.selection([('out_invoice', 'Sales'),('in_invoice','Purchase')]," VAT"),
                'from_date'   :   fields.date("From Date"),  
                'to_date'     :   fields.date("To Date"),
                'company_id'  :   fields.many2one("res.company", "Company" ),
                'refund'      :   fields.boolean("Refund"),  
#                 'fiscal_year' :   fields.many2one("account.fiscalyear", "Fiscal Year"),
                'type'        :   fields.selection([('itemwise', 'Item Wise'),('partywise', 'Party Wise')],'Type'),
                'partner_id'  :   fields.many2one("res.partner", "Party"),     
                'report_type' :   fields.selection([('annually','Annually'),('quarterly','Quarterly'),('monthly','Monthly')],"Report Type"),
                'product_id'  :   fields.many2one("product.product", "Product"),
                'profit_type' :   fields.selection([('billwise','Billwise Profit'),('partywise', 'Partywise Profit')], "Type"),
                'tax'         :   fields.boolean("Tax"),
                
                'new_sale_vat':   fields.boolean("Consolidated Sales/Purchase Vat"),       
                # Creating Dummy Field to filter customer & Suppiler
                'part_id'   :     fields.many2one("res.partner", "Party"),  
                # for Portal Users or Managers
#                 'portal_cust_type': fields.selection([('itemwise', 'Item Wise')],"Type"),
                }
    
    _defaults = {
                 'type' : 'itemwise',
                 'inv_type': 'out_invoice',
                 'partner_id': get_partner_id,
                 'company_id':get_partner_company_id,
                 }
        
    
#     Party Wise Sales VAT / Purchase VAT Analysis
    def partywise_sale(self, cr, uid, ids, context=None):
        sale_obj = self.pool.get("sale.order")
        if not context:
            context = {}
        for case in self.browse(cr, uid, ids, context=context):
            if case.new_sale_vat != True and case.inv_type == 'out_invoice':
                report_name = 'Partywise Sales'
            
            elif case.new_sale_vat == True and case.inv_type == 'out_invoice':
                report_name= 'New Sale Vat'
                
            elif case.new_sale_vat == True and case.inv_type == 'in_invoice':
                report_name= 'New Purchase Vat'
            else: 
                report_name = 'Partywise Purchase' 
            data = {}
            data['ids'] = ids
            data['model'] = context.get('active_model', 'ir.ui.menu')
      
            data['output_type'] = 'xls'
            data['variables'] = {
                                 'inv_type'     : case.inv_type,
                                 'from_date'    : case.from_date,
                                 'to_date'      : case.to_date,  
                                 'company_id'   : case.company_id.id,
                                 'refund'       : case.refund or False,
                                 
                                }
            return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
                }
             
             
    # Item Wise Sales/Purchase Analysis     
    def partywise_sales_analysis(self, cr, uid, ids, context=None):
        if not context:
            cntext={}
#         fiscal_obj = self.pool.get("account.fiscalyear")
         
        for case in self.browse(cr, uid, ids, context=context):
#             fiscal = fiscal_obj.browse(cr, uid, case.fiscal_year.id) 
            partner = 0
            if case.type=='itemwise':
                if case.partner_id:
                    partner = case.partner_id.id
                if case.part_id:
                    partner = case.part_id.id
                report_name = 'Itemwise Sales Purchase'
                data={}
                data['ids'] = ids
                data['model'] = context.get('active_model','ir.ui.menu')
                data['output_type'] = 'xls'
                data['variables'] = {
                                     'inv_type'     : case.inv_type,
                                     'type'         : case.type,
                                     'partner_id'   : partner,
                                     'company_id'   : case.company_id.id or 0,
                                     'from_date'    : case.from_date,
                                     'to_date'      : case.to_date,  
                                     'partner_name' : case.partner_id.name or '',
                                     }
            elif case.type == 'partywise':
                report_name = 'Partywise Sales Purchase' 
                data = {}
                data['ids'] = ids
                data['model'] = context.get('active_model', 'ir.ui.menu')
           
                data['output_type'] = 'xls'
                data['variables'] = {
                                     'inv_type'     :   case.inv_type,
                                     'from_date'    :   case.from_date,
                                     'to_date'      :   case.to_date,
                                     'report_type'  :   case.report_type,
                                     'company_id'   :   case.company_id.id or 0,
                                    }
                  
        return {
        'type': 'ir.actions.report.xml',
        'report_name': report_name,
        'datas': data,
            }
    # Itemwise Report for Portal Users
    def portal_cust_itemwise(self, cr, uid, ids, context=None):
        if not context:
            cntext={}
         
        for case in self.browse(cr, uid, ids, context=context):
            partner = 0
            if case.type =='itemwise':
                report_name = 'Itemwise Sales Purchase'
                data={}
                data['ids'] = ids
                data['model'] = context.get('active_model','ir.ui.menu')
                data['output_type'] = 'xls'
                data['variables'] = {
                                     'inv_type'     : case.inv_type,
                                     'type'         : case.type,
                                     'partner_id'   : case.partner_id.id or 0,
                                     'company_id'   : case.company_id.id or 0,
                                     'from_date'    : case.from_date,
                                     'to_date'      : case.to_date,  
                                     'partner_name' : case.partner_id.name or '',
                                     }
        return {
        'type': 'ir.actions.report.xml',
        'report_name': report_name,
        'datas': data,
            }
        
        
        
    def onchange_analysis(self, cr, uid, ids, inv_type, context=None):
        res={}
        dom={}
        if inv_type =="out_invoice":
            dom = {'partner_id':  [('customer','=', True)]}
        else:
            dom = {'partner_id':  [('supplier','=', True)]}
        return {'value':res, 'domain':dom }
        
        # Product/Stock Ledger
           
    def product_ledger(self, cr, uid, ids, context=None):
        if not context:
            cntext={}
        fiscal_obj = self.pool.get("account.fiscalyear")
        prod_obj = self.pool.get("product.product")
        fiscal_id = self.pool.get('account.fiscalyear').find(cr, uid, context=context)
        for case in self.browse(cr, uid, ids, context=context):
            fiscal = fiscal_obj.browse(cr, uid, fiscal_id) 
            report_name = 'Stock Ledger'
            data={}
            data['ids'] = ids
            data['model'] = context.get('active_model','ir.ui.menu')
            data['output_type'] = 'xls'
            data['variables'] = {
                                 
                                 'from_date'    : case.from_date,
                                 'to_date'      : case.to_date,
                                 'product_id'   : case.product_id.id,  
                                 'company_id'   : case.company_id.id or 0,
                                 'fscalst_date' : fiscal.date_start,
                                 # for Stock Ledger  
                                 'product'      : case.product_id.name or '',
                                 }
                  
        return {
        'type': 'ir.actions.report.xml',
        'report_name': report_name,
        'datas': data,
            }
      # Bill Wise & Party Wise Profitability      
    def billwise_partywise_profit(self, cr, uid, ids, context=None):
        if not context:
            cntext={}
        for case in self.browse(cr, uid, ids, context=context):
            if  case.profit_type == 'billwise':
                report_name = 'Bill Wise Profitability'
                data={}
                data['ids'] = ids
                data['model'] = context.get('active_model','ir.ui.menu')
                data['output_type'] = 'xls'
                data['variables'] = {
                                     
                                     'from_date'    : case.from_date,
                                     'to_date'      : case.to_date,
                                     'company_id'   : case.company_id.id or 0,
                                     'partner_id'   : case.partner_id.id or 0,
                                     'tax'          : case.tax or False,
                                     }
                      
                return {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': data,
                        }
            if case.profit_type == 'partywise':
                report_name = 'Party Wise Profitability'
                data={}
                data['ids'] = ids
                data['model'] = context.get('active_model','ir.ui.menu')
                data['output_type'] = 'xls'
                data['variables'] = {
                                     
                                     'from_date'    : case.from_date,
                                     'to_date'      : case.to_date,
                                     'company_id'   : case.company_id.id or 0,
                                     'partner_id'   : case.partner_id.id or 0,
                                     'tax'          : case.tax or False,
                                     }
                      
                return {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': data,
                    }
             
    def bills_receivable(self, cr, uid, ids, context=None):
        if not context:
            cntext={}
        for case in self.browse(cr, uid, ids, context=context):
            report_name = 'Bills Receivable'
            data={}
            data['ids'] = ids
            data['model'] = context.get('active_model','ir.ui.menu')
            data['output_type'] = 'xls'
            data['variables'] = {
                                 
                                 'from_date'    : case.from_date,
                                 'to_date'      : case.to_date,
                                 'company_id'   : case.company_id.id or 0,
                                 }
                  
        return {
        'type': 'ir.actions.report.xml',
        'report_name': report_name,
        'datas': data,
            }
     
     
    # Supplier Sales Analysis for Supplier                
    def supplier_sales_analysis(self, cr, uid, ids, context=None):
        if not context:
            cntext={}
        for case in self.browse(cr, uid, ids, context=context):
            report_name = 'Suppliers Sales Analysis'
            data={}
            data['ids'] = ids
            data['model'] = context.get('active_model','ir.ui.menu')
            data['output_type'] = 'xls'
            data['variables'] = {
                                 'from_date'    : case.from_date,
                                 'to_date'      : case.to_date,
                                 'partner_id'   : case.partner_id.id or 0,
                                 'company_id'   : case.company_id.id or 0,  

                                 }
                  
        return {
        'type': 'ir.actions.report.xml',
        'report_name': report_name,
        'datas': data,
            }
                 
    def itemwise_gross_profit(self, cr, uid, ids, context=None):
        if not context:
            cntext={}
        fiscal_obj = self.pool.get("account.fiscalyear")
        fiscal_id = self.pool.get('account.fiscalyear').find(cr, uid, context=context)
        for case in self.browse(cr, uid, ids, context=context):
            fiscal = fiscal_obj.browse(cr, uid, fiscal_id) 
            report_name = 'Itemwise Gross Profit'
            data={}
            data['ids'] = ids
            data['model'] = context.get('active_model','ir.ui.menu')
            data['output_type'] = 'xls'
            data['variables'] = {
                                 
                                 'from_date'    : case.from_date,
                                 'to_date'      : case.to_date,
                                 'fscalst_date' : fiscal.date_start,
#                                  'product_id'   : case.product_id.id,  
                                 'company_id'   : case.company_id.id or 0,
                                 'refund'       : case.refund or False,
                                 }
                  
        return {
        'type': 'ir.actions.report.xml',
        'report_name': report_name,
        'datas': data,
            }
               
sale_reportwiz()



# For General Ledger
class account_report_general_ledger(osv.osv_memory):
    _inherit='account.report.general.ledger'
    _columns={
              'partner_id':fields.many2one('res.partner','Partner'),
              'account_id':fields.many2one('account.account','Account'),
              'client_heading' : fields.boolean('Client Heading'),
              'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic Account'),
              'output_type' : fields.selection([('pdf', 'Portable Document (pdf)'),
                                                 ('xls', 'Excel Spreadsheet (xls)')],
                                                'Report format', help='Choose the format for the output'),
               'tledger_id': fields.many2one('tr.ledger', 'Ledger'),

              }
#     def _get_all_journal(self, cr, uid, context=None):
#         cid = self.pool.get('res.users')._get_company(cr, uid, context=None)
#         return self.pool.get('account.journal').search(cr, uid ,[('company_id', '=', cid)])

    _defaults={
               'output_type' : 'pdf',
               'client_heading' : False,
               'landscape' : False,
               'filter':'filter_date',
               'initial_balance':False,
               'amount_currency' : False,
#                'date_from' : time.strftime("%Y-%m-%d")
#                'journal_ids' : _get_all_journal
               }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}

        res = super(account_report_general_ledger, self).default_get(cr, uid, fields, context=context)
        res.update({'partner_id': context.get('frm_custview') and context.get('active_id') or False})
        return res

    def xls_export(self, cr, uid, ids, context=None):
        return self.check_report(cr, uid, ids, context=context)


# # Overriden
#     def _print_report(self, cr, uid, ids, data, context=None):
#         if context is None:
#             context = {}
#         data = self.pre_print_report(cr, uid, ids, data, context=context)
#         data['form'].update(self.read(cr, uid, ids, ['landscape', 'initial_balance', 'amount_currency', 'sortby'])[0])
# #         data['form'].update(self.read(cr, uid, ids, ['account_id'], context=context)[0])
#         for case in self.browse(cr, uid, ids):
#             data['form'].update({'chart_account_id':case.account_id and case.account_id.id or case.chart_account_id.id,
#                                  'chart_account_name' : case.chart_account_id and case.chart_account_id.name or '',
#                                  'account_id':case.account_id and case.account_id.id or 0,
#                                  'output_type':case.output_type or 'pdf',
#                                  'tledger_id' : case.tledger_id and case.tledger_id.id or False,
#                                  'company_id' : case.company_id and case.company_id.id or 0})
#         data['form'].update(self.read(cr, uid, ids, ['partner_id', 'account_analytic_id'], context=context)[0])
#         if 'client_heading' in context:
#             data['form'].update({'client_heading':True})
#         else:
#             data['form'].update({'client_heading':False})
#         if not data['form']['fiscalyear_id']:  # GTK client problem onchange does not consider in save record
#             data['form'].update({'initial_balance': False})
#         if 'client_heading' in context:
#             if data['form']['output_type'] == 'xls':
#                 return { 'type': 'ir.actions.report.xml', 'report_name': 'account.account_report_general_ledger_xls', 'name' : 'Client Satement', 'datas': data}
#             if data['form']['landscape']:
#                 return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger_landscape', 'name' : 'Client Satement', 'datas': data}
#             return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger', 'name' : 'Client Satement', 'datas': data}
#         if data['form']['output_type'] == 'xls':
#             return { 'type': 'ir.actions.report.xml', 'report_name': 'account.account_report_general_ledger_xls', 'datas': data}
#         if data['form']['landscape']:
#             return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger_landscape', 'datas': data}
#         # Update model to pass account_id in set_context
#         if data.get('model') == 'res.partner' : data.update({'model' : 'ir.ui.menu'})
#         return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger', 'datas': data}

    def print_penreport(self, cr, uid, ids, data, context=None):
        for case in self.browse(cr, uid, ids):

            if context is None : context = {}
            if case.filter == 'filter_date':
                if case.date_to < case.date_from:
    #                 raise UserError(_('Please Check the given dates!!!'))
                    raise osv.except_osv(_('User Error'), _('Please Check the given dates!'))

            #~~~ To show Partner name in details
            show_partner = False
            if not case.partner_id and not case.account_id and case.tledger_id:
                show_partner = True
            if not case.partner_id and case.account_id  and not case.tledger_id:
                if case.account_id.type not in ('receivable', 'payable'):
                    show_partner = True
            if not case.partner_id and not case.account_id  and not case.tledger_id:
                show_partner = True

            address = ''
            address = case.company_id and ((case.company_id.street or '')
                                           + (case.company_id.street2 and (', ' + case.company_id.street2) or '')
                                           + (case.company_id.state_id and (', ' + case.company_id.state_id.name) or '')
                                           + (case.company_id.city and (', ' + case.company_id.city) or '')
                                           + (case.company_id.country_id and (', ' + case.company_id.country_id.name) or '')
                                           + (case.company_id.zip and (' - ' + case.company_id.zip) or '')
                                           )

            heading = 'Ledger Report'
            if case.client_heading:
                heading = 'Client Statement' + (case.partner_id and (' - ' + case.partner_id.name) or '')
            if case.tledger_id:
                heading = case.tledger_id.name
            data = {}
            data['ids'] = ids
            data['model'] = context.get('active_model', 'ir.ui.menu')
            data['output_type'] = case.output_type
            data['variables'] = {
                                'start_date'        : case.date_from or time.strftime("%Y-%m-%d"),
                                'end_date'          : case.date_to or time.strftime("%Y-%m-%d"),
                                'company_id'        : case.company_id and case.company_id.id or 0,
                                'company_name'      : case.company_id and case.company_id.name or case.company_id.name,
                                'company_address'   : address or '',
                                'chart_account_id'  : case.chart_account_id and case.chart_account_id.id or 0,
                                'target_move'       : case.target_move or 'all',
                                'display_account'   : case.display_account or '',
                                'partner_id'        : case.partner_id and case.partner_id.id or 0,
                                'partner_name'      : case.partner_id and case.partner_id.name or '',
                                'partner_code'      : case.partner_id and case.partner_id.ref or '',
                                'account_id'        : case.account_id and case.account_id.id or 0,
                                'account_name'      : case.account_id and case.account_id.code
                                                        and ('[' + case.account_id.code + '] ' + case.account_id.name)
                                                        or (case.account_id and case.account_id.name or ''),
                                'account_type'      : case.account_id and case.account_id.type in ('receivable', 'payable') and 1 or 0,
                                'analytic_account_id' : case.account_analytic_id and case.account_analytic_id.id or 0,
                                'analytic_account_name' : case.account_analytic_id and case.account_analytic_id.name or '',
                                'tledger_id'        : case.tledger_id and case.tledger_id.id or 0,
                                'tledger_name'      : case.tledger_id and case.tledger_id.name or '',
                                'output_type'       : case.output_type or 'pdf',
                                'ids'               : [x.id for x in case.journal_ids] or 0,
                                'currency_symbol'   : case.company_id and case.company_id.currency_id and case.company_id.currency_id.name or 0,
                                'show_partner'      : show_partner and 1 or 0,
                                'heading'           : heading or '',
#                                 'rundate'           : tg.UTC_To_LocalTime(self, cr, uid, datetime.today().strftime("%Y-%m-%d %H:%M:%S"), context),
#                                 'date_format'       : tg.dateFormat(self, cr, uid, context),
                                }
            return {
                    'report_name': 'general_ledger_report',
                    'type': 'ir.actions.report.xml',
                    'datas': data,
                }

#     def onchange_account(self, cr, uid, ids, account_id,):
#         result = {}
#         acc_obj = self.pool.get('account.account')
#         prop_obj = self.pool.get('ir.property')
#
#         if account_id:
#             acc_id = 'account.account' + ',' + str(account_id)
#             if acc_id:
#                 ir_ids = prop_obj.search(cr, uid, [('value_reference', '=', acc_id)], limit=1)
#                 ir_id = ir_ids and ir_ids[0] or False
#                 if not ir_id:
#                     return False  # return {'value':{'partner_id' : False}}
#
#                 prop = prop_obj.browse(cr, uid, ir_id)
#                 res = prop.res_id
#                 if res and res[0:res.find(',') + 1] == 'res.partner,' or False:
#                     p_id = int(res[res.find(',') + 1:].strip())
#                     result = {
#                            'partner_id' : p_id and p_id or False
#                           }
#         return {'value':result}

    def onchange_partner_id(self, cr, uid, ids, partner_id, company_id=False):
        result = {}
        opt = [('uid', str(uid))]
        acc_id = False
        partner_obj = self.pool.get('res.partner')
        if partner_id:
            p = partner_obj.browse(cr, uid, partner_id)
            sql = """select substring(value_reference,17) from ir_property
                            where (name ilike '%property_account_receivable%' or name ilike '%property_account_payable%')
                             and company_id =""" + str(company_id) +"""
                             and res_id = 'res.partner,""" + str(p.id)  + """'"""
            cr.execute(sql)
            acc_id = [x[0] for x in cr.fetchall()]
        result = {'value': {'account_id': acc_id and int(acc_id[0]) }}
        return result

    #Inherited:
    def onchange_chart_id(self, cr, uid, ids, chart_account_id=False, context=None):
        res = {}
        res = super(account_report_general_ledger, self).onchange_chart_id(cr, uid, ids, chart_account_id, context=context)
        acc_obj = self.pool.get('account.account')
        if 'company_id' in res['value']:
            company_id = res['value']['company_id'] or acc_obj.browse(cr, uid, chart_account_id, context=context).company_id.id
            jids = self.pool.get('account.journal').search(cr, uid ,[('company_id', '=', company_id)])
            res['value'].update({'journal_ids' : jids
                            ,'company_id': company_id
                            , 'account_id' : False
                            , 'tledger_id' : False})
            res['domain'] = {
                            'account_id' : [('type', '!=', 'view'), ('type', '!=', 'consolidation'),('company_id','=',company_id)]
                                  }
        return res

    def onchange_tledger_id(self, cr, uid, ids, tledger_id, company_id):
        domain = [('type', '!=', 'view'), ('type', '!=', 'consolidation'),('company_id','=',company_id)]
        if tledger_id:
            domain += [('tledger_id', '=', tledger_id)]
        result = {'domain' : {'account_id' : domain}}
        return result

    def onchange_filter(self, cr, uid, ids, filter='filter_no', fiscalyear_id=False, context=None):
        res = super(account_report_general_ledger, self).onchange_filter(cr, uid, ids, filter=filter, fiscalyear_id=fiscalyear_id, context=context)
        fiscal_obj = self.pool.get('account.fiscalyear')
        fid = fiscal_obj.browse(cr, uid, fiscalyear_id)
        if fid : res['value'].update({'date_from' : time.strftime("%Y-%m-%d"), })
        return res


account_report_general_ledger()




