from odoo import fields, models, api
from odoo.exceptions import ValidationError
from ..utils import notification

class Passport(models.Model):
    _name = "forexmanager.passport"
    _description = "A model for defyning everything related to the customer passport or ID."

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
    ID_number = fields.Char(string="Número de documento", required=True) # Unique
    
    
    @api.model
    def create(self, vals_list):
        for vals in vals_list:
            # # Check if there is an existing record in DB for this ID
            # existing_ID = self.env["forexmanager.passport"].search([
            #     ("ID_number", "=", vals["ID_number"]),
            #     ], limit=1)
            
            # if existing_ID:
            #     notification(self, "ID ya existe", 
            #                  "Ya existe un ID en BBDD. Se actualizarán los datos asociados que hayan sido modificados.", 
            #                  "info")
            #     # Actualizar con los nuevos valores
            #     existing_ID.write(vals)
            #     return existing_ID  # devolvemos el registro actualizado
            # else:
            #     notification(self, "Nuevo pasaporte creado", 
            #                  "Se creó correctamente un nuevo registro con los datos de este pasaporte.", 
            #                  "info")
            #     # Si no existe, lo creamos normalmente
            return super().create(vals)
            
