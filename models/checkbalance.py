from odoo import fields, models, api
from odoo.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
from ..utils import get_base_rate


class CheckBalance(models.Model):
    """A model for checking initial and final balance for a session."""
    _name = "forexmanager.checkbalance"
    _description = "Arqueo de balance de divisas"

    # MAIN FIELDS
    name = fields.Char(compute="_compute_name", readonly=True, string="Nombre")
    session_id = fields.Many2one("forexmanager.worksession", required=True, readonly=True, string="Sesión")
    user_id = fields.Many2one("res.users", required=True, readonly=True, string="Empleado")
    desk_id = fields.Many2one("forexmanager.desk", required=True, readonly=True, string="Ventanilla")
    date = fields.Datetime(string="Fecha", default=fields.Datetime.now(), readonly=True)
    currency_id = fields.Many2one("forexmanager.currency", required=True, readonly=True, string="Divisa")
    physical_balance = fields.Float(string="En físico", required=True, default=False)
    BD_balance = fields.Float(readonly=True, string="En BD") # manual compute from WorkSession model
    difference = fields.Float(readonly=True, string="Diferencia") # manual compute from WorkSession model (is a temporal difference after search_difference())
    saved_difference = fields.Float(readonly=True, string="Quebranto") # Assign after confirm balance
    value = fields.Float(compute="_compute_value", string="Valor en moneda base", store=True) # Shows the value in base currency for the saved_difference
    checked = fields.Boolean(default=False, readonly=True, string="Chequeado") # True after search_difference() in model WorkSession
    confirmed = fields.Boolean(default=False, readonly=True, string="Confirmado") # True after confirm_balances() in model WorkSession
    closed = fields.Boolean(default=True, string="Cerrado") # When there is a saved_difference, admins have to explain in the notes and close it
    closed_by = fields.Many2one("res.users", string="Cerrado por")
    note = fields.Text(string="Notas")
   

    @api.depends("saved_difference", "currency_id")
    def _compute_value(self):
        for rec in self:
            if rec.saved_difference and rec.currency_id:
                base_rate = Decimal(get_base_rate(
                                            from_currency=rec.currency_id.initials, 
                                            to_currency=rec.currency_id.currency_base_id.name)).quantize(
                                                                                            Decimal("0.01"), rounding=ROUND_HALF_UP
                                    ) if rec.currency_id.initials != rec.currency_id.currency_base_id.name else 1
                rec.value = float(Decimal(Decimal(rec.saved_difference) * base_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            else:
                rec.value = 0

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
            # Check if record was previously open (not closed) and now is closed
            # to assign closed_by a value
            if not rec.closed and ("closed" in vals and vals["closed"]):
                rec.closed_by = self.env.user.id

            checkbalance = super().write(vals)

            if self.env.context.get('from_list_view') and rec.saved_difference and not rec.note and rec.closed:
                raise ValidationError("Debes añadir unas notas explicando este quebranto.")
            
        return checkbalance