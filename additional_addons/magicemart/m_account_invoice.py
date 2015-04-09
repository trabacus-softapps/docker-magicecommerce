from osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
import amount_to_text_softapps
import time
import datetime

class account_invoice(osv.osv):
    _name = 'account.invoice'
    _inherit = 'account.invoice'
    
    #Overidden
    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        without_round = 0.00
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'round_off' : 0.0,
            }
            for line in invoice.invoice_line:
                res[invoice.id]['amount_untaxed'] += line.price_subtotal
            for line in invoice.tax_line:
                res[invoice.id]['amount_tax'] += line.amount
            res[invoice.id]['amount_total'] = round(res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed'])
            without_round = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed']
            res[invoice.id]['round_off'] = res[invoice.id]['amount_total'] - without_round 
        return res

   
    #Overidden
    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    #Overidden
    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()
    
    # Funtion To Convert Amount to Text
    def _amt_in_words(self, cr, uid, ids, field_name, args, context=None):
        res={}
        
        for case in self.browse(cr, uid, ids):
            txt=''
            if case.amount_total:
                txt += amount_to_text_softapps._100000000_to_text(int(round(case.amount_total)))        
                res[case.id] = txt     
        return res
    
    def _get_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        return context.get('type', 'out_invoice')
    
    def _get_invoice_from_line(self, cr, uid, ids, context=None):
        move = {}
        for line in self.pool.get('account.move.line').browse(cr, uid, ids, context=context):
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    move[line2.move_id.id] = True
            if line.reconcile_id:
                for line2 in line.reconcile_id.line_id:
                    move[line2.move_id.id] = True
        invoice_ids = []
        if move:
            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('move_id','in',move.keys())], context=context)
        return invoice_ids
    
    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()
    
    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    def _get_invoice_from_reconcile(self, cr, uid, ids, context=None):
        move = {}
        for r in self.pool.get('account.move.reconcile').browse(cr, uid, ids, context=context):
            for line in r.line_partial_ids:
                move[line.move_id.id] = True
            for line in r.line_id:
                move[line.move_id.id] = True

        invoice_ids = []
        if move:
            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('move_id','in',move.keys())], context=context)
        return invoice_ids
    
    _columns = {
                'contact_id'          : fields.many2one('res.partner','Contact Person'),
                'amt_in_words'        : fields.function(_amt_in_words, method=True, string="Amount in Words", type="text", 
                store={
                    'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                    'account.invoice.tax': (_get_invoice_tax, None, 20),
                    'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
                    },),
                'transport'            : fields.char("Customer PO Reference", size=50),
                'vehicle'              : fields.char("Vehicle", size=20),
                'dc_ref'               : fields.char("DC Reference", size=200),
                'date_from'            : fields.function(lambda *a,**k:{}, method=True, type='date',string="From"),
                'date_to'              : fields.function(lambda *a,**k:{}, method=True, type='date',string="To"),
                'terms'                : fields.text("Terms And Condition"), 
                #Overidden
                'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Subtotal', track_visibility='always',
                    store={
                        'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                        'account.invoice.tax': (_get_invoice_tax, None, 20),
                        'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
                    },
                    multi='all'),
                'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tax',
                    store={
                        'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                        'account.invoice.tax': (_get_invoice_tax, None, 20),
                        'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
                    },
                    multi='all'),
                'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
                    store={
                        'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                        'account.invoice.tax': (_get_invoice_tax, None, 20),
                        'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
                    },
                    multi='all'),
                 
                'round_off'  : fields.function(_amount_all,digits_compute=dp.get_precision('Account'), string='Round off',
                    store={
                        'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                        'account.invoice.tax': (_get_invoice_tax, None, 20),
                        'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
                    },
                    multi='all'),
                
                
                }
    def unlink(self, cr, uid, ids, context=None):
        pick_obj = self.pool.get("stock.picking.out")
        for case in self.browse(cr, uid, ids):
            if case.state == 'draft':
                self.write(cr, uid, ids,{'internal_number':False})
                pick_ids = pick_obj.search(cr, uid,[('invoice_id','=',case.id)])
                pick_obj.write(cr, uid,pick_ids,{'invoice_state':'2binvoiced'})
        return super(account_invoice,self).unlink(cr, uid, ids, context)
    
    # updating company onchange_company_id account company, period company, line company, journal company
    def onchange_company_id(self, cr, uid, ids, company_id, part_id, type, invoice_line, currency_id):
        today = time.strftime('%Y-%m-%d')
        res = {}                      
        res = super(account_invoice,self).onchange_company_id(cr, uid, ids, company_id=company_id, part_id=part_id, type=type, invoice_line=invoice_line, currency_id=currency_id)
        acc_obj = self.pool.get("account.account")

        if company_id:
            cr.execute("select id from account_period where company_id='"+ str(company_id)+"' and date_start <= '" + today + "' and date_stop >='" + today + "'")
            period = cr.fetchone()
            if period:
                res['value']['period_id']=period[0]
        return res
    
     #Overidden
    def invoice_print(self, cr, uid, ids, context=None):
        case = self.browse(cr, uid, ids[0])
        datas = {
             'ids': ids,
             'model': 'account.invoice',
             }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'sales invoice',
            'datas': datas,
            'name' : case.number and 'sales invoice - ' + case.number or 'sales invoice',
        }
    
    
    def create(self, cr, uid, vals, context = None):
        today = time.strftime("%Y-%m-%d")
        if not vals.get("date_invoice", ''):
            vals.update({
                         "date_invoice" : today 
                         })
        comp_obj = self.pool.get('res.company')
        if vals.get('company_id', False):
            print "sda",vals.get('company_id', False)
            for c in comp_obj.browse(cr, uid, [vals.get('company_id', False)]):
                if not c.parent_id:
                    raise osv.except_osv(_('User Error'), _('You must select sub company sale shop !'))
        return super(account_invoice,self).create(cr, uid, vals, context)
    
    def write(self, cr, uid, ids, vals, context = None):
        ln_ids=[]
        ln_obj = self.pool.get('account.invoice.line')
        res = super(account_invoice, self).write(cr, uid, ids, vals, context = context)
        for case in self.browse(cr, uid, ids):
            cr.execute("update account_invoice_line set company_id ="+str(case.company_id.id) +" where invoice_id ="+ str(case.id))
        return res 
    
    def action_date_assign(self, cr, uid, ids, *args):
        case = self.browse(cr, uid, ids[0])
        for ln in case.invoice_line:
            for t in ln.invoice_line_tax_id:
                if t.company_id.id != case.company_id.id :
                    raise osv.except_osv(_('Configuration Error!'),_('Please define the taxes which is related to the company \n "%s" !')%(case.company_id.name))
        return super(account_invoice, self).action_date_assign(cr, uid, ids, *args)
      
    
#    To Update company_id in account_voucher wizzard
    def invoice_pay_customer(self, cr, uid, ids, context=None):
        inv = self.browse(cr, uid, ids[0])
        res = super(account_invoice, self).invoice_pay_customer(cr, uid, ids, context=context)
        if res:
            res['context'].update({
                 'default_company_id' : inv.company_id.id,
                 })
     
        return res
    
# Overriden
# Round off Calculation
    def action_move_create(self, cr, uid, ids, context=None):
        """Creates invoice related analytics and financial move lines"""
        ait_obj = self.pool.get('account.invoice.tax')
        cur_obj = self.pool.get('res.currency')
        period_obj = self.pool.get('account.period')
        payment_term_obj = self.pool.get('account.payment.term')
        journal_obj = self.pool.get('account.journal')
        move_obj = self.pool.get('account.move')
        if context is None:
            context = {}
        for inv in self.browse(cr, uid, ids, context=context):
            if not inv.journal_id.sequence_id:
                raise osv.except_osv(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise osv.except_osv(_('No Invoice Lines!'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue
            
            ctx = context.copy()
            ctx.update({'lang': inv.partner_id.lang})
            if not inv.date_invoice:
                self.write(cr, uid, [inv.id], {'date_invoice': fields.date.context_today(self,cr,uid,context=context)}, context=ctx)
            company_currency = self.pool['res.company'].browse(cr, uid, inv.company_id.id).currency_id.id
            # create the analytical lines
            # one move line per invoice line
            iml = self._get_analytic_lines(cr, uid, inv.id, context=ctx)
            
            # ------------------------------------------------------------  
            #      ROUND-OFF calculation & passing Journal Entry  
            # ------------------------------------------------------------
            invln_accid = False
            inv_lin =  inv.invoice_line
            if inv_lin:
                inv_lin = inv_lin[0]
            invln_accid = inv_lin.account_id.id 
            print "befor append IML", iml 
            if inv.round_off != 0:
               
               iml.append({
                        'type': 'src',
                        'analytic_account_id': False,
                        'name':'Round-Off',
                        'product_id': False,
                        'uos_id': 1,
                        'taxes': [],
                        'price_unit':inv.round_off,
                        'price':inv.round_off,
                        'account_id':invln_accid,
                        'quantity': 1.0
                      })
            print "After append IML", iml 
            # check if taxes are all computed
            compute_taxes = ait_obj.compute(cr, uid, inv.id, context=ctx)
            self.check_tax_lines(cr, uid, inv, compute_taxes, ait_obj)

            # I disabled the check_total feature
            group_check_total_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'group_supplier_inv_check_total')[1]
            group_check_total = self.pool.get('res.groups').browse(cr, uid, group_check_total_id, context=context)
            if group_check_total and uid in [x.id for x in group_check_total.users]:
                if (inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding/2.0)):
                    raise osv.except_osv(_('Bad Total!'), _('Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise osv.except_osv(_('Error!'), _("Cannot create the invoice.\nThe related payment term is probably misconfigured as it gives a computed amount greater than the total invoiced amount. In order to avoid rounding issues, the latest line of your payment term must be of type 'balance'."))

            # one move line per tax line
            iml += ait_obj.move_line_get(cr, uid, inv.id)

            entry_type = ''
            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
                entry_type = 'journal_pur_voucher'
                if inv.type == 'in_refund':
                    entry_type = 'cont_voucher'
            else:
                ref = self._convert_ref(cr, uid, inv.number)
                entry_type = 'journal_sale_vou'
                if inv.type == 'out_refund':
                    entry_type = 'cont_voucher'

            diff_currency_p = inv.currency_id.id <> company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total = 0
            total_currency = 0
            total, total_currency, iml = self.compute_invoice_totals(cr, uid, inv, company_currency, ref, iml, context=ctx)
            acc_id = inv.account_id.id

            name = inv['name'] or inv['supplier_invoice_number'] or '/'
            totlines = False
            if inv.payment_term:
                totlines = payment_term_obj.compute(cr,
                        uid, inv.payment_term.id, total, inv.date_invoice or False, context=ctx)
            if totlines:
                res_amount_currency = total_currency
                i = 0
                ctx.update({'date': inv.date_invoice})
                for t in totlines:
                    if inv.currency_id.id != company_currency:
                        amount_currency = cur_obj.compute(cr, uid, company_currency, inv.currency_id.id, t[1], context=ctx)
                    else:
                        amount_currency = False

                    # last line add the diff
                    res_amount_currency -= amount_currency or 0
                    i += 1
                    if i == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': acc_id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency_p \
                                and amount_currency or False,
                        'currency_id': diff_currency_p \
                                and inv.currency_id.id or False,
                        'ref': ref,
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': acc_id,
                    'date_maturity': inv.date_due or False,
                    'amount_currency': diff_currency_p \
                            and total_currency or False,
                    'currency_id': diff_currency_p \
                            and inv.currency_id.id or False,
                    'ref': ref
            })

            date = inv.date_invoice or time.strftime('%Y-%m-%d')

            part = self.pool.get("res.partner")._find_accounting_partner(inv.partner_id)

            line = map(lambda x:(0,0,self.line_get_convert(cr, uid, x, part.id, date, context=ctx)),iml)

            line = self.group_lines(cr, uid, iml, line, inv)
            print "Line" , line

            journal_id = inv.journal_id.id
            journal = journal_obj.browse(cr, uid, journal_id, context=ctx)
            if journal.centralisation:
                raise osv.except_osv(_('User Error!'),
                        _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            line = self.finalize_invoice_move_lines(cr, uid, inv, line)

            move = {
                'ref': inv.reference and inv.reference or inv.name,
                'line_id': line,
                'journal_id': journal_id,
                'date': date,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
            }
            period_id = inv.period_id and inv.period_id.id or False
            ctx.update(company_id=inv.company_id.id,
                       account_period_prefer_normal=True)
            if not period_id:
                period_ids = period_obj.find(cr, uid, inv.date_invoice, context=ctx)
                period_id = period_ids and period_ids[0] or False
            if period_id:
                move['period_id'] = period_id
                for i in line:
                    i[2]['period_id'] = period_id

            ctx.update(invoice=inv)
            move_id = move_obj.create(cr, uid, move, context=ctx)
            new_move_name = move_obj.browse(cr, uid, move_id, context=ctx).name
            # make the invoice point to that move
            self.write(cr, uid, [inv.id], {'move_id': move_id,'period_id':period_id, 'move_name':new_move_name}, context=ctx)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move_obj.post(cr, uid, [move_id], context=ctx)
        self._log_event(cr, uid, ids)
        return True

    
    
    
    
account_invoice()

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    
    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            amount = 0.0
            res[line.id] = {'price_total':0.0,'price_subtotal':0.0}
            price = line.price_unit * (1-(line.discount or 0.0)/100.0)
            taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
            if line.invoice_id:
                cur = line.invoice_id.currency_id
                res[line.id]['price_subtotal'] = cur_obj.round(cr, uid, cur, taxes['total'])
                
                #for price total
                amount = taxes['total']
                for t in taxes.get('taxes',False):
                    amount += t['amount'] 
                res[line.id]['price_total'] = round(cur_obj.round(cr, uid, cur, amount))
        return res
    # Updating Cost Price for Report
    def _cost_prize(self, cr, uid, ids, field_name, args, context=None):
        res = {}
#         ids = self.search(cr, uid, [])
        for case in self.browse(cr, uid, ids):
            cost =0.00
            avg_cost = 0.00
            pol_amt=[]
            cr.execute("""select  sum(pl.price_unit) 
                        from purchase_order_line pl 
                        inner join purchase_order po on po.id = pl.order_id 
                        where product_id="""+str(case.product_id.id)+"""  and po.state in ('approved','done')
                        and pl.price_unit >0 
                        and  po.date_order <='"""+str(case.invoice_id.date_invoice)+"""' group by po.date_order,po.id order by po.date_order desc limit 3""")
                        
            pol_amt = [x[0] for x in cr.fetchall()]
            if not pol_amt or 0 in pol_amt:
                avg_cost = (case.price_subtotal)/case.quantity
            else:
                for amount in pol_amt:
                    cost += amount
            if 0.0 not in pol_amt or not pol_amt :
                if len(pol_amt) > 0.00:
                    try:
                         avg_cost = (float(cost) / len(pol_amt))
                    except:
                        pass
            res[case.id] = avg_cost
        return res    
    # Updating Cost Tax Price for Report
    def _cost_prize_tax(self, cr, uid, ids, field_name, args, context=None):
        res = {}
#         ids = self.search(cr, uid, ids)
        for case in self.browse(cr, uid, ids):
            cost =0.00
            avg_cost = 0.00
            pol_amt=[]
            cr.execute("""select  sum(pl.price_subtotal1/pl.product_qty) 
                        from purchase_order_line pl 
                        inner join purchase_order po on po.id = pl.order_id 
                        where product_id="""+str(case.product_id.id)+"""  and po.state in ('approved','done')
                        and pl.price_unit >0 
                        and  po.date_order <='"""+str(case.invoice_id.date_invoice)+"""' group by po.date_order,po.id order by po.date_order desc limit 3""")
                        
            pol_txamt = [x[0] for x in cr.fetchall()]
            if not pol_txamt or 0 in pol_txamt:
                avg_txcost = (case.price_total)/case.quantity
            else:
                for amount in pol_txamt:
                    cost += amount
            if 0.0 not in pol_txamt or not pol_txamt :
                if len(pol_txamt) > 0.00:
                    try:
                         avg_txcost = (float(cost) / len(pol_txamt))
                    except:
                        pass
            res[case.id] = avg_txcost
        return res   
    
    # Updating latest 3 Sale Price(AVG) for Report
    def _sale_prize(self, cr, uid, ids, field_name, args, context=None):
        res = {}
#         ids = self.search(cr, uid, [])
        for case in self.browse(cr, uid, ids):
            cost =0.00
            avg_cost = 0.00
            sol_amt=[]
            cr.execute("""select  sum(sl.price_unit) 
                            from sale_order_line sl 
                            inner join sale_order s on s.id = sl.order_id 
                            where sl.product_id="""+str(case.product_id.id)+""" and s.state='done'
                            and sl.price_unit >0 
                            and  s.date_order <='"""+str(case.invoice_id.date_invoice)+"""'
                            group by s.date_order,s.id
                            order by s.date_order desc limit 3""")
                        
            sol_amt = [x[0] for x in cr.fetchall()]
            if not sol_amt or 0 in sol_amt:
                avg_cost = (case.price_subtotal)/case.quantity
            else:
                for amount in sol_amt:
                    cost += amount
            if 0.0 not in sol_amt or not sol_amt :
                if len(sol_amt) > 0.00:
                    try:
                         avg_cost = (float(cost) / len(sol_amt))
                    except:
                        pass
            res[case.id] = avg_cost
        return res 
     
    
    _columns = {
                'price_total'   :fields.function(_amount_line, string='Tax included in Amount', type="float",
                                                  digits_compute= dp.get_precision('Account'), store=True, multi='all'), 
                'price_subtotal': fields.function(_amount_line, string='Amount', type="float",
                                                  digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'reference': fields.char("Reference", size=20),  
                
                'cost_price' : fields.function(_cost_prize, string='Cost Price', type="float",
                                                  digits_compute= dp.get_precision('Account'), store=True),
                'costwith_txprice' : fields.function(_cost_prize_tax, string='Cost Price With Tax', type="float",
                                                  digits_compute= dp.get_precision('Account'), store=True),
                
                'sale_price' : fields.function(_sale_prize, string='Sales Price', type="float",
                                                  digits_compute= dp.get_precision('Account'), store=True),
                
                }

#     def update_saleprice_button(self, cr, uid, ids, context=None):
#         res = {}
#         ids = self.search(cr, uid, [])
#         for case in self.browse(cr, uid, ids):
#             cost =0.00
#             avg_cost = 0.00
#             pol_amt=[]
#             cr.execute("""select  sum(sl.price_unit) 
#                             from sale_order_line sl 
#                             inner join sale_order s on s.id = sl.order_id 
#                             where sl.product_id="""+str(case.product_id.id)+""" and s.state='done'
#                             and sl.price_unit >0 
#                             and  s.date_order <='"""+str(case.invoice_id.date_invoice)+"""'
#                             group by s.date_order,s.id
#                             order by s.date_order desc limit 3""")
#                          
#             sol_amt = [x[0] for x in cr.fetchall()]
#             if not sol_amt or 0 in sol_amt:
#                 avg_cost = (case.price_subtotal)/case.quantity 
#             else:
#                 for amount in pol_amt:
#                     cost += amount
#             if 0.0 not in sol_amt  or not sol_amt:
#                 if len(sol_amt) > 0.00:
#                     try:
#                          avg_cost = (float(cost) / len(sol_amt))
#                     except:
#                         pass
#             self.write(cr,uid,[case.id],{'sale_price': avg_cost})
#             print "id",
#             print "cost-",avg_cost
#         return res
      
    
#     def update_taxbutton(self, cr, uid, ids, context=None):
#        res = {}
#        ids = self.search(cr, uid, [])
#        for case in self.browse(cr, uid, [1736,1737,1738,1739]):
#             cost =0.00
#             avg_cost = 0.00
#             pol_amt=[]
#             cr.execute("""select  sum(pl.price_subtotal1/pl.product_qty) 
#                         from purchase_order_line pl 
#                         inner join purchase_order po on po.id = pl.order_id 
#                         where product_id="""+str(case.product_id.id)+"""  and po.state in ('approved','done')
#                         and pl.price_unit >0 
#                         and  po.date_order <='"""+str(case.invoice_id.date_invoice)+"""' group by po.date_order,po.id order by po.date_order desc limit 3""")
#                          
#             pol_txamt = [x[0] for x in cr.fetchall()]
#             if not pol_txamt or 0 in pol_txamt:
#                 avg_txcost = (case.price_total)/case.quantity
#             else:
#                 for amount in pol_txamt:
#                     cost += amount
#             if 0.0 not in pol_txamt or not pol_txamt :
#                 if len(pol_txamt) > 0.00:
#                     try:
#                          avg_txcost = (float(cost) / len(pol_txamt))
#                     except:
#                         pass
#             self.write(cr,uid,[case.id],{'cost_price': avg_txcost})
#             print "id",
#             print "cost-",avg_txcost
#        return res
#     
    
    
account_invoice_line()

class account_tax(osv.osv):
    _inherit='account.tax'
    _columns={
              'description': fields.char('Tax Code',size=6),
              
              }
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []
        for record in self.read(cr, uid, ids, ['description','name'], context=context):
            name = record['name'] and record['name'] or record['description']
            res.append((record['id'],name ))
        return res
    
    
account_tax()

class account_move_line(osv.osv):
    _inherit = "account.move.line"
    
    
    def company_default_get(self, cr, uid, object=False, field=False, context=None):
        """
        Check if the object for this company have a default value
        """
        if not context:
            context = {}
            active_id = context.get('active_id', False)
            inv = self.pool.get("account.invoice").browse(cr, uid,active_id)
        return inv.company_id.id
    
    _defaults ={
                'company_id' : company_default_get,
                
                }

account_move_line()
    
class account_bank_statement(osv.osv):
    _inherit = "account.bank.statement"
    
#     Bank Statements Receipts and Payments
    def _get_voucher_lines(self, cr, uid, ids, name, args, context=None):
        res = {} 
        rcpt_ids = pay_ids = []
        voucher_obj = self.pool.get('account.voucher')
        journal_obj = self.pool.get('account.journal')
          
        for case in self.browse(cr, uid, ids):
            res[case.id] = {'receipt_ids': [], 'payment_ids': []}  
            jour_ids = journal_obj.search(cr, uid, [('default_debit_account_id','=',case.journal_id.default_debit_account_id.id)])
                           
            if case.state == 'confirm' or case.closing_date:
                sql_str = "select id from account_bank_statement where closing_date is not null and journal_id = " + str(case.journal_id.id) + " and date < '" + str(case.date) + "' ORDER BY closing_date desc limit 1"
                cr.execute(sql_str)
                prev_id = cr.fetchone() 
                if prev_id:
                    prev_rec = self.browse(cr, uid, prev_id[0])
                    rcpt_ids = voucher_obj.search(cr, uid, [('date','>',prev_rec.closing_date),('date','<=',case.closing_date),('journal_id','in',jour_ids),('type','=','receipt'),('state','=','posted')])
                    pay_ids = voucher_obj.search(cr, uid, [('date','>',prev_rec.closing_date),('date','<=',case.closing_date),('journal_id','in',jour_ids),('type','=','payment'),('state','=','posted')])
               
            else:
                prev_id = self.search(cr, uid, [('journal_id','=',case.journal_id.id), ('state','=','confirm')], order='closing_date desc', limit=1)
                if prev_id:
                    prev_rec = self.browse(cr, uid, prev_id[0])
                    rcpt_ids = voucher_obj.search(cr, uid, [('date','>',prev_rec.closing_date),('journal_id','in',jour_ids),('type','=','receipt'),('state','=','posted')])
                    pay_ids  = voucher_obj.search(cr, uid, [('date','>',prev_rec.closing_date),('journal_id','in',jour_ids),('type','=','payment'),('state','=','posted')])
                    
            res[case.id]['receipt_ids'] = rcpt_ids
            res[case.id]['payment_ids'] = pay_ids 
                
        return res


#     Bank Statements or Cash Registers Cash

    def _get_cash_lines(self, cr, uid, ids, name, args, context=None):
        res = {} 
        cash_ids = []
        stline_obj = self.pool.get('account.bank.statement.line') 
        journal_obj = self.pool.get('account.journal')
          
        for case in self.browse(cr, uid, ids): 
            if case.state == 'confirm' or case.closing_date:
                sql_str = "select id from account_bank_statement where closing_date is not null and journal_id = " + str(case.journal_id.id) + " and date < '" + str(case.date) + "' ORDER BY closing_date desc limit 1"
                cr.execute(sql_str)
                prev_id = cr.fetchone() 
                if prev_id: 
                    prev_cash_st = self.browse(cr, uid, prev_id[0])
                    cr.execute("""  select bl.id
                                    from account_bank_statement b
                                    inner join account_bank_statement_line bl on bl.statement_id = b.id
                                    where bl.account_id  = """ + str(case.journal_id.default_debit_account_id.id) + """
                                    and bl.date > '""" + str(prev_cash_st.closing_date)+ """' and bl.date <= '""" + str (case.closing_date)+ """'
                                    and b.state = 'confirm'
                                """)
                    cash = cr.fetchall()
                    if cash:
                        cash_ids = stline_obj.search(cr, uid, [('id','in',cash)]) 
                                    
                    
            else:
                prev_id = self.search(cr, uid, [('journal_id','=',case.journal_id.id), ('state','=','confirm')], order='closing_date desc', limit=1)
                if prev_id:
                    prev_cash_st = self.browse(cr, uid, prev_id[0])
                    cr.execute("""  select bl.id
                                    from account_bank_statement b
                                    inner join account_bank_statement_line bl on bl.statement_id = b.id
                                    where bl.account_id  = """ + str(case.journal_id.default_debit_account_id.id) + """
                                    and bl.date > '""" + str(prev_cash_st.closing_date)+ """' 
                                    and b.state = 'confirm'
                                """)
                    cash = cr.fetchall()
                    if cash:
                        cash_ids = stline_obj.search(cr, uid, [('id','in',cash)]) 

            res[case.id] = cash_ids
        return res

#    Overriden Total Transaction Calculation
    def _get_sum_entry_encoding(self, cr, uid, ids, name, arg, context=None):

        """ Find encoding total of statements "
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res = {}
        st = self.browse(cr, uid, ids, context=context)
        if st:
            st = st[0]
        p_amt = 0.00
        r_amt = 0.00
        strsptline_amt = 0.00
        stptline_amt = 0.00
        tot = 0.00
        if st.payment_ids:
            for p in st.payment_ids:
                p_amt += p.amount
        if st.line_ids:
            for st_line in st.line_ids:
                if st_line.t_type == "receipt":
                    strsptline_amt +=  st_line.amount
                if st_line.t_type == "payment":
                    stptline_amt +=  st_line.amount
        if st.receipt_ids:
            for r in st.receipt_ids:
                r_amt +=  r.amount
        tot = strsptline_amt +stptline_amt  + r_amt - p_amt
        res[st.id] = tot  
        return res
    
#    Standard for Total Transaction
    def _get_statement_from_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.bank.statement.line').browse(cr, uid, ids, context=context):
            result[line.statement_id.id] = True
        return result.keys()
    
#     Computed Balance
    def _end_balance(self, cursor, user, ids, name, attr, context=None):
        res = {}
        r_amt =0.00
        strsptline_amt = 0.00
        stptline_amt = 0.00
        p_amt = 0.00
        for statement in self.browse(cursor, user, ids, context=context):
           if statement.line_ids:
               for st_line in statement.line_ids:
                   if st_line.t_type == "receipt":
                       strsptline_amt +=  st_line.amount 
                   if  st_line.t_type == "payment":
                       stptline_amt += st_line.amount
           if statement.receipt_ids:
                for r in statement.receipt_ids:
                    r_amt += r.amount 
           if statement.payment_ids:
                for p in statement.payment_ids:
                    p_amt += p.amount 
                    
           res[statement.id] = statement.balance_start + statement.total_entry_encoding
        return res
    
#    Standard for Computed Balance
    def _get_statement(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.bank.statement.line').browse(cr, uid, ids, context=context):
            result[line.statement_id.id] = True
        return result.keys()
    
    _columns={
              'receipt_ids' : fields.function(_get_voucher_lines, method=True, relation='account.voucher', type="many2many", string='Receipts', multi=True),
              'payment_ids' : fields.function(_get_voucher_lines, method=True, relation='account.voucher', type="many2many", string='Payments', multi=True),
              'cash_ids'    : fields.function(_get_cash_lines, method=True, relation='account.bank.statement.line', type="many2many", string='Cash Register'),
              'total_entry_encoding': fields.function(_get_sum_entry_encoding, string="Total Transactions",
                            store = {
                                'account.bank.statement': (lambda self, cr, uid, ids, context=None: ids, ['line_ids','move_line_ids'], 10),
                                'account.bank.statement.line': (_get_statement_from_line, ['amount'], 10),
                                   }),
            'balance_end'   : fields.function(_end_balance,
                            store = {
                                'account.bank.statement': (lambda self, cr, uid, ids, c={}: ids, ['line_ids','move_line_ids','balance_start'], 10),
                                'account.bank.statement.line': (_get_statement, ['amount'], 10),
                            },
                            string="Computed Balance", help='Balance as calculated based on Starting Balance and transaction lines'),
              }


    # Overriden    
#     def balance_check(self, cr, uid, st_id, journal_type='bank', context=None):
#         if not context:
#             context = {}
#         st = self.browse(cr, uid, st_id, context=context)
#         r_amt = 0.00
#         p_amt = 0.00
#         stline_amt = 0.00
#         tot = 0.00
#         if st.receipt_ids:
#             for r in st.receipt_ids:
#                 r_amt += r.amount
#         if st.payment_ids:
#             for p in st.payment_ids:
#                 p_amt += p.amount
#         if st.line_ids:
#             for st_line in st.line_ids:
#                 stline_amt +=  st_line.amount
#             tot = st.balance_start + stline_amt + r_amt - p_amt
#         if not ((abs((tot  or 0.0) - st.balance_end_real) < 0.0001) or (abs((tot or 0.0) - st.balance_end_real) < 0.0001)):
#             raise osv.except_osv(_('Error!'),
#             _('The statement balance is incorrect !\nThe expected balance (%.2f) is different than the computed one. (%.2f)') % (st.balance_end_real, st.balance_end))
#         return True
        
    # Inherited
    def button_confirm_bank(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        for statement in self.browse(cr, uid, ids, context=context):
            r_amt = 0.00
            p_amt = 0.00
            strsptline_amt = 0.00
            stptline_amt = 0.00
            if statement.receipt_ids:
                for r in statement.receipt_ids:
                    r_amt += r.amount 
            if statement.payment_ids:
                for p in statement.payment_ids:
                    p_amt += p.amount
            if statement.line_ids:
                for statement_line in statement.line_ids:
                    if statement_line.t_type == "receipt":
                        strsptline_amt +=  statement_line.amount
                    if statement_line.t_type == "payment":
                        stptline_amt +=  statement_line.amount
            self.write(cr, uid, [statement.id], {
                    'balance_end_real': statement.balance_start + strsptline_amt + stptline_amt + r_amt - p_amt,
                    'closing_date' : time.strftime("%Y-%m-%d %H:%M:%S"),
            }, context=context)
   
#                 print "Total", statement.balance_start + statement_line.amount + r_amt - p_amt
        return super(account_bank_statement,self).button_confirm_bank( cr, uid, ids, context=context)
        
    # Inherited
    def create(self, cr, uid, vals, context=None):
#         if not context:
#             context = {}
#         journal_type = context.get('journal_type', '')
        cur_date = vals.get('date', False)
        journal_obj = self.pool.get("account.journal")
        if cur_date:
            stdt_ids = self.search(cr, uid,[('date','=',cur_date),('journal_id','=',vals.get('journal_id', False))])
            if stdt_ids:
                raise osv.except_osv(_('Warrning!'),_('Your not supposed to create the Multiple Bank Statements on the same date, you can add the lines  !'))
        j_id = vals.get('journal_id',False)
        journal = journal_obj.browse(cr, uid, j_id)
        if j_id:
             vals.update({
                         'company_id' : journal.company_id.id,
                         })
        return super(account_bank_statement,self).create(cr, uid, vals, context=context)
    
    # Inherited
    def write(self, cr, uid, ids, vals, context=None):
        journal_obj = self.pool.get("account.journal")
        case = self.browse(cr, uid, ids)
        if case:
            case = case[0]
        j_id = vals.get('journal_id', case.journal_id.id)
        journal = journal_obj.browse(cr, uid, j_id)
        if j_id:
            vals.update({
                         'company_id' : journal.company_id.id,
                         })
        return super(account_bank_statement,self).write(cr, uid, ids, vals, context=context)     
account_bank_statement()

class account_bank_statement_line(osv.osv):
    _inherit = "account.bank.statement.line"
    _description = "Bank Statement Line"
    _columns={
              't_type'    :   fields.selection([('receipt', 'Receipt'),('payment','Payment')], "Transaction Type"),
              't_amount'  :   fields.float("Amount", digits=(16,2)),
              }
    
        
    def onchange_trnstyp_amount(self, cr, uid, ids, t_type, t_amount):
        res = {}
        if t_amount:
            sign = (t_type == 'payment') and -1 or 1
            res['amount'] = t_amount * sign
        return {'value':res} 
        
account_bank_statement_line()







