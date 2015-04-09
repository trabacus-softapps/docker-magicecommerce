from osv import fields, osv

class account_voucher(osv.osv):
    _inherit = 'account.voucher'
    
    def onchange_company_id(self, cr, uid, ids,company_id,context = None):
        journal_obj = self.pool.get('account.journal')
        ctx = {}
        res = {}
        if context is None: context = {}
        if company_id:
            ctx = dict(context, account_period_prefer_normal=True)
            ctx.update({'company_id':company_id})
            periods = self.pool.get('account.period').find(cr, uid, context=ctx)
            res.update({'period_id':periods[0]})
            j_ids = journal_obj.search(cr,uid,[('company_id','=',company_id),('name','like','Cash')])
            res.update({'journal_id':j_ids[0]})
        return {'value':res}
    
account_voucher()