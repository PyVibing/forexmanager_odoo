from odoo import fields, models, api


class Cashcount(models.Model):
    _name = "forexmanager.cashcount"
    _description = "A model for keep the currency inventory for every desk. Records will be created from create() in model Currency and model Desk."

    name = fields.Char(compute="_compute_name", store=True)
    workcenter_id = fields.Many2one("forexmanager.workcenter", string="Centro de trabajo", required=True)
    desk_id = fields.Many2one("forexmanager.desk", string="Ventanilla", required=True)
    currency_id = fields.Many2one("forexmanager.currency", string="Divisa", required=True)
    balance = fields.Float(string="Balance", required=True)


    @api.depends("workcenter_id", "desk_id", "currency_id")
    def _compute_name(self):
        for rec in self:
            if rec.workcenter_id and rec.desk_id and rec.currency_id:
                rec.name = f"Balance {rec.currency_id.name} para {rec.workcenter_id.name}/{rec.desk_id.name}"
            else:
                rec.name = "Nuevo balance de moneda"