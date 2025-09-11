from odoo import fields, models, api


class CheckBalance(models.Model):
    _name = "forexmanager.checkbalance"
    _description = "A model for checking initial and final balance for a session."

    name = fields.Char(compute="_compute_name", readonly=True)
    session_id = fields.Many2one("forexmanager.worksession", required=True, readonly=True)
    user_id = fields.Many2one("res.users", required=True, readonly=True)
    desk_id = fields.Many2one("forexmanager.desk", required=True, readonly=True)
    currency_id = fields.Many2one("forexmanager.currency", required=True, readonly=True)
    physical_balance = fields.Float(string="Cantidad en físico", required=True, default=False)
    BD_balance = fields.Float(readonly=True) # manual compute
    difference = fields.Float(readonly=True) # manual compute from WorkSession model (is a temporal difference after search_difference())
    saved_difference = fields.Float(readonly=True, string="Quebranto")
    checked = fields.Boolean(default=False, readonly=True) # True after search_difference() in model WorkSession
    confirmed = fields.Boolean(default=False, readonly=True) # True after confirm_balances() in model WorkSession
    

    @api.depends("currency_id", "session_id")
    def _compute_name(self):
        for rec in self:
            if rec.currency_id and rec.session_id:
                session_type_field = rec.session_id._fields["session_type"]
                session_label = dict(session_type_field.selection).get(rec.session_id.session_type)
                rec.name = f"{session_label} de divisa {rec.currency_id.name}"
            else:
                rec.name = "Nuevo arqueo de divisa"

    def write(self, vals):
        for rec in self:
            checkbalance = super().write(vals)

            return checkbalance