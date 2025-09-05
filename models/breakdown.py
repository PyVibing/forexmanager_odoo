from odoo import fields, models, api

class Breakdown(models.Model):
    _name = "forexmanager.breakdown"
    _description = "A model for defyning the bills and coins for a currency."

    name = fields.Char(compute="_compute_name") # agregar compute
    currency_id = fields.Many2one("forexmanager.currency", string="Divisa")
    unit = fields.Selection([
        ("bill", "Billete"),
        ("coin", "Moneda")
        ], required=True, default="bill", string="Billete/moneda")    
    value = fields.Float(string="Valor del billete/moneda")
    image_ids = fields.One2many("forexmanager.image", "breakdown_id")

    # Technical field - currency real (res.currency) for showing right symbol in the views for the monetary fields
    currency_real_id = fields.Many2one(related="currency_id.currency_id", readonly=True, store=True)


    @api.depends("currency_id", "unit", "value")
    def _compute_name(self):
        for rec in self:
            if rec.currency_id and rec.unit:
                if rec.unit == "bill":
                    rec.name = f"Billete de {rec.value} {rec.currency_id.initials}"
                elif rec.unit == "coin":
                    rec.name = f"Moneda de {rec.value} {rec.currency_id.initials}"
                else:
                    rec.name = "Nuevo billete / moneda"
            else:
                rec.name = "Nuevo billete / moneda"

