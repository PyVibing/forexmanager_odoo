from odoo import fields, models


class Image(models.Model):
    """A model for defyning the images of accepted bills and coins"""
    _name = "forexmanager.image"
    _description = "Libro de billetes y monedas aceptadas"

    # MAIN FIELDS
    name = fields.Char(related="breakdown_id.name", string="Nombre", store=True)
    breakdown_id = fields.Many2one("forexmanager.breakdown")
    image_front = fields.Image(string="Anverso", required=True)
    image_back = fields.Image(string="Reverso", required=True)

    # OTHER FIELDS
    unit_type = fields.Selection(related="breakdown_id.unit", string="Tipo")
    unit_value = fields.Float(related="breakdown_id.value", string="Valor")
    currency_id = fields.Many2one(related="breakdown_id.currency_real_id")
    