from odoo import fields, api, models
from odoo.exceptions import ValidationError
from ..utils import notification
import datetime


class TransferBase(models.AbstractModel):
    """A model for send money between desks."""

    _name = "forexmanager.transfer.base"
    _description = "Traspaso"
    
    def _default_worksession_id(self):
        # Get current_desk_id for current user
        user_id = self.env.user
        current_desk_id = user_id.current_desk_id
        if not current_desk_id:
            raise ValidationError("No puedes traspasar dinero sin ventanilla de trabajo asociada.")
        
        worksession_id = self.env["forexmanager.worksession"].search([
            ("desk_id", "=", current_desk_id.id),
            ("user_id", "=", user_id.id),
            ("session_status", "=", "open"),
            ("session_type", "=", "checkin")
            ], limit=1)
        if not worksession_id:
            raise ValidationError("No puedes traspasar dinero sin una sesión de trabajo iniciada en esta ventanilla.")
        return worksession_id
    
    def _default_opening_desk_worksession_id(self):
        # Get opening_desk_id for current user
        user_id = self.env.user
        opening_desk_id = user_id.opening_desk_id
        
        opening_desk_worksession_id = self.env["forexmanager.worksession"].search([
            ("desk_id", "=", opening_desk_id.id),
            ("user_id", "=", user_id.id),
            ("session_status", "=", "open"),
            ("session_type", "=", "checkin")
            ], limit=1)
        if not opening_desk_worksession_id:
            raise ValidationError("No puedes traspasar dinero sin una sesión de trabajo iniciada en esta ventanilla.")
        return opening_desk_worksession_id

    # MAIN FIELDS
    # Readonly
    name = fields.Char(string="Nombre", default="Nuevo traspaso", readonly=True)
    user_id = fields.Many2one("res.users", string="Enviado por", default=lambda self: self.env.user.id, readonly=True)
    worksession_id = fields.Many2one("forexmanager.worksession", string="Sesión de trabajo", readonly=True)
    opening_desk_worksession_id = fields.Many2one("forexmanager.worksession", string="Sesión de trabajo de origen", readonly=True) # For controlling visibility in list view
    current_desk_id = fields.Many2one("forexmanager.desk", string="Ventanilla de trabajo", related="worksession_id.desk_id", store=True)
    opening_desk_id = fields.Many2one("forexmanager.desk", string="Ventanilla de origen", related="worksession_id.opening_desk_id", store=True)
    sent_time = fields.Datetime(string="Hora de envío", readonly=True)
    
    transfer_line_ids = fields.One2many("forexmanager.transfer.line", "transfer_id", string="Líneas de traspaso") # Required on create()
    user_transfer_line_ids = fields.One2many("forexmanager.transfer.line", "transfer_id", string="Líneas de traspaso", 
                                        compute='_compute_user_transfer_line_ids') # To show lines only to current user on transfer form view
    destination_users = fields.Many2many(
        "res.users",
        string="Usuarios destino",
        compute="_compute_destination_users",
        store=True
        )
    destination_worksessions = fields.Many2many(
        "forexmanager.worksession",
        string="Sesiones destino",
        compute="_compute_destination_worksessions",
        store=True
        )
    
    def action_open_my_transfers(self):
        # Calculate destination user worksession if it's open 
        destination_worksession_id = self.env["forexmanager.worksession"].search([
            ("user_id", "=", self.env.uid),
            ("session_status", "=", "open"),
            ("balances_checked_ended", "=", True)
            ], limit=1)
        
        # Calculate source user worksession when sender user is in secondary desk
        source_worksession_ids = self.env["forexmanager.worksession"].search([
            ("user_id", "=", self.env.uid),
            ("session_status", "=", "open")
            ])
        
        # Transfer is not allowed if user has not completed checkbalance in opening desk id
        if self.user_id.current_desk_id and self.user_id.opening_desk_id:
            source_worksession_id = self.env["forexmanager.worksession"].search([
            ("user_id", "=", self.env.uid),
            ("session_status", "=", "open"),
            ("session_type", "=", "checkin"),
            ("balances_checked_ended", "=", True)
            ], limit=1)
            if not source_worksession_id:
                raise ValidationError("No puedes traspasar dinero sin haber realizado el arqueo de entrada en tu ventanilla de arqueo.")
        
        # Shows transfers only sent during current session for sender user and every receiver users
        domain = [
            "|",
                "&",
                    ("user_id", "=", self.env.uid),
                    ("opening_desk_worksession_id", "in", source_worksession_ids.ids),
                "&",
                    ("destination_users", "in", [self.env.uid]),
                    ("destination_worksessions", "in", [destination_worksession_id.id]),
        ]

        return {
            "type": "ir.actions.act_window",
            "name": "Mis Traspasos",
            "res_model": "forexmanager.transfer",
            "views": [
                (self.env.ref("forexmanager.forexmanager_transfer_list_view").id, "list"),
                (self.env.ref("forexmanager.forexmanager_transfer_form_view").id, "form")
            ],
            "domain": domain,
            "context": {"default_user_view": True},
        }
    
    @api.depends("transfer_line_ids")
    def _compute_current_worksession(self):
        for rec in self:
            if self.env.user.id != rec.user_id.id: # Means current user is one of the receivers
                if rec.transfer_line_ids:
                    for line in rec.transfer_line_ids:
                        receiver_user = line.sent_to
                        if receiver_user.id == self.env.user.id:                          
                            rec.current_worksession = self.env["forexmanager.worksession"].search([
                                ("user_id", "=", receiver_user.id),
                                ("session_type", "=", "checkin"),
                                ("session_status", "=", "open"),
                                ("opening_desk_id", "=", rec.receiver_desk_id.id),
                                ("desk_id", "=", rec.receiver_desk_id.id)
                                ], limit=1)
                else:
                    rec.current_worksession = None
            else: # Means current user is the sender
                rec.current_worksession = self.env["forexmanager.worksession"].search([
                    ("user_id", "=", rec.user_id.id),
                    ("session_type", "=", "checkin"),
                    ("session_status", "=", "open"),
                    ("opening_desk_id", "=", rec.opening_desk_id.id),
                    ("desk_id", "=", rec.opening_desk_id.id)
                    ], limit=1) if rec.opening_desk_id else None        
    
    @api.depends('transfer_line_ids')
    def _compute_user_transfer_line_ids(self):
        # Only shows in transfer form view, the transfer_line_ids for destination user. 
        # So current user can't see transfer lines to other users
        uid = self.env.uid
        for rec in self:
            rec.user_transfer_line_ids = rec.transfer_line_ids.filtered(lambda l: l.sent_to.id == uid or l.sent_by.id == uid)

    @api.depends("transfer_line_ids.sent_to")
    def _compute_destination_users(self):
        for rec in self:
            users = rec.transfer_line_ids.mapped("sent_to")
            rec.destination_users = [(6, 0, users.ids)]

    @api.depends("destination_users")
    def _compute_destination_worksessions(self):
        for rec in self:
            worksession_ids = self.env["forexmanager.worksession"].search([
                ("session_type", "=", "checkin"),
                ("session_status", "=", "open"),
                ("balances_checked_ended", "=", True),
                ("user_id", "in", rec.destination_users.ids),
            ])
            
            rec.destination_worksessions = [(6, 0, worksession_ids.ids)]

    def create(self, vals):
        vals["sent_time"] = datetime.datetime.now()               
        transfer = super().create(vals)
        
        lines = vals.get("transfer_line_ids") 
        if not lines:
            raise ValidationError("Debe añadir al menos una divisa para traspasar.")
        
        # Check again amount_available and if destination desk has an opening session 
        for l in transfer.transfer_line_ids:
            l.check_amount_available()
            if not l.amount_available:
                raise ValidationError("No tienes suficiente saldo de esta divisa en tu ventanilla de arqueo para realizar este traspaso.")
            l.check_destination_checked_in()
            if not l.destination_checked_in:
                raise ValidationError(f"La ventanilla {self.receiver_desk_id.name} no tiene una sesión de inicio abierta. No se puede realizar el traspaso.")
            # Substract from opening_desk_id
            l.update_balance_sender("decrease") 

        notification(self, "Traspaso completado", "El traspaso se realizó correctamente. Se actualizaron los saldos correspondientes en ventanilla de origen.",
                     "success")

        return transfer
    






