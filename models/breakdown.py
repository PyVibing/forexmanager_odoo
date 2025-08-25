from odoo import fields, models, api

class Breakdown(models.Model):
    _name = "forexmanager.breakdown"
    _description = "A model for defyning the bills and coins for a currency."

    name = fields.Char(compute="_compute_name") # agregar compute
    currency_id = fields.Many2one("forexmanager.currency", string="Moneda", required=True)
    unit = fields.Selection([
        ("bill", "Billete"),
        ("coin", "Moneda")
        ], required=True, default="bill")
    
    # Check on write that there is a bill o coin mandatory (1 of 2 at least)
    bill_value = fields.Float(string="Valor del billete")
    coin_value = fields.Float(string="Valor de la moneda") 

    # Technical field - currency real (res.currency) for showing right symbol in the views for the monetary fields
    currency_real_id = fields.Many2one(related="currency_id.currency_id", readonly=True, store=True)


    @api.depends("currency_id", "unit", "bill_value", "coin_value")
    def _compute_name(self):
        for rec in self:
            if rec.currency_id and rec.unit:
                if rec.bill_value:
                    rec.name = f"Billete de {rec.bill_value} {rec.currency_id.initials}"
                elif rec.coin_value:
                    rec.name = f"Moneda de {rec.coin_value} {rec.currency_id.initials}"
                else:
                    rec.name = "Nuevo billete / moneda"
            else:
                rec.name = "Nuevo billete / moneda"

    @api.onchange("bill_value", "coin_value", "unit")
    def _delete_oposite_value(self):
        for rec in self:
            if rec.unit == "bill":
                rec.coin_value = False
            elif rec.unit == "coin":
                rec.bill_value = False