from odoo import fields, models, api


class Customer(models.Model):
    _name = "forexmanager.customer"
    _description = "A model for defyning the personal information about the customer."

    # Customer personal info
    name = fields.Char(compute="_get_full_name", store=True)
    first_name_1 = fields.Char(string="Primer nombre")
    first_name_2 = fields.Char(string="Segundo(s) nombre(s)")
    last_name_1 = fields.Char(string="Primer apellido")
    last_name_2 = fields.Char(string="Segundo(s) apellido(s)")
    birth_country_id = fields.Many2one("res.country", string="País de nacimiento")
    birth_date = fields.Date(string="Fecha de nacimiento") # Must be not under 18
    gender = fields.Selection([
        ("female", "Mujer"),
        ("male", "Hombre"),
        ("other", "Otro")
        ], string="Género")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Teléfono")
    
    # Customer address
    country_id = fields.Many2one("res.country", string="País de residencia", default=68)
    street = fields.Char(string="Calle")
    number = fields.Char(string="Número")
    province_id = fields.Many2one("res.country.state", string="Provincia")

    # Relation with Passport model
    passport_id = fields.Many2one("forexmanager.passport", string="Pasaporte")
    # passport_country = fields.Many2one(related="passport_id.passport_country", string="País de emisión")
    # passport_expedition = fields.Date(related="passport_id.passport_expedition", string="Fecha de emisión")
    # passport_expiration = fields.Date(related="passport_id.passport_expiration", string="Fecha de vencimiento")
    # passport_number = fields.Char(related="passport_id.passport_number", string="Número de pasaporte")


    @api.depends("first_name_1", "first_name_2", "last_name_1", "last_name_2")
    def _get_full_name(self):
        for rec in self:
            if rec.first_name_1 and rec.last_name_1:
                rec.name = f"{rec.first_name_1} {rec.first_name_2 if rec.first_name_2 else ''} {rec.last_name_1} {rec.last_name_2 if rec.last_name_2 else ''}"
            else:
                rec.name = ""