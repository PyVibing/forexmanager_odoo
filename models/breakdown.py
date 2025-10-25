from odoo import fields, models, api
from odoo.exceptions import ValidationError
from ..utils import notification


class Breakdown(models.Model):
    """A model for defyning the accepted bills and coins for a currency."""
    
    _name = "forexmanager.breakdown"
    _description = "Desglose de billetes y monedas"

    # MAIN FIELDS
    name = fields.Char(compute="_compute_name", string="Nombre")
    currency_id = fields.Many2one("forexmanager.currency", string="Divisa")
    unit = fields.Selection([
        ("bill", "Billete"),
        ("coin", "Moneda")
        ], required=True, string="Tipo")    
    value = fields.Float(string="Valor")
    note = fields.Char(string="Notas")
    # currency real (res.currency) for showing right symbol in the views for the monetary fields
    currency_real_id = fields.Many2one(related="currency_id.currency_id", readonly=True, store=True)
    # To know if there is already a breakdown line for this value and unit type for this currency
    repeated_line = fields.Boolean(default=False, store=False)

    # RELATIONS WITH OTHERS MODELS
    image_ids = fields.One2many("forexmanager.image", "breakdown_id")
    

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
    
    # Calculates if there is already a breakdown line for this same value 
    # and unit type for this currency.
    @api.onchange("unit", "value")
    def _onchange_currencies_id(self):
        for rec in self:
            if (rec.unit and rec.value):
                self.check_repeated_line(rec)
    
    # Auxiliar method (called from _onchange_currencies_id and from create() and write())
    @staticmethod
    def check_repeated_line(self):
        other_lines = [i for i in self.currency_id.unit_ids if i != self]
                
        for i in other_lines:
            self.repeated_line = False # Restart value from previous True
            if (i.unit == self.unit) and (i.value == self.value):
                self.repeated_line = True
                notification(self, "Ya existe un desglose de moneda similar", 
                            f"Ya existe un desglose para {i.name}. No puedes agregarlo nuevamente.",
                            "warning")
                break

    # vals here is a list of dictionaries
    def create(self, vals):
        for val in vals:
            value = val.get("value")

            if value <= 0:
                raise ValidationError("No puedes crear un billete/moneda con un valor igual a 0.00 o inferior.")

        breakdown = super().create(vals)
        
        for rec in breakdown:
            Breakdown.check_repeated_line(rec)
            if rec.repeated_line:
                raise ValidationError(f"Ya existe un desglose para {rec.name}. No puedes agregarlo nuevamente.")

        return breakdown
    
    def write(self, vals):
        new_value = vals.get("value")
        new_unit = vals.get("unit")

        for rec in self:
            if len(vals) == 1 and "repeated_line" in vals:
                continue # Because write is triggered from create() and write() when check_repeated_line()

            if new_value is not None and new_value <= 0:
                raise ValidationError("No puedes crear un billete/moneda con un valor igual a 0.00 o inferior.")
            
        breakdown = super().write(vals)

        # Check for repeated_line
        if new_unit or new_value:
            Breakdown.check_repeated_line(rec)
            if rec.repeated_line:
                raise ValidationError(f"Ya existe un desglose para {rec.name}. No puedes agregarlo nuevamente.")
                
        return breakdown
