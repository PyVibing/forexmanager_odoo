from odoo import fields, api, models
from odoo.exceptions import ValidationError
from ..utils import notification
import datetime


class TransferLineBase(models.AbstractModel):
    """A model for defyning the currencies and amounts when sending money between desks."""

    _name = "forexmanager.transfer.line.base"
    _description = "Línea de Traspaso"

    # MAIN FIELDS
    sender_desk_id = fields.Many2one("forexmanager.desk", string="Ventanilla de origen", required=True, 
                                     readonly=True, related="transfer_id.opening_desk_id")
    receiver_desk_id = fields.Many2one("forexmanager.desk", string="Ventanilla de destino", 
                                       domain="[('id', '!=', opening_desk_id)]", required=True)
    currency_id = fields.Many2one("forexmanager.currency", string="Divisa", required=True)
    amount = fields.Float(string="Cantidad", required=True)
    status_source = fields.Selection([
        ("cancelled", "Cancelado"),
        ("sent", "Enviado"),
        ], string="Estado/origen", readonly=True) # default="sent" in create()
    status_destination = fields.Selection([
        ("cancelled", "Cancelado"),
        ("pending", "Pendiente de recibir"),
        ("received", "Recibido")
        ], string="Estado/destino", readonly=True) # default="pending" in create()
    sent_by = fields.Many2one("res.users", related="transfer_id.user_id", store=True, string="Enviado por")
    sent_to = fields.Many2one("res.users", compute="_compute_sent_to", store=True, string="Enviado a")
    source_time = fields.Datetime(string="Hora")
    destination_time = fields.Datetime(string="Hora")

    # OTHER FIELDS
    transfer_id = fields.Many2one("forexmanager.transfer", string="Traspaso")
    opening_desk_id = fields.Many2one(related="transfer_id.opening_desk_id", string="Ventanilla de arqueo")
    accepted_currencies = fields.Many2many(related="opening_desk_id.workcenter_id.currency_ids") # For currency_id domain in form view
    amount_available = fields.Boolean(default=False)
    destination_checked_in = fields.Boolean(default=False) # To know if receiver_desk is already checked in


    @api.depends("receiver_desk_id")
    def _compute_sent_to(self):
        for rec in self:
            if rec.receiver_desk_id:
                sent_to = self.env["res.users"].search([
                    ("opening_desk_id", "=", rec.receiver_desk_id)
                    ], limit=1)
                rec.sent_to = sent_to if sent_to else False
            else:
                rec.sent_to = False

    def get_cashcount(self, desk):
        if desk == "sender":
            return self.env["forexmanager.cashcount"].search([
                        ("currency_id", "=", self.currency_id.id),
                        ("desk_id", "=", self.opening_desk_id.id)
                        ], limit=1)
        elif desk == "receiver":
            return self.env["forexmanager.cashcount"].search([
                        ("currency_id", "=", self.currency_id.id),
                        ("desk_id", "=", self.receiver_desk_id.id)
                        ], limit=1)
        else:
            raise ValidationError("Ocurrió un error inesperado. Consulte a su administrador de sistemas.")
    
    def check_amount_available(self):
        cashcount = self.get_cashcount("sender")
        self.amount_available = cashcount.balance >= self.amount if cashcount else False
        if not self.amount_available:
            notification(self, "No hay saldo disponible", 
                            "No tienes suficiente saldo de esta divisa en tu ventanilla de arqueo para realizar este traspaso.",
                            "warning")

    def check_destination_checked_in(self):          
        # Check if receiver desk has an open checkin worksession
        receiver_worksession_id = self.env["forexmanager.worksession"].search([
            ("opening_desk_id", "=", self.receiver_desk_id.id),
            ("desk_id", "=", self.receiver_desk_id.id),
            ("session_type", "=", "checkin"),
            ("session_status", "=", "open"),
            ("balances_checked_ended", "=", True)
            ], limit=1)
        self.destination_checked_in = True if receiver_worksession_id else False

        if not self.destination_checked_in:
            notification(self, "Ventanilla de destino sin sesión iniciada", 
                                f"La ventanilla {self.receiver_desk_id.name} no tiene una sesión de inicio abierta. No se puede realizar el traspaso.",
                                "warning")
            
    def update_balance_sender(self, operator):
        cashcount = self.get_cashcount("sender")
        current_balance = cashcount.balance

        if operator == "decrease":
            new_balance = current_balance - self.amount
            if new_balance < 0:
                raise ValidationError("Al realizar el envío, la cantidad en ventanilla de origen no puede quedar en negativo.")
        elif operator == "increase":
            new_balance = current_balance + self.amount
        else:
            raise ValidationError("Ocurrió un error inesperado. Consulte a su administrador de sistemas.")
        
        cashcount.write({
            "balance": new_balance
            })
    
    def update_balance_receiver(self, operator):
        cashcount = self.get_cashcount("receiver")
        current_balance = cashcount.balance

        if operator == "decrease":
            new_balance = current_balance - self.amount
            if new_balance < 0:
                raise ValidationError("Al realizar el envío, la cantidad en ventanilla de destino no puede quedar en negativo.")
        elif operator == "increase":
            new_balance = current_balance + self.amount
        else:
            raise ValidationError("Ocurrió un error inesperado. Consulte a su administrador de sistemas.")
        
        cashcount.write({
            "balance": new_balance
            })
    
    # Here vals comes as a list
    def create(self, vals_list):
        for vals in vals_list:
            vals["status_source"] = "sent"
            vals["source_time"] = datetime.datetime.now()
            vals["status_destination"] = "pending"

            transfer_line = super().create(vals)
        
        return transfer_line
    
    def write(self, vals):
        for rec in self:
            
            # Only field editable is receiver_desk_id
            if "receiver_desk_id" in vals and vals["receiver_desk_id"] != rec.receiver_desk_id.id: # Admin is changing receiver_desk_id
                transfer_line = super().write(vals)
                # Check if receiver_desk_id has an opening session
                rec.check_destination_checked_in()        
                if not rec.destination_checked_in:
                    raise ValidationError(f"La ventanilla {rec.receiver_desk_id.name} no tiene una sesión de inicio abierta. No se pudo redirigir el traspaso.")
                rec.status_destination = "pending"
                rec.destination_time = False
                rec.source_time = datetime.datetime.now()
                return transfer_line

            transfer_line = super().write(vals)
        
        return transfer_line
    
    # BUTTONS CALLS
    def cancel_transfer_source(self):
        if self.env.user.id != self.sent_by.id:
            raise ValidationError("No puedes cancelar un traspaso si no eres quien lo envió.")
        
        if self.status_destination == "pending" and self.status_source == "sent":
            self.update_balance_sender("increase")
            self.status_source = "cancelled"
            self.source_time = datetime.datetime.now()
            self.status_destination = "cancelled"
            notification(self, "Traspaso cancelado", "El traspaso se canceló correctamente. Se actualizó el saldo de la ventanilla de origen.",
                     "success")
        elif self.status_destination == "received":
            raise ValidationError("No puedes cancelar este traspaso. Ya fue recibido en la ventanilla de destino.")
        elif self.status_source == "cancelled":
            raise ValidationError("El traspaso ya ha sido cancelado con anterioridad. No puedes volver a cancelarlo.")

    def receive_transfer(self):
        if self.env.user.id != self.sent_to.id:
            raise ValidationError("No puedes recibir un traspaso si no eres el destinatario.")
        
        if self.status_destination == "pending" and self.status_source == "sent":
            self.update_balance_receiver("increase")
            self.status_destination = "received"
            self.destination_time = datetime.datetime.now()
            notification(self, "Traspaso recibido", "El traspaso se recibió correctamente. Se actualizó el saldo de la ventanilla de destino.",
                     "success")
        elif self.status_destination == "received":
            raise ValidationError("No puedes recibir nuevamente este traspaso. Ya fue recibido correctamente.")
        elif self.status_destination == "cancelled" and self.status_source != "cancelled":
            raise ValidationError("El traspaso está cancelado en ventanilla de destino. Ya no puedes recibirlo.")
        elif self.status_destination == "cancelled" and self.status_source == "cancelled":
            raise ValidationError("El traspaso está cancelado en ventanilla de origen y destino. Ya no puedes recibirlo.")
        
    def reject_transfer(self):
        if self.env.user.id != self.sent_to.id:
            raise ValidationError("No puedes rechazar un traspaso si no eres el destinatario.")
        
        if self.status_destination == "pending" and self.status_source == "sent":
            self.status_destination = "cancelled"
            self.destination_time = datetime.datetime.now()
            notification(self, "Traspaso rechazado", "El traspaso se rechazó correctamente.",
                     "success")
        elif self.status_destination == "received":
            raise ValidationError("No puedes rechazar este traspaso. Ya fue recibido correctamente.")
        elif self.status_destination == "cancelled" and self.status_source != "cancelled":
            raise ValidationError("El traspaso está cancelado en ventanilla de destino. No puedes volver a rechazarlo.")
        elif self.status_destination == "cancelled" and self.status_source == "cancelled":
            raise ValidationError("El traspaso está cancelado en ventanilla de origen y destino. Ya no puedes rechazarlo.")