from odoo import fields, models, api
from ..utils import get_base_rate

class Currency(models.Model):
    _name = "forexmanager.currency"
    _description = "A model for defining the allowed currencies for this exchange company, and balance."

    currency_base_id = fields.Many2one("res.currency", default=125, readonly=True, required=True) # EUR by default

    name = fields.Char(default="Nueva moneda", compute="_compute_name", store=True, required=True)

    currency_id = fields.Many2one("res.currency", string="Añadir moneda", required=True)
    initials = fields.Char(related="currency_id.name", readonly=True, store=True)
    symbol = fields.Char(related="currency_id.symbol", readonly=True, store=True)
    short_name = fields.Char(related="currency_id.full_name", readonly=True, store=True)

    initial_balance = fields.Monetary(currency_field="currency_id", string="Saldo inicial", default=0.00, required=True) # can't be updated
    current_balance = fields.Monetary(currency_field="currency_id", string="Saldo actual") # add compute, readonly
    base_rate = fields.Float(compute="_compute_base_rate") # currency_id related to currency_base_id
    units_ids = fields.One2many("forexmanager.breakdown", "currency_id", string="Billetes y monedas aceptadas") # Bill and coins    

    active = fields.Boolean(default=True, string="Activa")

    @api.depends("currency_id")
    def _compute_name(self):
        for rec in self:
            if rec.currency_id:
                rec.name = f"{rec.currency_id.name}  ({rec.currency_id.full_name})"
            else:
                rec.name = "Nueva moneda"
    
    @api.depends("currency_id")
    def _compute_base_rate(self):
        for rec in self:
            if rec.currency_id:
                if rec.currency_id != rec.currency_base_id:
                    rec.base_rate = get_base_rate(from_currency=rec.currency_base_id.name, to_currency=rec.currency_id.name)
                else:
                    rec.base_rate = 1
            else:
                rec.base_rate = 0
            
