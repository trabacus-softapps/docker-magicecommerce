
# Odoo version for Functions Fields

from openerp import models, fields as Fields, api
import openerp.addons.decimal_precision as dp
import time
import datetime

class account_invoice(models.Model):
    _inherit = "account.invoice"


    @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line)
        self.amount_tax = sum(line.amount for line in self.tax_line)
        self.amount_total = round(self.amount_untaxed + self.amount_tax)
        self.round_off = round(self.amount_untaxed + self.amount_tax) - (self.amount_untaxed + self.amount_tax)






    amount_untaxed = Fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
                              store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    
    amount_tax = Fields.Float(string='Tax', digits=dp.get_precision('Account'),
                              store=True, readonly=True, compute='_compute_amount')
    
    amount_total = Fields.Float(string='Total', digits=dp.get_precision('Account'),
                              store=True, readonly=True, compute='_compute_amount')
    
    round_off = Fields.Float(string='Round off', digits=dp.get_precision('Account'),
                              store=True, readonly=True, compute='_compute_amount')
    
    @api.model
    def create(self,vals):
        cr, uid,  = self._cr, self._uid
        comp_obj = self.env['res.company']
        today = time.strftime("%Y-%m-%d")
        if not vals.get("date_invoice", ''):
            vals.update({
                         "date_invoice" : today, 
                         })
            
        if vals.get('company_id', False):
            for c in comp_obj.browse([vals.get('company_id', False)]):
                if not c.parent_id:
                    raise osv.except_osv(_('User Error'), _('You must select sub company sale shop !'))
        return super(account_invoice,self).create(vals)
    
           
        
    @api.multi
    def write(self,vals):
       cr = self._cr 
       res = False 
       res = super(account_invoice, self).write(vals)
      
       for inv in self:
           cr.execute("update account_invoice_line set company_id ="+str(inv.company_id.id) +" where invoice_id ="+ str(inv.id))
       return res 

         
                    
class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"



    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_id', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id')
    def _compute_price(self):
        invoice = self.env['account.invoice']
        if invoice.type in ( "out_invoice","out_refund","in_refund"):
            price = line.price_unit
        else:    
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = self.invoice_line_tax_id.compute_all(price, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = taxes['total']
        if self.invoice_id:
            self.price_subtotal = self.invoice_id.currency_id.round(self.price_subtotal)
#         
#         amount = self.price_subtotal
#         for t in taxes.get('taxes',False):  
#              amount + = t['amount']       
#         self.price_total = self.invoice_id.currency_id.round(amount)
                    

     
        

        price_subtotal = Fields.Float(string='Amount', digits= dp.get_precision('Account'),
                                          store=True, readonly=True, compute='_compute_price')
        
        # creating this field  coz created in new version of saas-6
        price_subtotal_signed = Fields.Float(string='Amount Signed', digits=0,
                                             store=True, readonly=True, compute='_compute_price'),
        