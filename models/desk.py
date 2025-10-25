from odoo import fields, models, api
from odoo.exceptions import ValidationError


class Desk(models.Model):
    """A model for defyning the desks (physical workplaces). Every desk has its own currency inventory."""
    
    _name = "forexmanager.desk"
    _description = "Ventanilla de trabajo"

    # MAIN FIELDS
    name = fields.Char(string="Nombre de ventanilla", required=True)
    workcenter_id = fields.Many2one("forexmanager.workcenter", string="Centro de trabajo", required=True)
    note = fields.Char(string="Notas")

    # OTHER FIELDS
    # Relation with cashcount model
    cashcount_ids = fields.One2many("forexmanager.cashcount", "desk_id", string="Balances de divisas") # One2one
    # A code for linking the odoo desk with the physical desk.
    desk_code = fields.Char(string="Código de vinculación", required=True) # Must be unique (api.constrains)

    @api.constrains("desk_code")
    def _unique_code_desk(self):
        for rec in self:
             if rec.desk_code:
                 exists = self.env["forexmanager.desk"].search([
                    ("desk_code", "=", rec.desk_code),
                    ("id", "!=", rec.id) 
                    ], limit=1)
                 if exists:
                     raise ValidationError(f"Ya existe este código (ID: {exists.id}) para la ventanilla {exists.name}.")
    
    def create(self, vals):
        desk = super().create(vals)
        # Let's create the initial inventory (CashCount model) for this desk, from existing currencies.
        # If a currency is created later, we will update de inventory from create() in Currency model
        currencies_id = desk.workcenter_id.currency_ids # Look for currencies accepted in this workcenter

        for currency_id in currencies_id:
            self.env["forexmanager.cashcount"].create({
                "workcenter_id": desk.workcenter_id.id,
                "desk_id": desk.id,
                "currency_id": currency_id.id,
                "balance": 0,
                })

        return desk

    