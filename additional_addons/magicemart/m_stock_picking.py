from openerp import netsvc
from osv import fields, osv
import time
import datetime
from lxml import etree
from datetime import datetime
from openerp.tools.translate import _
from openerp.osv.orm import setup_modifiers

class stock_picking_in(osv.osv):
    _name = 'stock.picking.in'
    _inherit = 'stock.picking.in'
    _columns = {
                'date_from'    : fields.function(lambda *a, **k:{}, method=True, type='date', string="From"),
                'date_to'      : fields.function(lambda *a, **k:{}, method=True, type='date', string="To"),
                'terms'                : fields.text("Terms And Condition"),
                'return_st'     : fields.boolean('Returned Delivery Order'),
#                 'receive_date' : fields.date("Receive Date"),
                }

stock_picking_in()


class stock_picking_out(osv.osv):
    _name = 'stock.picking.out'
    _inherit = 'stock.picking.out'
    
    _columns = {
                'contact_id'   : fields.many2one('res.partner', 'Contact Person'),
                'vehicle'      : fields.char('Vehicle', size=15),
                 # fields to Populate Invoce Number
                'invoice_id'       : fields.many2one('account.invoice', 'Invoice'),
                'date_from'    : fields.function(lambda *a, **k:{}, method=True, type='date', string="From"),
                'date_to'      : fields.function(lambda *a, **k:{}, method=True, type='date', string="To"),
                'terms'                : fields.text("Terms And Condition"),
                'delivery_date' : fields.date("Delivery Date"),
                'return_st'     : fields.boolean('Returned Delivery Order'),
                }
    
    _defaults = {
               'return_st'  :False,
            }
 
    
    
    # Check Availability
    def action_assign(self, cr, uid, ids, *args):
        move_obj = self.pool.get("stock.move")
        for pick in self.browse(cr, uid, ids):
            move_ids = [x.id for x in pick.move_lines if x.state == 'confirmed']
            for op in move_obj.browse(cr, uid, move_ids):
                quantity_available = move_obj.get_qty(cr, uid, op.product_id.id, op.location_id.id)
                if op.product_qty > quantity_available and pick.type in ('out'):
                   raise osv.except_osv(_('Warning'), _(str(op.product_id.name_template) + ' Quantity is greater than the Available Stock!!!'))
        return super(stock_picking_out, self).action_assign(cr, uid, ids, *args)
    

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('company_id', False):
            for case in self.browse(cr, uid, ids):
                if case.sale_id.company_id.id != vals.get('company_id', False):
                    raise osv.except_osv(_('User Error'), _('Company mismatch between Quotation and Delivey Order'))
        return super(stock_picking_out, self).write(cr, uid, ids, vals, context=context)
    
    
stock_picking_out()

class stock_picking(osv.osv):
    _name = 'stock.picking'
    _inherit = 'stock.picking'
    
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        
        if context is None:
            context = {}
        res = super(stock_picking, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        doc = etree.XML(res['arch'])
        shipment_type = context.get('default_type', False)
        if shipment_type == 'internal':
            if view_type == 'form':
                for node in doc.xpath("//field[@name='partner_id']"):
                    node.set('invisible', '1')
                    setup_modifiers(node, res['fields']['partner_id'])
                    res['arch'] = etree.tostring(doc)
        return res
    
    
    _columns = {
                'contact_id'       : fields.many2one('res.partner', 'Contact Person'),
                'vehicle'          : fields.char('Vehicle', size=15),
                'invoice_id'       : fields.many2one('account.invoice', 'Invoice'),
                'available_qty'    : fields.char("Available Quantity", size=15),
                'date_from'        : fields.function(lambda *a, **k:{}, method=True, type='date', string="From"),
                'date_to'          : fields.function(lambda *a, **k:{}, method=True, type='date', string="To"),
                'terms'            : fields.text("Terms And Condition"),
                'delivery_date'    : fields.date("Delivery Date"),
                'receive_date'     : fields.date("Receive Date"),
                'return_st'        : fields.boolean('Returned Delivery Order'),
                
         
                
                }
    
    _defaults = {
               'return_st'  :False,
            }
    
 # Overriden
    def action_invoice_create(self, cr, uid, ids, journal_id=False,
            group=False, type='out_invoice', context=None):
        """ Creates invoice based on the invoice state selected for picking.
        @param journal_id: Id of journal
        @param group: Whether to create a group invoice or not
        @param type: Type invoice to be created
        @return: Ids of created invoices for the pickings
        """
        if context is None:
            context = {}
  
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        partner_obj = self.pool.get('res.partner')
#         tax_obj = self.pool.get('account.invoice.tax')
        invoices_group = {}
        res = {}
        inv_type = type
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.invoice_state != '2binvoiced':
                continue
            partner = self._get_partner_to_invoice(cr, uid, picking, context=context)
            if isinstance(partner, int):
                partner = partner_obj.browse(cr, uid, [partner], context=context)[0]
            if not partner:
                raise osv.except_osv(_('Error, no partner!'),
                    _('Please put a partner on the picking list if you want to generate invoice.'))
  
            if not inv_type:
                inv_type = self._get_invoice_type(picking)
  
            if group and partner.id in invoices_group:
                invoice_id = invoices_group[partner.id]
                invoice = invoice_obj.browse(cr, uid, invoice_id)
                invoice_vals_group = self._prepare_invoice_group(cr, uid, picking, partner, invoice, context=context)
                invoice_obj.write(cr, uid, [invoice_id], invoice_vals_group, context=context)
            else:
                invoice_vals = self._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
                invoice_id = invoice_obj.create(cr, uid, invoice_vals, context=context)
                invoices_group[partner.id] = invoice_id
            res[picking.id] = invoice_id
            for move_line in picking.move_lines:
                if move_line.state == 'cancel':
                    continue
                if move_line.scrapped:
                    # do no invoice scrapped products
                    continue
                vals = self._prepare_invoice_line(cr, uid, group, picking, move_line,
                                invoice_id, invoice_vals, context=context)
                
                if vals:
                    # while merging
                    invln_id = invoice_line_obj.search(cr, uid, [('account_id', '=', vals.get('account_id')), ('price_unit', '=', vals.get('price_unit')),
                                                                  ('invoice_id', '=', vals.get('invoice_id')), ('product_id', '=', vals.get('product_id')),
                                                                  ('discount', '=', vals.get('discount'))])
                    
                    if invln_id:
                        qty = 0
                        # While merging DO, if it contains same product in different DO's just adding the quantity in invoice line
                        for inv_ln in invoice_line_obj.browse(cr, uid, invln_id):
                            if vals.get('invoice_line_tax_id') == [(6, 0, [x.id for x in inv_ln.invoice_line_tax_id])]:
                                qty = inv_ln.quantity + vals.get('quantity') 
                                invoice_line_obj.write(cr, uid, invln_id, {'quantity':qty})    
                        
                    else:
                                 
                        invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=context)
                        self._invoice_line_hook(cr, uid, move_line, invoice_line_id)
  
            invoice_obj.button_compute(cr, uid, [invoice_id], context=context,
                    set_total=(inv_type in ('in_invoice', 'in_refund')))
            self.write(cr, uid, [picking.id], {
                'invoice_state': 'invoiced',
                }, context=context)
            self._invoice_hook(cr, uid, picking, invoice_id)
        self.write(cr, uid, res.keys(), {
            'invoice_state': 'invoiced',
            }, context=context)
        return res
  
    
    
    
    
    # Inherit Creating Invoice
    def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        stock_obj = self.pool.get("stock.picking.out")
        accinv_obj = self.pool.get("account.invoice")
        journal_obj = self.pool.get("account.journal")
        account_obj = self.pool.get("account.account")
        period_obj = self.pool.get("account.period")
        invoice_vals = super(stock_picking, self)._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context)
        do_name = ''
        ctx = {}
        for pick in self.browse(cr, uid, context.get('active_ids', [])):
            if invoice_vals.get('partner_id', False) == pick.partner_id.id:
                do_name += pick.name + ', '
            if len(context.get('active_ids', [])) == 1:
                invoice_vals.update({
                                     'vehicle'     : pick.vehicle and pick.vehicle or False,
                                     'transport'   : pick.carrier_tracking_ref or False,
                                     'contact_id'  : pick.contact_id and pick.contact_id.id or False,
                                     'company_id'  : pick.company_id.id,
                                     })

            
            invoice_vals.update({
                'dc_ref'         : do_name and do_name[0:-2] or None,
                
                                })
#         onchange_company = accinv_obj.onchange_company_id(cr, uid, pick.id, pick.company_id.id, partner, inv_type, [0,0,False],False)
        return invoice_vals
#     
    def _prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id, invoice_vals, context=None):
        soline_obj = self.pool.get("sale.order.line")
        invline_obj = self.pool.get("account.invoice.line")
        stkrtn_obj = self.pool.get("stock.return.picking")
        update_line = False
        if context is None:
            context = {}
        context.update({'active_id':picking.id})
        invoice_vals = super(stock_picking, self)._prepare_invoice_line(cr, uid, group, picking=picking, move_line=move_line, invoice_id=invoice_id, invoice_vals=invoice_vals, context=context)
        
        # Creating Invoice for delivery Order in which some products returned         
        res = stkrtn_obj.default_get(cr, uid, '[product_return_moves, invoice_state]', context=context)
        if res:
            for m in res['product_return_moves']:
                # for back order validation 
                if move_line.id in [x.id for x in picking.move_lines]:
                    if m['move_id'] == move_line.id:
                       if m['quantity'] <= move_line.product_qty:
                            invoice_vals.update({
                                                 'quantity' : m['quantity']
                                                 })
                            update_line = True
                            break
                       else:
                            update_line = False
                    else:
                        update_line = False
                else:
                    update_line = True         
                                
        if picking and picking.type == 'out':  
            sale = picking.sale_id
            if sale:
                for sol in sale.order_line:
                    if sol.id == move_line.sale_line_id.id and sol.reference:
                        invoice_vals.update({
                                             'reference'    :   sol.reference or '',
                                             })

        if update_line:                
            return invoice_vals
        else:
            return False
        
# For customer Portal,for returned Product records showing in seperate menu so making this field as True to differentiat 
#     def write(self, cr, uid, ids, vals, context=None):
#         if not context:
#             context = {}
#         return_st = context.get('return_st', False)
#         vals.update({
#                      'return_st':return_st,
#                      })
#         return super(stock_picking, self).write(cr, uid, ids, vals, context=context)  
#          

    def stock_internal_transfer(self, cr, uid, ids, context=None):
        for case in self.browse(cr, uid, ids):
            report_name = 'Stock Internal Transfer'
            data = {}
            data['ids'] = ids
            data['model'] = 'stock.move'
            data['output_type'] = 'xls'
                 
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
            'context' :context
    }

               
stock_picking()

class stock_invoice_onshipping(osv.osv_memory):
    _inherit = "stock.invoice.onshipping"
    _description = "Stock Invoice Onshipping"

    _columns = {
        'invoice_date': fields.date('Invoiced date'),
    }

    _defaults = {
                 'invoice_date' : time.strftime('%Y-%m-%d')
                 }
    # updating invoice_ to invoice_id field in delivery order
    def create_invoice(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        context.get('active_ids').sort()
        pick_obj = self.pool.get("stock.picking")
        accinv_obj = self.pool.get("account.invoice")
        invoice_id = super(stock_invoice_onshipping, self).create_invoice(cr, uid, ids, context)
        if invoice_id:
            for pick_id in context.get('active_ids', []):
                pick = pick_obj.browse(cr, uid, pick_id)
                pick_obj.write(cr, uid, pick_id, {'invoice_id':invoice_id[pick_id]})
                onchange_company = accinv_obj.onchange_company_id(cr, uid, [invoice_id[pick_id]], pick.company_id.id, pick.partner_id.id, 'out_invoice', [0, 0, False], False)
#                 print "vals", [[invoice_id][pick_id]]
                accinv_obj.write(cr, uid, [invoice_id[pick_id]], onchange_company['value'])
                
        return invoice_id
    
stock_invoice_onshipping()
    
     
class stock_return_picking(osv.osv_memory):
    _inherit = 'stock.return.picking'
    _description = 'Return Picking'
      
     
    def onchange_invoicing(self, cr, uid, ids, invoice_state, context=None):
        inv_obj = self.pool.get("account.invoice")
        stock_obj = self.pool.get("stock.picking")
        if not context:
            context = {}
        res = {}
        warning = ""
        pick_id = context.get("active_id", False)
        if pick_id:
            pick = stock_obj.browse(cr, uid, pick_id)
             
            if pick.invoice_state == "2binvoiced": 
#                 if pick_id not in inv_obj.origin:
                warning = {
                                 'title':_('Warning'),
                                        'message':_(' You are not supposed Refund, beacuse Invoice is not Created for this Record. So Please Select the No Invoicing Option. ')
                                                   
                                     }
                res.update({
                            'invoice_state' : 'none',
                            })
            else:
                warning = {
                     'title':_('Warning'),
                            'message':_(' You are not supposed Select No Invoicing Option, beacuse Invoice is already Created for this Record. So Please Select the Refund Option Option. ')
                                            
                         }
                res.update({
                            'invoice_state' : '2binvoiced',
                            })
                  
        return{'value':res , 'warning':warning}
       
      
      
    # Overriden
    def create_returns(self, cr, uid, ids, context=None):
        """ 
         Creates return picking.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of ids selected
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {} 
        record_id = context and context.get('active_id', False) or False
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        uom_obj = self.pool.get('product.uom')
        data_obj = self.pool.get('stock.return.picking.memory')
        act_obj = self.pool.get('ir.actions.act_window')
        model_obj = self.pool.get('ir.model.data')
        wf_service = netsvc.LocalService("workflow")
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        data = self.read(cr, uid, ids[0], context=context)
        date_cur = time.strftime('%Y-%m-%d %H:%M:%S')
        set_invoice_state_to_none = True
        returned_lines = 0
        
#        Create new picking for returned products
#         inv_state = ""
        seq_obj_name = 'stock.picking'
        new_type = 'internal'
        if pick.type == 'out':
            return_st = True
            new_type = 'in'
            seq_obj_name = 'stock.picking.in'
        elif pick.type == 'in':
            return_st = False
            new_type = 'out'
            seq_obj_name = 'stock.picking.out'
        new_pick_name = self.pool.get('ir.sequence').get(cr, uid, seq_obj_name)
        new_picking = pick_obj.copy(cr, uid, pick.id, {
                                        'name': _('%s-%s-return') % (new_pick_name, pick.name),
                                        'move_lines': [],
                                        'state':'draft',
                                        'type': new_type,
                                        'date':date_cur,
                                        'invoice_state': data['invoice_state'],
        })
        
        val_id = data['product_return_moves']
        for v in val_id:
            data_get = data_obj.browse(cr, uid, v, context=context)
            mov_id = data_get.move_id.id
            if not mov_id:
                raise osv.except_osv(_('Warning !'), _("You have manually created product lines, please delete them to proceed"))
            new_qty = data_get.quantity
            move = move_obj.browse(cr, uid, mov_id, context=context)
            new_location = move.location_dest_id.id
            returned_qty = move.product_qty
            for rec in move.move_history_ids2:
                returned_qty -= rec.product_qty

            if returned_qty != new_qty:
                set_invoice_state_to_none = False
            if new_qty:
                returned_lines += 1
                new_move = move_obj.copy(cr, uid, move.id, {
                                            'product_qty': new_qty,
                                            'product_uos_qty': uom_obj._compute_qty(cr, uid, move.product_uom.id, new_qty, move.product_uos.id),
                                            'picking_id': new_picking,
                                            'state': 'draft',
                                            'location_id': new_location,
                                            'location_dest_id': move.location_id.id,
                                            'date': date_cur,
                })
                move_obj.write(cr, uid, [move.id], {'move_history_ids2':[(4, new_move)]}, context=context)
        if not returned_lines:
            raise osv.except_osv(_('Warning!'), _("Please specify at least one non-zero quantity."))
        
        # update state as 2binvoiced for delivery order after returning some products  
        return_history = self.get_return_history(cr, uid, pick.id, context=context)
        if return_history:
            for m in pick.move_lines: 
                if m.product_qty != return_history[m.id] :
                    pick_obj.write(cr, uid, [pick.id], {'invoice_state':'2binvoiced'}, context=context)
#                     inv_state = "2binvoiced"
                    break
                  
                else:
                    pick_obj.write(cr, uid, [pick.id], {'invoice_state':'none'}, context=context)
#                     inv_state = "none"
                    print "State--------",pick.invoice_state
        wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
        pick_obj.force_assign(cr, uid, [new_picking], context)
        # For customer Portal,for returned Product records showing in seperate menu so making this field as True to differentialt
        context.update({"return_st":True})
        pick_obj.write(cr, uid, [new_picking], {'return_st':return_st, 'invoice_state':'2binvoiced'}, context=context)
        
        if pick.invoice_state == "2binvoiced":
            pick_obj.write(cr, uid, [new_picking], {'return_st':return_st, 'invoice_state': 'none'}, context=context)
       
            
        
            
        # Update view id in context, lp:702939
        model_list = {
                'out': 'stock.picking.out',
                'in': 'stock.picking.in',
                'internal': 'stock.picking',
        }
        return {
            'domain': "[('id', 'in', [" + str(new_picking) + "])]",
            'name': _('Returned Picking'),
            'view_type':'form',
            'view_mode':'tree,form',
            'res_model': model_list.get(new_type, 'stock.picking'),
            'type':'ir.actions.act_window',
            'context':context,
        }




stock_return_picking()
    
class stock_move(osv.osv):
    _inherit = "stock.move"
    
     # To get Qty of Perticular Stock
    def get_qty(self, cr, uid, product_id, location_id):
        prod_obj = self.pool.get("product.product")
        result = prod_obj.get_product_available(cr, uid, [product_id], context={'states':('done',), 'what':('in', 'out'), 'location':location_id})
        qty = result.get(product_id, 0.00)
        return qty
    
#     def _amount_subtotal(self,cr, uid, ids, field_name, args, context=None):
#         res ={}
#         for move in self.browse(cr, uid, ids):
#             amt = move.product_id.standard_price * move.product_qty
#             res[move.id] = amt
#         return res
        
    
    _columns = {
    
                'available_qty'     : fields.float("Available Quantity", digits=(16, 4)),
                'product_image'     : fields.binary('Product Image'),
                
                'c_price'           : fields.related('product_id', 'standard_price', type="float", string="Price", store=True),
#                 'sub_total'         : fields.function(_amount_subtotal, type='float', string='Sub Total', store=True),
                
            }

    _order = 'id asc'
    
    # Updating Available qty & Product Image. 
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False,
                            loc_dest_id=False, partner_id=False):
        prod_obj = self.pool.get('product.product')
        result = super(stock_move, self).onchange_product_id(cr, uid, ids, prod_id=prod_id, loc_id=loc_id, loc_dest_id=loc_dest_id, partner_id=partner_id)['value']
        prod = prod_obj.browse(cr, uid, [prod_id])[0]
        qty = self.get_qty(cr, uid, prod_id, loc_id)
        result.update({
                      'available_qty'   :   qty,
                      'product_image'   :   prod.image_medium
                      })

        return {'value': result}
    
   
    def write(self, cr, uid, ids, vals, context=None):
        for move in self.browse(cr, uid, ids):
            qty = self.get_qty(cr, uid, move.product_id.id, move.location_id.id)
            cr.execute("update stock_move set available_qty=" + str(qty) + " where id =" + str(move.id))
        return super(stock_move, self).write(cr, uid, ids, vals, context)
    
    # Should not Select the Location which as  Children
    def onchange_location_id(self, cr, uid, ids, location_id=False, location_dest_id=False, context=None):
        if not context:
            context = {}
        res = {}
        warning = ""
        loc_obj = self.pool.get("stock.location")
        if context.get('type'): 
            if location_id:
                loc_ids = loc_obj.search(cr, uid, [('location_id', '=', location_id)])
                if loc_ids:
                    res['location_id'] = False
                    warning = {
                                                 'title':_('Location Warning'),
                                                        'message':_(' You cant Select This Location, Please Select Stock / Output ')
                                                     }
            if location_dest_id:
                loc_ids = loc_obj.search(cr, uid, [('location_id', '=', location_dest_id)])
                if loc_ids:
                    res['location_dest_id'] = False
                    warning = {
                                                 'title':_('Location Warning'),
                                                        'message':_(' You cant Select This Location, Please Select Stock / Output ')
                                                     }
                 
        return{'value':res , 'warning':warning}
        
    """ Updating Customer Stock if there, else Updating Just Customer Location.
         Updating Company Stock while Incoming Shipment based on Company """
         
    def create(self, cr, uid, vals, context=None):
        stock_obj = self.pool.get("stock.picking")
        partner_obj = self.pool.get("res.partner")
        loc_obj = self.pool.get("stock.location")
        location_id = vals.get('location_id')
        location_dest_id = vals.get('location_dest_id')
        if location_id:
            loc_id = loc_obj.search(cr, uid, [('location_id', '=', location_id)])
            if loc_id:
                raise osv.except_osv(_('Warning'), _('You cant Select This Location, Please Select Stock / Output !'))
        
        if location_dest_id:
            loc_id = loc_obj.search(cr, uid, [('location_id', '=', location_dest_id)])
            if loc_id:
                raise osv.except_osv(_('Warning'), _('You cant Select This Location, Please Select Stock / Output !'))
        partner_id = vals.get('partner_id', '')
        partner = partner_obj.browse(cr, uid, partner_id)
        if partner_id:
            part_stock = partner.source_location_id.id
            pick_id = vals.get("picking_id")
            # This proces should work only if they create through Sale or Delivery Order not Through Stock moves
            if pick_id:
                pick = stock_obj.browse(cr, uid, pick_id)
            # Update Customer Stock
                if part_stock and pick.type == "out":
                    vals.update({
                                 'location_dest_id' : part_stock
                                })
                # Return delivery Order update Company Location    
                if part_stock and pick.type == "in":
                    vals.update({
                                 'location_dest_id' : location_dest_id
                                })
                else:            
                    if pick.type == "out" and "return" not in pick.name and not part_stock:   
                        custloc_id = loc_obj.search(cr, uid, [('complete_name', '=', 'Partner Locations / Customers / Stock')])
                        if custloc_id:
                            custloc_id = custloc_id[0]
                        vals.update({
                                     'location_dest_id' : custloc_id
                                     })
                    if pick.type == "out" and "return" in pick.name:   
                        suplloc_id = loc_obj.search(cr, uid, [('complete_name', '=', 'Partner Locations / Suppliers / Stock')])
                        if suplloc_id:
                            suplloc_id = suplloc_id[0]
                        vals.update({
                                     'location_dest_id' : suplloc_id
                                     })
                        
                    if pick.type == "in" and "return" in pick.name:   
                        comploc_id = loc_obj.search(cr, uid, [('name', '=', 'Stock'), ('company_id', '=', vals.get("company_id"))])
                        if comploc_id:
                            comploc_id = comploc_id[0]
                        vals.update({
                                     'location_dest_id' : comploc_id
                                     })    
        if vals.get("type") == "in":
            comploc_id = loc_obj.search(cr, uid, [('name', '=', 'Stock'), ('company_id', '=', vals.get("company_id"))])
            if comploc_id:
                comploc_id = comploc_id[0]
            vals.update({
                         'location_dest_id' : comploc_id
                         })
        return super(stock_move, self).create(cr, uid, vals, context)
    

stock_move()

class stock_warehouse_orderpoint(osv.osv):
    """
    Defines Minimum stock rules.
    """
    _inherit = "stock.warehouse.orderpoint"
    _description = "Minimum Inventory Rule"
    _columns = {
#                 'body_text' : fields.text("Body Text"),
                   'prod_body' : fields.text("Products"),
                   'minqty_body' : fields.text("Minimum Quanity") 
                }
    
    # Sending a Mail to Warehouse,Sales,Purchase Managers Every day if Stock Reaches the minimum Level
    def send_mail(self, cr, uid, ids, context=None):
        to_emails = ''
        subject = ''
#         body = ''
        case = self.browse(cr, uid, ids)[0]
        mail_obj = self.pool.get("mail.mail")
        partner_obj = self.pool.get("res.partner")
        email_obj = self.pool.get('email.template')
         
        cr.execute("""
                        select distinct rp.email
                            from res_groups_users_rel gu 
                            inner join res_groups g on g.id = gu.gid
                            inner join res_users ru on ru.id = gu.uid
                            inner join res_partner rp on rp.id = ru.partner_id
                            and g.category_id in (select id from ir_module_category where name in('Purchases','Warehouse','Sales'))
                            and g.name ='Manager' and rp.email is not null
                """)
         
        managers = [x[0] for x in cr.fetchall()]
        if managers:
            for m in managers:
                to_emails += m + ',' 
         
        template = self.pool.get('ir.model.data').get_object(cr, uid, 'magicemart', 'email_template_record_rule')
        email_obj.write(cr, uid, [template.id], {'email_to'      :  to_emails[:-1]})
        assert template._name == 'email.template'
        mail_id = self.pool.get('email.template').send_mail(cr, uid, template.id, case.id, True, context=context)
        return True


    # Schedular for Stock Re-Ordering
    def do_stock_reorder(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
#     def do_stock_reorder(self, cr, uid, ids, context=None):
        print "inside schedular"
        mail_obj = self.pool.get("mail.mail")
        product_obj = self.pool.get("product.product")
        move_obj = self.pool.get("stock.move")
        reorder_ids = self.search(cr, uid, [])
        b = ''
        c = ''
        
        if reorder_ids:
            for case in self.browse(cr, uid, reorder_ids):
                available_qty = move_obj.get_qty(cr, uid, case.product_id.id, case.location_id.id)
                if available_qty <= case.product_min_qty:
                    b += case.product_id.name + '\n'
                    c += str(case.product_min_qty) + '\n'
            self.write(cr, uid, reorder_ids, {'prod_body': b , 'minqty_body': c})
            self.send_mail(cr, uid, [case.id], context=context)
        return True 
    


stock_warehouse_orderpoint()


class stock_partial_picking(osv.osv_memory):
    _inherit = "stock.partial.picking"
    # Created 2 fields & Updating date when product received and Delivery
    def do_partial(self, cr, uid, ids, context=None):
        res = super(stock_partial_picking, self).do_partial(cr, uid, ids, context=context)
        if not context:
            context = {}
        active_id = context.get('active_id', '')
        today = time.strftime('%Y-%m-%d')
        pickin_obj = self.pool.get("stock.picking.in")
        pickout_obj = self.pool.get("stock.picking.out")
        pick = pickin_obj.browse(cr, uid, active_id)
        if pick and pick.type == "in":
            pickin_obj.write(cr, uid, pick.id, {'receive_date': today})
            return res
        if pick and pick.type == "out":
            pickout_obj.write(cr, uid, pick.id, {'delivery_date': today})
            return res                
stock_partial_picking()

 
