from odoo import fields, models

# delete later, not used
class Rate(models.Model):
    _name = "forexmanager.rate"
    _description = "A model for stablishing the commercial rates, based on the oficial rates."

    currency_base = fields.Many2one("forexmanager.currency", string="Moneda base") # EUR by default
    currency_source = fields.Many2one("forexmanager.currency", string="Moneda ofrecida")
    currency_target = fields.Many2one("forexmanager.currency", string="Moneda demandada")
