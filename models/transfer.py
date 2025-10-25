from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Transfer(models.Model):
    """A model for send money between desks."""
    
    _name = "forexmanager.transfer"
    _description = "Crear nuevo traspaso"
    _inherit = "forexmanager.transfer.base"

    worksession_id = fields.Many2one("forexmanager.worksession", string="Sesión", default=lambda self: self._default_worksession_id(), store=True)
    opening_desk_worksession_id = fields.Many2one("forexmanager.worksession", string="Sesión", default=lambda self: self._default_opening_desk_worksession_id(), store=True)


    @api.onchange("transfer_line_ids")
    def _onchange_transfer_line_ids(self):
        for rec in self:
            # Avoid adding a line with no availability or in 0.00 or a line for sending to a desk not checked in
            rec.transfer_line_ids = rec.transfer_line_ids.filtered(lambda l: l.amount_available)
            rec.transfer_line_ids = rec.transfer_line_ids.filtered(lambda l: l.destination_checked_in)
            rec.transfer_line_ids = rec.transfer_line_ids.filtered(lambda l: l.amount > 0)
    


