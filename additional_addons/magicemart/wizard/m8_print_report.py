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
        'name' : invoice.number and 'sales invoice - ' + invoice.number  or 'sales invoice',
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



