from odoo import fields, models, api
from odoo.exceptions import ValidationError
from ..utils import create_initial_inventories


class WorkCenter(models.Model):
    _name = "forexmanager.workcenter"
    _description = "A model for defyning all the workcenters for the Exchange Currency Company. Only for admins."

    name = fields.Char(string="Nombre del centro", required=True)
    desk_ids = fields.One2many("forexmanager.desk", "workcenter_id", string="Ventanillas")
    note = fields.Char(string="Notas")

    currency_ids = fields.Many2many(
        comodel_name="forexmanager.currency",
        relation="workcenter_currency_rel",
        column1="workcenter_id",
        column2="currency_id",
        string="Monedas aceptadas"
        )

    # Call from button in list view ONLY FOR DEV --- DELETE
    def create_inventories(self):
        create_initial_inventories(self)
        
    
    def write(self, vals):
        for rec in self:

            if "currency_ids" in vals: # Means user is editing this field
                currency_vals = vals["currency_ids"]
                for currency_val in currency_vals:
                    currency_val_id = currency_val[1]
                    if currency_val[0] == 3: 
                        # Means the user is deleting the relation with this currency (currency_rec)
                        # So let's check if there is balance > 0 for this currency in cashcount for every desk in 
                        # this workcenter and avoid deleting the relation
                        for desk_id in rec.desk_ids:
                            cashcount_rec = self.env["forexmanager.cashcount"].search([
                                ("desk_id", "=", desk_id),
                                ("workcenter_id", "=", rec.id),
                                ("currency_id", "=", currency_val_id)
                                ], limit=1)
                            if cashcount_rec:
                                if cashcount_rec.balance > 0:
                                    currency = cashcount_rec.currency_id
                                    raise ValidationError(f"No puede desvincular este centro de trabajo de la divisa {currency.name} mientras existan ventanillas con saldo de esta divisa mayor que 0.00 {currency.initials}")
                                else:
                                    cashcount_rec.unlink()
                        
                    elif currency_val[0] == 4: 
                        # Means the user is adding a new accepted currency for this workcenter
                        # So let's create the initial inventory (cashcount) for this currency and desk
                        workcenter = super().write(vals)
                        create_initial_inventories(self.env["forexmanager.workcenter"].browse(rec.id))

            workcenter = super().write(vals)
        return workcenter