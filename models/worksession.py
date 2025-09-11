from odoo import fields, models, api
from odoo.exceptions import ValidationError
import datetime
from ..utils import notification


class WorkSession(models.Model):
    _name = "forexmanager.worksession"
    _description = "A model for creating the work sessions."

    name = fields.Char(compute="_compute_name", store=True, string="Nombre")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user.id, required=True, readonly=True, string="Usuario")
    desk_id = fields.Many2one("forexmanager.desk", string="Ventanilla actual", required=True)

    # opening_desk_id: Is the desk where the user logged in for the first time. It must checked the currency balances here
    opening_desk_id = fields.Many2one("forexmanager.desk", string="Ventanilla de arqueo", readonly=True) # Assigned manually

    # desk_code = fields.File(required=True, string="Código de vinculación")
    session_type = fields.Selection([
        ("checkin", "Inicio de sesión"),
        ("checkout", "Cierre de sesión")
        ], required=True, string="Tipo de sesión")
    session_status = fields.Selection([
        ("open", "Abierta"),
        ("closed", "Cerrada")
        ], default="open", string="Estado de la sesión", required=True, readonly=True)
    session_to_close = fields.Many2one("forexmanager.worksession", compute="_get_session_to_close", store=True, string="Sesión a cerrar",
                                        readonly=True) # for checkout sessions
    closing_session = fields.Many2one("forexmanager.worksession", readonly=True, string="Sesión de cierre") # for checkin sessions after closing it
    start_time = fields.Datetime(string="Hora de inicio", readonly=True)
    close_time = fields.Datetime(string="Hora de cierre", readonly=True)
    op_ids = fields.One2many("forexmanager.operation", "worksession_id")

    checkbalance_ids = fields.One2many("forexmanager.checkbalance", "session_id")    
    # Shows only the currencies with non confirmed balance
    pending_checkbalance_ids = fields.One2many(
        "forexmanager.checkbalance",
        "session_id",
        string="Balances sin confirmar",
        domain=[("checked", "=", False)]
        )    
    # Shows only the currencies with confirmed balance
    completed_checkbalance_ids = fields.One2many(
        "forexmanager.checkbalance",
        "session_id",
        string="Balances confirmados",
        domain=[("checked", "=", True)]
        )
    # Shows only the currencies with difference during balance check
    difference_checkbalance_ids = fields.One2many(
        "forexmanager.checkbalance",
        "session_id",
        string="Balances con diferencia",
        domain=[("difference", "!=", 0)]
        )   

    balances_checked_started = fields.Boolean(string="Arqueo comenzado", default=False) # At creating the checkbalance recs
    balances_checked_ended = fields.Boolean(string="Arqueo completado", default=False) # After no difference in balances or confirmed
    
    # Checkbox (to connect the odoo session with a physical pc with its own currency balance)
    checkbox_connect = fields.Boolean(string="Vincular ventanilla", store=False)
    # currencies_confirmed = fields.Boolean(compute="_compute_currencies_confirmed", store=True)

    # Manually executed from worksession.search_difference()
    def check_balances_checked_ended(self): 
        for rec in self:
            total = self.env["forexmanager.checkbalance"].search_count([('session_id', '=', rec.id)])
            checked_count = self.env['forexmanager.checkbalance'].search_count([('session_id', '=', rec.id), ('confirmed', '=', True)])
            rec.balances_checked_ended = total > 0 and total == checked_count

    # Manually executed from worksession.search_difference() and confirm_balances()
    # def check_balances_confirmed(self): 
    #     for rec in self:
    #         total = self.env["forexmanager.checkbalance"].search_count([('session_id', '=', rec.id)])
    #         checked_count = self.env['forexmanager.checkbalance'].search_count([('session_id', '=', rec.id), ('confirmed', '=', True)])
    #         rec.balances_checked_ended = total > 0 and total == checked_count


    @api.depends("session_type", "desk_id", "user_id")
    def _compute_name(self):
        for rec in self:
            if rec.desk_id and rec.session_type and rec.user_id and rec.id:
                session_label = dict(self._fields["session_type"].selection).get(rec.session_type)
                rec.name = f"(ID: {rec.id}) {session_label} de {rec.desk_id.name} ({rec.user_id.name})"
            else:
                rec.name = "Nuevo arqueo de entrada/salida"

    @api.depends("session_type", "user_id", "desk_id", "session_status")
    def _get_session_to_close(self):
        for rec in self:
            # Prevent the value being recalculated after create()
            if not rec.id:            
                if rec.session_type and rec.session_type == "checkout" and rec.user_id and rec.desk_id and rec.session_status:
                    session = self.env["forexmanager.worksession"].search([
                        ("user_id", "=", rec.user_id),
                        ("desk_id", "=", rec.desk_id),
                        ("session_type", "=", "checkin"),
                        ("session_status", "=", "open")
                        ], limit=1)
                    
                    rec.session_to_close = session
                    
                    if rec.desk_id == rec.opening_desk_id:
                        if not rec.session_to_close.balances_checked_started:
                            raise ValidationError("No puede lanzar el arqueo de salida. Queda pendiente realizar el arqueo de entrada.")
                        elif not rec.session_to_close.balances_checked_ended:
                            raise ValidationError("No puede lanzar el arqueo de salida. Queda pendiente finalizar el arqueo de entrada.")
                            
        
   
    # Called from button on form view. It creates records for model CheckBalance related to this session
    def start_checkbalance(self):
        def get_BD_balance(desk_id, currency_id):
            cashcount = self.env["forexmanager.cashcount"].search([
                ("desk_id", "=", desk_id),
                ("currency_id", "=", currency_id)
                ], limit=1)
            return cashcount.balance

        # Create records for CheckBalance only in the opening desk (only once)
        if self.desk_id == self.opening_desk_id:
            if self.balances_checked_started:
                if self.balances_checked_ended:
                    raise ValidationError("Ya se completó correctamente el arqueo para esta sesión.")
                else:
                    raise ValidationError("Ya existe un proceso de arqueo para esta sesión. Por favor, finalícelo cuanto antes.")
            
            # Get the coins of this desk
            desk_currencies = self.opening_desk_id.workcenter_id.currency_ids
            for currency in desk_currencies:
                self.env["forexmanager.checkbalance"].create({
                    "session_id": self.id,
                    "user_id": self.user_id.id,
                    "desk_id": self.opening_desk_id.id,
                    "currency_id": currency.id,
                    "BD_balance": get_BD_balance(desk_id=self.opening_desk_id.id, currency_id=currency.id)
                    })
            if desk_currencies and not self.balances_checked_started:
                self.balances_checked_started = True
        else:
            notification(self, "Ventanilla secundaria", "Solo puedes lanzar el arqueo en tu ventanilla de apertura.", "warning", True)
    
    # Called from button on form view. It simulates the write() method for checkbalance model
    def search_difference(self):
        def check(rec):
            if rec.physical_balance is not None:
                rec.difference = rec.physical_balance - rec.BD_balance
                rec.checked = True            
            
        for rec in self.pending_checkbalance_ids:
            check(rec)
            if not rec.difference:
                rec.confirmed = True                
                
        for rec in self.difference_checkbalance_ids:
            check(rec)
            if not rec.difference:
                rec.confirmed = True

        # Check if balance check is complete
        self.check_balances_checked_ended()
        

    # Called from button on form view. 
    def confirm_balances(self):
        for rec in self.difference_checkbalance_ids:            
            # When physical_balance != BD_balance, it overwrite BD_balance with physical_balance
            rec.BD_balance = rec.physical_balance
            
            # Save the difference
            rec.saved_difference = rec.difference

            # Update balance for this currency in this desk in cashcount
            cashcount = self.env["forexmanager.cashcount"].search([
                ("desk_id", "=", rec.desk_id.id),
                ("currency_id", "=", rec.currency_id.id)
                ])
            cashcount.write({
                "balance": rec.physical_balance,
                })

            # Restarts the difference
            rec.difference = 0 # So it dissapears from view (page difference_checkbalance_ids)
            rec.confirmed = True

            # Check if balance check is complete
            self.check_balances_checked_ended()

    # Forces the create() method
    def launch_create(self):
        pass
   


    # @api.depends("checkbox_connect")
    # def _compute_desk_id(self):
    #     for rec in self:
    #         if rec.checkbox_connect:

    def create(self, vals):
        # Important:
        # First time the user opens session in a desk, he must complete the balance check.
        # Then, even with an open session, he can move to another desk (temporary desk) and login, but not check balance.
        # If he moves to a temporary desk, the opening desk balance will be assigned to this session.

        # Check if this is the first open session for this users (if not, then this is a temporary desk)
        open_session = self.env["forexmanager.worksession"].search([
                    ("user_id", "==", vals["user_id"]),
                    ("session_type", "=", "checkin"),
                    ("session_status", "=", "open")
                    ])
        if not open_session: # Means this is the opening desk for this user
            # First, lets check if somebody else is checked-in in this desk
            busy_desk = self.env["res.users"].search([
                    ("opening_desk_id", "==", vals["desk_id"])
                    ], limit=1)
            if busy_desk:
                raise ValidationError("Debes arquearte en otra ventanilla. Ya esta ventanilla tiene otro usuario arqueado.")

            # Assign opening desk to res.users.opening_desk
            user_rec = self.env["res.users"].browse(vals["user_id"])            
            user_rec.write({
                "opening_desk_id": vals["desk_id"]
                })
            

        # Check if there is already an open session for same user in the same desk_id
        user_in_desk = self.env["forexmanager.worksession"].search([
                    ("user_id", "=", vals["user_id"]),
                    ("desk_id", "=", vals["desk_id"]),
                    ("session_type", "=", "checkin"),
                    ("session_status", "=", "open")
                    ], limit=1)       
        
        if vals["session_type"] == "checkin":
            if user_in_desk:
                raise ValidationError("Ya tienes una sesión de inicio abierta en esta ventanilla")
            else:
                # Assign start_time
                vals["start_time"] = datetime.datetime.now()
                vals["opening_desk_id"] = self.env["res.users"].browse(vals["user_id"]).opening_desk_id.id
        
        elif vals["session_type"] == "checkout":
            if not vals["session_to_close"]:
                raise ValidationError("No se encontró una sesión de inicio abierta para cerrar.")
            else:                
                vals["start_time"] = user_in_desk.start_time
                vals["close_time"] = datetime.datetime.now()
                vals["opening_desk_id"] = user_in_desk.opening_desk_id.id
            
        worksession = super().create(vals)

        if worksession.session_type == "checkout" and worksession.session_to_close:
            # Close checkin session only if it's a secondary desk. If not, will be close in write() after confirming all currencies balances
            if user_in_desk.opening_desk_id != user_in_desk.desk_id:
                # Updating the opening session
                user_in_desk.write({
                        "closing_session": worksession.id,
                        "session_status": "closed",
                        "close_time": datetime.datetime.now()
                        })
                worksession.session_status = "closed"
                    


        return worksession


    def write(self, vals):
        for rec in self:

            worksession = super().write(vals)

            if rec.session_type == "checkout" and rec.session_to_close and rec.session_status == "open":                
                # If it's the opening_desk, this session and opening session are closed after confirm balances
                opening_session = self.env["forexmanager.worksession"].search([
                    ("user_id", "=", rec.user_id.id),
                    ("desk_id", "=", rec.desk_id.id),
                    ("session_type", "=", "checkin"),
                    ("session_status", "=", "open")
                    ], limit=1) 

                if rec.opening_desk_id == rec.desk_id:
                    if rec.balances_checked_ended:
                        # Close opening session
                        opening_session.closing_session = rec.id
                        opening_session.session_status = "closed"
                        opening_session.close_time = datetime.datetime.now()

                        # Reseting the opening_desk_id in res_users
                        self.env["res.users"].browse(rec.user_id.id).write({
                            "opening_desk_id": False
                            })

                        # Close this session (closing session)
                        rec.session_status = "closed"

                        # Close all the other open secundary sessions for this user
                        other_sessions = self.env["forexmanager.worksession"].search([
                            ("user_id", "=", rec.user_id.id),
                            ("session_status", "=", "open")
                            ])
                        for session in other_sessions:
                            session.session_status = "closed"
                            session.closing_session = rec.id
            

            return worksession

        


