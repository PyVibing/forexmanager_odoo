from odoo import fields, models, api
from .transfer_base import TransferBase


class TransferTransient(models.TransientModel):
    """A model for send money between desks from Operation model form view."""
    
    _name = "forexmanager.transfertransient"
    _description = "Traspaso (transient)"
    _inherit = "forexmanager.transfer.base"

    operation = fields.Many2one("forexmanager.operation", string="Operación")
    worksession_id = fields.Many2one("forexmanager.worksession", string="Sesión", default=lambda self: self._default_worksession_id(), store=True)
    opening_desk_worksession_id = fields.Many2one("forexmanager.worksession", string="Sesión", default=lambda self: self._default_opening_desk_worksession_id(), store=True)
    

    @api.onchange("transfer_line_ids")
    def _onchange_transfer_line_ids(self):
        for rec in self:
            # Deletes a line having a currency with no availability or with amount <= 0.00 or if destination desk is not checked in
            rec.transfer_line_ids = rec.transfer_line_ids.filtered(lambda l: l.amount_available)
            rec.transfer_line_ids = rec.transfer_line_ids.filtered(lambda l: l.destination_checked_in)
            rec.transfer_line_ids = rec.transfer_line_ids.filtered(lambda l: l.amount > 0)
