from odoo import fields, models

class Passport(models.Model):
    _name = "forexmanager.passport"
    _description = "A model for defyning everything related to the customer passport."

    name = fields.Char(related="customer_id.name")
    customer_id = fields.One2many("forexmanager.customer", "passport_id", string="Cliente")
    passport_country = fields.Many2one("res.country", string="País de emisión")
    passport_expedition = fields.Date(string="Fecha de emisión")
    passport_expiration = fields.Date(string="Fecha de vencimiento")
    passport_number = fields.Char(string="Número de pasaporte")
    image_1 = fields.Image(string="Imagen 1") # Solo esta required=True
    image_2 = fields.Image(string="Imagen 2")
    image_3 = fields.Image(string="Imagen 3")
    image_4 = fields.Image(string="Imagen 4")