from odoo import fields, models, api


class Image(models.Model):
    _name = "forexmanager.image"
    _description = "A model for defyning the images of accepted bills and coins"

    name = fields.Char(related="breakdown_id.name")
    breakdown_id = fields.Many2one("forexmanager.breakdown", string="Billete/moneda")
    unit_type = fields.Selection(related="breakdown_id.unit")
    unit_value = fields.Float(related="breakdown_id.value")
    currency_id = fields.Many2one(related="breakdown_id.currency_real_id")
    image_front = fields.Image(string="Anverso")
    image_back = fields.Image(string="Reverso")
    