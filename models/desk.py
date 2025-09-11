from odoo import fields, models, api


class Desk(models.Model): 
    _name = "forexmanager.desk"
    _description = "A model for defyning the desks (physical workplaces). Only for admins."

    name = fields.Char(string="Nombre de ventanilla", required=True)
    workcenter_id = fields.Many2one("forexmanager.workcenter", string="Centro de trabajo", required=True)
    note = fields.Char(string="Notas")

    cashcount_ids = fields.One2many("forexmanager.cashcount", "desk_id", string="Balances de divisas") # One2one
    worksession_ids = fields.One2many("forexmanager.worksession", "desk_id", string="Sesiones en esta ventanilla")
    

    @api.model
    def create(self, vals_list):
        for vals in vals_list: # is a list of dict
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

    