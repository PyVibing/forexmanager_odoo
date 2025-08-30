from odoo import fields, models, api
from odoo.exceptions import ValidationError
from passporteye import read_mrz
import base64
from datetime import datetime
from io import BytesIO

# Eliminar luego, solo development
import warnings
warnings.filterwarnings("ignore")

class Operation(models.Model):
    _name = "forexmanager.operation"
    _description = "A model for converting currencies from source to destination currency."

    name = fields.Char(default="Cambio de moneda", readonly=True)
    date = fields.Date(string="Fecha de hoy", readonly=True, copy=False) # compute datetime.now().date() and readonly True
    user_id = fields.Many2one("res.users", string="Empleado", default=lambda self: self.env.uid, readonly=True, copy=False)

    calculation_ids = fields.One2many("forexmanager.calculation", "operation_id", string="Línea de cambio")
    # customer_id = fields.Many2one("forexmanager.customer", string="Cliente")

    # CUSTOMER DATA
    first_name_1 = fields.Char(string="Primer nombre")
    first_name_2 = fields.Char(string="Segundo(s) nombre(s)")
    last_name_1 = fields.Char(string="Primer apellido")
    last_name_2 = fields.Char(string="Segundo(s) apellido(s)")
    birth_country_id = fields.Many2one("res.country", string="País de nacimiento")
    birth_date = fields.Date(string="Fecha de nacimiento") # Must be not under 18
    sex = fields.Selection([
        ("female", "Mujer"),
        ("male", "Hombre"),
        ("undefined", "Indefinido")
        ], string="Sexo")
    email = fields.Char(string="Email")
    
    # Customer address
    country_id = fields.Many2one("res.country", string="País de residencia", default=68)
    province_id = fields.Many2one("res.country.state", string="Provincia")
    city = fields.Char(string="Localidad")
    street = fields.Char(string="Calle")
    number = fields.Char(string="Número")
    other = fields.Char(string="Piso/escalera/portal/etc...")

    # Relation with Passport model
    passport_id = fields.Many2one("forexmanager.passport", string="Pasaporte")

    # ID DATA
    ID_type = fields.Selection([
            ("p", "Pasaporte"),
            ("id", "DNI"),
            ("other", "Otro")
        ])
    ID_country = fields.Many2one("res.country", string="País de emisión")
    nationality = fields.Many2one("res.country", string="Nacionalidad")
    ID_expiration = fields.Date(string="Fecha de vencimiento")
    ID_number = fields.Char(string="Número")
    image_1 = fields.Image(string="Imagen 1", attachment=True) # Solo esta required=True
    image_2 = fields.Image(string="Imagen 2")
    image_3 = fields.Image(string="Imagen 3")
    image_4 = fields.Image(string="Imagen 4")
    read_ID = fields.Boolean(default=False)

    @api.onchange("read_ID", "image_1")
    def get_passport_info(self):
        for rec in self:
            if not rec.image_1:
                if rec.read_ID:
                    rec.read_ID = False
            elif rec.image_1 and rec.read_ID:
                try:
                    img_bytes = base64.b64decode(rec.image_1)
                    img_stream = BytesIO(img_bytes)
                    mrz = read_mrz(img_stream)
                    mrz_dict = mrz.to_dict()
                    print(mrz_dict)
                    print("--------------------------")
                    print("--------------------------")
                    print("--------------------------")
                except Exception:
                    raise ValidationError("No se pudo leer la información del documento. Por favor, rellene los datos manualmente.")
                valid_score = mrz_dict["valid_score"]
                mrz_type = mrz_dict["mrz_type"].replace("<", "") # TD1 (card-size documents) or TD3 (passport type). TD2 not allowed

                ID_type = mrz_dict["type"].replace("<", "") # IR, IT, ID, P
                ID_country = mrz_dict["country"].replace("<", "")
                ID_number = mrz_dict["optional1"].replace("<", "") if mrz_type == "TD1" else mrz_dict["number"].replace("<", "")
                ID_expiration_date = mrz_dict["expiration_date"].replace("<", "")
                valid_expiration_date = mrz_dict["valid_expiration_date"]

                names = mrz_dict["names"].replace("<", "")
                last_names = mrz_dict["surname"].replace("<", "")
                nationality = mrz_dict["nationality"].replace("<", "")
                birth_date = mrz_dict["date_of_birth"].replace("<", "")
                valid_birth_date = mrz_dict["valid_date_of_birth"]
                sex = mrz_dict["sex"].replace("<", "")

                print(ID_type, ID_country, ID_number, ID_expiration_date, names, last_names, nationality, birth_date, sex)

                # Assign values to variables
                country_rec = self.env['res.country'].search([('code', '=', ID_country)], limit=1)
                if country_rec:
                    rec.ID_country = country_rec

                rec.ID_number = ID_number

                expiration_date = datetime.strptime(ID_expiration_date, "%y%m%d").date() if valid_expiration_date else None
                if expiration_date:
                    rec.ID_expiration = expiration_date

                first_names = names.split()
                first_name_1 = first_names[0]
                first_name_2 = first_names[1:] if len(first_names) > 1 else None
                full_first_name_2 = ""
                if first_name_2:
                    for n in first_name_2:
                        full_first_name_2 += n + " "
                    full_first_name_2 = full_first_name_2.strip()
                rec.first_name_1 = first_name_1
                rec.first_name_2 = full_first_name_2
                
                last_names = last_names.split()
                last_name_1 = last_names[0]
                last_name_2 = last_names[1:] if len(last_names) > 1 else None
                full_last_name_2 = ""
                if last_name_2:
                    full_last_name_2 = ""
                    for n in last_name_2:
                        full_last_name_2 += n + " "
                    full_last_name_2 = full_last_name_2.strip()
                rec.last_name_1 = last_name_1
                rec.last_name_2 = full_last_name_2

                nationality_rec = self.env['res.country'].search([('code', '=', nationality)], limit=1)
                if nationality_rec:
                    rec.nationality = nationality_rec

                birth_date = datetime.strptime(birth_date, "%y%m%d").date() if valid_birth_date else None
                if birth_date:
                    rec.birth_date = birth_date

                if sex == "F":
                    rec.sex = "female"
                elif sex == "M":
                    rec.sex = "male"
                else:
                    rec.sex = "undefined"