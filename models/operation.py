from odoo import fields, models, api

class Operation(models.Model):
    _name = "forexmanager.operation"
    _description = "A model for converting currencies from source to destination currency."

    name = fields.Char(default="Cambio de moneda", readonly=True)
    date = fields.Date(string="Fecha de hoy", readonly=True, copy=False) # compute datetime.now().date() and readonly True
    user_id = fields.Many2one("res.users", string="Empleado", default=lambda self: self.env.uid, readonly=True, copy=False)

    calculation_ids = fields.One2many("forexmanager.calculation", "operation_id", string="Líneas de cambio")

    # Customer personal info
    # first_name_1 = fields.Char(string="Primer nombre", required=True)
    # first_name_2 = fields.Char(string="Segundo nombre")
    # last_name_1 = fields.Char(string="Primer apellido", required=True)
    # last_name_2 = fields.Char(string="Segundo apellido")
    # birth_country_id = fields.Many2one("res.country", string="País de nacimiento", required=True)
    # birth_date = fields.Date(string="Fecha de nacimiento", required=True) # Must be not under 18
    # gender = fields.Selection([
    #     ("female", "Mujer"),
    #     ("male", "Hombre"),
    #     ("other", "Otro")
    #     ], string="Género", required=True)
    
    # Customer address
    # country_id = fields.Many2one("res.country", string="País de residencia", default=68, required=True)
    # street = fields.Char(string="Calle", required=True)
    # number = fields.Char(string="Número", required=True)
    # province_id = fields.Many2one("res.country.state", string="Provincia", required=True)

