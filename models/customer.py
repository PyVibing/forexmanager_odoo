from odoo import fields, models, api


class Customer(models.Model):
    """This model will be only accesible through the Operation model. Records will be always created from there."""
    _name = "forexmanager.customer"
    _description = "A model for defyning the personal information about the customer."

    # CUSTOMER DATA
    name = fields.Char(string="Nombre completo", compute="_get_full_name", store=True)
    first_name_1 = fields.Char(string="Primer nombre", required=True)
    first_name_2 = fields.Char(string="Segundo(s) nombre(s)")
    last_name_1 = fields.Char(string="Primer apellido", required=True)
    last_name_2 = fields.Char(string="Segundo(s) apellido(s)")
    birth_country_id = fields.Many2one("res.country", string="País de nacimiento", required=True)
    birth_date = fields.Date(string="Fecha de nacimiento", required=True) # Must be not under 18
    sex = fields.Selection([
        ("female", "Mujer"),
        ("male", "Hombre"),
        ("undefined", "Indefinido")
        ], string="Sexo", required=True)
    email = fields.Char(string="Email")
    
    # Customer address
    country_id = fields.Many2one("res.country", string="País", default=68, required=True)
    province_id = fields.Many2one("res.country.state", string="Provincia", required=True)
    city = fields.Char(string="Localidad", required=True)
    street = fields.Char(string="Calle", required=True)
    number = fields.Char(string="Número", required=True)
    other = fields.Char(string="Piso/portal/etc...")
    postal_code = fields.Integer(string="Código postal")

    # Relation with Passport model
    passport_ids = fields.One2many("forexmanager.passport", "customer_id", string="Pasaporte", required=True)
    
    @api.depends("first_name_1", "first_name_2", "last_name_1", "last_name_2")
    def _get_full_name(self):
        for rec in self:
            if rec.first_name_1 and rec.last_name_1:
                rec.name = f"{rec.first_name_1} {rec.first_name_2 if rec.first_name_2 else ''} {rec.last_name_1} {rec.last_name_2 if rec.last_name_2 else ''}"
            else:
                rec.name = "Nuevo cliente"