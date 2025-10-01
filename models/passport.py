from odoo import fields, models, api
from ..utils import notification

class Passport(models.Model):
    """A model for defyning everything related to the customer passport or ID."""
    _name = "forexmanager.passport"
    _description = "Documento de identidad"

    # MAIN FIELDS
    name = fields.Char(related="customer_id.name")
    customer_id = fields.Many2one("forexmanager.customer", string="Cliente", ondelete="cascade")    
    ID_type = fields.Selection([
            ("p", "Pasaporte"),
            ("id", "DNI"),
            ("other", "Otro")
        ], string="Tipo de documento", required=True)
    ID_country = fields.Many2one("res.country", string="País emisor", required=True)
    nationality = fields.Many2one("res.country", string="Nacionalidad", required=True)
    ID_expiration = fields.Date(string="Fecha de vencimiento", required=True)
    ID_number = fields.Char(string="Número de documento", required=True)            
