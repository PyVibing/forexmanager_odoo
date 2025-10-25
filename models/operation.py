from odoo import fields, models, api
from odoo.exceptions import ValidationError
from passporteye import read_mrz
import base64
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from ..utils import notification


class Operation(models.Model):
    """A model for converting currencies from source to destination currency."""

    _name = "forexmanager.operation"
    _description = "Operación de cambio de divisas"

    # MAIN FIELDS
    name = fields.Char(default="Cambio de moneda", readonly=True, string="Nombre")
    date = fields.Datetime(string="Fecha", readonly=True, copy=False, default=lambda self: datetime.now())
    user_id = fields.Many2one("res.users", string="Empleado", default=lambda self: self.env.uid, readonly=True, copy=False)
    desk_id = fields.Many2one("forexmanager.desk", string="Ventanilla actual", required=True, readonly=True,
                              default=lambda self: self.env.user.current_desk_id.id)
    worksession_id = fields.Many2one("forexmanager.worksession", compute="_compute_worksession_id", store=True, string="Sesión", readonly=True)
    opening_desk_id = fields.Many2one(related="worksession_id.opening_desk_id", string="Ventanilla de apertura", store=True, readonly=True)

    # Customer data
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

    # ID DATA
    passport_id = fields.Many2one("forexmanager.passport") # False or null means passport info is not in Passport model 
    ID_type = fields.Selection([
            ("p", "Pasaporte"),
            ("id", "DNI"),
            ("other", "Otro")
        ], string="Tipo de documento", required=True)
    ID_country = fields.Many2one("res.country", string="País emisor", required=True)
    nationality = fields.Many2one("res.country", string="Nacionalidad", required=True)
    ID_expiration = fields.Date(string="Fecha de vencimiento", required=True)
    ID_number = fields.Char(string="Número de documento", required=True)
    image_1 = fields.Image(string="Imagen 1", attachment=True, required=True)
    image_2 = fields.Image(string="Imagen 2")
    image_3 = fields.Image(string="Imagen 3")
    image_4 = fields.Image(string="Imagen 4")
    # Storing this field to know if the info was taken from DB or current document read.
    # In case first time the info was wrongly taken, we know which user made the mistake.
    data_from_db = fields.Boolean(string="Datos del cliente encontrados en la BBDD", default=False)
    # HTML fields for showing in the form view
    summary = fields.Html(string="Movimientos", options="{'sanitize': False}", compute="_onchange_summary_tables", store=True)
    diff_calc_summary = fields.Html(string="Resumen", options="{'sanitize': False}", store=True)

    # OTHER FIELDS
    closing_session_check_started = fields.Boolean(related="worksession_id.closing_session.balances_checked_started")
    closing_session_check_ended = fields.Boolean(related="worksession_id.closing_session.balances_checked_ended")    
    calculation_ids = fields.One2many("forexmanager.calculation", "operation_id", string="Línea de cambio") # Required in create()
    # Checkboxs
    read_ID = fields.Boolean(default=False, store=False) # Checkbox on the view to read data from id document
    search_ID = fields.Boolean(string="Buscar cliente", default=False, store=False) # Checkbox on the view to look in the DB
    confirm = fields.Boolean(default=False, string="Todo listo", store=False) # Required True (validated in create()). This way, avoid accidental save when browser window loses focus or any other reason
    available = fields.Boolean(related="calculation_ids.available")
    
    
    @api.onchange("calculation_ids")
    def _onchange_summary_tables(self):
        for rec in self:
            # Avoid adding a repeated line or a line with no availability or a line with amount <= 0
            rec.calculation_ids = rec.calculation_ids.filtered(lambda l: l.available)
            rec.calculation_ids = rec.calculation_ids.filtered(lambda l: not l.repeated_line)
            rec.calculation_ids = rec.calculation_ids.filtered(lambda l: l.amount_received > 0)
            rec.calculation_ids = rec.calculation_ids.filtered(lambda l: l.amount_delivered > 0)

            receive_summary = {} # {currency: amount}
            deliver_summary = {} # {currency: amount}
            diff_calc_summary = {} # {currency: {"receive": amount, "deliver": amount}}

            # Grouping the amounts for every currency
            for line in rec.calculation_ids:
                # Convert to Decimal
                amount_received = Decimal(str(line.amount_received or 0))
                amount_delivered = Decimal(str(line.amount_delivered or 0))

                # Group by amount
                receive_summary.setdefault(line.currency_source_id.name, Decimal('0'))
                receive_summary[line.currency_source_id.name] += amount_received

                deliver_summary.setdefault(line.currency_target_id.name, Decimal('0'))
                deliver_summary[line.currency_target_id.name] += amount_delivered

            # Calculating difference if currency is in both tables (receive and deliver)
            for currency, amount in receive_summary.items():
                diff_calc_summary.setdefault(currency, {"receive": 0, "deliver": 0})
                
                if currency not in deliver_summary:
                    diff_calc_summary[currency]["receive"] = amount
                else: 
                    if receive_summary[currency] > deliver_summary[currency]:
                        diff_calc_summary[currency]["receive"] = receive_summary[currency] - deliver_summary[currency]
                    elif receive_summary[currency] < deliver_summary[currency]:
                        diff_calc_summary[currency]["deliver"] = deliver_summary[currency] - receive_summary[currency]
            for currency, amount in deliver_summary.items():
                if currency not in receive_summary:
                    diff_calc_summary.setdefault(currency, {"receive": 0, "deliver": 0})
                    diff_calc_summary[currency]["deliver"] = amount

            # Convert to float:
            if receive_summary:
                receive_summary = {k: float(v) for k, v in receive_summary.items()}
            if deliver_summary:
                deliver_summary = {k: float(v) for k, v in deliver_summary.items()}
            if diff_calc_summary:
                diff_calc_summary = {
                    k: {"receive": float(v["receive"]), "deliver": float(v["deliver"])}
                    for k, v in diff_calc_summary.items()
                    }

            html_summary = ""
            html_diff_calc_summary = ""

            # RECEIVE table
            if receive_summary:
                html_summary += """
                    <div style="width: 25%; min-width: 350px; float: left; margin: 5px; padding: 15px; background-color: #ffffff;
                                border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.08);
                                border-left: 4px solid #007bff;">
                        <h4 style="color:#007bff;">RECIBIR</h4>
                        <table class="table table-sm table-striped" style="width:100%; table-layout: fixed;">
                            <thead>
                                <tr>
                                    <th style="width:70%; background-color: #007bff; color: white;">DIVISA</th>
                                    <th style="width:30%; background-color: #007bff; color: white;">CANTIDAD</th>
                                </tr>
                            </thead>
                            <tbody>
                    """
                for currency, amount in receive_summary.items():
                    html_summary += f"""
                            <tr>
                                <td><strong>{currency}</strong></td>
                                <td>{amount}</td>
                            </tr>
                    """
                html_summary += """
                            </tbody>
                        </table>
                    </div>
                """

            # DELIVER table
            if deliver_summary:
                html_summary += """
                <div style="width: 25%; min-width: 350px; float: left; margin: 5px; padding: 15px; background-color: #ffffff;
                            border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.08);
                            border-left: 4px solid #ffc107;">
                    <h4 style="color:#ffc107;">ENTREGAR</h4>
                    <table class="table table-sm table-striped" style="width:100%; table-layout: fixed;">
                        <thead>
                            <tr>
                                <th style="width:70%; background-color: #ffc107; color: white;">DIVISA</th>
                                <th style="width:30%; background-color: #ffc107; color: white;">CANTIDAD</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for currency, amount in deliver_summary.items():
                    html_summary += f"""
                            <tr>
                                <td><strong>{currency}</strong></td>
                                <td>{amount}</td>
                            </tr>
                    """
                html_summary += """
                        </tbody>
                    </table>
                </div>
                """

            rec.summary = html_summary

            # DIFF_CALC table
            if diff_calc_summary:
                html_diff_calc_summary += """
                    <div class="personal-card" style="width: 40%; min-width: 500px;">
                    <h4 style="color:#007bff;">RESUMEN DE LA OPERACIÓN</h4>
                    <table class="table table-sm table-striped" style="width:100%; table-layout: fixed;">
                        <thead>
                            <tr>
                                <th style="width:60%; background-color: #007bff; color: white;">DIVISA</th>
                                <th style="width:20%; background-color: #007bff; color: white;">RECIBIR</th>
                                <th style="width:20%; background-color: #007bff; color: white;">ENTREGAR</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for currency in diff_calc_summary.keys():
                    if diff_calc_summary[currency]["receive"] or diff_calc_summary[currency]["deliver"]: # If difference is 0, we just don't show the currency/amount
                        html_diff_calc_summary += f"""
                                <tr>
                                    <td><strong>{currency}</strong></td>
                                    <td>{diff_calc_summary[currency]["receive"]}</td>
                                    <td>{diff_calc_summary[currency]["deliver"]}</td>
                                </tr>
                        """
                html_diff_calc_summary += """
                            </tbody>
                        </table>
                    </div>
                """
            
            rec.diff_calc_summary = html_diff_calc_summary

    @api.depends("desk_id")
    def _compute_worksession_id(self):
        for rec in self:
            if rec.desk_id:
                # Get open (checkin) session associated to this desk and user (must be only one)
                session = self.env["forexmanager.worksession"].search([
                        ("user_id", "=", rec.user_id), 
                        ("session_status", "=", "open"), 
                        ("session_type", "=", "checkin"),
                        ("desk_id", "=", rec.desk_id.id),
                        ], limit=1)
                
                # Get all open (checkin) sessions (main and secondaries) for this user
                all_sessions = self.env["forexmanager.worksession"].search([
                        ("user_id", "=", rec.user_id), 
                        ("session_status", "=", "open"), 
                        ("session_type", "=", "checkin"),
                        ])
                for _ in all_sessions:
                    if session.desk_id == session.opening_desk_id: # We are operating in our opening_desk
                            rec.worksession_id = session.id if session.balances_checked_ended else False
                    else: # We are in a temporary desk, must check if balance check is finished in the associated opening desk
                        rec.worksession_id = session.id if all_sessions[0].balances_checked_ended else False
                        break # Only check in one of many possibles secondary sessions
    
    @api.onchange("read_ID", "image_1")
    def get_passport_info(self):
        for rec in self:
            def clean_images():
                rec.image_1 = False
                rec.image_2 = False
                rec.image_3 = False
                rec.image_4 = False
                rec.read_ID = False
                rec.passport_id = False                
                
            def clean_data():
                # Customer data
                rec.first_name_1 = False
                rec.first_name_2 = False
                rec.last_name_1 = False
                rec.last_name_2 = False
                rec.birth_country_id = False
                rec.birth_date = False
                rec.sex = False
                # Contact data
                rec.email = False
                # Customer address
                rec.country_id = False
                rec.province_id = False
                rec.city = False
                rec.street = False
                rec.number = False
                rec.other = False
                rec.postal_code = False
                # ID/Passport data
                rec.ID_type = False
                rec.ID_country = False
                rec.nationality = False
                rec.ID_expiration = False
                rec.ID_number = False
                rec.passport_id = False
                # Buttons
                rec.search_ID = False                

            if not rec.image_1:
                # If deleting the first image or clicking the checkbox with no first image loaded
                clean_data()
                clean_images()        
            
            elif rec.image_1 and not rec.read_ID:
                # When loading the first image after filling manually the data
                clean_data()

            elif rec.image_1 and rec.read_ID:
                # When reading the data from the image
                clean_data()

                try:
                    img_bytes = base64.b64decode(rec.image_1)
                    img_stream = BytesIO(img_bytes)
                    mrz = read_mrz(img_stream)
                    mrz_dict = mrz.to_dict()
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
                
                if valid_score > 50:
                    # Assign values to variables
                    rec.ID_number = ID_number
                    rec.search_passport()

                    if not rec.passport_id: # Assign values from document read
                        if ID_type == "P":
                            rec.ID_type = "p"
                        elif ID_type == "ID":
                            rec.ID_type = "id"
                        else:
                            rec.ID_type = "other"

                        country_rec = self.env['res.country'].search([('code', '=', ID_country)], limit=1)
                        if country_rec:
                            rec.ID_country = country_rec
                        
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
                    
                else:
                    notification(rec, "Lectura de documento poco fiable", 
                                 "Por favor, introduzca manualmente el número de pasaporte y busque los datos " \
                                 "del cliente en la Base de Datos.",
                                 "warning")                        
                    rec.read_ID = False

    def assign_values_from_db(self, ID_exists):
        for rec in self:
            # Customer data
            rec.first_name_1 = ID_exists.customer_id.first_name_1
            rec.first_name_2 = ID_exists.customer_id.first_name_2
            rec.last_name_1 = ID_exists.customer_id.last_name_1
            rec.last_name_2 = ID_exists.customer_id.last_name_2
            rec.birth_country_id = ID_exists.customer_id.birth_country_id
            rec.birth_date = ID_exists.customer_id.birth_date
            rec.sex = ID_exists.customer_id.sex
            # Contact data
            rec.email = ID_exists.customer_id.email
            # Customer address
            rec.country_id = ID_exists.customer_id.country_id.id
            rec.province_id = ID_exists.customer_id.province_id.id
            rec.city = ID_exists.customer_id.city
            rec.street = ID_exists.customer_id.street
            rec.number = ID_exists.customer_id.number
            rec.other = ID_exists.customer_id.other
            rec.postal_code = ID_exists.customer_id.postal_code
            # ID/Passport data
            rec.ID_type = ID_exists.ID_type
            rec.ID_country = ID_exists.ID_country
            rec.nationality = ID_exists.nationality
            rec.ID_expiration = ID_exists.ID_expiration
            rec.ID_number = ID_exists.ID_number
                   
    @api.onchange("search_ID")
    def activate_search_passport(self):
        for rec in self:
            if rec.search_ID and not rec.read_ID:
                if rec.ID_number:
                    rec.search_passport()
                else:
                    rec.search_ID = False

    def search_passport(self):
        for rec in self:
            ID_exists = self.env["forexmanager.passport"].search([
                ("ID_number", "=", rec.ID_number)
                ])            
            rec.passport_id = ID_exists
            rec.search_ID = True # This disables (readonly) the button when TRUE

            if rec.passport_id:
                notification(rec, "Datos encontrados", 
                             "Se cargaron los datos del cliente desde la Base de Datos. Sus datos principales no pueden ser modificados.", 
                             "info")
                rec.assign_values_from_db(rec.passport_id)
            else:
                if not rec.read_ID: # Means that there is no image or is not readable (low valid_score assign False to read_ID)
                    notification(rec, "Cliente no encontrado en la Base de Datos", 
                                "Rellene manualmente los datos solicitados. " \
                                "Asegúrese de que sean correctos antes de continuar con la operación.", 
                                "warning")
                else: # Values are inserted from current document read
                    notification(rec, "Cliente no encontrado en la Base de Datos", 
                                "Se rellenaron los campos requeridos con la información obtenida al leer el documento. " \
                                "Verifique que sean correctos antes de continuar con la operación", 
                                "warning")

    def create(self, vals):
        if not vals.get("calculation_ids"):
            raise ValidationError("Falta añadir al menos una línea de cambio de divisa.")
        if not vals.get("confirm"):
            raise ValidationError("Por razones de seguridad, debes marcar la opción TODO LISTO (en la pestaña FINALIZAR) " \
                                    "antes de confirmar la operación.")
        
        operation = super(Operation, self).create(vals)

        for line in operation.calculation_ids:
            amount_delivered = line.amount_delivered
            amount_received = line.amount_received
            currency_target_id = line.currency_target_id.id
            currency_source_id = line.currency_source_id.id
            opening_desk_id = operation.opening_desk_id.id
            cashcount_deliver = self.env["forexmanager.cashcount"].search([
                ("currency_id", "=", currency_target_id),
                ("desk_id", "=", opening_desk_id)
                ])
            cashcount_receive = self.env["forexmanager.cashcount"].search([
                ("currency_id", "=", currency_source_id),
                ("desk_id", "=", opening_desk_id)
                ])
            
            # Check availability again
            if cashcount_deliver.balance < amount_delivered:
                raise ValidationError("No hay disponibilidad suficiente para la cantidad de divisa que solicita el cliente. Modifique la cantidad para finalizar la operación.")
        
            # Update balance in cashcount model for this opening_desk
            new_amount_receive = (Decimal(cashcount_receive.balance) + Decimal(amount_received)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            cashcount_receive.write({"balance": float(new_amount_receive)})
            new_amount_deliver = (Decimal(cashcount_deliver.balance) - Decimal(amount_delivered)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            cashcount_deliver.write({"balance": float(new_amount_deliver)})
        
        if not operation.passport_id: # Means it wasn't found on customer search
            # Creating customer record in Customer model
            customer = self.env["forexmanager.customer"].create({
                "first_name_1": operation.first_name_1,
                "first_name_2": operation.first_name_2,
                "last_name_1": operation.last_name_1,
                "last_name_2": operation.last_name_2,
                "birth_country_id": operation.birth_country_id.id,
                "birth_date": operation.birth_date,
                "sex": operation.sex,
                "email": operation.email,
                "country_id": operation.country_id.id,
                "province_id": operation.province_id.id,
                "city": operation.city,
                "street": operation.street,
                "number": operation.number,
                "other": operation.other,
                "postal_code": operation.postal_code,
                })
        
            # Creating passport record in Passport model (relation with customer)
            self.env["forexmanager.passport"].create({
                "customer_id": customer.id,
                "ID_type": operation.ID_type,
                "ID_country": operation.ID_country.id,
                "nationality": operation.nationality.id,
                "ID_expiration": operation.ID_expiration,
                "ID_number": operation.ID_number
                })
            
            operation.data_from_db = False
        else:
            # Lets update the info that can be updated (address, email), accesing the customer through his passport/ID
            customer = self.env["forexmanager.passport"].search([
                ("ID_number", "=", operation.ID_number)
                ], limit=1).customer_id
            
            customer.write({
                "email": vals["email"],
                "country_id": vals["country_id"],
                "province_id": vals["province_id"],
                "city": vals["city"],
                "street": vals["street"],
                "number": vals["number"],
                "other": vals["other"],
                "postal_code": vals["postal_code"],
                })
            
            operation.data_from_db = True
        
        notification(self, "Operación realizada exitosamente", 
                     "La operación fue completada sin errores. Puedes chequearla en el historial de operaciones.", 
                     "success")
        
        return operation
            