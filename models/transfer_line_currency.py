from odoo import fields, api, models
from odoo.exceptions import ValidationError
from ..utils import notification


class TransferBase(models.AbstractModel):
    _name = "forexmanager.transfer.line.currency"
    _description = "Monedas a traspasar a cada ventanilla"
    _inherit = "forexmanager.transfer.line.currency.base"

    # MAIN FIELDS
    
    # DELETE