from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TransferLine(models.Model):
    """A model for defyning the currencies and amounts when sending money between desks."""
    
    _name = "forexmanager.transfer.line"
    _description = "Crear nueva línea de traspaso"
    _inherit = "forexmanager.transfer.line.base"


    @api.onchange("currency_id", "amount", "opening_desk_id")
    def _onchange_get_amount_available(self):
        for rec in self:
            if rec.currency_id and rec.amount and rec.opening_desk_id:
                # Check (from opening_desk_id balance, even if user is in a secondary desk) 
                # if there is enough currency to deliver to client
                self.check_amount_available()

    @api.onchange("receiver_desk_id")
    def _onchange_get_destination_checked_in(self):
        for rec in self:
            if rec.receiver_desk_id:
                self.check_destination_checked_in()