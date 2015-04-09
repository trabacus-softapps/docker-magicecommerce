from osv import fields,osv
from openerp.tools.translate import _
import datetime
from dateutil.relativedelta import relativedelta
from dateutil import parser
class m_portal_request(osv.osv):
    _name = 'm.portal.request'
    _description = "MagicEMart Portal"
    
    def get_partner(self, cr , uid, ids,  context=None):
        
        cr.execute("""select partner_id  from res_users where id =""" +str(uid))
        partner_id = cr.fetchone()
        
        return partner_id
        
    _columns = {
                   'product_ids': fields.one2many('m.product.line','product_lines_id','Product'),
                   'emp_name'   : fields.char('Employee Name', size = 30, required=True),
                   'emp_no'     : fields.char('Employee No.', size = 30, required=True),
                   'user_id'        : fields.many2one('res.users','User',readonly = True),
                   'partner_id'     : fields.many2one('res.partner', 'Customer', readonly = True),
                   'state': fields.selection([('draft', 'New'),('done', 'Done')], 'Status', select=True, readonly=True, track_visibility='onchange'),
               }
    _defaults = {
                    'user_id'   :  lambda s, cr, u, c: u,
                    'partner_id':  get_partner,
                    'state' : 'draft'
                }
    _sql_constraints = [('emp_no', 'unique(emp_no)', 'The Employee No. must be unique')]
        
#     ********Function to create stock move on click of submit********
    def get_product_request(self, cr , uid, ids,  context=None): 
         
        if context == None: context = {}
        move_obj = self.pool.get('stock.move')
        prod_line_obj = self.pool.get('m.product.line')
        moveids = []
         
        for case in self.browse(cr, uid, ids):
            user = self.pool.get('res.users').browse(cr, uid, uid)
            cr.execute("""select s.id from stock_location s inner join res_partner p on p.source_location_id = s.id where p.id =(select partner_id from res_users where id =""" +str(uid)+""")""")
            loc1 = cr.fetchone()
            
            cr.execute("""select s.id from stock_location s inner join res_partner p on p.dest_location_id = s.id where p.id =(select partner_id from res_users where id =""" +str(uid)+""")""")
            loc2 = cr.fetchone()
            
            cr.execute("""SELECT to_char(now(),'mm/dd/yyyy hh:mi:ss')""")
            sysdate = cr.fetchone()
            datexp = parser.parse(sysdate[0])
            for case in self.browse(cr, uid, ids): 
                for p in case.product_ids: 
                    if p.product_qty <= 0:
                         raise osv.except_osv(_('Please'),_('Enter the correct quantity!'))
                    if p.product_qty > p.product_id.qty_available:
                         raise osv.except_osv(_('Warning'),_('Requested quantity for ')+p.product_id.name+_(' is not available in the stock! You can request later'))  
                    if not loc1 and not loc2:
                         raise osv.except_osv(_('Warning'),_('No location found for the customer to send request!!'))
                    vals = { 
                        'product_id'  : p.product_id.id,
                        'product_qty' : p.product_qty,
                        'product_uom' : p.product_id.uom_id and p.product_id.uom_id.id or 0,
                        'name'        : p.product_id.name,
                        'company_id'  : user.company_id and user.company_id.id or 0,
                        'location_id' : loc1[0] or 0,
                        'location_dest_id': loc2[0] or 0,
                        'date_expected'   : datexp
                        }
                      
                    moveid = move_obj.create(cr,uid, vals, context=context)
                    moveids.append(moveid)
                    self.write(cr, uid, ids, {'state':'done'})
                     
            return move_obj.action_done(cr, uid, moveids, context=context)
    
    
m_portal_request()


class m_product_line(osv.osv):
    _name = 'm.product.line'
    _description = "MagicEMart Product Request Line"
    
    _columns = {
                 'product_id': fields.many2one('product.product','Product', required=True),
                 'product_qty': fields.float('Quantity', required=True),
                 'product_lines_id':fields.many2one('m.portal.request','Product Lines',ondelete='cascade', required=True),
               }
        
m_product_line()